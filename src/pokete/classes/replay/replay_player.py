"""Battle replay player for read-only playback"""

from __future__ import annotations
import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

from .replay_format import (
    ReplayFormat,
    ReplayEvent,
    ReplayEventType,
    ReplayVersion,
    ReplayLoadError,
    ReplayVersionError,
    ProviderRecord,
    PokeStateRecord,
)
from .state_snapshot import StateSnapshot, PokeSnapshot, ProviderSnapshot


class PlaybackState(Enum):
    """State of the replay player"""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()


@dataclass
class ReplayFrame:
    """A single frame in the replay"""

    frame_index: int
    event: ReplayEvent
    state_before: Optional[ReplayPlayerState]
    state_after: ReplayPlayerState
    description: str


@dataclass
class ReplayPlayerState:
    """Current state during replay playback"""

    turn_number: int
    active_provider_index: int
    provider_states: List[ProviderPlaybackState]

    def to_snapshot(self) -> Dict:
        return {
            "turn": self.turn_number,
            "active": self.active_provider_index,
            "providers": [p.to_dict() for p in self.provider_states],
        }


@dataclass
class PokePlaybackState:
    """Poke state during playback"""

    identifier: str
    name: str
    hp: int
    max_hp: int
    attacks: List[str]
    attack_aps: List[int]
    effects: List[str]
    xp: int
    level: int

    @classmethod
    def from_record(cls, record: PokeStateRecord) -> PokePlaybackState:
        return cls(
            identifier=record.identifier,
            name=record.name,
            hp=record.hp,
            max_hp=record.max_hp,
            attacks=list(record.attacks),
            attack_aps=list(record.attack_aps),
            effects=list(record.effects),
            xp=record.xp,
            level=record.level,
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.identifier,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attacks": self.attacks,
            "aps": self.attack_aps,
            "effects": self.effects,
            "xp": self.xp,
            "level": self.level,
        }


@dataclass
class ProviderPlaybackState:
    """Provider state during playback"""

    name: str
    provider_type: str
    pokes: List[PokePlaybackState]
    current_index: int

    @classmethod
    def from_record(cls, record: ProviderRecord) -> ProviderPlaybackState:
        return cls(
            name=record.name,
            provider_type=record.provider_type,
            pokes=[PokePlaybackState.from_record(p) for p in record.pokes],
            current_index=record.current_poke_index,
        )

    @property
    def current_poke(self) -> PokePlaybackState:
        return self.pokes[self.current_index]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.provider_type,
            "pokes": [p.to_dict() for p in self.pokes],
            "current_index": self.current_index,
        }


