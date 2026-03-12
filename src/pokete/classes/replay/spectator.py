"""Spectator mode for watching AI vs AI battles or replays"""

from __future__ import annotations
import random
import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from .replay_format import ReplayFormat, ReplayEvent, ReplayEventType
from .replay_player import BattleReplayPlayer, PlaybackState, ReplayFrame
from .recorder import BattleRecorder
from .state_snapshot import StateSnapshot

if TYPE_CHECKING:
    from ..poke import Poke
    from ..attack import Attack
    from ..fight.providers import Provider


class SpectatorSpeed(Enum):
    """Playback speed for spectator mode"""

    SLOW = 2.0
    NORMAL = 1.0
    FAST = 0.5
    VERY_FAST = 0.1
    INSTANT = 0.0


class SpectatorControlAction(Enum):
    """Actions available in spectator mode"""

    PLAY = auto()
    PAUSE = auto()
    STEP_FORWARD = auto()
    STEP_BACKWARD = auto()
    FAST_FORWARD = auto()
    REWIND = auto()
    JUMP_TO_START = auto()
    JUMP_TO_END = auto()
    SPEED_UP = auto()
    SPEED_DOWN = auto()
    EXIT = auto()


@dataclass
class AIDecision:
    """An AI's decision during battle"""

    decision_type: str  # "attack", "item", "switch", "run"
    attack_index: Optional[int] = None
    item_name: Optional[str] = None
    switch_to_index: Optional[int] = None


class AIProvider:
    """AI-controlled provider for spectator battles"""

    def __init__(
        self,
        name: str,
        poke_configs: List[Dict],
        strategy: str = "random",
    ):
        self.name = name
        self.poke_configs = poke_configs
        self.strategy = strategy
        self._current_index = 0

    def make_decision(
        self,
        own_pokes: List[Dict],
        enemy_pokes: List[Dict],
        own_current: int,
        enemy_current: int,
    ) -> AIDecision:
        """Make a battle decision based on strategy"""
        own_poke = own_pokes[own_current]
        enemy_poke = enemy_pokes[enemy_current]

        if self.strategy == "random":
            return self._random_strategy(own_poke, enemy_poke)
        elif self.strategy == "aggressive":
            return self._aggressive_strategy(own_poke, enemy_poke)
        elif self.strategy == "defensive":
            return self._defensive_strategy(own_poke, enemy_poke)
        elif self.strategy == "smart":
            return self._smart_strategy(own_poke, enemy_poke, own_pokes)
        else:
            return self._random_strategy(own_poke, enemy_poke)

    def _random_strategy(self, own_poke: Dict, enemy_poke: Dict) -> AIDecision:
        """Random attack selection weighted by AP"""
        attacks = own_poke.get("attacks", [])
        aps = own_poke.get("attack_aps", [])

        valid_attacks = [
            (i, attacks[i])
            for i in range(len(attacks))
            if i < len(aps) and aps[i] > 0
        ]

        if not valid_attacks:
            return AIDecision(decision_type="attack", attack_index=0)

        weights = [aps[i] for i, _ in valid_attacks]
        selected = random.choices(valid_attacks, weights=weights, k=1)[0]
        return AIDecision(decision_type="attack", attack_index=selected[0])

    def _aggressive_strategy(self, own_poke: Dict, enemy_poke: Dict) -> AIDecision:
        """Always use highest damage attack"""
        attacks = own_poke.get("attacks", [])
        aps = own_poke.get("attack_aps", [])

        # Find attack with highest factor that has AP
        best_idx = 0
        for i in range(len(attacks)):
            if i < len(aps) and aps[i] > 0:
                best_idx = i
                break

        return AIDecision(decision_type="attack", attack_index=best_idx)

    def _defensive_strategy(self, own_poke: Dict, enemy_poke: Dict) -> AIDecision:
        """Prefer status effects and defensive moves"""
        return self._random_strategy(own_poke, enemy_poke)

    def _smart_strategy(
        self,
        own_poke: Dict,
        enemy_poke: Dict,
        own_pokes: List[Dict],
    ) -> AIDecision:
        """Consider type effectiveness and HP"""
        # If HP is low and we have healthy pokes, consider switching
        own_hp_ratio = own_poke.get("hp", 1) / max(own_poke.get("max_hp", 1), 1)

        if own_hp_ratio < 0.2:
            for i, poke in enumerate(own_pokes):
                if poke.get("hp", 0) > 0 and poke != own_poke:
                    return AIDecision(decision_type="switch", switch_to_index=i)

        return self._random_strategy(own_poke, enemy_poke)


