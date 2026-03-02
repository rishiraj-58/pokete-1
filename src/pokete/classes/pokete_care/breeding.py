"""Breeding system for the Pokete Care facility.

Allows two compatible Poketes (sharing at least one type) to breed and produce
an egg that hatches into a new Pokete after a certain time.
"""

import random
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from ..poke import Poke, Stats, PokeNature
from ..asset_service.service import asset_service


class BreedingPairDict(TypedDict):
    """Type definition for serialized breeding pair data."""
    parent1: dict | None
    parent2: dict | None


class EggDict(TypedDict):
    """Type definition for serialized egg data."""
    pokete_identifier: str
    hp: int
    atc: int
    defense: int
    initiative: int
    created_time: int
    hatch_time: int
    parent1_identifier: str
    parent2_identifier: str
    shiny: bool


class BreedingManagerDict(TypedDict):
    """Type definition for serialized breeding manager data."""
    breeding_pair: BreedingPairDict
    egg: EggDict | None
    notifications: list[str]


# Base hatching time in in-game minutes (approximately 2 in-game hours)
BASE_HATCH_TIME = 120

# Weight factors for stat inheritance
PARENT_WEIGHT_MIN = 0.3
PARENT_WEIGHT_MAX = 0.7


@dataclass
class EggStats:
    """Holds the computed stats for an egg before it hatches."""
    hp: int
    atc: int
    defense: int
    initiative: int


class Egg:
    """Represents a Pokete egg that will hatch after a certain time.
    
    Args:
        pokete_identifier: The identifier of the Pokete that will hatch
        stats: The computed stats for the egg
        created_time: The in-game time when the egg was created
        hatch_time: The in-game time when the egg will be ready to hatch
        parent1_identifier: The identifier of the first parent
        parent2_identifier: The identifier of the second parent
        shiny: Whether the hatched Pokete will be shiny
    """
    
    def __init__(
        self,
        pokete_identifier: str,
        stats: EggStats,
        created_time: int,
        hatch_time: int,
        parent1_identifier: str,
        parent2_identifier: str,
        shiny: bool = False
    ):
        self.pokete_identifier = pokete_identifier
        self.stats = stats
        self.created_time = created_time
        self.hatch_time = hatch_time
        self.parent1_identifier = parent1_identifier
        self.parent2_identifier = parent2_identifier
        self.shiny = shiny
    
    def is_ready(self, current_time: int) -> bool:
        """Check if the egg is ready to hatch."""
        return current_time >= self.hatch_time
    
    def time_remaining(self, current_time: int) -> int:
        """Return the time remaining until hatch in in-game minutes."""
        return max(0, self.hatch_time - current_time)
    
    def hatch(self) -> Poke:
        """Create the Pokete from this egg.
        
        Returns:
            A new Poke instance with inherited stats.
        """
        poke = Poke(
            self.pokete_identifier,
            _xp=0,
            _hp="SKIP",
            shiny=self.shiny
        )
        poke.poke_stats = Stats(
            poke.name,
            datetime.now(),
            caught_with="egg"
        )
        return poke
    
    def dict(self) -> EggDict:
        """Serialize egg to a dictionary."""
        return {
            "pokete_identifier": self.pokete_identifier,
            "hp": self.stats.hp,
            "atc": self.stats.atc,
            "defense": self.stats.defense,
            "initiative": self.stats.initiative,
            "created_time": self.created_time,
            "hatch_time": self.hatch_time,
            "parent1_identifier": self.parent1_identifier,
            "parent2_identifier": self.parent2_identifier,
            "shiny": self.shiny
        }
    
    @classmethod
    def from_dict(cls, data: EggDict) -> "Egg":
        """Deserialize egg from a dictionary."""
        stats = EggStats(
            hp=data["hp"],
            atc=data["atc"],
            defense=data["defense"],
            initiative=data["initiative"]
        )
        return cls(
            pokete_identifier=data["pokete_identifier"],
            stats=stats,
            created_time=data["created_time"],
            hatch_time=data["hatch_time"],
            parent1_identifier=data["parent1_identifier"],
            parent2_identifier=data["parent2_identifier"],
            shiny=data.get("shiny", False)
        )


