"""Breeding system for the Pokete Care facility.

Allows compatible poketes (sharing at least one type) to breed and produce
eggs that hatch after a certain time. Stats of the offspring are computed
as weighted averages of the parents' base stats.
"""

import random
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from ..asset_service.service import asset_service
from ..poke import Poke
from ..poke.nature import PokeNature
from ..poke.stats import Stats


class BreedingPairDict(TypedDict):
    """Serialization format for a breeding pair."""
    parent1: dict | None
    parent2: dict | None
    start_time: int
    egg_ready: bool
    egg: dict | None


class EggDict(TypedDict):
    """Serialization format for an egg."""
    identifier: str
    hp: int
    atc: int
    defense: int
    initiative: int
    hatch_time: int
    parent1_identifier: str
    parent2_identifier: str


@dataclass
class EggData:
    """Holds computed egg data before it becomes a full Poke."""
    identifier: str
    hp: int
    atc: int
    defense: int
    initiative: int
    hatch_time: int
    parent1_identifier: str
    parent2_identifier: str

    def dict(self) -> EggDict:
        return {
            "identifier": self.identifier,
            "hp": self.hp,
            "atc": self.atc,
            "defense": self.defense,
            "initiative": self.initiative,
            "hatch_time": self.hatch_time,
            "parent1_identifier": self.parent1_identifier,
            "parent2_identifier": self.parent2_identifier,
        }

    @classmethod
    def from_dict(cls, data: EggDict) -> "EggData":
        return cls(
            identifier=data["identifier"],
            hp=data["hp"],
            atc=data["atc"],
            defense=data["defense"],
            initiative=data["initiative"],
            hatch_time=data["hatch_time"],
            parent1_identifier=data["parent1_identifier"],
            parent2_identifier=data["parent2_identifier"],
        )


# Base hatching time in game ticks (can be adjusted for balance)
BASE_HATCH_TIME = 300


