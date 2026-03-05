"""Breeding manager for the pokete care facility."""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from pokete.classes.poke import Poke

from .breeding_config import IBreedingConfigProvider, breeding_config
from .compatibility_checker import (
    ICompatibilityChecker,
    CompatibilityChecker,
    CompatibilityResult,
)
from .stat_calculator import IStatCalculator, StatCalculator
from .egg_generator import IEggGenerator, EggGenerator, EggPokete
from .breeding_notification_service import (
    IBreedingNotificationService,
    BreedingNotificationService,
)
from .breeding_pair import BreedingPair
from .models import BreedingStateDict


class BreedingManager:
    """Manages the breeding system in the pokete care facility."""

    def __init__(
        self,
        config: IBreedingConfigProvider = None,
        compatibility_checker: ICompatibilityChecker = None,
        stat_calculator: IStatCalculator = None,
        egg_generator: IEggGenerator = None,
        notification_service: IBreedingNotificationService = None,
    ):
        self._config = config or breeding_config
        self._compatibility_checker = compatibility_checker or CompatibilityChecker(
            self._config
        )
        self._stat_calculator = stat_calculator or StatCalculator(self._config)
        self._egg_generator = egg_generator or EggGenerator(
            self._config, self._stat_calculator
        )
        self._notification_service = (
            notification_service or BreedingNotificationService()
        )

        self._active_breeding_pair: Optional[BreedingPair] = None
        self._pending_eggs: list[EggPokete] = []
        self._collected_eggs_count: int = 0
        self._egg_ready_notified: bool = False

    @property
    def has_active_breeding(self) -> bool:
        """Returns True if there is an active breeding pair."""
        return self._active_breeding_pair is not None

    @property
    def active_breeding_pair(self) -> Optional[BreedingPair]:
        """Returns the active breeding pair."""
        return self._active_breeding_pair

    @property
    def pending_eggs_count(self) -> int:
        """Returns the number of pending eggs."""
        return len(self._pending_eggs)

    @property
    def collected_eggs_count(self) -> int:
        """Returns the total number of collected eggs."""
        return self._collected_eggs_count

    def check_compatibility(
        self, poke1: "Poke", poke2: "Poke"
    ) -> CompatibilityResult:
        """Checks if two poketes are compatible for breeding."""
        return self._compatibility_checker.check_compatibility(poke1, poke2)

    def start_breeding(
        self, parent1: "Poke", parent2: "Poke", current_time: int
    ) -> bool:
        """Starts breeding between two poketes."""
        if self._active_breeding_pair is not None:
            return False

        compatibility = self.check_compatibility(parent1, parent2)
        if not compatibility.is_compatible:
            self._notification_service.notify_incompatible_pair(
                compatibility.message
            )
            return False

        egg = self._egg_generator.generate_egg(parent1, parent2, current_time)

        self._active_breeding_pair = BreedingPair(
            parent1=parent1,
            parent2=parent2,
            start_time=current_time,
            hatch_time=egg.hatch_time,
            egg=egg,
            is_ready=False,
        )
        self._egg_ready_notified = False

        self._notification_service.notify_breeding_started(
            parent1.name, parent2.name, egg.hatch_time
        )

        return True

    def update(self, current_time: int) -> None:
        """Updates the breeding state based on current time."""
        if self._active_breeding_pair is None:
            return

        if self._active_breeding_pair.egg is None:
            return

        if self._active_breeding_pair.egg.is_ready_to_hatch(current_time):
            if not self._active_breeding_pair.is_ready:
                self._active_breeding_pair.is_ready = True
            if not self._egg_ready_notified:
                self._notification_service.notify_egg_ready(
                    self._active_breeding_pair.egg.child_identifier
                )
                self._egg_ready_notified = True

    def is_egg_ready(self, current_time: int) -> bool:
        """Checks if an egg is ready to be collected."""
        if self._active_breeding_pair is None:
            return False
        return self._active_breeding_pair.is_egg_ready(current_time)

    def get_remaining_time(self, current_time: int) -> int:
        """Returns the remaining time until the egg is ready."""
        if self._active_breeding_pair is None:
            return 0
        return self._active_breeding_pair.get_remaining_time(current_time)

    def collect_egg(self, current_time: int) -> Optional["Poke"]:
        """Collects the ready egg and returns the hatched pokete."""
        if not self.is_egg_ready(current_time):
            return None

        if self._active_breeding_pair is None or self._active_breeding_pair.egg is None:
            return None

        egg = self._active_breeding_pair.egg
        poke = self._hatch_egg(egg)

        self._collected_eggs_count += 1
        self._notification_service.notify_egg_collected(poke.name)

        self._active_breeding_pair = None
        self._egg_ready_notified = False

        return poke

    def _hatch_egg(self, egg: EggPokete) -> "Poke":
        """Hatches an egg and creates a new pokete."""
        from pokete.classes.poke import Poke, Stats

        poke = Poke(
            egg.child_identifier,
            egg.child_xp,
            egg.child_hp,
            _attacks=egg.child_attacks,
            shiny=egg.child_shiny,
            nature=egg.child_nature,
        )

        stats = Stats(
            poke_name=poke.name,
            ownership_date=datetime.now(),
            caught_with="breeding",
        )
        poke.set_poke_stats(stats)

        return poke

    def cancel_breeding(self) -> tuple[Optional["Poke"], Optional["Poke"]]:
        """Cancels the current breeding and returns the parents."""
        if self._active_breeding_pair is None:
            return None, None

        parent1 = self._active_breeding_pair.parent1
        parent2 = self._active_breeding_pair.parent2

        self._active_breeding_pair = None
        self._egg_ready_notified = False
        self._notification_service.notify_breeding_cancelled()

        return parent1, parent2

    def get_breeding_status(self, current_time: int) -> dict:
        """Returns the current breeding status."""
        if self._active_breeding_pair is None:
            return {
                "active": False,
                "parent1": None,
                "parent2": None,
                "remaining_time": 0,
                "is_ready": False,
            }

        return {
            "active": True,
            "parent1": self._active_breeding_pair.parent1.name
            if self._active_breeding_pair.parent1
            else None,
            "parent2": self._active_breeding_pair.parent2.name
            if self._active_breeding_pair.parent2
            else None,
            "remaining_time": self.get_remaining_time(current_time),
            "is_ready": self.is_egg_ready(current_time),
        }

    def dict(self) -> BreedingStateDict:
        """Serializes the breeding manager state to a dictionary."""
        return {
            "active_breeding_pair": self._active_breeding_pair.dict()
            if self._active_breeding_pair
            else None,
            "pending_eggs": [egg.dict() for egg in self._pending_eggs],
            "collected_eggs_count": self._collected_eggs_count,
        }

    def from_dict(self, data: BreedingStateDict) -> None:
        """Loads the breeding manager state from a dictionary."""
        if data.get("active_breeding_pair"):
            self._active_breeding_pair = BreedingPair.from_dict(
                data["active_breeding_pair"]
            )
        else:
            self._active_breeding_pair = None

        self._pending_eggs = [
            EggPokete.from_dict(egg_data) for egg_data in data.get("pending_eggs", [])
        ]
        self._collected_eggs_count = data.get("collected_eggs_count", 0)
        self._egg_ready_notified = False


breeding_manager = BreedingManager()
