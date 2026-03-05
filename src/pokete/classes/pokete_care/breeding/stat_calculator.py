"""Stat calculation for bred poketes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from pokete.classes.poke import Poke

from .breeding_config import (
    IBreedingConfigProvider,
    StatInheritanceStrategy,
    breeding_config,
)


@dataclass
class CalculatedStats:
    """Calculated stats for a bred pokete."""
    atc: int
    defense: int
    initiative: int
    hp: int
    miss_chance: float


class IStatCalculator(Protocol):
    """Interface for stat calculation."""

    def calculate_offspring_stats(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates the stats for offspring based on parents."""
        ...


class StatCalculator(IStatCalculator):
    """Calculates stats for bred poketes using configured strategies."""

    def __init__(self, config: IBreedingConfigProvider = None):
        self._config = config or breeding_config
        self._strategy_handlers = {
            StatInheritanceStrategy.WEIGHTED_AVERAGE: self._calculate_weighted_average,
            StatInheritanceStrategy.RANDOM_PARENT: self._calculate_random_parent,
            StatInheritanceStrategy.BEST_PARENT: self._calculate_best_parent,
            StatInheritanceStrategy.AVERAGE: self._calculate_average,
        }

    def calculate_offspring_stats(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates the stats for offspring based on parents."""
        strategy = self._config.stat_inheritance_strategy
        handler = self._strategy_handlers.get(
            strategy, self._calculate_weighted_average
        )
        return handler(parent1, parent2)

    def _calculate_weighted_average(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates stats using weighted average of parents."""
        w1 = self._config.parent1_weight
        w2 = self._config.parent2_weight
        total_weight = w1 + w2

        return CalculatedStats(
            atc=int((parent1.inf.atc * w1 + parent2.inf.atc * w2) / total_weight),
            defense=int(
                (parent1.inf.defense * w1 + parent2.inf.defense * w2) / total_weight
            ),
            initiative=int(
                (parent1.inf.initiative * w1 + parent2.inf.initiative * w2)
                / total_weight
            ),
            hp=int((parent1.inf.hp * w1 + parent2.inf.hp * w2) / total_weight),
            miss_chance=(
                parent1.inf.miss_chance * w1 + parent2.inf.miss_chance * w2
            )
            / total_weight,
        )

    def _calculate_random_parent(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates stats by randomly selecting from each parent."""
        selected_atc = random.choice([parent1.inf.atc, parent2.inf.atc])
        selected_defense = random.choice([parent1.inf.defense, parent2.inf.defense])
        selected_initiative = random.choice(
            [parent1.inf.initiative, parent2.inf.initiative]
        )
        selected_hp = random.choice([parent1.inf.hp, parent2.inf.hp])
        selected_miss_chance = random.choice(
            [parent1.inf.miss_chance, parent2.inf.miss_chance]
        )

        return CalculatedStats(
            atc=selected_atc,
            defense=selected_defense,
            initiative=selected_initiative,
            hp=selected_hp,
            miss_chance=selected_miss_chance,
        )

    def _calculate_best_parent(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates stats by taking the best value from each parent."""
        return CalculatedStats(
            atc=max(parent1.inf.atc, parent2.inf.atc),
            defense=max(parent1.inf.defense, parent2.inf.defense),
            initiative=max(parent1.inf.initiative, parent2.inf.initiative),
            hp=max(parent1.inf.hp, parent2.inf.hp),
            miss_chance=min(parent1.inf.miss_chance, parent2.inf.miss_chance),
        )

    def _calculate_average(
        self, parent1: "Poke", parent2: "Poke"
    ) -> CalculatedStats:
        """Calculates stats using simple average of parents."""
        return CalculatedStats(
            atc=int((parent1.inf.atc + parent2.inf.atc) / 2),
            defense=int((parent1.inf.defense + parent2.inf.defense) / 2),
            initiative=int((parent1.inf.initiative + parent2.inf.initiative) / 2),
            hp=int((parent1.inf.hp + parent2.inf.hp) / 2),
            miss_chance=(parent1.inf.miss_chance + parent2.inf.miss_chance) / 2,
        )