class BreedingPair:
    """Represents a pair of Poketes that can potentially breed.
    
    Args:
        parent1: The first parent Pokete (or None)
        parent2: The second parent Pokete (or None)
    """
    
    def __init__(self, parent1: Poke | None = None, parent2: Poke | None = None):
        self.parent1 = parent1
        self.parent2 = parent2
    
    def is_complete(self) -> bool:
        """Check if both parents are present."""
        return self.parent1 is not None and self.parent2 is not None
    
    def is_empty(self) -> bool:
        """Check if no parents are present."""
        return self.parent1 is None and self.parent2 is None
    
    def has_slot_available(self) -> bool:
        """Check if there's a slot available for a parent."""
        return self.parent1 is None or self.parent2 is None
    
    def add_parent(self, poke: Poke) -> bool:
        """Add a parent to the breeding pair.
        
        Returns:
            True if the parent was added successfully, False otherwise.
        """
        if self.parent1 is None:
            self.parent1 = poke
            return True
        elif self.parent2 is None:
            self.parent2 = poke
            return True
        return False
    
    def remove_parent(self, index: int) -> Poke | None:
        """Remove and return a parent from the breeding pair.
        
        Args:
            index: 0 for parent1, 1 for parent2
            
        Returns:
            The removed Poke, or None if the slot was empty.
        """
        if index == 0:
            poke = self.parent1
            self.parent1 = None
            return poke
        elif index == 1:
            poke = self.parent2
            self.parent2 = None
            return poke
        return None
    
    def get_shared_types(self) -> list[str]:
        """Get the types shared between both parents.
        
        Returns:
            A list of shared type names.
        """
        if not self.is_complete():
            return []
        
        types1 = set(self.parent1.inf.types)
        types2 = set(self.parent2.inf.types)
        return list(types1 & types2)
    
    def is_compatible(self) -> bool:
        """Check if the pair is compatible for breeding.
        
        Two Poketes are compatible if they share at least one type.
        """
        return len(self.get_shared_types()) > 0
    
    def clear(self):
        """Clear both parents from the pair."""
        self.parent1 = None
        self.parent2 = None
    
    def dict(self) -> BreedingPairDict:
        """Serialize the breeding pair to a dictionary."""
        return {
            "parent1": None if self.parent1 is None else self.parent1.dict(),
            "parent2": None if self.parent2 is None else self.parent2.dict()
        }
    
    @classmethod
    def from_dict(cls, data: BreedingPairDict) -> "BreedingPair":
        """Deserialize a breeding pair from a dictionary."""
        parent1 = None if data.get("parent1") is None else Poke.from_dict(data["parent1"])
        parent2 = None if data.get("parent2") is None else Poke.from_dict(data["parent2"])
        return cls(parent1, parent2)