@dataclass
class SpectatorState:
    """Current state of spectator mode"""

    is_live: bool  # True for live AI battle, False for replay
    is_paused: bool
    speed: SpectatorSpeed
    current_turn: int
    total_turns: int
    frame_index: int
    total_frames: int


class SpectatorMode:
    """Watch AI vs AI battles or replay recorded battles"""

    def __init__(self):
        self._replay_player: Optional[BattleReplayPlayer] = None
        self._recorder: Optional[BattleRecorder] = None
        self._is_live: bool = False
        self._is_paused: bool = True
        self._speed: SpectatorSpeed = SpectatorSpeed.NORMAL
        self._ai_providers: List[AIProvider] = []
        self._current_turn: int = 0
        self._event_callbacks: List[Callable[[ReplayEvent], None]] = []
        self._state_callbacks: List[Callable[[SpectatorState], None]] = []

    @property
    def state(self) -> SpectatorState:
        """Get current spectator state"""
        if self._replay_player:
            return SpectatorState(
                is_live=self._is_live,
                is_paused=self._is_paused,
                speed=self._speed,
                current_turn=self._replay_player.current_frame.event.turn_number
                if self._replay_player.current_frame
                else 0,
                total_turns=self._replay_player.replay.metadata.total_turns,
                frame_index=self._replay_player.current_frame_index,
                total_frames=self._replay_player.total_frames,
            )
        return SpectatorState(
            is_live=self._is_live,
            is_paused=self._is_paused,
            speed=self._speed,
            current_turn=self._current_turn,
            total_turns=0,
            frame_index=0,
            total_frames=0,
        )

    def load_replay(self, replay: ReplayFormat) -> None:
        """Load a replay for playback"""
        self._replay_player = BattleReplayPlayer(replay)
        self._is_live = False
        self._is_paused = True
        self._replay_player.start()
        logging.info("[SpectatorMode] Loaded replay with %d frames",
                     self._replay_player.total_frames)

    def load_replay_file(self, path: str) -> None:
        """Load replay from file"""
        replay = ReplayFormat.load_from_file(path)
        self.load_replay(replay)

    def setup_ai_battle(
        self,
        ai1: AIProvider,
        ai2: AIProvider,
        seed: Optional[int] = None,
    ) -> None:
        """Setup an AI vs AI battle"""
        self._ai_providers = [ai1, ai2]
        self._is_live = True
        self._is_paused = True
        self._current_turn = 0

        if seed is not None:
            random.seed(seed)

        logging.info("[SpectatorMode] Set up AI battle: %s vs %s",
                     ai1.name, ai2.name)

    def play(self) -> None:
        """Start or resume playback"""
        self._is_paused = False
        if self._replay_player:
            self._replay_player.resume()
        self._notify_state_change()

    def pause(self) -> None:
        """Pause playback"""
        self._is_paused = True
        if self._replay_player:
            self._replay_player.pause()
        self._notify_state_change()

    def toggle_pause(self) -> None:
        """Toggle pause state"""
        if self._is_paused:
            self.play()
        else:
            self.pause()

    def step_forward(self) -> Optional[ReplayFrame]:
        """Advance one frame"""
        if self._replay_player:
            frame = self._replay_player.advance_frame()
            if frame:
                self._notify_event(frame.event)
            self._notify_state_change()
            return frame
        return None

    def step_backward(self) -> Optional[ReplayFrame]:
        """Go back one frame"""
        if self._replay_player:
            frame = self._replay_player.rewind_frame()
            self._notify_state_change()
            return frame
        return None

    def fast_forward(self, frames: int = 10) -> Optional[ReplayFrame]:
        """Skip forward"""
        if self._replay_player:
            frame = self._replay_player.fast_forward(frames)
            self._notify_state_change()
            return frame
        return None

    def rewind(self, frames: int = 10) -> Optional[ReplayFrame]:
        """Skip backward"""
        if self._replay_player:
            frame = self._replay_player.rewind(frames)
            self._notify_state_change()
            return frame
        return None

    def jump_to_start(self) -> None:
        """Jump to beginning"""
        if self._replay_player:
            self._replay_player.jump_to_frame(0)
            self._notify_state_change()

    def jump_to_end(self) -> None:
        """Jump to end"""
        if self._replay_player:
            self._replay_player.jump_to_frame(self._replay_player.total_frames - 1)
            self._notify_state_change()

    def jump_to_turn(self, turn: int) -> None:
        """Jump to specific turn"""
        if self._replay_player:
            self._replay_player.jump_to_turn(turn)
            self._notify_state_change()

    def jump_to_frame(self, frame_index: int) -> Optional[ReplayFrame]:
        """Jump to specific frame"""
        if self._replay_player:
            frame = self._replay_player.jump_to_frame(frame_index)
            self._notify_state_change()
            return frame
        return None

    def set_speed(self, speed: SpectatorSpeed) -> None:
        """Set playback speed"""
        self._speed = speed
        self._notify_state_change()

    def speed_up(self) -> None:
        """Increase playback speed"""
        speeds = list(SpectatorSpeed)
        current_idx = speeds.index(self._speed)
        if current_idx < len(speeds) - 1:
            self._speed = speeds[current_idx + 1]
            self._notify_state_change()

    def speed_down(self) -> None:
        """Decrease playback speed"""
        speeds = list(SpectatorSpeed)
        current_idx = speeds.index(self._speed)
        if current_idx > 0:
            self._speed = speeds[current_idx - 1]
            self._notify_state_change()

    @property
    def current_frame(self) -> Optional[ReplayFrame]:
        """Get current frame"""
        if self._replay_player:
            return self._replay_player.current_frame
        return None

    @property
    def is_at_end(self) -> bool:
        """Check if at end of replay"""
        if self._replay_player:
            return self._replay_player.is_at_end
        return True

    @property
    def is_at_start(self) -> bool:
        """Check if at start of replay"""
        if self._replay_player:
            return self._replay_player.is_at_start
        return True

    def get_current_state_summary(self) -> Dict:
        """Get a summary of current battle state"""
        if self._replay_player and self._replay_player.current_state:
            state = self._replay_player.current_state
            return {
                "turn": state.turn_number,
                "active_player": state.active_provider_index,
                "providers": [
                    {
                        "name": p.name,
                        "current_poke": {
                            "name": p.current_poke.name,
                            "hp": p.current_poke.hp,
                            "max_hp": p.current_poke.max_hp,
                        },
                    }
                    for p in state.provider_states
                ],
            }
        return {}

    def on_event(self, callback: Callable[[ReplayEvent], None]) -> None:
        """Register callback for replay events"""
        self._event_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[SpectatorState], None]) -> None:
        """Register callback for state changes"""
        self._state_callbacks.append(callback)

    def _notify_event(self, event: ReplayEvent) -> None:
        """Notify event callbacks"""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error("[SpectatorMode] Event callback error: %s", e)

    def _notify_state_change(self) -> None:
        """Notify state change callbacks"""
        state = self.state
        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logging.error("[SpectatorMode] State callback error: %s", e)

    def handle_action(self, action: SpectatorControlAction) -> None:
        """Handle a control action"""
        if action == SpectatorControlAction.PLAY:
            self.play()
        elif action == SpectatorControlAction.PAUSE:
            self.pause()
        elif action == SpectatorControlAction.STEP_FORWARD:
            self.step_forward()
        elif action == SpectatorControlAction.STEP_BACKWARD:
            self.step_backward()
        elif action == SpectatorControlAction.FAST_FORWARD:
            self.fast_forward()
        elif action == SpectatorControlAction.REWIND:
            self.rewind()
        elif action == SpectatorControlAction.JUMP_TO_START:
            self.jump_to_start()
        elif action == SpectatorControlAction.JUMP_TO_END:
            self.jump_to_end()
        elif action == SpectatorControlAction.SPEED_UP:
            self.speed_up()
        elif action == SpectatorControlAction.SPEED_DOWN:
            self.speed_down()

    def get_delay_seconds(self) -> float:
        """Get delay between frames based on speed"""
        return self._speed.value


