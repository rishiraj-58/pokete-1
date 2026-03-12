"""Battle Recorder - Records battles for replay"""

from __future__ import annotations
import random
from datetime import datetime
from typing import Callable, Any, Optional, List

from .format import (
    ReplayFormat,
    ReplayMetadata,
    ReplayVersion,
    ReplayFrame,
    FrameType,
    DecisionFrame,
    StateFrame,
    DecisionType,
    PokeSnapshot,
    ProviderSnapshot,
)


class RandomRecorder:
    """Intercepts random calls and records their values"""

    def __init__(self):
        self.recorded_values: List[float] = []
        self._original_random = random.random
        self._original_choice = random.choice
        self._original_choices = random.choices
        self._original_randint = random.randint
        self._active = False

    def start(self):
        """Start recording random values"""
        self.recorded_values = []
        self._active = True

    def stop(self) -> List[float]:
        """Stop recording and return recorded values"""
        self._active = False
        values = self.recorded_values.copy()
        self.recorded_values = []
        return values

    def record(self, value: float) -> float:
        """Record a random value"""
        if self._active:
            self.recorded_values.append(value)
        return value


class BattleRecorder:
    """Records battle decisions and state for replay"""

    def __init__(self):
        self._recording = False
        self._frames: List[ReplayFrame] = []
        self._initial_state: Optional[StateFrame] = None
        self._turn = 0
        self._providers: List[Any] = []
        self._battle_type = "unknown"
        self._random_recorder = RandomRecorder()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, providers: list, battle_type: str = "standard"):
        """Start recording a battle"""
        self._recording = True
        self._frames = []
        self._turn = 0
        self._providers = providers
        self._battle_type = battle_type
        self._initial_state = self._capture_state()

    def _capture_provider_snapshot(self, provider, index: int) -> ProviderSnapshot:
        """Capture snapshot of a provider"""
        provider_type = type(provider).__name__
        name = getattr(provider, 'name', f"Provider_{index}")

        pokes = []
        for poke in provider.pokes[:6]:
            pokes.append(PokeSnapshot.from_poke(poke))

        return ProviderSnapshot(
            provider_type=provider_type,
            name=name,
            play_index=provider.play_index,
            pokes=pokes,
            escapable=provider.escapable,
            xp_multiplier=provider.xp_multiplier,
        )

    def _capture_state(self) -> StateFrame:
        """Capture complete state snapshot"""
        providers = [
            self._capture_provider_snapshot(p, i)
            for i, p in enumerate(self._providers)
        ]
        return StateFrame(turn=self._turn, providers=providers)

    def record_decision(
        self,
        provider_index: int,
        decision_type: DecisionType,
        attack_index: Optional[str] = None,
        item_name: Optional[str] = None,
        poke_index: Optional[int] = None,
        random_values: Optional[List[float]] = None,
    ):
        """Record a battle decision"""
        if not self._recording:
            return

        frame = DecisionFrame(
            turn=self._turn,
            provider_index=provider_index,
            decision_type=decision_type,
            attack_index=attack_index,
            item_name=item_name,
            poke_index=poke_index,
            random_values=random_values or [],
        )
        self._frames.append(ReplayFrame(
            frame_type=FrameType.DECISION,
            data=frame,
        ))

    def record_state_snapshot(self):
        """Record a state snapshot (useful for keyframes)"""
        if not self._recording:
            return

        state = self._capture_state()
        self._frames.append(ReplayFrame(
            frame_type=FrameType.STATE_SNAPSHOT,
            data=state,
        ))

    def advance_turn(self):
        """Advance the turn counter"""
        self._turn += 1

    def start_random_recording(self):
        """Start recording random values for current decision"""
        self._random_recorder.start()

    def stop_random_recording(self) -> List[float]:
        """Stop recording random values and return them"""
        return self._random_recorder.stop()

    def stop_recording(self, winner_index: Optional[int] = None) -> ReplayFormat:
        """Stop recording and return the replay format"""
        if not self._recording:
            raise RuntimeError("Not currently recording")

        self._recording = False
        final_state = self._capture_state()

        metadata = ReplayMetadata(
            version=ReplayVersion.current(),
            timestamp=datetime.now().isoformat(),
            battle_type=self._battle_type,
            provider_names=[
                getattr(p, 'name', f"Provider_{i}")
                for i, p in enumerate(self._providers)
            ],
            winner_index=winner_index,
            total_turns=self._turn,
        )

        replay = ReplayFormat(
            metadata=metadata,
            initial_state=self._initial_state,
            frames=self._frames,
            final_state=final_state,
        )

        self._frames = []
        self._initial_state = None
        self._providers = []

        return replay

    def cancel_recording(self):
        """Cancel recording without producing a replay"""
        self._recording = False
        self._frames = []
        self._initial_state = None
        self._providers = []


# Global recorder instance for integration with fight system
_global_recorder: Optional[BattleRecorder] = None


def get_recorder() -> Optional[BattleRecorder]:
    """Get the global recorder instance"""
    return _global_recorder


def set_recorder(recorder: Optional[BattleRecorder]):
    """Set the global recorder instance"""
    global _global_recorder
    _global_recorder = recorder
