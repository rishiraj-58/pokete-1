"""Battle recorder for capturing fight events"""

from __future__ import annotations
import time
import random
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from .replay_format import (
    ReplayFormat,
    ReplayVersion,
    ReplayEvent,
    ReplayEventType,
    ReplayMetadata,
    ProviderRecord,
    PokeStateRecord,
)
from .state_snapshot import StateSnapshot, PokeSnapshot, ProviderSnapshot

if TYPE_CHECKING:
    from ..poke import Poke
    from ..attack import Attack
    from ..fight.providers import Provider
    from ..items.invitem import InvItem


class BattleRecorder:
    """Records all battle events for replay"""

    def __init__(self, seed: Optional[int] = None):
        self._events: List[ReplayEvent] = []
        self._turn_number: int = 0
        self._start_time_ms: int = 0
        self._initial_state: List[ProviderRecord] = []
        self._providers: List[Provider] = []
        self._is_recording: bool = False
        self._random_seed: Optional[int] = seed
        self._battle_type: str = "wild"
        self._winner_index: Optional[int] = None
        self._state_snapshots: List[StateSnapshot] = []

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def turn_number(self) -> int:
        return self._turn_number

    @property
    def events(self) -> List[ReplayEvent]:
        return self._events.copy()

    def _current_time_ms(self) -> int:
        return int(time.time() * 1000) - self._start_time_ms

    def _create_poke_record(self, poke: Poke) -> PokeStateRecord:
        return PokeStateRecord(
            identifier=poke.identifier,
            name=poke.name,
            hp=poke.hp,
            max_hp=poke.full_hp,
            xp=poke.xp,
            level=poke.lvl(),
            attacks=list(poke.attacks),
            attack_aps=[atk.ap for atk in poke.attack_obs],
            effects=[eff.c_name for eff in poke.effects],
            shiny=poke.shiny,
        )

    def _create_provider_record(self, provider: Provider) -> ProviderRecord:
        provider_type = type(provider).__name__
        name = getattr(provider, "name", provider_type)
        return ProviderRecord(
            provider_type=provider_type,
            name=name,
            pokes=[self._create_poke_record(p) for p in provider.pokes],
            current_poke_index=provider.play_index,
            escapable=provider.escapable,
        )

    def _add_event(
        self,
        event_type: ReplayEventType,
        provider_index: int,
        data: Optional[Dict] = None,
    ) -> ReplayEvent:
        event = ReplayEvent(
            event_type=event_type,
            turn_number=self._turn_number,
            provider_index=provider_index,
            data=data or {},
            timestamp_ms=self._current_time_ms(),
        )
        self._events.append(event)
        return event

    def start_recording(
        self,
        providers: List[Provider],
        battle_type: str = "wild",
        seed: Optional[int] = None,
    ) -> None:
        """Start recording a battle"""
        if self._is_recording:
            raise RecordingError("Recording already in progress")

        self._is_recording = True
        self._start_time_ms = int(time.time() * 1000)
        self._turn_number = 0
        self._events = []
        self._providers = providers
        self._battle_type = battle_type
        self._random_seed = seed if seed is not None else self._random_seed
        self._winner_index = None
        self._state_snapshots = []

        # Capture initial state
        self._initial_state = [self._create_provider_record(p) for p in providers]

        # Record battle start
        self._add_event(
            ReplayEventType.BATTLE_START,
            provider_index=-1,
            data={"battle_type": battle_type, "seed": self._random_seed},
        )

        # Capture initial snapshot
        self._capture_snapshot(-1)

        logging.info("[BattleRecorder] Started recording battle")

    def stop_recording(self, winner_index: Optional[int] = None) -> ReplayFormat:
        """Stop recording and return the replay data"""
        if not self._is_recording:
            raise RecordingError("No recording in progress")

        self._winner_index = winner_index
        self._add_event(
            ReplayEventType.BATTLE_END,
            provider_index=winner_index if winner_index is not None else -1,
            data={"winner": winner_index},
        )

        # Final snapshot
        self._capture_snapshot(winner_index if winner_index is not None else -1)

        duration_ms = self._current_time_ms()
        metadata = ReplayMetadata(
            recorded_at=datetime.now().isoformat(),
            duration_ms=duration_ms,
            total_turns=self._turn_number,
            winner_index=winner_index,
            battle_type=self._battle_type,
            random_seed=self._random_seed,
        )

        replay = ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=self._initial_state,
            events=self._events,
        )

        self._is_recording = False
        logging.info(
            "[BattleRecorder] Stopped recording. Turns: %d, Events: %d",
            self._turn_number,
            len(self._events),
        )

        return replay

    def _capture_snapshot(self, active_index: int) -> StateSnapshot:
        """Capture current battle state"""
        snapshot = StateSnapshot.capture(
            self._turn_number,
            active_index,
            self._providers,
        )
        self._state_snapshots.append(snapshot)
        return snapshot

    def record_turn_start(self, active_provider_index: int) -> None:
        """Record start of a new turn"""
        if not self._is_recording:
            return

        self._turn_number += 1
        self._add_event(
            ReplayEventType.TURN_START,
            provider_index=active_provider_index,
            data={"turn": self._turn_number},
        )
        self._capture_snapshot(active_provider_index)

    def record_attack_chosen(
        self,
        provider_index: int,
        attack: Attack,
        target_provider_index: int,
    ) -> None:
        """Record attack choice"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.ATTACK_CHOSEN,
            provider_index=provider_index,
            data={
                "attack_index": attack.index,
                "attack_name": attack.name,
                "target": target_provider_index,
            },
        )

    def record_attack_executed(
        self,
        provider_index: int,
        attack: Attack,
        target_provider_index: int,
        damage: int,
        effectiveness: float,
        random_factor: float,
        attacker_hp_before: int,
        defender_hp_before: int,
        attacker_hp_after: int,
        defender_hp_after: int,
    ) -> None:
        """Record attack execution with all damage details"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.ATTACK_EXECUTED,
            provider_index=provider_index,
            data={
                "attack_index": attack.index,
                "attack_name": attack.name,
                "target": target_provider_index,
                "damage": damage,
                "eff": effectiveness,
                "rand_factor": random_factor,
                "attacker_hp_before": attacker_hp_before,
                "defender_hp_before": defender_hp_before,
                "attacker_hp_after": attacker_hp_after,
                "defender_hp_after": defender_hp_after,
            },
        )

    def record_item_used(
        self,
        provider_index: int,
        item: InvItem,
        target_poke_index: Optional[int] = None,
        result: str = "success",
    ) -> None:
        """Record item usage"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.ITEM_USED,
            provider_index=provider_index,
            data={
                "item_name": item.name,
                "item_func": item.func,
                "target_poke": target_poke_index,
                "result": result,
            },
        )

    def record_poke_switch(
        self,
        provider_index: int,
        from_poke_index: int,
        to_poke_index: int,
        reason: str = "manual",
    ) -> None:
        """Record poke switch"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.POKE_SWITCHED,
            provider_index=provider_index,
            data={
                "from_index": from_poke_index,
                "to_index": to_poke_index,
                "reason": reason,
            },
        )

    def record_run_attempt(
        self,
        provider_index: int,
        success: bool,
        roll: Optional[int] = None,
    ) -> None:
        """Record escape attempt"""
        if not self._is_recording:
            return

        event_type = (
            ReplayEventType.RUN_AWAY_SUCCESS
            if success
            else ReplayEventType.RUN_AWAY_FAILED
        )
        self._add_event(
            event_type,
            provider_index=provider_index,
            data={"success": success, "roll": roll},
        )

    def record_effect_applied(
        self,
        provider_index: int,
        poke_index: int,
        effect_name: str,
    ) -> None:
        """Record effect being applied"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.EFFECT_APPLIED,
            provider_index=provider_index,
            data={"poke_index": poke_index, "effect": effect_name},
        )

    def record_effect_removed(
        self,
        provider_index: int,
        poke_index: int,
        effect_name: str,
    ) -> None:
        """Record effect removal"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.EFFECT_REMOVED,
            provider_index=provider_index,
            data={"poke_index": poke_index, "effect": effect_name},
        )

    def record_hp_change(
        self,
        provider_index: int,
        poke_index: int,
        old_hp: int,
        new_hp: int,
        reason: str = "damage",
    ) -> None:
        """Record HP change"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.HP_CHANGED,
            provider_index=provider_index,
            data={
                "poke_index": poke_index,
                "old_hp": old_hp,
                "new_hp": new_hp,
                "delta": new_hp - old_hp,
                "reason": reason,
            },
        )

    def record_ap_change(
        self,
        provider_index: int,
        poke_index: int,
        attack_index: int,
        old_ap: int,
        new_ap: int,
    ) -> None:
        """Record AP change"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.AP_CHANGED,
            provider_index=provider_index,
            data={
                "poke_index": poke_index,
                "attack_index": attack_index,
                "old_ap": old_ap,
                "new_ap": new_ap,
            },
        )

    def record_poke_fainted(
        self,
        provider_index: int,
        poke_index: int,
    ) -> None:
        """Record poke fainting"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.POKE_FAINTED,
            provider_index=provider_index,
            data={"poke_index": poke_index},
        )
        self._capture_snapshot(provider_index)

    def record_xp_gained(
        self,
        provider_index: int,
        poke_index: int,
        xp_gained: int,
        new_total_xp: int,
    ) -> None:
        """Record XP gain"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.XP_GAINED,
            provider_index=provider_index,
            data={
                "poke_index": poke_index,
                "xp_gained": xp_gained,
                "new_total": new_total_xp,
            },
        )

    def record_level_up(
        self,
        provider_index: int,
        poke_index: int,
        old_level: int,
        new_level: int,
    ) -> None:
        """Record level up"""
        if not self._is_recording:
            return

        self._add_event(
            ReplayEventType.LEVEL_UP,
            provider_index=provider_index,
            data={
                "poke_index": poke_index,
                "old_level": old_level,
                "new_level": new_level,
            },
        )

    def record_catch_attempt(
        self,
        provider_index: int,
        target_provider_index: int,
        ball_name: str,
        success: bool,
        catch_chance: Optional[float] = None,
    ) -> None:
        """Record catch attempt"""
        if not self._is_recording:
            return

        event_type = (
            ReplayEventType.CATCH_SUCCESS if success else ReplayEventType.CATCH_FAILED
        )
        self._add_event(
            event_type,
            provider_index=provider_index,
            data={
                "target": target_provider_index,
                "ball": ball_name,
                "success": success,
                "chance": catch_chance,
            },
        )

    def record_state_snapshot(self, active_provider_index: int) -> None:
        """Manually record a state snapshot"""
        if not self._is_recording:
            return

        snapshot = self._capture_snapshot(active_provider_index)
        self._add_event(
            ReplayEventType.STATE_SNAPSHOT,
            provider_index=active_provider_index,
            data=snapshot.to_dict(),
        )

    def get_state_snapshots(self) -> List[StateSnapshot]:
        """Get all captured state snapshots"""
        return self._state_snapshots.copy()


class RecordingError(Exception):
    """Error during battle recording"""

    pass
