"""Breeding system for the Pokete Care facility.

Two compatible Poketes (sharing at least one type) can breed when kept
in the care center. The offspring's base stats are computed as a weighted
average of the parents' stats.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from pokete.classes.asset_service.service import asset_service

if TYPE_CHECKING:
    from pokete.classes.poke.poke import Poke


# Base hatching time in in-game minutes (configurable)
BASE_HATCH_TIME = 300  # 5 in-game hours

# Maximum breeding history entries to keep
MAX_BREEDING_HISTORY = 5


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


@dataclass
class BreedingHistoryEntry:
    """Record of a completed breeding."""
    parent1_name: str
    parent2_name: str
    offspring_name: str
    offspring_identifier: str
    completed_time: str  # ISO format timestamp
    was_shiny: bool

    def to_dict(self) -> dict:
        return {
            "parent1_name": self.parent1_name,
            "parent2_name": self.parent2_name,
            "offspring_name": self.offspring_name,
            "offspring_identifier": self.offspring_identifier,
            "completed_time": self.completed_time,
            "was_shiny": self.was_shiny,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BreedingHistoryEntry":
        return cls(
            parent1_name=data["parent1_name"],
            parent2_name=data["parent2_name"],
            offspring_name=data["offspring_name"],
            offspring_identifier=data["offspring_identifier"],
            completed_time=data["completed_time"],
            was_shiny=data["was_shiny"],
        )


class BreedingManager:
    """Manages breeding pairs in the Pokete Care facility.

    Tracks breeding pairs, computes hatching time, generates offspring,
    and handles notifications when eggs are ready.
    """

    def __init__(self):
        self._breeding_pair: BreedingPairData | None = None
        self._history: list[BreedingHistoryEntry] = []

    @property
    def has_breeding_pair(self) -> bool:
        return self._breeding_pair is not None

    @property
    def breeding_pair(self) -> BreedingPairData | None:
        return self._breeding_pair

    @property
    def history(self) -> list[BreedingHistoryEntry]:
        """Get the breeding history (most recent first)."""
        return list(reversed(self._history))

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

    def _compute_shiny_chance(self, poke1: "Poke", poke2: "Poke") -> int:
        """Compute shiny chance denominator based on parent shininess.

        Base chance: 1/500
        One shiny parent: 1/250 (halved)
        Both shiny parents: 1/125 (halved again)
        """
        base_chance = 500
        shiny_count = sum([poke1.shiny, poke2.shiny])

        if shiny_count == 1:
            return base_chance // 2  # 250
        elif shiny_count == 2:
            return base_chance // 4  # 125
        return base_chance

    def compute_offspring_stats(
        self, poke1: "Poke", poke2: "Poke", offspring_identifier: str
    ) -> dict:
        """Compute the offspring's inherited stats.

        Stats (atc, defense, initiative) are weighted averages of parents' 
        base stats with some randomness. Returns a dict that can be used 
        to create the offspring Poke.
        """
        # Random weight between 0.3 and 0.7 for variety
        weight = random.uniform(0.3, 0.7)

        # The offspring starts at level 1 (xp = 0)
        base_xp = 0

        # Compute weighted averages of parent stats
        inherited_atc = self._compute_weighted_stat(
            poke1.inf.atc, poke2.inf.atc, weight
        )
        inherited_defense = self._compute_weighted_stat(
            poke1.inf.defense, poke2.inf.defense, weight
        )
        inherited_initiative = self._compute_weighted_stat(
            poke1.inf.initiative, poke2.inf.initiative, weight
        )

        # Determine if shiny based on parent shininess
        shiny_chance = self._compute_shiny_chance(poke1, poke2)
        is_shiny = random.randint(0, shiny_chance - 1) == 0

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
            # Inherited stats for post-creation application
            "inherited_stats": {
                "atc": inherited_atc,
                "defense": inherited_defense,
                "initiative": inherited_initiative,
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

    def _add_to_history(
        self,
        parent1_name: str,
        parent2_name: str,
        offspring_name: str,
        offspring_identifier: str,
        was_shiny: bool,
    ):
        """Add a breeding result to history."""
        entry = BreedingHistoryEntry(
            parent1_name=parent1_name,
            parent2_name=parent2_name,
            offspring_name=offspring_name,
            offspring_identifier=offspring_identifier,
            completed_time=datetime.now().isoformat(),
            was_shiny=was_shiny,
        )
        self._history.append(entry)
        # Keep only the last MAX_BREEDING_HISTORY entries
        if len(self._history) > MAX_BREEDING_HISTORY:
            self._history = self._history[-MAX_BREEDING_HISTORY:]

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

        # Get offspring name for history
        pokes = asset_service.get_base_assets().pokes
        offspring_poke_data = pokes.get(offspring_data["name"])
        offspring_name = (
            offspring_poke_data.name if offspring_poke_data else offspring_data["name"]
        )

        # Add to history
        self._add_to_history(
            parent1_name=parent1.name,
            parent2_name=parent2.name,
            offspring_name=offspring_name,
            offspring_identifier=offspring_data["name"],
            was_shiny=offspring_data["shiny"],
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
            "history": [entry.to_dict() for entry in self._history],
        }

    def from_dict(self, data: dict):
        """Restore breeding manager state from saved data."""
        pair_data = data.get("breeding_pair")
        if pair_data is not None:
            self._breeding_pair = BreedingPairData.from_dict(pair_data)
        else:
            self._breeding_pair = None

        # Restore history
        history_data = data.get("history", [])
        self._history = [
            BreedingHistoryEntry.from_dict(entry) for entry in history_data
        ]


# Global breeding manager instance
breeding_manager = BreedingManager()
