"""Battle Replay - Replays recorded battles"""

from __future__ import annotations
import random
from typing import Iterator, Any, Optional, List
from dataclasses import dataclass

from .format import (
    ReplayFormat,
    ReplayFrame,
    FrameType,
    DecisionFrame,
    StateFrame,
    DecisionType,
    PokeSnapshot,
    ProviderSnapshot,
    ReplayVersion,
    ReplayMigrator,
)


@dataclass
class ReplayState:
    """Current state during replay"""
    frame_index: int
    turn: int
    providers: List[ProviderSnapshot]
    finished: bool = False


class RandomReplayer:
    """Replays recorded random values"""

    def __init__(self):
        self._values: List[float] = []
        self._index = 0

    def set_values(self, values: List[float]):
        """Set values to replay"""
        self._values = values
        self._index = 0

    def next(self) -> float:
        """Get next random value"""
        if self._index < len(self._values):
            value = self._values[self._index]
            self._index += 1
            return value
        return random.random()

    def has_values(self) -> bool:
        return self._index < len(self._values)


class BattleReplay:
    """Replays a recorded battle frame by frame"""

    def __init__(self, replay: ReplayFormat):
        self._replay = replay
        self._frame_index = 0
        self._current_state: StateFrame = replay.initial_state
        self._random_replayer = RandomReplayer()
        self._finished = False

        valid, errors = replay.validate()
        if not valid:
            raise ValueError(f"Invalid replay: {errors}")

    @classmethod
    def from_file(cls, filepath: str) -> BattleReplay:
        """Load replay from file"""
        replay = ReplayFormat.load(filepath)
        return cls(replay)

    @classmethod
    def from_json(cls, json_str: str) -> BattleReplay:
        """Load replay from JSON string"""
        replay = ReplayFormat.from_json(json_str)
        return cls(replay)

    @property
    def metadata(self):
        return self._replay.metadata

    @property
    def total_frames(self) -> int:
        return len(self._replay.frames)

    @property
    def current_frame_index(self) -> int:
        return self._frame_index

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def current_state(self) -> StateFrame:
        return self._current_state

    def get_initial_state(self) -> StateFrame:
        """Get the initial battle state"""
        return self._replay.initial_state

    def get_final_state(self) -> Optional[StateFrame]:
        """Get the final battle state"""
        return self._replay.final_state

    def reset(self):
        """Reset replay to beginning"""
        self._frame_index = 0
        self._current_state = self._replay.initial_state
        self._finished = False

    def get_frame(self, index: int) -> Optional[ReplayFrame]:
        """Get frame at specific index"""
        if 0 <= index < len(self._replay.frames):
            return self._replay.frames[index]
        return None

    def current_frame(self) -> Optional[ReplayFrame]:
        """Get current frame"""
        return self.get_frame(self._frame_index)

    def advance(self) -> Optional[ReplayFrame]:
        """Advance to next frame and return it"""
        if self._frame_index >= len(self._replay.frames):
            self._finished = True
            return None

        frame = self._replay.frames[self._frame_index]
        self._frame_index += 1

        if frame.frame_type == FrameType.STATE_SNAPSHOT:
            self._current_state = frame.data

        if self._frame_index >= len(self._replay.frames):
            self._finished = True
            if self._replay.final_state:
                self._current_state = self._replay.final_state

        return frame

    def rewind(self, frames: int = 1) -> bool:
        """Rewind by specified number of frames"""
        target_index = max(0, self._frame_index - frames)

        self._frame_index = 0
        self._current_state = self._replay.initial_state
        self._finished = False

        while self._frame_index < target_index:
            frame = self._replay.frames[self._frame_index]
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                self._current_state = frame.data
            self._frame_index += 1

        return True

    def seek(self, frame_index: int) -> bool:
        """Seek to specific frame"""
        if frame_index < 0:
            frame_index = 0
        if frame_index > len(self._replay.frames):
            frame_index = len(self._replay.frames)

        if frame_index < self._frame_index:
            self._frame_index = 0
            self._current_state = self._replay.initial_state
            self._finished = False

        while self._frame_index < frame_index:
            frame = self._replay.frames[self._frame_index]
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                self._current_state = frame.data
            self._frame_index += 1

        self._finished = self._frame_index >= len(self._replay.frames)
        return True

    def get_decision_frames(self) -> List[DecisionFrame]:
        """Get all decision frames"""
        return [
            f.data for f in self._replay.frames
            if f.frame_type == FrameType.DECISION
        ]

    def get_provider_state(self, provider_index: int) -> Optional[ProviderSnapshot]:
        """Get current state for a specific provider"""
        if 0 <= provider_index < len(self._current_state.providers):
            return self._current_state.providers[provider_index]
        return None

    def get_poke_state(
        self, provider_index: int, poke_index: int
    ) -> Optional[PokeSnapshot]:
        """Get current state for a specific poke"""
        provider = self.get_provider_state(provider_index)
        if provider and 0 <= poke_index < len(provider.pokes):
            return provider.pokes[poke_index]
        return None

    def iter_frames(self) -> Iterator[ReplayFrame]:
        """Iterate through all frames from current position"""
        while not self._finished:
            frame = self.advance()
            if frame:
                yield frame

    def get_random_values(self) -> List[float]:
        """Get random values for current decision frame"""
        frame = self.current_frame()
        if frame and frame.frame_type == FrameType.DECISION:
            return frame.data.random_values
        return []

    def setup_random_replay(self):
        """Setup random replayer with current frame's values"""
        values = self.get_random_values()
        self._random_replayer.set_values(values)

    def next_random(self) -> float:
        """Get next random value from replay"""
        return self._random_replayer.next()


class ReplayValidator:
    """Validates replay integrity by comparing states"""

    @staticmethod
    def compare_poke_states(
        expected: PokeSnapshot, actual: PokeSnapshot
    ) -> List[str]:
        """Compare two poke states and return differences"""
        diffs = []
        if expected.hp != actual.hp:
            diffs.append(f"HP mismatch: expected {expected.hp}, got {actual.hp}")
        if expected.attack_aps != actual.attack_aps:
            diffs.append(
                f"AP mismatch: expected {expected.attack_aps}, "
                f"got {actual.attack_aps}"
            )
        if expected.effects != actual.effects:
            diffs.append(
                f"Effects mismatch: expected {expected.effects}, "
                f"got {actual.effects}"
            )
        return diffs

    @staticmethod
    def compare_provider_states(
        expected: ProviderSnapshot, actual: ProviderSnapshot
    ) -> List[str]:
        """Compare two provider states"""
        diffs = []
        if expected.play_index != actual.play_index:
            diffs.append(
                f"Play index mismatch: expected {expected.play_index}, "
                f"got {actual.play_index}"
            )
        for i, (exp_poke, act_poke) in enumerate(
            zip(expected.pokes, actual.pokes)
        ):
            poke_diffs = ReplayValidator.compare_poke_states(exp_poke, act_poke)
            for diff in poke_diffs:
                diffs.append(f"Poke {i}: {diff}")
        return diffs

    @staticmethod
    def compare_states(
        expected: StateFrame, actual: StateFrame
    ) -> List[str]:
        """Compare two state frames"""
        diffs = []
        for i, (exp_prov, act_prov) in enumerate(
            zip(expected.providers, actual.providers)
        ):
            prov_diffs = ReplayValidator.compare_provider_states(
                exp_prov, act_prov
            )
            for diff in prov_diffs:
                diffs.append(f"Provider {i}: {diff}")
        return diffs
