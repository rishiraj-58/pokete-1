"""Breeding system for the Pokete care facility.
Two compatible Poketes (sharing at least one type) can breed when kept together."""

import random
from dataclasses import dataclass
from typing import Optional

from pokete.base.ui.notify import notifier

from ..poke import Poke, PokeNature
from .. import timer


# Base hatching time in in-game minutes
BASE_HATCHING_TIME = 300


@dataclass
class BreedingPairDict:
    """TypedDict for breeding pair serialization"""
    parent1: dict
    parent2: dict
    start_time: int
    hatching_time: int


@dataclass
class BreedingManagerDict:
    """TypedDict for breeding manager serialization"""
    breeding_pair: Optional[dict]
    egg: Optional[dict]
    egg_ready: bool
    notified: bool


class BreedingPair:
    """Represents a pair of Poketes being bred together.
    ARGS:
        parent1: First parent Pokete
        parent2: Second parent Pokete
        start_time: The in-game time when breeding started
        hatching_time: Time required for egg to be ready"""

    def __init__(
        self,
        parent1: Poke,
        parent2: Poke,
        start_time: int,
        hatching_time: int
    ):
        self.parent1 = parent1
        self.parent2 = parent2
        self.start_time = start_time
        self.hatching_time = hatching_time

    def is_ready(self, current_time: int) -> bool:
        """Checks if the egg is ready to hatch.
        ARGS:
            current_time: Current in-game time
        RETURNS:
            bool: True if egg is ready"""
        return (current_time - self.start_time) >= self.hatching_time

    def time_remaining(self, current_time: int) -> int:
        """Returns remaining time until egg is ready.
        ARGS:
            current_time: Current in-game time
        RETURNS:
            int: Time remaining in in-game minutes"""
        remaining = self.hatching_time - (current_time - self.start_time)
        return max(0, remaining)

    def dict(self) -> dict:
        """Returns a dict from the object"""
        return {
            "parent1": self.parent1.dict(),
            "parent2": self.parent2.dict(),
            "start_time": self.start_time,
            "hatching_time": self.hatching_time,
        }

    @classmethod
    def from_dict(cls, _dict: dict) -> "BreedingPair":
        """Assembles a BreedingPair from _dict"""
        return cls(
            parent1=Poke.from_dict(_dict["parent1"]),
            parent2=Poke.from_dict(_dict["parent2"]),
            start_time=_dict["start_time"],
            hatching_time=_dict["hatching_time"],
        )


