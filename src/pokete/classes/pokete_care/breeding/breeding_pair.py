"""Breeding pair tracking."""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pokete.classes.poke import Poke

from .egg_generator import EggPokete
from .models import BreedingPairDict


@dataclass
class BreedingPair:
    """Represents a pair of poketes that are breeding."""
    parent1: Optional["Poke"]
    parent2: Optional["Poke"]
    start_time: int
    hatch_time: int
    egg: Optional[EggPokete]
    is_ready: bool = False

    def is_complete(self) -> bool:
        """Returns True if the breeding pair has both parents."""
        return self.parent1 is not None and self.parent2 is not None

    def is_egg_ready(self, current_time: int) -> bool:
        """Checks if the egg is ready to be collected."""
        if self.egg is None:
            return False
        return self.egg.is_ready_to_hatch(current_time)

    def get_remaining_time(self, current_time: int) -> int:
        """Returns the remaining time until the egg is ready."""
        if self.egg is None:
            return self.hatch_time
        remaining = (self.egg.created_at + self.egg.hatch_time) - current_time
        return max(0, remaining)

    def dict(self) -> BreedingPairDict:
        """Serializes the breeding pair to a dictionary."""
        return {
            "parent1": self.parent1.dict() if self.parent1 else None,
            "parent2": self.parent2.dict() if self.parent2 else None,
            "start_time": self.start_time,
            "hatch_time": self.hatch_time,
            "egg": self.egg.dict() if self.egg else None,
            "is_ready": self.is_ready,
        }

    @classmethod
    def from_dict(cls, data: BreedingPairDict) -> "BreedingPair":
        """Deserializes a breeding pair from a dictionary."""
        from pokete.classes.poke import Poke

        parent1 = Poke.from_dict(data["parent1"]) if data.get("parent1") else None
        parent2 = Poke.from_dict(data["parent2"]) if data.get("parent2") else None
        egg = EggPokete.from_dict(data["egg"]) if data.get("egg") else None

        return cls(
            parent1=parent1,
            parent2=parent2,
            start_time=data.get("start_time", 0),
            hatch_time=data.get("hatch_time", 0),
            egg=egg,
            is_ready=data.get("is_ready", False),
        )

    @classmethod
    def create_empty(cls) -> "BreedingPair":
        """Creates an empty breeding pair."""
        return cls(
            parent1=None,
            parent2=None,
            start_time=0,
            hatch_time=0,
            egg=None,
            is_ready=False,
        )
