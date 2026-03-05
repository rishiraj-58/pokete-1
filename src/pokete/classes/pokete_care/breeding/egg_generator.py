"""Egg generation for the breeding system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from pokete.classes.poke import Poke

from .breeding_config import (
    IBreedingConfigProvider,
    HatchTimeStrategy,
    breeding_config,
)
from .stat_calculator import IStatCalculator, StatCalculator, CalculatedStats
from .models import EggDict


@dataclass
class EggPokete:
    """Represents an egg pokete that will hatch into a new pokete."""
    parent1_identifier: str
    parent2_identifier: str
    child_identifier: str
    child_xp: int
    child_hp: int
    child_attacks: list[str]
    child_shiny: bool
    child_nature: dict
    base_atc: int
    base_defense: int
    base_initiative: int
    created_at: int
    hatch_time: int

    def dict(self) -> EggDict:
        """Serializes the egg to a dictionary."""
        return {
            "parent1_identifier": self.parent1_identifier,
            "parent2_identifier": self.parent2_identifier,
            "child_identifier": self.child_identifier,
            "child_xp": self.child_xp,
            "child_hp": self.child_hp,
            "child_attacks": self.child_attacks,
            "child_shiny": self.child_shiny,
            "child_nature": self.child_nature,
            "base_atc": self.base_atc,
            "base_defense": self.base_defense,
            "base_initiative": self.base_initiative,
            "created_at": self.created_at,
            "hatch_time": self.hatch_time,
        }

    @classmethod
    def from_dict(cls, data: EggDict) -> "EggPokete":
        """Deserializes an egg from a dictionary."""
        return cls(
            parent1_identifier=data["parent1_identifier"],
            parent2_identifier=data["parent2_identifier"],
            child_identifier=data["child_identifier"],
            child_xp=data["child_xp"],
            child_hp=data["child_hp"],
            child_attacks=data["child_attacks"],
            child_shiny=data["child_shiny"],
            child_nature=data["child_nature"],
            base_atc=data["base_atc"],
            base_defense=data["base_defense"],
            base_initiative=data["base_initiative"],
            created_at=data["created_at"],
            hatch_time=data["hatch_time"],
        )

    def is_ready_to_hatch(self, current_time: int) -> bool:
        """Checks if the egg is ready to hatch based on current time."""
        return current_time >= self.created_at + self.hatch_time


class IEggGenerator(Protocol):
    """Interface for egg generation."""

    def generate_egg(
        self, parent1: "Poke", parent2: "Poke", current_time: int
    ) -> EggPokete:
        """Generates an egg from two parent poketes."""
        ...

    def calculate_hatch_time(self, parent1: "Poke", parent2: "Poke") -> int:
        """Calculates the time required for an egg to hatch."""
        ...


class EggGenerator(IEggGenerator):
    """Generates eggs from breeding pairs."""

    def __init__(
        self,
        config: IBreedingConfigProvider = None,
        stat_calculator: IStatCalculator = None,
    ):
        self._config = config or breeding_config
        self._stat_calculator = stat_calculator or StatCalculator(self._config)
        self._hatch_time_handlers = {
            HatchTimeStrategy.FIXED: self._calculate_fixed_hatch_time,
            HatchTimeStrategy.LEVEL_BASED: self._calculate_level_based_hatch_time,
            HatchTimeStrategy.RARITY_BASED: self._calculate_rarity_based_hatch_time,
            HatchTimeStrategy.COMBINED: self._calculate_combined_hatch_time,
        }

    def generate_egg(
        self, parent1: "Poke", parent2: "Poke", current_time: int
    ) -> EggPokete:
        """Generates an egg from two parent poketes."""
        child_identifier = self._select_child_identifier(parent1, parent2)
        stats = self._stat_calculator.calculate_offspring_stats(parent1, parent2)
        hatch_time = self.calculate_hatch_time(parent1, parent2)
        is_shiny = self._determine_shiny_status(parent1, parent2)
        attacks = self._inherit_attacks(parent1, parent2)
        nature = self._generate_nature()

        return EggPokete(
            parent1_identifier=parent1.identifier,
            parent2_identifier=parent2.identifier,
            child_identifier=child_identifier,
            child_xp=self._config.egg_starting_xp,
            child_hp=stats.hp,
            child_attacks=attacks,
            child_shiny=is_shiny,
            child_nature=nature,
            base_atc=stats.atc,
            base_defense=stats.defense,
            base_initiative=stats.initiative,
            created_at=current_time,
            hatch_time=hatch_time,
        )

    def calculate_hatch_time(self, parent1: "Poke", parent2: "Poke") -> int:
        """Calculates the time required for an egg to hatch."""
        strategy = self._config.hatch_time_strategy
        handler = self._hatch_time_handlers.get(
            strategy, self._calculate_fixed_hatch_time
        )
        return handler(parent1, parent2)

    def _calculate_fixed_hatch_time(
        self, parent1: "Poke", parent2: "Poke"
    ) -> int:
        """Returns a fixed hatch time regardless of parents."""
        return self._config.base_hatch_time

    def _calculate_level_based_hatch_time(
        self, parent1: "Poke", parent2: "Poke"
    ) -> int:
        """Calculates hatch time based on average parent level."""
        avg_level = (parent1.lvl() + parent2.lvl()) / 2
        return int(
            self._config.base_hatch_time
            + avg_level * self._config.level_hatch_time_multiplier
        )

    def _calculate_rarity_based_hatch_time(
        self, parent1: "Poke", parent2: "Poke"
    ) -> int:
        """Calculates hatch time based on average parent rarity."""
        avg_rarity = (parent1.inf.rarity + parent2.inf.rarity) / 2
        rarity_factor = 1.0 / max(avg_rarity, 0.1)
        return int(
            self._config.base_hatch_time
            + rarity_factor * self._config.rarity_hatch_time_multiplier
        )

    def _calculate_combined_hatch_time(
        self, parent1: "Poke", parent2: "Poke"
    ) -> int:
        """Combines level and rarity factors for hatch time calculation."""
        level_component = self._calculate_level_based_hatch_time(parent1, parent2)
        rarity_component = self._calculate_rarity_based_hatch_time(parent1, parent2)
        return int((level_component + rarity_component) / 2)

    def _select_child_identifier(
        self, parent1: "Poke", parent2: "Poke"
    ) -> str:
        """Selects which parent's species the child will be."""
        return random.choice([parent1.identifier, parent2.identifier])

    def _determine_shiny_status(
        self, parent1: "Poke", parent2: "Poke"
    ) -> bool:
        """Determines if the offspring will be shiny."""
        base_chance = 1 / 500
        multiplier = self._config.shiny_chance_multiplier
        if parent1.shiny or parent2.shiny:
            multiplier *= 2
        if parent1.shiny and parent2.shiny:
            multiplier *= 2
        final_chance = base_chance * multiplier
        return random.random() < final_chance

    def _inherit_attacks(
        self, parent1: "Poke", parent2: "Poke"
    ) -> list[str]:
        """Determines which attacks the offspring will inherit."""
        all_attacks = list(set(parent1.attacks[:2] + parent2.attacks[:2]))
        return all_attacks[:4]

    def _generate_nature(self) -> dict:
        """Generates a random nature for the offspring."""
        from pokete.classes.poke import PokeNature
        nature = PokeNature.random()
        return nature.dict()