class BreedingManager:
    """Manages the breeding system for the Pokete Care facility.
    
    Tracks breeding pairs, computes hatching times, generates eggs,
    and handles notifications when eggs are ready.
    """
    
    def __init__(self):
        self.breeding_pair = BreedingPair()
        self.egg: Egg | None = None
        self.notifications: list[str] = []
    
    def add_to_breeding_pair(self, poke: Poke) -> bool:
        """Add a Pokete to the breeding pair.
        
        Args:
            poke: The Pokete to add
            
        Returns:
            True if successfully added, False otherwise.
        """
        if self.egg is not None:
            return False
        return self.breeding_pair.add_parent(poke)
    
    def remove_from_breeding_pair(self, index: int) -> Poke | None:
        """Remove a Pokete from the breeding pair.
        
        Args:
            index: 0 for first parent, 1 for second parent
            
        Returns:
            The removed Poke, or None if the slot was empty.
        """
        return self.breeding_pair.remove_parent(index)
    
    def can_breed(self) -> bool:
        """Check if breeding can start.
        
        Returns:
            True if breeding pair is complete, compatible, and no egg exists.
        """
        return (
            self.breeding_pair.is_complete() and
            self.breeding_pair.is_compatible() and
            self.egg is None
        )
    
    def get_incompatibility_reason(self) -> str | None:
        """Get the reason why breeding cannot start.
        
        Returns:
            A string describing the reason, or None if breeding can start.
        """
        if self.egg is not None:
            return "An egg is already incubating"
        if not self.breeding_pair.is_complete():
            return "Two Poketes are required for breeding"
        if not self.breeding_pair.is_compatible():
            return "These Poketes don't share any types and cannot breed"
        return None
    
    def start_breeding(self, current_time: int) -> Egg | None:
        """Start the breeding process and generate an egg.
        
        Args:
            current_time: The current in-game time
            
        Returns:
            The generated Egg, or None if breeding cannot start.
        """
        if not self.can_breed():
            return None
        
        parent1 = self.breeding_pair.parent1
        parent2 = self.breeding_pair.parent2
        
        # Determine which Pokete the offspring will be
        offspring_identifier = self._select_offspring_identifier(parent1, parent2)
        
        # Compute stats using weighted average
        stats = self._compute_offspring_stats(parent1, parent2, offspring_identifier)
        
        # Compute hatch time based on parents' levels
        hatch_time = self._compute_hatch_time(parent1, parent2, current_time)
        
        # Determine if shiny (very rare - 1 in 500 chance, slightly better if either parent is shiny)
        shiny_chance = 500
        if parent1.shiny or parent2.shiny:
            shiny_chance = 250
        shiny = random.randint(1, shiny_chance) == 1
        
        self.egg = Egg(
            pokete_identifier=offspring_identifier,
            stats=stats,
            created_time=current_time,
            hatch_time=hatch_time,
            parent1_identifier=parent1.identifier,
            parent2_identifier=parent2.identifier,
            shiny=shiny
        )
        
        return self.egg
    
    def _select_offspring_identifier(self, parent1: Poke, parent2: Poke) -> str:
        """Select which Pokete the offspring will be.
        
        The offspring is one of the parents' base forms (or the parent itself
        if it doesn't evolve from anything), selected randomly.
        """
        pokes = asset_service.get_base_assets().pokes
        
        candidates = []
        for parent in [parent1, parent2]:
            # Find the base form by checking if any pokete evolves into this one
            base_form = parent.identifier
            for poke_id, poke_data in pokes.items():
                if poke_data.evolve_poke == parent.identifier:
                    base_form = poke_id
                    break
            candidates.append(base_form)
        
        return random.choice(candidates)
    
    def _compute_offspring_stats(
        self,
        parent1: Poke,
        parent2: Poke,
        offspring_identifier: str
    ) -> EggStats:
        """Compute the offspring's stats using weighted average of parents.
        
        The weight is randomly determined within a range for each stat,
        making each offspring unique.
        """
        pokes = asset_service.get_base_assets().pokes
        base_stats = pokes[offspring_identifier]
        
        def weighted_avg(stat1: int, stat2: int, base: int) -> int:
            weight = random.uniform(PARENT_WEIGHT_MIN, PARENT_WEIGHT_MAX)
            # Combine parent stats with base stats
            parent_avg = stat1 * weight + stat2 * (1 - weight)
            # The final stat is influenced by both parents and the base species
            return int((parent_avg + base) / 2)
        
        return EggStats(
            hp=weighted_avg(parent1.inf.hp, parent2.inf.hp, base_stats.hp),
            atc=weighted_avg(parent1.inf.atc, parent2.inf.atc, base_stats.atc),
            defense=weighted_avg(parent1.inf.defense, parent2.inf.defense, base_stats.defense),
            initiative=weighted_avg(parent1.inf.initiative, parent2.inf.initiative, base_stats.initiative)
        )
    
    def _compute_hatch_time(
        self,
        parent1: Poke,
        parent2: Poke,
        current_time: int
    ) -> int:
        """Compute when the egg will be ready to hatch.
        
        Higher level parents produce eggs that hatch faster.
        """
        avg_level = (parent1.lvl() + parent2.lvl()) / 2
        # Reduce hatch time by 1 minute per level (minimum 30 minutes)
        hatch_duration = max(30, BASE_HATCH_TIME - int(avg_level))
        return current_time + hatch_duration
    
    def check_egg_ready(self, current_time: int) -> bool:
        """Check if the egg is ready and add notification if so.
        
        Args:
            current_time: The current in-game time
            
        Returns:
            True if the egg is ready, False otherwise.
        """
        if self.egg is None:
            return False
        
        if self.egg.is_ready(current_time):
            notification = f"Your egg is ready to hatch! It's a {self.egg.pokete_identifier}!"
            if notification not in self.notifications:
                self.notifications.append(notification)
            return True
        return False
    
    def get_egg_status(self, current_time: int) -> str | None:
        """Get a human-readable status of the current egg.
        
        Args:
            current_time: The current in-game time
            
        Returns:
            A status string, or None if no egg exists.
        """
        if self.egg is None:
            return None
        
        if self.egg.is_ready(current_time):
            return "Your egg is ready to collect!"
        
        remaining = self.egg.time_remaining(current_time)
        hours = remaining // 60
        minutes = remaining % 60
        
        if hours > 0:
            return f"Time until hatch: {hours}h {minutes}m"
        return f"Time until hatch: {minutes}m"
    
    def collect_egg(self) -> Poke | None:
        """Collect the hatched Pokete from the egg.
        
        Returns:
            The hatched Poke, or None if no egg or not ready.
        """
        if self.egg is None:
            return None
        
        poke = self.egg.hatch()
        self.egg = None
        # Clear the notification about this egg
        self.notifications = [n for n in self.notifications if "egg is ready" not in n.lower()]
        return poke
    
    def has_notification(self) -> bool:
        """Check if there are any pending notifications."""
        return len(self.notifications) > 0
    
    def get_notifications(self) -> list[str]:
        """Get and clear all pending notifications."""
        notifications = self.notifications.copy()
        self.notifications.clear()
        return notifications
    
    def get_breeding_pair_status(self) -> str:
        """Get a human-readable status of the breeding pair."""
        if self.breeding_pair.is_empty():
            return "No Poketes in breeding pair"
        
        parent1_name = self.breeding_pair.parent1.name if self.breeding_pair.parent1 else "Empty"
        parent2_name = self.breeding_pair.parent2.name if self.breeding_pair.parent2 else "Empty"
        
        status = f"Parent 1: {parent1_name}, Parent 2: {parent2_name}"
        
        if self.breeding_pair.is_complete():
            if self.breeding_pair.is_compatible():
                shared = self.breeding_pair.get_shared_types()
                status += f" (Compatible - shared types: {', '.join(shared)})"
            else:
                status += " (Incompatible - no shared types)"
        
        return status
    
    def return_parents(self) -> tuple[Poke | None, Poke | None]:
        """Return both parents and clear the breeding pair.
        
        Returns:
            A tuple of (parent1, parent2), either can be None.
        """
        parent1 = self.breeding_pair.parent1
        parent2 = self.breeding_pair.parent2
        self.breeding_pair.clear()
        return parent1, parent2
    
    def dict(self) -> BreedingManagerDict:
        """Serialize the breeding manager to a dictionary."""
        return {
            "breeding_pair": self.breeding_pair.dict(),
            "egg": None if self.egg is None else self.egg.dict(),
            "notifications": self.notifications.copy()
        }
    
    def from_dict(self, data: BreedingManagerDict):
        """Load state from a dictionary."""
        self.breeding_pair = BreedingPair.from_dict(data.get("breeding_pair", {"parent1": None, "parent2": None}))
        egg_data = data.get("egg")
        self.egg = None if egg_data is None else Egg.from_dict(egg_data)
        self.notifications = data.get("notifications", [])


# Global breeding manager instance
breeding_manager = BreedingManager()
