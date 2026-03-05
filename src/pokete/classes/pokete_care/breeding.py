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

# Maximum number of breeding history entries to keep
MAX_HISTORY_SIZE = 5

# Shiny chance constants
BASE_SHINY_CHANCE = 500  # 1 in 500
SINGLE_SHINY_PARENT_CHANCE = 250  # 1 in 250 (halved)
BOTH_SHINY_PARENTS_CHANCE = 125  # 1 in 125 (halved again)

# Climate multiplier bounds
CLIMATE_MULTIPLIER_MIN = 0.6
CLIMATE_MULTIPLIER_MAX = 1.2
CLIMATE_BONUS = 0.2  # 20% bonus for matching climate

# Biome keywords mapped to type affinities
BIOME_TYPE_AFFINITIES: dict[str, list[str]] = {
    "cave": ["stone", "ground", "undead"],
    "sea": ["water"],
    "lake": ["water"],
    "beach": ["water", "ground"],
    "forest": ["plant", "normal", "bird"],
    "meadow": ["plant", "normal"],
    "field": ["plant", "ground", "normal"],
    "mountain": ["stone", "ground", "flying"],
    "temple": ["undead", "normal"],
    "village": ["normal"],
    "town": ["normal"],
    "house": ["normal"],
    "route": ["normal", "flying"],
    "arena": ["normal"],
}


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
    """Entry in the breeding history log."""
    parent1_name: str
    parent2_name: str
    offspring_name: str
    offspring_shiny: bool
    timestamp: str
    inherited_stats: dict

    def to_dict(self) -> dict:
        return {
            "parent1_name": self.parent1_name,
            "parent2_name": self.parent2_name,
            "offspring_name": self.offspring_name,
            "offspring_shiny": self.offspring_shiny,
            "timestamp": self.timestamp,
            "inherited_stats": self.inherited_stats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BreedingHistoryEntry":
        return cls(
            parent1_name=data["parent1_name"],
            parent2_name=data["parent2_name"],
            offspring_name=data["offspring_name"],
            offspring_shiny=data["offspring_shiny"],
            timestamp=data["timestamp"],
            inherited_stats=data.get("inherited_stats", {}),
        )


class BreedingManager:
    """Manages breeding pairs in the Pokete Care facility.

    Tracks breeding pairs, computes hatching time, generates offspring,
    and handles notifications when eggs are ready.
    """

    def __init__(self):
        self._breeding_pair: BreedingPairData | None = None
        self._history: list[BreedingHistoryEntry] = []
        self._current_map_name: str | None = None

    @property
    def has_breeding_pair(self) -> bool:
        return self._breeding_pair is not None

    @property
    def breeding_pair(self) -> BreedingPairData | None:
        return self._breeding_pair

    @property
    def history(self) -> list[BreedingHistoryEntry]:
        """Return history with most recent entries first."""
        return list(reversed(self._history))

    def set_current_map(self, map_name: str):
        """Set the current map name for climate calculations."""
        self._current_map_name = map_name

    def _get_poke_types(self, poke: "Poke") -> set[str]:
        """Get the type names from a Poke object."""
        return set(t.name for t in poke.types)

    def _get_primary_type(self, poke: "Poke") -> str:
        """Get the primary (first) type name of a Poke."""
        if poke.types:
            return poke.types[0].name
        return "normal"

    def are_compatible(self, poke1: "Poke", poke2: "Poke") -> bool:
        """Check if two Poketes can breed (share at least one type)."""
        types1 = self._get_poke_types(poke1)
        types2 = self._get_poke_types(poke2)
        return len(types1 & types2) > 0

    def get_shared_types(self, poke1: "Poke", poke2: "Poke") -> list[str]:
        """Get the types shared between two Poketes."""
        types1 = self._get_poke_types(poke1)
        types2 = self._get_poke_types(poke2)
        return list(types1 & types2)

    def _infer_biome_from_map(self, map_name: str | None) -> str | None:
        """Infer biome type from map name."""
        if not map_name:
            return None

        map_name_lower = map_name.lower()
        for biome_keyword in BIOME_TYPE_AFFINITIES:
            if biome_keyword in map_name_lower:
                return biome_keyword
        return None

    def compute_climate_multiplier(
        self, poke1: "Poke", poke2: "Poke", map_name: str | None = None
    ) -> float:
        """Compute climate multiplier based on map biome and parent types.

        Returns a multiplier between CLIMATE_MULTIPLIER_MIN (0.6) and
        CLIMATE_MULTIPLIER_MAX (1.2).
        """
        if map_name is None:
            map_name = self._current_map_name

        biome = self._infer_biome_from_map(map_name)
        if biome is None:
            return 1.0  # No climate effect

        affinity_types = BIOME_TYPE_AFFINITIES.get(biome, [])
        if not affinity_types:
            return 1.0

        # Get primary types of both parents
        primary1 = self._get_primary_type(poke1)
        primary2 = self._get_primary_type(poke2)

        # Count how many parents match the biome
        matches = 0
        if primary1 in affinity_types:
            matches += 1
        if primary2 in affinity_types:
            matches += 1

        # Calculate multiplier: 0 matches = 1.2 (slower), 1 match = 1.0, 2 matches = 0.6 (faster)
        if matches == 2:
            return CLIMATE_MULTIPLIER_MIN  # Both match: 40% faster
        elif matches == 1:
            return 1.0 - CLIMATE_BONUS  # One matches: 20% faster
        else:
            return CLIMATE_MULTIPLIER_MAX  # Neither matches: 20% slower

    def compute_hatch_time(
        self, poke1: "Poke", poke2: "Poke", map_name: str | None = None
    ) -> int:
        """Compute hatching time based on parents' levels, compatibility, and climate.

        Higher level parents and more shared types result in faster hatching.
        Climate matching can reduce or increase time by up to 40%.
        Returns time in in-game minutes.
        """
        shared_types = len(self.get_shared_types(poke1, poke2))
        avg_level = (poke1.lvl() + poke2.lvl()) / 2

        # Base time reduced by shared types (max 50% reduction)
        type_multiplier = max(0.5, 1.0 - (shared_types - 1) * 0.1)

        # Higher level parents hatch faster (max 30% reduction at lvl 50+)
        level_multiplier = max(0.7, 1.0 - (avg_level / 50) * 0.3)

        # Climate influence
        climate_multiplier = self.compute_climate_multiplier(poke1, poke2, map_name)

        return int(BASE_HATCH_TIME * type_multiplier * level_multiplier * climate_multiplier)

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
        self, stat1: int, stat2: int, weight: float = 0.5
    ) -> int:
        """Compute weighted average of two stats."""
        return int(stat1 * weight + stat2 * (1.0 - weight))

    def _compute_shiny_chance(self, poke1: "Poke", poke2: "Poke") -> int:
        """Compute shiny chance based on parent shininess.

        Base chance is 1/500.
        If one parent is shiny: 1/250 (halved).
        If both parents are shiny: 1/125 (halved again).
        """
        if poke1.shiny and poke2.shiny:
            return BOTH_SHINY_PARENTS_CHANCE
        elif poke1.shiny or poke2.shiny:
            return SINGLE_SHINY_PARENT_CHANCE
        return BASE_SHINY_CHANCE

    def compute_offspring_stats(
        self, poke1: "Poke", poke2: "Poke", offspring_identifier: str
    ) -> dict:
        """Compute the offspring's inherited stats.

        Stats (atc, defense, initiative) are weighted averages of parents' stats.
        Returns a dict that can be used to create the offspring Poke.
        """
        # Random weight between 0.3 and 0.7 for variety
        weight = random.uniform(0.3, 0.7)

        # The offspring starts at level 1 (xp = 0)
        base_xp = 0

        # Compute inherited stats as weighted averages
        inherited_atc = self._compute_weighted_stat(
            poke1.inf.atc, poke2.inf.atc, weight
        )
        inherited_defense = self._compute_weighted_stat(
            poke1.inf.defense, poke2.inf.defense, weight
        )
        inherited_initiative = self._compute_weighted_stat(
            poke1.inf.initiative, poke2.inf.initiative, weight
        )

        # Determine if shiny using the shiny parent bonus
        shiny_chance = self._compute_shiny_chance(poke1, poke2)
        is_shiny = random.randint(0, shiny_chance - 1) == 0

        # Get base attacks for offspring species
        pokes = asset_service.get_base_assets().pokes
        offspring_data = pokes.get(offspring_identifier)
        if offspring_data:
            base_attacks = offspring_data.attacks[:4]
        else:
            base_attacks = []

        inherited_stats = {
            "atc": inherited_atc,
            "defense": inherited_defense,
            "initiative": inherited_initiative,
        }

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
            "inherited_stats": inherited_stats,
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

        # Add to breeding history
        self._add_to_history(
            parent1_name=parent1.name,
            parent2_name=parent2.name,
            offspring_name=self._breeding_pair.offspring_identifier,
            offspring_shiny=offspring_data["shiny"],
            inherited_stats=offspring_data.get("inherited_stats", {}),
        )

        self._breeding_pair = None
        return offspring_data

    def _add_to_history(
        self,
        parent1_name: str,
        parent2_name: str,
        offspring_name: str,
        offspring_shiny: bool,
        inherited_stats: dict,
    ):
        """Add a breeding result to the history log."""
        entry = BreedingHistoryEntry(
            parent1_name=parent1_name,
            parent2_name=parent2_name,
            offspring_name=offspring_name,
            offspring_shiny=offspring_shiny,
            timestamp=datetime.now().isoformat(),
            inherited_stats=inherited_stats,
        )
        self._history.append(entry)
        # Keep only the last MAX_HISTORY_SIZE entries
        if len(self._history) > MAX_HISTORY_SIZE:
            self._history = self._history[-MAX_HISTORY_SIZE:]

    def get_history(self) -> list[BreedingHistoryEntry]:
        """Get the breeding history log (last 5 entries)."""
        return list(self._history)

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

        history_data = data.get("history", [])
        self._history = [
            BreedingHistoryEntry.from_dict(entry) for entry in history_data
        ]

    def clear_history(self):
        """Clear the breeding history."""
        self._history = []


# Global breeding manager instance
breeding_manager = BreedingManager()