class BattleReplayPlayer:
    """Plays back recorded battles frame by frame"""

    def __init__(self, replay: ReplayFormat):
        self._replay = replay
        self._validate_replay()

        self._frame_index: int = -1
        self._playback_state = PlaybackState.STOPPED
        self._frames: List[ReplayFrame] = []
        self._current_state: Optional[ReplayPlayerState] = None
        self._event_handlers: Dict[ReplayEventType, List[Callable]] = {}

        self._build_frames()

    def _validate_replay(self) -> None:
        """Validate replay before playback"""
        current_version = ReplayVersion.current()
        if not self._replay.version.is_compatible(current_version):
            raise ReplayVersionError(
                f"Incompatible replay version: {self._replay.version}, "
                f"current: {current_version}"
            )

        issues = self._replay.validate()
        if issues:
            logging.warning("[ReplayPlayer] Replay validation issues: %s", issues)

    def _build_frames(self) -> None:
        """Build all frames from events"""
        self._frames = []

        # Initialize state from initial_state
        self._current_state = ReplayPlayerState(
            turn_number=0,
            active_provider_index=-1,
            provider_states=[
                ProviderPlaybackState.from_record(p)
                for p in self._replay.initial_state
            ],
        )

        for i, event in enumerate(self._replay.events):
            state_before = self._clone_state(self._current_state)
            self._apply_event(event)
            state_after = self._clone_state(self._current_state)

            frame = ReplayFrame(
                frame_index=i,
                event=event,
                state_before=state_before,
                state_after=state_after,
                description=self._describe_event(event),
            )
            self._frames.append(frame)

    def _clone_state(self, state: ReplayPlayerState) -> ReplayPlayerState:
        """Deep clone the current state"""
        return ReplayPlayerState(
            turn_number=state.turn_number,
            active_provider_index=state.active_provider_index,
            provider_states=[
                ProviderPlaybackState(
                    name=p.name,
                    provider_type=p.provider_type,
                    pokes=[
                        PokePlaybackState(
                            identifier=pk.identifier,
                            name=pk.name,
                            hp=pk.hp,
                            max_hp=pk.max_hp,
                            attacks=list(pk.attacks),
                            attack_aps=list(pk.attack_aps),
                            effects=list(pk.effects),
                            xp=pk.xp,
                            level=pk.level,
                        )
                        for pk in p.pokes
                    ],
                    current_index=p.current_index,
                )
                for p in state.provider_states
            ],
        )

    def _apply_event(self, event: ReplayEvent) -> None:
        """Apply an event to update current state"""
        if self._current_state is None:
            return

        event_type = event.event_type

        if event_type == ReplayEventType.TURN_START:
            self._current_state.turn_number = event.data.get(
                "turn", self._current_state.turn_number + 1
            )
            self._current_state.active_provider_index = event.provider_index

        elif event_type == ReplayEventType.HP_CHANGED:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            new_hp = event.data.get("new_hp", 0)
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    prov.pokes[poke_idx].hp = new_hp

        elif event_type == ReplayEventType.AP_CHANGED:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            attack_idx = event.data.get("attack_index", 0)
            new_ap = event.data.get("new_ap", 0)
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    poke = prov.pokes[poke_idx]
                    if attack_idx < len(poke.attack_aps):
                        poke.attack_aps[attack_idx] = new_ap

        elif event_type == ReplayEventType.POKE_SWITCHED:
            prov_idx = event.provider_index
            to_idx = event.data.get("to_index", 0)
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                self._current_state.provider_states[prov_idx].current_index = to_idx

        elif event_type == ReplayEventType.EFFECT_APPLIED:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            effect = event.data.get("effect", "")
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    if effect not in prov.pokes[poke_idx].effects:
                        prov.pokes[poke_idx].effects.append(effect)

        elif event_type == ReplayEventType.EFFECT_REMOVED:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            effect = event.data.get("effect", "")
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    if effect in prov.pokes[poke_idx].effects:
                        prov.pokes[poke_idx].effects.remove(effect)

        elif event_type == ReplayEventType.XP_GAINED:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            new_xp = event.data.get("new_total", 0)
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    prov.pokes[poke_idx].xp = new_xp

        elif event_type == ReplayEventType.LEVEL_UP:
            prov_idx = event.provider_index
            poke_idx = event.data.get("poke_index", 0)
            new_level = event.data.get("new_level", 0)
            if prov_idx >= 0 and prov_idx < len(
                self._current_state.provider_states
            ):
                prov = self._current_state.provider_states[prov_idx]
                if poke_idx < len(prov.pokes):
                    prov.pokes[poke_idx].level = new_level

    def _describe_event(self, event: ReplayEvent) -> str:
        """Generate human-readable description of event"""
        prov_name = "Unknown"
        if 0 <= event.provider_index < len(self._replay.initial_state):
            prov_name = self._replay.initial_state[event.provider_index].name

        event_type = event.event_type

        if event_type == ReplayEventType.BATTLE_START:
            return "Battle started"
        elif event_type == ReplayEventType.BATTLE_END:
            winner = event.data.get("winner")
            if winner is not None and 0 <= winner < len(
                self._replay.initial_state
            ):
                winner_name = self._replay.initial_state[winner].name
                return "Battle ended - {} wins!".format(winner_name)
            return "Battle ended"
        elif event_type == ReplayEventType.TURN_START:
            return "Turn {} - {}'s turn".format(event.data.get('turn', '?'), prov_name)
        elif event_type == ReplayEventType.ATTACK_CHOSEN:
            return "{} chose {}".format(prov_name, event.data.get('attack_name', 'attack'))
        elif event_type == ReplayEventType.ATTACK_EXECUTED:
            dmg = event.data.get("damage", 0)
            atk = event.data.get("attack_name", "attack")
            return "{} used {}! ({} damage)".format(prov_name, atk, dmg)
        elif event_type == ReplayEventType.ITEM_USED:
            return "{} used {}".format(prov_name, event.data.get('item_name', 'item'))
        elif event_type == ReplayEventType.POKE_SWITCHED:
            return "{} switched Pokete".format(prov_name)
        elif event_type == ReplayEventType.RUN_AWAY_SUCCESS:
            return "{} ran away!".format(prov_name)
        elif event_type == ReplayEventType.RUN_AWAY_FAILED:
            return "{} failed to run away".format(prov_name)
        elif event_type == ReplayEventType.EFFECT_APPLIED:
            return "{} applied".format(event.data.get('effect', 'Effect'))
        elif event_type == ReplayEventType.EFFECT_REMOVED:
            return "{} removed".format(event.data.get('effect', 'Effect'))
        elif event_type == ReplayEventType.HP_CHANGED:
            delta = event.data.get("delta", 0)
            return "HP changed by {}".format(delta)
        elif event_type == ReplayEventType.POKE_FAINTED:
            return "A Pokete fainted!"
        elif event_type == ReplayEventType.XP_GAINED:
            xp = event.data.get("xp_gained", 0)
            return "Gained {} XP".format(xp)
        elif event_type == ReplayEventType.LEVEL_UP:
            lvl = event.data.get("new_level", 0)
            return "Level up! Now level {}".format(lvl)
        elif event_type == ReplayEventType.CATCH_SUCCESS:
            return "Caught the Pokete!"
        elif event_type == ReplayEventType.CATCH_FAILED:
            return "Failed to catch"
        else:
            return "Event: {}".format(event.event_type.name)

    @property
    def replay(self) -> ReplayFormat:
        return self._replay

    @property
    def state(self) -> PlaybackState:
        return self._playback_state

    @property
    def current_frame_index(self) -> int:
        return self._frame_index

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    @property
    def current_frame(self) -> Optional[ReplayFrame]:
        if 0 <= self._frame_index < len(self._frames):
            return self._frames[self._frame_index]
        return None

    @property
    def current_state(self) -> Optional[ReplayPlayerState]:
        if self._frame_index < 0:
            # Return initial state
            return ReplayPlayerState(
                turn_number=0,
                active_provider_index=-1,
                provider_states=[
                    ProviderPlaybackState.from_record(p)
                    for p in self._replay.initial_state
                ],
            )
        if self._frame_index < len(self._frames):
            return self._frames[self._frame_index].state_after
        return None

    @property
    def is_at_start(self) -> bool:
        return self._frame_index <= 0

    @property
    def is_at_end(self) -> bool:
        return self._frame_index >= len(self._frames) - 1

    def start(self) -> None:
        """Start playback from beginning"""
        self._frame_index = -1
        self._playback_state = PlaybackState.PLAYING

    def stop(self) -> None:
        """Stop playback"""
        self._playback_state = PlaybackState.STOPPED

    def pause(self) -> None:
        """Pause playback"""
        if self._playback_state == PlaybackState.PLAYING:
            self._playback_state = PlaybackState.PAUSED

    def resume(self) -> None:
        """Resume playback"""
        if self._playback_state == PlaybackState.PAUSED:
            self._playback_state = PlaybackState.PLAYING

    def advance_frame(self) -> Optional[ReplayFrame]:
        """Advance to next frame, returns the frame or None if at end"""
        if self._frame_index >= len(self._frames) - 1:
            self._playback_state = PlaybackState.FINISHED
            return None

        self._frame_index += 1
        frame = self._frames[self._frame_index]
        self._trigger_handlers(frame.event)
        return frame

    def rewind_frame(self) -> Optional[ReplayFrame]:
        """Go back one frame, returns the frame or None if at start"""
        if self._frame_index <= 0:
            return None

        self._frame_index -= 1
        return self._frames[self._frame_index]

    def jump_to_frame(self, frame_index: int) -> Optional[ReplayFrame]:
        """Jump to specific frame"""
        if frame_index < 0:
            frame_index = 0
        if frame_index >= len(self._frames):
            frame_index = len(self._frames) - 1

        self._frame_index = frame_index
        return self._frames[self._frame_index] if self._frames else None

    def jump_to_turn(self, turn_number: int) -> Optional[ReplayFrame]:
        """Jump to the start of a specific turn"""
        for i, frame in enumerate(self._frames):
            if (
                frame.event.event_type == ReplayEventType.TURN_START
                and frame.event.data.get("turn", 0) == turn_number
            ):
                return self.jump_to_frame(i)
        return None

    def fast_forward(self, frames: int = 10) -> Optional[ReplayFrame]:
        """Skip forward multiple frames"""
        target = min(self._frame_index + frames, len(self._frames) - 1)
        return self.jump_to_frame(target)

    def rewind(self, frames: int = 10) -> Optional[ReplayFrame]:
        """Skip backward multiple frames"""
        target = max(self._frame_index - frames, 0)
        return self.jump_to_frame(target)

    def register_handler(
        self,
        event_type: ReplayEventType,
        handler: Callable[[ReplayEvent], None],
    ) -> None:
        """Register a handler for specific event types"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def _trigger_handlers(self, event: ReplayEvent) -> None:
        """Trigger registered handlers for an event"""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logging.error("[ReplayPlayer] Handler error: %s", e)

    def get_events_in_turn(self, turn_number: int) -> List[ReplayEvent]:
        """Get all events in a specific turn"""
        return [
            frame.event
            for frame in self._frames
            if frame.event.turn_number == turn_number
        ]

    def get_hp_history(self, provider_index: int, poke_index: int = 0) -> List[int]:
        """Get HP history for a specific poke"""
        hp_values = []
        for frame in self._frames:
            if frame.state_after and provider_index < len(
                frame.state_after.provider_states
            ):
                prov = frame.state_after.provider_states[provider_index]
                if poke_index < len(prov.pokes):
                    hp_values.append(prov.pokes[poke_index].hp)
        return hp_values

    def verify_state(self, expected_state: StateSnapshot) -> List[str]:
        """Verify current state matches expected state"""
        if self.current_state is None:
            return ["No current state"]

        differences = []
        current = self.current_state

        if current.turn_number != expected_state.turn_number:
            differences.append(
                f"Turn mismatch: {current.turn_number} vs {expected_state.turn_number}"
            )

        for i, (curr_prov, exp_prov) in enumerate(
            zip(current.provider_states, expected_state.providers)
        ):
            if curr_prov.current_index != exp_prov.current_index:
                differences.append(
                    f"Provider {i} current index: {curr_prov.current_index} vs {exp_prov.current_index}"
                )

            for j, (curr_poke, exp_poke) in enumerate(
                zip(curr_prov.pokes, exp_prov.pokes)
            ):
                if curr_poke.hp != exp_poke.hp:
                    differences.append(
                        f"Provider {i} Poke {j} HP: {curr_poke.hp} vs {exp_poke.hp}"
                    )
                if tuple(curr_poke.attack_aps) != exp_poke.attack_aps:
                    differences.append(
                        f"Provider {i} Poke {j} APs: {curr_poke.attack_aps} vs {list(exp_poke.attack_aps)}"
                    )

        return differences
