"""Breeding system for the Pokete Care facility.

Allows compatible poketes (sharing at least one type) to breed and produce
eggs that hatch after a certain time. Stats of the offspring are computed
as weighted averages of the parents' base stats.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from ..asset_service.service import asset_service
from ..poke import Poke
from ..poke.nature import PokeNature
from ..poke.stats import Stats


class BreedingHistoryEntryDict(TypedDict):
    """Serialization format for a breeding history entry."""
    offspring_identifier: str
    offspring_name: str
    parent1_identifier: str
    parent1_name: str
    parent2_identifier: str
    parent2_name: str
    hatch_timestamp: int
    inherited_moves: list[str]
    shiny: bool


@dataclass
class BreedingHistoryEntry:
    """Record of a completed breeding."""
    offspring_identifier: str
    offspring_name: str
    parent1_identifier: str
    parent1_name: str
    parent2_identifier: str
    parent2_name: str
    hatch_timestamp: int
    inherited_moves: list[str]
    shiny: bool

    def dict(self) -> BreedingHistoryEntryDict:
        return {
            "offspring_identifier": self.offspring_identifier,
            "offspring_name": self.offspring_name,
            "parent1_identifier": self.parent1_identifier,
            "parent1_name": self.parent1_name,
            "parent2_identifier": self.parent2_identifier,
            "parent2_name": self.parent2_name,
            "hatch_timestamp": self.hatch_timestamp,
            "inherited_moves": self.inherited_moves,
            "shiny": self.shiny,
        }

    @classmethod
    def from_dict(cls, data: BreedingHistoryEntryDict) -> "BreedingHistoryEntry":
        return cls(
            offspring_identifier=data["offspring_identifier"],
            offspring_name=data["offspring_name"],
            parent1_identifier=data["parent1_identifier"],
            parent1_name=data["parent1_name"],
            parent2_identifier=data["parent2_identifier"],
            parent2_name=data["parent2_name"],
            hatch_timestamp=data["hatch_timestamp"],
            inherited_moves=data.get("inherited_moves", []),
            shiny=data.get("shiny", False),
        )


class BreedingPairDict(TypedDict):
    """Serialization format for a breeding pair."""
    parent1: dict | None
    parent2: dict | None
    parent1_index: int | None
    parent2_index: int | None
    start_time: int
    egg_ready: bool
    egg: dict | None
    history: list[BreedingHistoryEntryDict]


class EggDict(TypedDict):
    """Serialization format for an egg."""
    identifier: str
    hp_bonus: int
    atc_bonus: int
    defense_bonus: int
    initiative_bonus: int
    hatch_time: int
    parent1_identifier: str
    parent2_identifier: str
    inherited_moves: list[str]


@dataclass
class EggData:
    """Holds computed egg data before it becomes a full Poke.
    
    The bonus stats are added to the hatched Poke's base stats after construction.
    """
    identifier: str
    hp_bonus: int
    atc_bonus: int
    defense_bonus: int
    initiative_bonus: int
    hatch_time: int
    parent1_identifier: str
    parent2_identifier: str
    inherited_moves: list[str] = field(default_factory=list)

    def dict(self) -> EggDict:
        return {
            "identifier": self.identifier,
            "hp_bonus": self.hp_bonus,
            "atc_bonus": self.atc_bonus,
            "defense_bonus": self.defense_bonus,
            "initiative_bonus": self.initiative_bonus,
            "hatch_time": self.hatch_time,
            "parent1_identifier": self.parent1_identifier,
            "parent2_identifier": self.parent2_identifier,
            "inherited_moves": self.inherited_moves,
        }

    @classmethod
    def from_dict(cls, data: EggDict) -> "EggData":
        return cls(
            identifier=data["identifier"],
            hp_bonus=data.get("hp_bonus", 0),
            atc_bonus=data.get("atc_bonus", 0),
            defense_bonus=data.get("defense_bonus", 0),
            initiative_bonus=data.get("initiative_bonus", 0),
            hatch_time=data["hatch_time"],
            parent1_identifier=data["parent1_identifier"],
            parent2_identifier=data["parent2_identifier"],
            inherited_moves=data.get("inherited_moves", []),
        )


# Base hatching time in game ticks (can be adjusted for balance)
BASE_HATCH_TIME = 300
# Maximum breeding history entries to keep
MAX_HISTORY_ENTRIES = 5
# Multi-type bonus: 10% reduction when sharing 2+ types
MULTI_TYPE_BONUS = 0.10


class BreedingManager:
    """Manages breeding pairs and egg generation in the Pokete Care facility.

    Two compatible poketes (sharing at least one type) can breed to produce
    an egg. The egg's base stats are computed as weighted averages of the
    parents' base stats.
    """

    def __init__(self):
        self.parent1: Poke | None = None
        self.parent2: Poke | None = None
        self.parent1_index: int | None = None
        self.parent2_index: int | None = None
        self.start_time: int = 0
        self.egg_ready: bool = False
        self.egg: EggData | None = None
        self.history: list[BreedingHistoryEntry] = []
        self._notified: bool = False

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

    def start_breeding(
        self, poke1: Poke, poke2: Poke, index1: int, index2: int, current_time: int
    ) -> bool:
        """Start breeding two poketes if they are compatible.

        Args:
            poke1: First parent pokete
            poke2: Second parent pokete
            index1: Index of first parent in player's team
            index2: Index of second parent in player's team
            current_time: Current game time

        Returns True if breeding started successfully, False otherwise.
        """
        if not self.can_breed(poke1, poke2):
            return False

        if self.parent1 is not None or self.parent2 is not None:
            return False

        self.parent1 = poke1
        self.parent2 = poke2
        self.parent1_index = index1
        self.parent2_index = index2
        self.start_time = current_time
        self.egg_ready = False
        self.egg = None
        self._notified = False
        return True

    def _compute_stat_bonus(self, stat1: int, stat2: int) -> int:
        """Compute bonus stat from parents' stats.
        
        Returns a bonus value based on weighted average of parents' stats
        with some random variation.
        """
        base = (stat1 + stat2) / 2
        variation = random.uniform(-0.1, 0.1) * base
        # Return bonus (can be positive or negative relative to base species)
        return int(variation + (base * 0.1))  # 10% of average as bonus

    def _select_offspring_identifier(self) -> str:
        """Select which pokete the offspring will be based on."""
        if self.parent1 is None or self.parent2 is None:
            raise ValueError("Both parents must be set")

        pokes = asset_service.get_base_assets().pokes
        candidates = []

        shared_types = self.get_shared_types(self.parent1, self.parent2)

        # Prefer parents that haven't evolved (base forms)
        for parent in [self.parent1, self.parent2]:
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

    def _compute_inherited_moves(self, offspring_identifier: str) -> list[str]:
        """Compute which moves the offspring inherits from parents.

        The child can inherit up to 1 move from each parent that it couldn't
        learn at level 1 (min_lvl > 0).
        """
        if self.parent1 is None or self.parent2 is None:
            return []

        attacks = asset_service.get_base_assets().attacks
        pokes = asset_service.get_base_assets().pokes
        offspring_info = pokes.get(offspring_identifier)

        if offspring_info is None:
            return []

        # Get the attacks the offspring can naturally learn
        offspring_learnable = set(offspring_info.attacks + offspring_info.pool)

        inherited = []

        # Try to inherit one move from each parent
        for parent in [self.parent1, self.parent2]:
            if len(inherited) >= 2:
                break

            # Get parent's current attacks that have min_lvl > 0
            eligible_attacks = []
            for atk_name in parent.attacks:
                if atk_name in attacks:
                    atk_data = attacks[atk_name]
                    # Must have min_lvl > 0 (not learnable at birth)
                    # and not already in offspring's natural moveset
                    if atk_data.min_lvl > 0 and atk_name not in offspring_learnable:
                        eligible_attacks.append(atk_name)

            if eligible_attacks:
                chosen = random.choice(eligible_attacks)
                if chosen not in inherited:
                    inherited.append(chosen)

        return inherited

    def compute_hatch_time(self) -> int:
        """Compute how long the egg needs to hatch based on parents.
        
        Includes multi-type bonus: 10% reduction when sharing 2+ types.
        """
        if self.parent1 is None or self.parent2 is None:
            return BASE_HATCH_TIME

        # Base time modified by average level of parents
        avg_level = (self.parent1.lvl() + self.parent2.lvl()) / 2
        # Higher level parents = slightly faster hatching
        level_modifier = max(0.5, 1.0 - (avg_level / 100))
        
        base_time = int(BASE_HATCH_TIME * level_modifier)
        
        # Apply multi-type bonus if sharing 2+ types
        shared_types = self.get_shared_types(self.parent1, self.parent2)
        if len(shared_types) >= 2:
            base_time = int(base_time * (1.0 - MULTI_TYPE_BONUS))
        
        return base_time

    def generate_egg(self) -> EggData | None:
        """Generate egg data based on the breeding pair."""
        if self.parent1 is None or self.parent2 is None:
            return None

        pokes = asset_service.get_base_assets().pokes
        offspring_id = self._select_offspring_identifier()

        # Compute stat bonuses from parents' base stats
        p1_inf = self.parent1.inf
        p2_inf = self.parent2.inf

        hp_bonus = self._compute_stat_bonus(p1_inf.hp, p2_inf.hp)
        atc_bonus = self._compute_stat_bonus(p1_inf.atc, p2_inf.atc)
        defense_bonus = self._compute_stat_bonus(p1_inf.defense, p2_inf.defense)
        initiative_bonus = self._compute_stat_bonus(p1_inf.initiative, p2_inf.initiative)

        # Compute inherited moves
        inherited_moves = self._compute_inherited_moves(offspring_id)

        return EggData(
            identifier=offspring_id,
            hp_bonus=hp_bonus,
            atc_bonus=max(0, atc_bonus),  # Don't go negative
            defense_bonus=max(0, defense_bonus),
            initiative_bonus=max(0, initiative_bonus),
            hatch_time=self.compute_hatch_time(),
            parent1_identifier=self.parent1.identifier,
            parent2_identifier=self.parent2.identifier,
            inherited_moves=inherited_moves,
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
            if not self._notified:
                self._notified = True
                return True

        return False

    def check_and_notify(self, current_time: int) -> bool:
        """Check if egg is ready and return True if notification should be sent.

        This is used by the periodic event to trigger notifications.
        """
        if not self.has_breeding_pair():
            return False

        was_ready = self.egg_ready
        self.update(current_time)

        # Return True only if egg just became ready
        return self.egg_ready and not was_ready

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

    def collect_egg(self, current_time: int) -> Poke | None:
        """Collect the hatched egg as a new Poke. Resets breeding state."""
        if not self.egg_ready or self.egg is None:
            return None

        # Determine shiny status
        is_shiny = random.randint(0, 100) == 0  # 1% chance for shiny

        # Get base attacks for the offspring
        pokes = asset_service.get_base_assets().pokes
        base_poke = pokes.get(self.egg.identifier)
        base_attacks = list(base_poke.attacks[:4]) if base_poke else []

        # Add inherited moves (replace last attacks if needed)
        final_attacks = base_attacks.copy()
        for move in self.egg.inherited_moves:
            if len(final_attacks) < 4:
                final_attacks.append(move)
            else:
                # Replace the last attack
                final_attacks[-1] = move

        # Create a new Poke from the egg data
        new_poke = Poke(
            self.egg.identifier,
            _xp=0,
            _hp="SKIP",
            _attacks=final_attacks if final_attacks else None,
            player=True,
            shiny=is_shiny,
            nature=None,  # Random nature
            stats=None,
        )

        # Apply stat bonuses from breeding
        # These are added on top of the computed stats
        new_poke.hp = max(1, new_poke.hp + self.egg.hp_bonus)
        new_poke.full_hp = new_poke.hp
        new_poke.atc = max(0, new_poke.atc + self.egg.atc_bonus)
        new_poke.defense = max(0, new_poke.defense + self.egg.defense_bonus)
        new_poke.initiative = max(0, new_poke.initiative + self.egg.initiative_bonus)

        # Update HP bar to reflect new HP
        new_poke.hp_bar.make(new_poke.hp)
        new_poke.text_hp.rechar(f"HP:{new_poke.hp}")

        # Set breeding-related stats info
        new_poke.poke_stats = Stats(
            new_poke.name,
            datetime.now(),
            caught_with="bred",
        )

        # Add to breeding history
        history_entry = BreedingHistoryEntry(
            offspring_identifier=self.egg.identifier,
            offspring_name=new_poke.name,
            parent1_identifier=self.egg.parent1_identifier,
            parent1_name=self.parent1.name if self.parent1 else "Unknown",
            parent2_identifier=self.egg.parent2_identifier,
            parent2_name=self.parent2.name if self.parent2 else "Unknown",
            hatch_timestamp=current_time,
            inherited_moves=self.egg.inherited_moves,
            shiny=is_shiny,
        )
        self.history.append(history_entry)

        # Keep only the last MAX_HISTORY_ENTRIES
        if len(self.history) > MAX_HISTORY_ENTRIES:
            self.history = self.history[-MAX_HISTORY_ENTRIES:]

        # Reset breeding state
        self.parent1 = None
        self.parent2 = None
        self.parent1_index = None
        self.parent2_index = None
        self.start_time = 0
        self.egg_ready = False
        self.egg = None
        self._notified = False

        return new_poke

    def cancel_breeding(self) -> tuple[Poke | None, Poke | None, int | None, int | None]:
        """Cancel breeding and return the parents with their original indices.
        
        Returns:
            Tuple of (parent1, parent2, parent1_index, parent2_index)
        """
        p1, p2 = self.parent1, self.parent2
        idx1, idx2 = self.parent1_index, self.parent2_index
        self.parent1 = None
        self.parent2 = None
        self.parent1_index = None
        self.parent2_index = None
        self.start_time = 0
        self.egg_ready = False
        self.egg = None
        self._notified = False
        return p1, p2, idx1, idx2

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

    def get_history(self) -> list[BreedingHistoryEntry]:
        """Get the breeding history (last 5 entries)."""
        return self.history.copy()

    def dict(self) -> BreedingPairDict:
        """Serialize the breeding manager state to a dict."""
        return {
            "parent1": self.parent1.dict() if self.parent1 else None,
            "parent2": self.parent2.dict() if self.parent2 else None,
            "parent1_index": self.parent1_index,
            "parent2_index": self.parent2_index,
            "start_time": self.start_time,
            "egg_ready": self.egg_ready,
            "egg": self.egg.dict() if self.egg else None,
            "history": [entry.dict() for entry in self.history],
        }

    def from_dict(self, data: BreedingPairDict) -> None:
        """Load breeding manager state from a dict."""
        self.parent1 = (
            Poke.from_dict(data["parent1"]) if data.get("parent1") else None
        )
        self.parent2 = (
            Poke.from_dict(data["parent2"]) if data.get("parent2") else None
        )
        self.parent1_index = data.get("parent1_index")
        self.parent2_index = data.get("parent2_index")
        self.start_time = data.get("start_time", 0)
        self.egg_ready = data.get("egg_ready", False)
        self.egg = EggData.from_dict(data["egg"]) if data.get("egg") else None
        self.history = [
            BreedingHistoryEntry.from_dict(entry)
            for entry in data.get("history", [])
        ]
        self._notified = self.egg_ready  # Don't re-notify on load


# Global breeding manager instance
breeding_manager = BreedingManager()