class BreedingManager:
    """Manages breeding pairs and egg generation in the Pokete Care facility.

    Two compatible poketes (sharing at least one type) can breed to produce
    an egg. The egg's base stats are computed as weighted averages of the
    parents' base stats.
    """

    def __init__(self):
        self.parent1: Poke | None = None
        self.parent2: Poke | None = None
        self.start_time: int = 0
        self.egg_ready: bool = False
        self.egg: EggData | None = None

    def can_breed(self, poke1: Poke, poke2: Poke) -> bool:
        """Check if two poketes are compatible for breeding.

        Poketes are compatible if they share at least one type.
        """
        if poke1 is None or poke2 is None:
            return False

        if poke1.identifier == "__fallback__" or poke2.identifier == "__fallback__":
            return False

        types1 = set(t.name for t in poke1.types)
        types2 = set(t.name for t in poke2.types)
        return bool(types1 & types2)

    def get_shared_types(self, poke1: Poke, poke2: Poke) -> list[str]:
        """Get the types shared between two poketes."""
        if poke1 is None or poke2 is None:
            return []
        types1 = set(t.name for t in poke1.types)
        types2 = set(t.name for t in poke2.types)
        return list(types1 & types2)

    def start_breeding(self, poke1: Poke, poke2: Poke, current_time: int) -> bool:
        """Start breeding two poketes if they are compatible.

        Returns True if breeding started successfully, False otherwise.
        """
        if not self.can_breed(poke1, poke2):
            return False

        if self.parent1 is not None or self.parent2 is not None:
            return False

        self.parent1 = poke1
        self.parent2 = poke2
        self.start_time = current_time
        self.egg_ready = False
        self.egg = None
        return True

    def _compute_weighted_stat(
        self, stat1: int, stat2: int, weight1: float = 0.5, weight2: float = 0.5
    ) -> int:
        """Compute weighted average of two stats with some random variation."""
        base = stat1 * weight1 + stat2 * weight2
        variation = random.uniform(-0.1, 0.1) * base
        return max(1, int(base + variation))

    def _select_offspring_identifier(self) -> str:
        """Select which pokete the offspring will be based on."""
        if self.parent1 is None or self.parent2 is None:
            raise ValueError("Both parents must be set")

        pokes = asset_service.get_base_assets().pokes
        candidates = []

        shared_types = self.get_shared_types(self.parent1, self.parent2)

        # Prefer parents that haven't evolved (base forms)
        for parent in [self.parent1, self.parent2]:
            # Check if this parent is a base form (not evolved from something)
            # A simple heuristic: add both parents as candidates
            candidates.append(parent.identifier)

        # Also consider poketes that share the common types
        for poke_id, poke_data in pokes.items():
            if poke_id == "__fallback__":
                continue
            poke_types = set(poke_data.types)
            if any(t in poke_types for t in shared_types):
                # Prefer base-level poketes (those with evolve_poke set)
                if poke_data.evolve_poke and poke_data.evolve_lvl > 0:
                    candidates.append(poke_id)

        # Weight towards parents
        weights = []
        for c in candidates:
            if c == self.parent1.identifier or c == self.parent2.identifier:
                weights.append(3)  # Higher chance for parent types
            else:
                weights.append(1)

        return random.choices(candidates, weights=weights, k=1)[0]

    def compute_hatch_time(self) -> int:
        """Compute how long the egg needs to hatch based on parents."""
        if self.parent1 is None or self.parent2 is None:
            return BASE_HATCH_TIME

        # Base time modified by average level of parents
        avg_level = (self.parent1.lvl() + self.parent2.lvl()) / 2
        # Higher level parents = slightly faster hatching
        level_modifier = max(0.5, 1.0 - (avg_level / 100))
        return int(BASE_HATCH_TIME * level_modifier)

    def generate_egg(self) -> EggData | None:
        """Generate egg data based on the breeding pair."""
        if self.parent1 is None or self.parent2 is None:
            return None

        pokes = asset_service.get_base_assets().pokes
        offspring_id = self._select_offspring_identifier()
        base_poke = pokes[offspring_id]

        # Compute stats as weighted average of parents' base stats + offspring base
        p1_inf = self.parent1.inf
        p2_inf = self.parent2.inf

        # Weight: 40% parent1, 40% parent2, 20% base offspring stats
        hp = self._compute_weighted_stat(p1_inf.hp, p2_inf.hp, 0.4, 0.4)
        hp = int(hp * 0.8 + base_poke.hp * 0.2)

        atc = self._compute_weighted_stat(p1_inf.atc, p2_inf.atc, 0.4, 0.4)
        atc = int(atc * 0.8 + base_poke.atc * 0.2)

        defense = self._compute_weighted_stat(p1_inf.defense, p2_inf.defense, 0.4, 0.4)
        defense = int(defense * 0.8 + base_poke.defense * 0.2)

        initiative = self._compute_weighted_stat(
            p1_inf.initiative, p2_inf.initiative, 0.4, 0.4
        )
        initiative = int(initiative * 0.8 + base_poke.initiative * 0.2)

        return EggData(
            identifier=offspring_id,
            hp=max(10, hp),  # Minimum HP of 10
            atc=max(0, atc),
            defense=max(0, defense),
            initiative=max(0, initiative),
            hatch_time=self.compute_hatch_time(),
            parent1_identifier=self.parent1.identifier,
            parent2_identifier=self.parent2.identifier,
        )

    def update(self, current_time: int) -> bool:
        """Update breeding state. Returns True if egg just became ready."""
        if self.parent1 is None or self.parent2 is None:
            return False

        if self.egg_ready:
            return False

        elapsed = current_time - self.start_time
        if self.egg is None:
            self.egg = self.generate_egg()

        if self.egg and elapsed >= self.egg.hatch_time:
            self.egg_ready = True
            return True

        return False

    def is_egg_ready(self) -> bool:
        """Check if an egg is ready to be collected."""
        return self.egg_ready and self.egg is not None

    def get_time_remaining(self, current_time: int) -> int:
        """Get remaining time until egg hatches. Returns 0 if ready or no breeding."""
        if self.parent1 is None or self.parent2 is None:
            return 0

        if self.egg_ready:
            return 0

        if self.egg is None:
            self.egg = self.generate_egg()

        if self.egg is None:
            return 0

        elapsed = current_time - self.start_time
        remaining = self.egg.hatch_time - elapsed
        return max(0, remaining)

    def collect_egg(self) -> Poke | None:
        """Collect the hatched egg as a new Poke. Resets breeding state."""
        if not self.egg_ready or self.egg is None:
            return None

        # Create a new Poke from the egg data
        # Start at level 1 (xp=0)
        new_poke = Poke(
            self.egg.identifier,
            _xp=0,
            _hp="SKIP",
            player=True,
            shiny=random.randint(0, 100) == 0,  # 1% chance for shiny
            nature=None,  # Random nature
            stats=None,
        )

        # Set breeding-related stats info
        new_poke.poke_stats = Stats(
            new_poke.name,
            datetime.now(),
            caught_with="bred",
        )

        # Reset breeding state
        self.parent1 = None
        self.parent2 = None
        self.start_time = 0
        self.egg_ready = False
        self.egg = None

        return new_poke

    def cancel_breeding(self) -> tuple[Poke | None, Poke | None]:
        """Cancel breeding and return the parents."""
        p1, p2 = self.parent1, self.parent2
        self.parent1 = None
        self.parent2 = None
        self.start_time = 0
        self.egg_ready = False
        self.egg = None
        return p1, p2

    def has_breeding_pair(self) -> bool:
        """Check if there's an active breeding pair."""
        return self.parent1 is not None and self.parent2 is not None

    def get_breeding_status(self, current_time: int) -> str:
        """Get a human-readable breeding status message."""
        if not self.has_breeding_pair():
            return "No poketes are currently breeding."

        if self.egg_ready:
            return "An egg is ready to be collected!"

        remaining = self.get_time_remaining(current_time)
        if remaining > 0:
            return f"Breeding in progress... {remaining} time units remaining."

        return "Breeding in progress..."

    def dict(self) -> BreedingPairDict:
        """Serialize the breeding manager state to a dict."""
        return {
            "parent1": self.parent1.dict() if self.parent1 else None,
            "parent2": self.parent2.dict() if self.parent2 else None,
            "start_time": self.start_time,
            "egg_ready": self.egg_ready,
            "egg": self.egg.dict() if self.egg else None,
        }

    def from_dict(self, data: BreedingPairDict) -> None:
        """Load breeding manager state from a dict."""
        self.parent1 = (
            Poke.from_dict(data["parent1"]) if data.get("parent1") else None
        )
        self.parent2 = (
            Poke.from_dict(data["parent2"]) if data.get("parent2") else None
        )
        self.start_time = data.get("start_time", 0)
        self.egg_ready = data.get("egg_ready", False)
        self.egg = EggData.from_dict(data["egg"]) if data.get("egg") else None


# Global breeding manager instance
breeding_manager = BreedingManager()
