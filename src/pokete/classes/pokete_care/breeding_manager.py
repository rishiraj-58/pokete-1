"""Breeding system for the Pokete care facility"""

import random
from datetime import datetime
from typing import TypedDict

from pokete.base.ui.notify import notifier

from ..poke import Poke, PokeNature, Stats
from .. import timer


class BreedingPairDict(TypedDict):
    parent1: dict | None
    parent2: dict | None
    start_time: int
    egg_ready: bool


class EggDict(TypedDict):
    identifier: str
    hp: int
    atc: int
    defense: int
    initiative: int
    attacks: list[str]
    parent1_identifier: str
    parent2_identifier: str
    hatch_time: int


class BreedingManager:
    """Manages pokete breeding in the care facility
    ARGS:
        parent1: First parent Pokete
        parent2: Second parent Pokete
        start_time: The in-game timestamp when breeding started
        egg: The resulting egg pokete (when ready)
        egg_ready: Whether the egg is ready to collect"""

    BASE_HATCH_TIME = 500

    def __init__(self):
        self.parent1: Poke | None = None
        self.parent2: Poke | None = None
        self.start_time: int = 0
        self.egg: Poke | None = None
        self.egg_ready: bool = False
        self._notified: bool = False

    def are_compatible(self, poke1: Poke, poke2: Poke) -> bool:
        """Check if two poketes share at least one type
        ARGS:
            poke1: First Pokete
            poke2: Second Pokete
        RETURNS:
            True if compatible, False otherwise"""
        types1 = set(t.name for t in poke1.types)
        types2 = set(t.name for t in poke2.types)
        return len(types1 & types2) > 0

    def get_shared_types(self, poke1: Poke, poke2: Poke) -> list[str]:
        """Get the shared types between two poketes
        ARGS:
            poke1: First Pokete
            poke2: Second Pokete
        RETURNS:
            List of shared type names"""
        types1 = set(t.name for t in poke1.types)
        types2 = set(t.name for t in poke2.types)
        return list(types1 & types2)

    def start_breeding(self, parent1: Poke, parent2: Poke) -> bool:
        """Start a breeding session between two poketes
        ARGS:
            parent1: First parent Pokete
            parent2: Second parent Pokete
        RETURNS:
            True if breeding started successfully, False otherwise"""
        if not self.are_compatible(parent1, parent2):
            return False
        if self.parent1 is not None or self.parent2 is not None:
            return False

        self.parent1 = parent1
        self.parent2 = parent2
        self.start_time = timer.time.time
        self.egg_ready = False
        self.egg = None
        self._notified = False
        return True

    def get_hatch_time(self) -> int:
        """Calculate the hatch time based on parent levels
        RETURNS:
            Hatch time in in-game minutes"""
        if self.parent1 is None or self.parent2 is None:
            return 0
        avg_level = (self.parent1.lvl() + self.parent2.lvl()) / 2
        return int(self.BASE_HATCH_TIME + avg_level * 10)

    def get_time_remaining(self) -> int:
        """Get the remaining time until egg is ready
        RETURNS:
            Time remaining in in-game minutes"""
        if self.parent1 is None or self.parent2 is None:
            return 0
        elapsed = timer.time.time - self.start_time
        remaining = self.get_hatch_time() - elapsed
        return max(0, remaining)

    def _compute_weighted_stat(self, stat1: int, stat2: int) -> int:
        """Compute weighted average of a stat with some randomness
        ARGS:
            stat1: Stat from parent 1
            stat2: Stat from parent 2
        RETURNS:
            Computed stat for offspring"""
        base = (stat1 + stat2) / 2
        variation = random.uniform(-0.1, 0.1) * base
        return max(1, int(base + variation))

    def _select_attacks(self) -> list[str]:
        """Select attacks for the offspring from both parents
        RETURNS:
            List of attack names (max 4)"""
        if self.parent1 is None or self.parent2 is None:
            return []
        all_attacks = list(set(self.parent1.attacks + self.parent2.attacks))
        random.shuffle(all_attacks)
        return all_attacks[:4]

    def _select_offspring_identifier(self) -> str:
        """Select which parent's species the offspring will be
        RETURNS:
            The identifier of the offspring species"""
        if self.parent1 is None or self.parent2 is None:
            return "__fallback__"
        return random.choice([self.parent1.identifier, self.parent2.identifier])

    def generate_egg(self) -> Poke | None:
        """Generate an egg pokete from the breeding pair
        RETURNS:
            The egg Pokete or None if breeding not active"""
        if self.parent1 is None or self.parent2 is None:
            return None

        offspring_id = self._select_offspring_identifier()
        attacks = self._select_attacks()

        hp_bonus = self._compute_weighted_stat(
            self.parent1.inf.hp, self.parent2.inf.hp
        ) - self.parent1.inf.hp if offspring_id == self.parent1.identifier else \
            self._compute_weighted_stat(
                self.parent1.inf.hp, self.parent2.inf.hp
            ) - self.parent2.inf.hp

        shiny = random.randint(0, 100) == 0

        egg = Poke(
            offspring_id,
            _xp=0,
            _attacks=attacks if attacks else None,
            shiny=shiny,
        )

        egg.poke_stats = Stats(
            egg.name,
            ownership_date=datetime.now(),
            caught_with="bred",
        )

        return egg

    def check_and_notify(self):
        """Check if egg is ready and notify user if so"""
        if self.parent1 is None or self.parent2 is None:
            return

        if self.get_time_remaining() == 0 and not self.egg_ready:
            self.egg_ready = True
            self.egg = self.generate_egg()
            if not self._notified:
                notifier.notify(
                    "Egg Ready!",
                    "Pokete Care",
                    f"Your {self.parent1.name} and {self.parent2.name} "
                    "have produced an egg!"
                )
                self._notified = True

    def collect_egg(self) -> Poke | None:
        """Collect the ready egg and return parents
        RETURNS:
            Tuple of (egg, parent1, parent2) or None if not ready"""
        if not self.egg_ready or self.egg is None:
            return None

        egg = self.egg
        self.egg = None
        self.egg_ready = False
        self._notified = False
        return egg

    def collect_parents(self) -> tuple[Poke | None, Poke | None]:
        """Collect the parents back
        RETURNS:
            Tuple of (parent1, parent2)"""
        p1, p2 = self.parent1, self.parent2
        self.parent1 = None
        self.parent2 = None
        self.start_time = 0
        return p1, p2

    def is_breeding(self) -> bool:
        """Check if breeding is currently in progress
        RETURNS:
            True if breeding, False otherwise"""
        return self.parent1 is not None and self.parent2 is not None

    def from_dict(self, _dict: dict):
        """Assembles a BreedingManager from _dict"""
        self.start_time = _dict.get("start_time", 0)
        self.egg_ready = _dict.get("egg_ready", False)
        self._notified = _dict.get("notified", False)

        parent1_dict = _dict.get("parent1")
        self.parent1 = None if parent1_dict is None else Poke.from_dict(parent1_dict)

        parent2_dict = _dict.get("parent2")
        self.parent2 = None if parent2_dict is None else Poke.from_dict(parent2_dict)

        egg_dict = _dict.get("egg")
        self.egg = None if egg_dict is None else Poke.from_dict(egg_dict)

    def dict(self) -> dict:
        """Returns a dict from the object"""
        return {
            "parent1": None if self.parent1 is None else self.parent1.dict(),
            "parent2": None if self.parent2 is None else self.parent2.dict(),
            "start_time": self.start_time,
            "egg_ready": self.egg_ready,
            "egg": None if self.egg is None else self.egg.dict(),
            "notified": self._notified,
        }


breeding_manager = BreedingManager()
