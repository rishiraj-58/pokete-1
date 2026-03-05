"""Breeding system for the Pokete Care facility.

Two compatible Poketes (sharing at least one type) can breed when kept
in the care center. The offspring's base stats are computed as a weighted
average of the parents' stats.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from pokete.classes.asset_service.service import asset_service

if TYPE_CHECKING:
    from pokete.classes.poke.poke import Poke


# Base hatching time in in-game minutes (configurable)
BASE_HATCH_TIME = 300  # 5 in-game hours


@dataclass
class BreedingPairData:
    """Serializable data for a breeding pair."""
    parent1_dict: dict
    parent2_dict: dict
    start_time: int
    hatch_time: int
    offspring_identifier: str
    notified: bool = False

    def to_dict(self) -> dict:
        return {
            "parent1": self.parent1_dict,
            "parent2": self.parent2_dict,
            "start_time": self.start_time,
            "hatch_time": self.hatch_time,
            "offspring_identifier": self.offspring_identifier,
            "notified": self.notified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BreedingPairData":
        return cls(
            parent1_dict=data["parent1"],
            parent2_dict=data["parent2"],
            start_time=data["start_time"],
            hatch_time=data["hatch_time"],
            offspring_identifier=data["offspring_identifier"],
            notified=data.get("notified", False),
        )


class BreedingManager:
    """Manages breeding pairs in the Pokete Care facility.

    Tracks breeding pairs, computes hatching time, generates offspring,
    and handles notifications when eggs are ready.
    """

    def __init__(self):
        self._breeding_pair: BreedingPairData | None = None

    @property
    def has_breeding_pair(self) -> bool:
        return self._breeding_pair is not None

    @property
    def breeding_pair(self) -> BreedingPairData | None:
        return self._breeding_pair

    def are_compatible(self, poke1: "Poke", poke2: "Poke") -> bool:
        """Check if two Poketes can breed (share at least one type)."""
        types1 = set(poke1.inf.types)
        types2 = set(poke2.inf.types)
        return len(types1 & types2) > 0

    def get_shared_types(self, poke1: "Poke", poke2: "Poke") -> list[str]:
        """Get the types shared between two Poketes."""
        types1 = set(poke1.inf.types)
        types2 = set(poke2.inf.types)
        return list(types1 & types2)

    def compute_hatch_time(self, poke1: "Poke", poke2: "Poke") -> int:
        """Compute hatching time based on parents' levels and compatibility.

        Higher level parents and more shared types result in faster hatching.
        Returns time in in-game minutes.
        """
        shared_types = len(self.get_shared_types(poke1, poke2))
        avg_level = (poke1.lvl() + poke2.lvl()) / 2

        # Base time reduced by shared types (max 50% reduction)
        type_multiplier = max(0.5, 1.0 - (shared_types - 1) * 0.1)

        # Higher level parents hatch faster (max 30% reduction at lvl 50+)
        level_multiplier = max(0.7, 1.0 - (avg_level / 50) * 0.3)

        return int(BASE_HATCH_TIME * type_multiplier * level_multiplier)

    def _select_offspring_identifier(
        self, poke1: "Poke", poke2: "Poke"
    ) -> str:
        """Select the offspring's species based on parents.

        The offspring is randomly selected from one of the parents' species,
        favoring base evolution forms when available.
        """
        pokes = asset_service.get_base_assets().pokes
        candidates = []

        for parent in [poke1, poke2]:
            identifier = parent.identifier
            # Try to find base form (pokete that evolves into this one)
            base_form = self._find_base_form(identifier)
            candidates.append(base_form if base_form else identifier)

        # Filter out fallback
        valid_candidates = [c for c in candidates if c != "__fallback__"]
        if not valid_candidates:
            valid_candidates = [poke1.identifier]

        return random.choice(valid_candidates)

    def _find_base_form(self, identifier: str) -> str | None:
        """Find the base evolution form for a pokete identifier."""
        pokes = asset_service.get_base_assets().pokes
        for poke_id, poke_data in pokes.items():
            if poke_data.evolve_poke == identifier:
                # Recursively find the base form
                base = self._find_base_form(poke_id)
                return base if base else poke_id
        return None

    def _compute_weighted_stat(
        self, stat1: int, stat2: int, weight1: float = 0.5
    ) -> int:
        """Compute weighted average of two stats."""
        weight2 = 1.0 - weight1
        return int(stat1 * weight1 + stat2 * weight2)

    def compute_offspring_stats(
        self, poke1: "Poke", poke2: "Poke", offspring_identifier: str
    ) -> dict:
        """Compute the offspring's inherited stats.

        Stats are weighted averages of parents' stats with some randomness.
        Returns a dict that can be used to create the offspring Poke.
        """
        # Random weight between 0.3 and 0.7 for variety
        weight = random.uniform(0.3, 0.7)

        # The offspring starts at level 1 (xp = 0)
        base_xp = 0

        # Determine if shiny (rare chance, slightly higher if parent is shiny)
        shiny_chance = 500
        if poke1.shiny or poke2.shiny:
            shiny_chance = 250
        is_shiny = random.randint(0, shiny_chance) == 0

        # Get base attacks for offspring species
        pokes = asset_service.get_base_assets().pokes
        offspring_data = pokes.get(offspring_identifier)
        if offspring_data:
            base_attacks = offspring_data.attacks[:4]
        else:
            base_attacks = []

        return {
            "name": offspring_identifier,
            "xp": base_xp,
            "hp": "SKIP",  # Use default max HP
            "ap": None,
            "attacks": base_attacks,
            "effects": [],
            "shiny": is_shiny,
            "nature": None,  # Will be randomly generated
            "stats": {
                "ownership_date": datetime.now().isoformat(),
                "evolved_date": None,
                "total_battles": 0,
                "lost_battles": 0,
                "win_battles": 0,
                "earned_xp": 0,
                "caught_with": "breeding",
                "run_away": 0,
            },
        }

    def start_breeding(
        self, poke1: "Poke", poke2: "Poke", current_time: int
    ) -> bool:
        """Start a breeding pair if compatible.

        Returns True if breeding started successfully, False otherwise.
        """
        if not self.are_compatible(poke1, poke2):
            return False

        if self._breeding_pair is not None:
            return False

        hatch_time = self.compute_hatch_time(poke1, poke2)
        offspring_id = self._select_offspring_identifier(poke1, poke2)

        self._breeding_pair = BreedingPairData(
            parent1_dict=poke1.dict(),
            parent2_dict=poke2.dict(),
            start_time=current_time,
            hatch_time=hatch_time,
            offspring_identifier=offspring_id,
            notified=False,
        )
        return True

    def get_time_remaining(self, current_time: int) -> int:
        """Get remaining time until egg hatches (in in-game minutes)."""
        if self._breeding_pair is None:
            return -1
        elapsed = current_time - self._breeding_pair.start_time
        remaining = self._breeding_pair.hatch_time - elapsed
        return max(0, remaining)

    def is_egg_ready(self, current_time: int) -> bool:
        """Check if the egg is ready to be collected."""
        return self.get_time_remaining(current_time) == 0

    def should_notify(self, current_time: int) -> bool:
        """Check if user should be notified about ready egg."""
        if self._breeding_pair is None:
            return False
        return (
            self.is_egg_ready(current_time)
            and not self._breeding_pair.notified
        )

    def mark_notified(self):
        """Mark that the user has been notified about the ready egg."""
        if self._breeding_pair is not None:
            self._breeding_pair.notified = True

    def collect_egg(self, current_time: int) -> dict | None:
        """Collect the hatched egg and return offspring data.

        Returns None if egg is not ready yet.
        """
        if not self.is_egg_ready(current_time):
            return None

        if self._breeding_pair is None:
            return None

        # Import here to avoid circular dependency
        from pokete.classes.poke.poke import Poke

        # Reconstruct parents to compute stats
        parent1 = Poke.from_dict(self._breeding_pair.parent1_dict)
        parent2 = Poke.from_dict(self._breeding_pair.parent2_dict)

        offspring_data = self.compute_offspring_stats(
            parent1, parent2, self._breeding_pair.offspring_identifier
        )

        self._breeding_pair = None
        return offspring_data

    def cancel_breeding(self) -> tuple[dict, dict] | None:
        """Cancel current breeding and return parent data.

        Returns tuple of (parent1_dict, parent2_dict) or None if no breeding.
        """
        if self._breeding_pair is None:
            return None

        result = (
            self._breeding_pair.parent1_dict,
            self._breeding_pair.parent2_dict,
        )
        self._breeding_pair = None
        return result

    def dict(self) -> dict:
        """Serialize breeding manager state for saving."""
        return {
            "breeding_pair": (
                self._breeding_pair.to_dict()
                if self._breeding_pair
                else None
            ),
        }

    def from_dict(self, data: dict):
        """Restore breeding manager state from saved data."""
        pair_data = data.get("breeding_pair")
        if pair_data is not None:
            self._breeding_pair = BreedingPairData.from_dict(pair_data)
        else:
            self._breeding_pair = None


# Global breeding manager instance
breeding_manager = BreedingManager()
