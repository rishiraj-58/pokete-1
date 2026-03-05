"""Compatibility checking for breeding pairs."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from pokete.classes.poke import Poke

from .breeding_config import IBreedingConfigProvider, breeding_config


class CompatibilityStatus(Enum):
    """Status codes for compatibility checks."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE_NO_SHARED_TYPES = "incompatible_no_shared_types"
    INCOMPATIBLE_SAME_POKETE = "incompatible_same_pokete"
    INCOMPATIBLE_FALLBACK = "incompatible_fallback"
    INCOMPATIBLE_NULL_POKETE = "incompatible_null_pokete"


@dataclass
class CompatibilityResult:
    """Result of a compatibility check between two poketes."""
    status: CompatibilityStatus
    shared_types: list[str]
    message: str

    @property
    def is_compatible(self) -> bool:
        """Returns True if the poketes are compatible for breeding."""
        return self.status == CompatibilityStatus.COMPATIBLE


class ICompatibilityChecker(Protocol):
    """Interface for compatibility checking."""

    def check_compatibility(
        self, poke1: "Poke", poke2: "Poke"
    ) -> CompatibilityResult:
        """Checks if two poketes are compatible for breeding."""
        ...

    def get_shared_types(self, poke1: "Poke", poke2: "Poke") -> list[str]:
        """Returns the list of shared types between two poketes."""
        ...


class CompatibilityChecker(ICompatibilityChecker):
    """Checks compatibility between poketes for breeding."""

    def __init__(self, config: IBreedingConfigProvider = None):
        self._config = config or breeding_config

    def check_compatibility(
        self, poke1: "Poke", poke2: "Poke"
    ) -> CompatibilityResult:
        """Checks if two poketes are compatible for breeding."""
        if poke1 is None or poke2 is None:
            return CompatibilityResult(
                status=CompatibilityStatus.INCOMPATIBLE_NULL_POKETE,
                shared_types=[],
                message="One or both poketes are null.",
            )

        if poke1.identifier == "__fallback__" or poke2.identifier == "__fallback__":
            return CompatibilityResult(
                status=CompatibilityStatus.INCOMPATIBLE_FALLBACK,
                shared_types=[],
                message="Fallback poketes cannot breed.",
            )

        if poke1 is poke2:
            return CompatibilityResult(
                status=CompatibilityStatus.INCOMPATIBLE_SAME_POKETE,
                shared_types=[],
                message="A pokete cannot breed with itself.",
            )

        shared_types = self.get_shared_types(poke1, poke2)

        if len(shared_types) < self._config.minimum_shared_types:
            return CompatibilityResult(
                status=CompatibilityStatus.INCOMPATIBLE_NO_SHARED_TYPES,
                shared_types=shared_types,
                message=f"Poketes must share at least {self._config.minimum_shared_types} type(s) to breed.",
            )

        return CompatibilityResult(
            status=CompatibilityStatus.COMPATIBLE,
            shared_types=shared_types,
            message="Poketes are compatible for breeding.",
        )

    def get_shared_types(self, poke1: "Poke", poke2: "Poke") -> list[str]:
        """Returns the list of shared types between two poketes."""
        if poke1 is None or poke2 is None:
            return []

        poke1_types = set(t.name for t in poke1.types)
        poke2_types = set(t.name for t in poke2.types)

        return list(poke1_types.intersection(poke2_types))
