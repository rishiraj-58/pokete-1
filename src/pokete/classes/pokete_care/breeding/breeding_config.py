"""Configuration for the breeding system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class HatchTimeStrategy(Enum):
    """Strategies for calculating hatch time."""
    FIXED = "fixed"
    LEVEL_BASED = "level_based"
    RARITY_BASED = "rarity_based"
    COMBINED = "combined"


class StatInheritanceStrategy(Enum):
    """Strategies for inheriting stats from parents."""
    WEIGHTED_AVERAGE = "weighted_average"
    RANDOM_PARENT = "random_parent"
    BEST_PARENT = "best_parent"
    AVERAGE = "average"


class IBreedingConfigProvider(Protocol):
    """Interface for breeding configuration providers."""

    @property
    def base_hatch_time(self) -> int:
        """Base time in game minutes required for an egg to hatch."""
        ...

    @property
    def hatch_time_strategy(self) -> HatchTimeStrategy:
        """Strategy used to calculate hatch time."""
        ...

    @property
    def stat_inheritance_strategy(self) -> StatInheritanceStrategy:
        """Strategy used for stat inheritance."""
        ...

    @property
    def parent1_weight(self) -> float:
        """Weight given to parent1 in weighted average calculations."""
        ...

    @property
    def parent2_weight(self) -> float:
        """Weight given to parent2 in weighted average calculations."""
        ...

    @property
    def shiny_chance_multiplier(self) -> float:
        """Multiplier for shiny chance when breeding."""
        ...

    @property
    def minimum_shared_types(self) -> int:
        """Minimum number of shared types required for compatibility."""
        ...

    @property
    def egg_starting_xp(self) -> int:
        """Starting XP for newly hatched poketes."""
        ...

    @property
    def level_hatch_time_multiplier(self) -> float:
        """Multiplier applied to hatch time based on parent levels."""
        ...

    @property
    def rarity_hatch_time_multiplier(self) -> float:
        """Multiplier applied to hatch time based on parent rarity."""
        ...


@dataclass
class BreedingConfig(IBreedingConfigProvider):
    """Concrete configuration for the breeding system."""

    _base_hatch_time: int = 300
    _hatch_time_strategy: HatchTimeStrategy = HatchTimeStrategy.COMBINED
    _stat_inheritance_strategy: StatInheritanceStrategy = StatInheritanceStrategy.WEIGHTED_AVERAGE
    _parent1_weight: float = 0.5
    _parent2_weight: float = 0.5
    _shiny_chance_multiplier: float = 2.0
    _minimum_shared_types: int = 1
    _egg_starting_xp: int = 0
    _level_hatch_time_multiplier: float = 2.0
    _rarity_hatch_time_multiplier: float = 50.0

    @property
    def base_hatch_time(self) -> int:
        return self._base_hatch_time

    @property
    def hatch_time_strategy(self) -> HatchTimeStrategy:
        return self._hatch_time_strategy

    @property
    def stat_inheritance_strategy(self) -> StatInheritanceStrategy:
        return self._stat_inheritance_strategy

    @property
    def parent1_weight(self) -> float:
        return self._parent1_weight

    @property
    def parent2_weight(self) -> float:
        return self._parent2_weight

    @property
    def shiny_chance_multiplier(self) -> float:
        return self._shiny_chance_multiplier

    @property
    def rarity_hatch_time_multiplier(self) -> float:
        return self._rarity_hatch_time_multiplier

    @property
    def level_hatch_time_multiplier(self) -> float:
        return self._level_hatch_time_multiplier

    @property
    def shiny_chance_multiplier(self) -> float:
        return self._shiny_chance_multiplier

    @property
    def minimum_shared_types(self) -> int:
        return self._minimum_shared_types

    @property
    def egg_starting_xp(self) -> int:
        return self._egg_starting_xp

    def with_base_hatch_time(self, value: int) -> "BreedingConfig":
        """Returns a new config with updated base_hatch_time."""
        return BreedingConfig(
            _base_hatch_time=value,
            _hatch_time_strategy=self._hatch_time_strategy,
            _stat_inheritance_strategy=self._stat_inheritance_strategy,
            _parent1_weight=self._parent1_weight,
            _parent2_weight=self._parent2_weight,
            _shiny_chance_multiplier=self._shiny_chance_multiplier,
            _minimum_shared_types=self._minimum_shared_types,
            _egg_starting_xp=self._egg_starting_xp,
            _level_hatch_time_multiplier=self._level_hatch_time_multiplier,
            _rarity_hatch_time_multiplier=self._rarity_hatch_time_multiplier,
        )

    def to_dict(self) -> dict:
        """Serializes the config to a dictionary."""
        return {
            "base_hatch_time": self._base_hatch_time,
            "hatch_time_strategy": self._hatch_time_strategy.value,
            "stat_inheritance_strategy": self._stat_inheritance_strategy.value,
            "parent1_weight": self._parent1_weight,
            "parent2_weight": self._parent2_weight,
            "shiny_chance_multiplier": self._shiny_chance_multiplier,
            "minimum_shared_types": self._minimum_shared_types,
            "egg_starting_xp": self._egg_starting_xp,
            "level_hatch_time_multiplier": self._level_hatch_time_multiplier,
            "rarity_hatch_time_multiplier": self._rarity_hatch_time_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BreedingConfig":
        """Deserializes the config from a dictionary."""
        return cls(
            _base_hatch_time=data.get("base_hatch_time", 300),
            _hatch_time_strategy=HatchTimeStrategy(
                data.get("hatch_time_strategy", "combined")
            ),
            _stat_inheritance_strategy=StatInheritanceStrategy(
                data.get("stat_inheritance_strategy", "weighted_average")
            ),
            _parent1_weight=data.get("parent1_weight", 0.5),
            _parent2_weight=data.get("parent2_weight", 0.5),
            _shiny_chance_multiplier=data.get("shiny_chance_multiplier", 2.0),
            _minimum_shared_types=data.get("minimum_shared_types", 1),
            _egg_starting_xp=data.get("egg_starting_xp", 0),
            _level_hatch_time_multiplier=data.get("level_hatch_time_multiplier", 2.0),
            _rarity_hatch_time_multiplier=data.get("rarity_hatch_time_multiplier", 50.0),
        )


breeding_config = BreedingConfig()