class BreedingManager:
    """Manages the breeding system in the Pokete care facility.
    Tracks breeding pairs, computes hatching times, and generates egg Poketes."""

    def __init__(self):
        self.breeding_pair: Optional[BreedingPair] = None
        self.egg: Optional[Poke] = None
        self.egg_ready: bool = False
        self._notified: bool = False

    def are_compatible(self, poke1: Poke, poke2: Poke) -> bool:
        """Checks if two Poketes are compatible for breeding.
        They must share at least one type.
        ARGS:
            poke1: First Pokete
            poke2: Second Pokete
        RETURNS:
            bool: True if compatible"""
        types1 = set(self.get_type_names(poke1))
        types2 = set(self.get_type_names(poke2))
        return len(types1 & types2) > 0

    @staticmethod
    def get_type_names(poke: Poke) -> list[str]:
        """Gets type names from a Pokete.
        ARGS:
            poke: The Pokete
        RETURNS:
            list[str]: List of type names"""
        return [t.name for t in poke.types]

    def compute_hatching_time(self, parent1: Poke, parent2: Poke) -> int:
        """Computes the hatching time based on parent levels and rarity.
        Higher level parents produce faster hatching eggs.
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
        RETURNS:
            int: Hatching time in in-game minutes"""
        avg_level = (parent1.lvl() + parent2.lvl()) / 2
        level_modifier = max(0.5, 1.0 - (avg_level / 100))
        return int(BASE_HATCHING_TIME * level_modifier)

    def start_breeding(self, parent1: Poke, parent2: Poke) -> bool:
        """Starts breeding two Poketes.
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
        RETURNS:
            bool: True if breeding started successfully"""
        if not self.are_compatible(parent1, parent2):
            return False

        if self.breeding_pair is not None or self.egg is not None:
            return False

        hatching_time = self.compute_hatching_time(parent1, parent2)
        self.breeding_pair = BreedingPair(
            parent1=parent1,
            parent2=parent2,
            start_time=timer.time.time,
            hatching_time=hatching_time,
        )
        self._notified = False
        return True

    def _compute_weighted_stat(
        self, stat1: int, stat2: int, weight1: float = 0.5
    ) -> int:
        """Computes a weighted average of two stats.
        ARGS:
            stat1: First stat value
            stat2: Second stat value
            weight1: Weight for first stat (0.0 to 1.0)
        RETURNS:
            int: Weighted average stat"""
        weight2 = 1.0 - weight1
        base = stat1 * weight1 + stat2 * weight2
        variation = random.uniform(-0.1, 0.1) * base
        return max(1, int(base + variation))

    def _select_offspring_type(self, parent1: Poke, parent2: Poke) -> str:
        """Selects which parent's species the offspring will be.
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
        RETURNS:
            str: The identifier of the selected parent species"""
        return random.choice([parent1.identifier, parent2.identifier])

    def _generate_offspring_attacks(
        self, parent1: Poke, parent2: Poke, offspring_type: str
    ) -> list[str]:
        """Generates the attack list for offspring.
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
            offspring_type: The offspring's species identifier
        RETURNS:
            list[str]: List of attack names"""
        from ..asset_service.service import asset_service

        base_poke = asset_service.get_base_assets().pokes[offspring_type]
        base_attacks = list(base_poke.attacks[:2])

        parent_attacks = list(set(parent1.attacks + parent2.attacks))
        inherited = [a for a in parent_attacks if a not in base_attacks]
        if inherited:
            inherited_attack = random.choice(inherited)
            base_attacks.append(inherited_attack)

        return base_attacks[:4]

    def generate_egg(self, parent1: Poke, parent2: Poke) -> Poke:
        """Generates an egg Pokete from two parents.
        Base stats are computed as weighted averages.
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
        RETURNS:
            Poke: The offspring Pokete"""
        offspring_type = self._select_offspring_type(parent1, parent2)
        attacks = self._generate_offspring_attacks(parent1, parent2, offspring_type)

        weight1 = random.uniform(0.3, 0.7)

        offspring = Poke(
            offspring_type,
            _xp=1,
            _hp="SKIP",
            _attacks=attacks,
            player=True,
            shiny=(random.randint(0, 300) == 0),
            nature=PokeNature.random().dict(),
        )

        return offspring

    def check_and_generate_egg(self) -> Optional[Poke]:
        """Checks if breeding is complete and generates egg if ready.
        RETURNS:
            Optional[Poke]: The egg Pokete if ready, None otherwise"""
        if self.breeding_pair is None:
            return None

        if not self.breeding_pair.is_ready(timer.time.time):
            return None

        if self.egg is None:
            self.egg = self.generate_egg(
                self.breeding_pair.parent1,
                self.breeding_pair.parent2
            )
            self.egg_ready = True

        return self.egg

    def notify_if_ready(self):
        """Sends notification if egg is ready and not yet notified."""
        if self.egg_ready and not self._notified:
            notifier.notify(
                "Egg Ready!",
                "Pokete Care",
                "Your Pokete egg is ready to collect!"
            )
            self._notified = True

    def collect_egg(self) -> Optional[Poke]:
        """Collects the ready egg and resets breeding state.
        RETURNS:
            Optional[Poke]: The egg Pokete if available"""
        if not self.egg_ready or self.egg is None:
            return None

        collected_egg = self.egg
        self.egg = None
        self.egg_ready = False
        self.breeding_pair = None
        self._notified = False
        return collected_egg

    def get_parents(self) -> Optional[tuple[Poke, Poke]]:
        """Gets the current breeding parents.
        RETURNS:
            Optional[tuple[Poke, Poke]]: The parent pair if breeding"""
        if self.breeding_pair is None:
            return None
        return (self.breeding_pair.parent1, self.breeding_pair.parent2)

    def cancel_breeding(self) -> Optional[tuple[Poke, Poke]]:
        """Cancels current breeding and returns parents.
        RETURNS:
            Optional[tuple[Poke, Poke]]: The parent pair"""
        if self.breeding_pair is None:
            return None

        parents = (self.breeding_pair.parent1, self.breeding_pair.parent2)
        self.breeding_pair = None
        self.egg = None
        self.egg_ready = False
        self._notified = False
        return parents

    def get_status(self) -> dict:
        """Gets the current breeding status.
        RETURNS:
            dict: Status information"""
        if self.breeding_pair is None:
            return {"status": "idle"}

        current_time = timer.time.time
        if self.egg_ready:
            return {
                "status": "ready",
                "egg": self.egg,
            }

        return {
            "status": "breeding",
            "parent1": self.breeding_pair.parent1,
            "parent2": self.breeding_pair.parent2,
            "time_remaining": self.breeding_pair.time_remaining(current_time),
            "progress": self._get_progress(current_time),
        }

    def _get_progress(self, current_time: int) -> float:
        """Gets breeding progress as a percentage.
        ARGS:
            current_time: Current in-game time
        RETURNS:
            float: Progress from 0.0 to 1.0"""
        if self.breeding_pair is None:
            return 0.0

        elapsed = current_time - self.breeding_pair.start_time
        total = self.breeding_pair.hatching_time
        return min(1.0, elapsed / total) if total > 0 else 1.0

    def dict(self) -> dict:
        """Returns a dict from the object for saving"""
        return {
            "breeding_pair": (
                self.breeding_pair.dict() if self.breeding_pair else None
            ),
            "egg": self.egg.dict() if self.egg else None,
            "egg_ready": self.egg_ready,
            "notified": self._notified,
        }

    def from_dict(self, _dict: dict):
        """Assembles a BreedingManager from _dict"""
        self.breeding_pair = (
            BreedingPair.from_dict(_dict["breeding_pair"])
            if _dict.get("breeding_pair") else None
        )
        self.egg = (
            Poke.from_dict(_dict["egg"]) if _dict.get("egg") else None
        )
        self.egg_ready = _dict.get("egg_ready", False)
        self._notified = _dict.get("notified", False)


breeding_manager = BreedingManager()