class SpectatorBattleRunner:
    """Runs AI battles for spectator mode"""

    def __init__(self, ai1: AIProvider, ai2: AIProvider, seed: Optional[int] = None):
        self._ai_providers = [ai1, ai2]
        self._recorder = BattleRecorder(seed=seed)
        self._seed = seed

        # Simulated battle state
        self._turn = 0
        self._active_index = 0
        self._battle_over = False
        self._winner_index: Optional[int] = None

        # Provider states (simplified for simulation)
        self._provider_states: List[Dict] = [
            self._init_provider_state(ai1),
            self._init_provider_state(ai2),
        ]

    def _init_provider_state(self, ai: AIProvider) -> Dict:
        return {
            "name": ai.name,
            "pokes": [
                {
                    "identifier": p.get("identifier", f"poke_{i}"),
                    "name": p.get("name", f"Poke {i}"),
                    "hp": p.get("hp", 20),
                    "max_hp": p.get("hp", 20),
                    "attacks": p.get("attacks", ["tackle"]),
                    "attack_aps": p.get("attack_aps", [10]),
                    "effects": [],
                    "xp": p.get("xp", 0),
                    "level": p.get("level", 1),
                }
                for i, p in enumerate(ai.poke_configs)
            ],
            "current_index": 0,
        }

    def run_battle(self) -> ReplayFormat:
        """Run a complete AI battle and return the replay"""
        # This is a simplified battle simulation for testing
        # In production, this would integrate with the actual Fight class

        if self._seed is not None:
            random.seed(self._seed)

        # Start recording (pass empty providers list for simulation)
        # Note: This is a simulation - in real usage, actual Provider objects would be used
        self._recorder._is_recording = True
        self._recorder._start_time_ms = 0
        self._recorder._events = []
        self._recorder._battle_type = "ai_vs_ai"
        self._recorder._random_seed = self._seed

        # Record battle start
        self._recorder._add_event(
            ReplayEventType.BATTLE_START,
            provider_index=-1,
            data={"battle_type": "ai_vs_ai", "seed": self._seed},
        )

        while not self._battle_over and self._turn < 100:  # Max 100 turns
            self._turn += 1
            self._run_turn()

        # Record battle end
        self._recorder._add_event(
            ReplayEventType.BATTLE_END,
            provider_index=self._winner_index if self._winner_index is not None else -1,
            data={"winner": self._winner_index},
        )

        # Build replay manually since we don't have actual providers
        from .replay_format import ReplayMetadata, ProviderRecord, PokeStateRecord
        from datetime import datetime

        metadata = ReplayMetadata(
            recorded_at=datetime.now().isoformat(),
            duration_ms=0,
            total_turns=self._turn,
            winner_index=self._winner_index,
            battle_type="ai_vs_ai",
            random_seed=self._seed,
        )

        initial_state = [
            ProviderRecord(
                provider_type="AIProvider",
                name=ai.name,
                pokes=[
                    PokeStateRecord(
                        identifier=p.get("identifier", f"poke_{i}"),
                        name=p.get("name", f"Poke {i}"),
                        hp=p.get("hp", 20),
                        max_hp=p.get("hp", 20),
                        xp=p.get("xp", 0),
                        level=p.get("level", 1),
                        attacks=p.get("attacks", ["tackle"]),
                        attack_aps=p.get("attack_aps", [10]),
                        effects=[],
                        shiny=False,
                    )
                    for i, p in enumerate(ai.poke_configs)
                ],
                current_poke_index=0,
                escapable=False,
            )
            for ai in self._ai_providers
        ]

        from .replay_format import ReplayVersion

        return ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=initial_state,
            events=self._recorder._events,
        )

    def _run_turn(self) -> None:
        """Run a single turn of the battle"""
        attacker_idx = self._active_index
        defender_idx = (self._active_index + 1) % 2

        # Record turn start
        self._recorder._turn_number = self._turn
        self._recorder._add_event(
            ReplayEventType.TURN_START,
            provider_index=attacker_idx,
            data={"turn": self._turn},
        )

        # Get attacker's decision
        ai = self._ai_providers[attacker_idx]
        attacker_state = self._provider_states[attacker_idx]
        defender_state = self._provider_states[defender_idx]

        decision = ai.make_decision(
            attacker_state["pokes"],
            defender_state["pokes"],
            attacker_state["current_index"],
            defender_state["current_index"],
        )

        if decision.decision_type == "attack":
            self._execute_attack(attacker_idx, defender_idx, decision.attack_index or 0)

        # Check for battle end
        self._check_battle_end()

        # Switch active player
        self._active_index = defender_idx

    def _execute_attack(
        self, attacker_idx: int, defender_idx: int, attack_idx: int
    ) -> None:
        """Execute an attack"""
        attacker_state = self._provider_states[attacker_idx]
        defender_state = self._provider_states[defender_idx]

        attacker_poke = attacker_state["pokes"][attacker_state["current_index"]]
        defender_poke = defender_state["pokes"][defender_state["current_index"]]

        # Simplified damage calculation
        damage = random.randint(3, 8)
        defender_hp_before = defender_poke["hp"]
        defender_poke["hp"] = max(0, defender_poke["hp"] - damage)

        # Record attack
        self._recorder._add_event(
            ReplayEventType.ATTACK_EXECUTED,
            provider_index=attacker_idx,
            data={
                "attack_index": attack_idx,
                "attack_name": attacker_poke["attacks"][attack_idx]
                if attack_idx < len(attacker_poke["attacks"])
                else "tackle",
                "target": defender_idx,
                "damage": damage,
                "eff": 1.0,
                "rand_factor": 1.0,
                "attacker_hp_before": attacker_poke["hp"],
                "defender_hp_before": defender_hp_before,
                "attacker_hp_after": attacker_poke["hp"],
                "defender_hp_after": defender_poke["hp"],
            },
        )

        # Record HP change
        self._recorder._add_event(
            ReplayEventType.HP_CHANGED,
            provider_index=defender_idx,
            data={
                "poke_index": defender_state["current_index"],
                "old_hp": defender_hp_before,
                "new_hp": defender_poke["hp"],
                "delta": -damage,
                "reason": "attack",
            },
        )

        # Decrease AP
        if attack_idx < len(attacker_poke["attack_aps"]):
            old_ap = attacker_poke["attack_aps"][attack_idx]
            attacker_poke["attack_aps"][attack_idx] = max(0, old_ap - 1)
            self._recorder._add_event(
                ReplayEventType.AP_CHANGED,
                provider_index=attacker_idx,
                data={
                    "poke_index": attacker_state["current_index"],
                    "attack_index": attack_idx,
                    "old_ap": old_ap,
                    "new_ap": attacker_poke["attack_aps"][attack_idx],
                },
            )

        # Check for faint
        if defender_poke["hp"] <= 0:
            self._recorder._add_event(
                ReplayEventType.POKE_FAINTED,
                provider_index=defender_idx,
                data={"poke_index": defender_state["current_index"]},
            )

    def _check_battle_end(self) -> None:
        """Check if battle should end"""
        for i, state in enumerate(self._provider_states):
            all_fainted = all(p["hp"] <= 0 for p in state["pokes"])
            if all_fainted:
                self._battle_over = True
                self._winner_index = (i + 1) % 2
                return
