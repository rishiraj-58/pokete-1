"""Spectator Mode - Watch AI battles or replay recorded battles"""

from __future__ import annotations
import time
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
from enum import Enum, auto

from .format import (
    ReplayFormat,
    ReplayFrame,
    FrameType,
    DecisionFrame,
    StateFrame,
    DecisionType,
    PokeSnapshot,
    ProviderSnapshot,
)
from .replay import BattleReplay


class PlaybackSpeed(Enum):
    SLOW = 2.0
    NORMAL = 1.0
    FAST = 0.5
    VERY_FAST = 0.25
    INSTANT = 0.0


class SpectatorCommand(Enum):
    ADVANCE = auto()
    REWIND = auto()
    FAST_FORWARD = auto()
    PAUSE = auto()
    RESUME = auto()
    SPEED_UP = auto()
    SPEED_DOWN = auto()
    QUIT = auto()
    SEEK_START = auto()
    SEEK_END = auto()


@dataclass
class SpectatorState:
    """Current state of spectator mode"""
    frame_index: int
    total_frames: int
    is_playing: bool
    is_finished: bool
    speed: PlaybackSpeed
    current_turn: int


class SpectatorMode:
    """Spectator mode for watching battles"""

    def __init__(
        self,
        replay: BattleReplay,
        on_frame: Optional[Callable[[ReplayFrame, SpectatorState], None]] = None,
        on_state_change: Optional[Callable[[StateFrame], None]] = None,
    ):
        self._replay = replay
        self._on_frame = on_frame
        self._on_state_change = on_state_change
        self._speed = PlaybackSpeed.NORMAL
        self._playing = False
        self._current_turn = 0
        self._command_queue: List[SpectatorCommand] = []

    @classmethod
    def from_file(
        cls,
        filepath: str,
        on_frame: Optional[Callable[[ReplayFrame, SpectatorState], None]] = None,
        on_state_change: Optional[Callable[[StateFrame], None]] = None,
    ) -> SpectatorMode:
        """Create spectator from replay file"""
        replay = BattleReplay.from_file(filepath)
        return cls(replay, on_frame, on_state_change)

    @property
    def state(self) -> SpectatorState:
        """Get current spectator state"""
        return SpectatorState(
            frame_index=self._replay.current_frame_index,
            total_frames=self._replay.total_frames,
            is_playing=self._playing,
            is_finished=self._replay.is_finished,
            speed=self._speed,
            current_turn=self._current_turn,
        )

    @property
    def replay(self) -> BattleReplay:
        return self._replay

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_finished(self) -> bool:
        return self._replay.is_finished

    def queue_command(self, command: SpectatorCommand):
        """Queue a command for processing"""
        self._command_queue.append(command)

    def _process_commands(self) -> bool:
        """Process queued commands, return True to continue playback"""
        while self._command_queue:
            cmd = self._command_queue.pop(0)
            if cmd == SpectatorCommand.QUIT:
                self._playing = False
                return False
            elif cmd == SpectatorCommand.PAUSE:
                self._playing = False
            elif cmd == SpectatorCommand.RESUME:
                self._playing = True
            elif cmd == SpectatorCommand.ADVANCE:
                self._advance_frame()
            elif cmd == SpectatorCommand.REWIND:
                self._rewind_frame()
            elif cmd == SpectatorCommand.FAST_FORWARD:
                self._fast_forward()
            elif cmd == SpectatorCommand.SPEED_UP:
                self._increase_speed()
            elif cmd == SpectatorCommand.SPEED_DOWN:
                self._decrease_speed()
            elif cmd == SpectatorCommand.SEEK_START:
                self._replay.reset()
                self._current_turn = 0
                if self._on_state_change:
                    self._on_state_change(self._replay.current_state)
            elif cmd == SpectatorCommand.SEEK_END:
                self._replay.seek(self._replay.total_frames)
                if self._on_state_change:
                    self._on_state_change(self._replay.current_state)
        return True

    def _advance_frame(self) -> Optional[ReplayFrame]:
        """Advance single frame"""
        frame = self._replay.advance()
        if frame:
            if frame.frame_type == FrameType.DECISION:
                self._current_turn = frame.data.turn
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                if self._on_state_change:
                    self._on_state_change(frame.data)
            if self._on_frame:
                self._on_frame(frame, self.state)
        return frame

    def _rewind_frame(self, count: int = 1) -> bool:
        """Rewind by frame count"""
        result = self._replay.rewind(count)
        if result and self._on_state_change:
            self._on_state_change(self._replay.current_state)
        return result

    def _fast_forward(self, frames: int = 5):
        """Fast forward by multiple frames"""
        for _ in range(frames):
            if self._replay.is_finished:
                break
            self._advance_frame()

    def _increase_speed(self):
        """Increase playback speed"""
        speeds = list(PlaybackSpeed)
        idx = speeds.index(self._speed)
        if idx < len(speeds) - 1:
            self._speed = speeds[idx + 1]

    def _decrease_speed(self):
        """Decrease playback speed"""
        speeds = list(PlaybackSpeed)
        idx = speeds.index(self._speed)
        if idx > 0:
            self._speed = speeds[idx - 1]

    def step(self) -> Optional[ReplayFrame]:
        """Step to next frame (manual advance)"""
        return self._advance_frame()

    def step_back(self) -> bool:
        """Step back one frame"""
        return self._rewind_frame(1)

    def play(self):
        """Start playback"""
        self._playing = True

    def pause(self):
        """Pause playback"""
        self._playing = False

    def toggle_play(self):
        """Toggle play/pause"""
        self._playing = not self._playing

    def reset(self):
        """Reset to beginning"""
        self._replay.reset()
        self._current_turn = 0
        self._playing = False
        if self._on_state_change:
            self._on_state_change(self._replay.current_state)

    def run_auto_playback(
        self,
        check_input: Optional[Callable[[], Optional[SpectatorCommand]]] = None,
    ):
        """Run automatic playback with optional input checking"""
        self._playing = True

        while not self._replay.is_finished:
            if not self._process_commands():
                break

            if check_input:
                cmd = check_input()
                if cmd:
                    self.queue_command(cmd)
                    continue

            if self._playing:
                frame = self._advance_frame()
                if frame and self._speed.value > 0:
                    time.sleep(self._speed.value)
            else:
                time.sleep(0.1)

        self._playing = False

    def get_frame_summary(self, frame: ReplayFrame) -> str:
        """Get human-readable summary of a frame"""
        if frame.frame_type == FrameType.DECISION:
            decision: DecisionFrame = frame.data
            provider_name = self._replay.metadata.provider_names[
                decision.provider_index
            ]
            action = ""
            if decision.decision_type == DecisionType.ATTACK:
                action = f"used attack '{decision.attack_index}'"
            elif decision.decision_type == DecisionType.ITEM:
                action = f"used item '{decision.item_name}'"
            elif decision.decision_type == DecisionType.RUN_AWAY:
                action = "tried to run away"
            elif decision.decision_type == DecisionType.CHOOSE_POKE:
                action = f"switched to poke #{decision.poke_index}"
            return f"Turn {decision.turn}: {provider_name} {action}"

        elif frame.frame_type == FrameType.STATE_SNAPSHOT:
            state: StateFrame = frame.data
            parts = []
            for i, prov in enumerate(state.providers):
                curr_poke = prov.pokes[prov.play_index]
                parts.append(
                    f"{prov.name}: {curr_poke.name} HP={curr_poke.hp}/{curr_poke.full_hp}"
                )
            return f"State at turn {state.turn}: " + " vs ".join(parts)

        return f"Frame type: {frame.frame_type.name}"

    def get_battle_summary(self) -> str:
        """Get summary of the entire battle"""
        meta = self._replay.metadata
        lines = [
            f"Battle: {' vs '.join(meta.provider_names)}",
            f"Type: {meta.battle_type}",
            f"Total turns: {meta.total_turns}",
            f"Recorded: {meta.timestamp}",
        ]
        if meta.winner_index is not None:
            lines.append(f"Winner: {meta.provider_names[meta.winner_index]}")
        return "\n".join(lines)


class AIBattleSpectator(SpectatorMode):
    """Specialized spectator for watching two AI providers battle"""

    def __init__(
        self,
        replay: BattleReplay,
        on_frame: Optional[Callable[[ReplayFrame, SpectatorState], None]] = None,
        on_state_change: Optional[Callable[[StateFrame], None]] = None,
        on_decision: Optional[Callable[[DecisionFrame, str], None]] = None,
    ):
        super().__init__(replay, on_frame, on_state_change)
        self._on_decision = on_decision

    def _advance_frame(self) -> Optional[ReplayFrame]:
        frame = super()._advance_frame()
        if frame and frame.frame_type == FrameType.DECISION:
            if self._on_decision:
                decision: DecisionFrame = frame.data
                provider_name = self._replay.metadata.provider_names[
                    decision.provider_index
                ]
                self._on_decision(decision, provider_name)
        return frame
