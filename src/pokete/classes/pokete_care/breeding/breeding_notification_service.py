"""Notification service for breeding events."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Callable, Optional

from pokete.base.ui.notify import notifier


class BreedingEventType(Enum):
    """Types of breeding events that can trigger notifications."""
    BREEDING_STARTED = "breeding_started"
    EGG_READY = "egg_ready"
    EGG_COLLECTED = "egg_collected"
    INCOMPATIBLE_PAIR = "incompatible_pair"
    BREEDING_CANCELLED = "breeding_cancelled"


@dataclass
class BreedingEvent:
    """Represents a breeding event."""
    event_type: BreedingEventType
    message: str
    details: dict


class IBreedingNotificationService(Protocol):
    """Interface for breeding notification service."""

    def notify_breeding_started(
        self, parent1_name: str, parent2_name: str, hatch_time: int
    ) -> None:
        """Notifies that breeding has started."""
        ...

    def notify_egg_ready(self, child_identifier: str) -> None:
        """Notifies that an egg is ready to be collected."""
        ...

    def notify_egg_collected(self, child_name: str) -> None:
        """Notifies that an egg has been collected."""
        ...

    def notify_incompatible_pair(self, reason: str) -> None:
        """Notifies that a breeding pair is incompatible."""
        ...

    def notify_breeding_cancelled(self) -> None:
        """Notifies that breeding has been cancelled."""
        ...


class BreedingNotificationService(IBreedingNotificationService):
    """Handles notifications for breeding events."""

    def __init__(self):
        self._event_handlers: list[Callable[[BreedingEvent], None]] = []
        self._pending_notifications: list[BreedingEvent] = []

    def register_handler(
        self, handler: Callable[[BreedingEvent], None]
    ) -> None:
        """Registers a handler for breeding events."""
        self._event_handlers.append(handler)

    def unregister_handler(
        self, handler: Callable[[BreedingEvent], None]
    ) -> None:
        """Unregisters a handler for breeding events."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def notify_breeding_started(
        self, parent1_name: str, parent2_name: str, hatch_time: int
    ) -> None:
        """Notifies that breeding has started."""
        event = BreedingEvent(
            event_type=BreedingEventType.BREEDING_STARTED,
            message=f"{parent1_name} and {parent2_name} are now breeding!",
            details={
                "parent1": parent1_name,
                "parent2": parent2_name,
                "hatch_time": hatch_time,
            },
        )
        self._dispatch_event(event)
        self._show_notification(
            "Breeding Started",
            "Pokete Care",
            f"{parent1_name} and {parent2_name} are breeding. Egg will be ready in {hatch_time} minutes.",
        )

    def notify_egg_ready(self, child_identifier: str) -> None:
        """Notifies that an egg is ready to be collected."""
        event = BreedingEvent(
            event_type=BreedingEventType.EGG_READY,
            message=f"An egg is ready to be collected!",
            details={"child_identifier": child_identifier},
        )
        self._dispatch_event(event)
        self._show_notification(
            "Egg Ready!",
            "Pokete Care",
            "Your egg is ready to be collected at the Pokete Care!",
        )

    def notify_egg_collected(self, child_name: str) -> None:
        """Notifies that an egg has been collected."""
        event = BreedingEvent(
            event_type=BreedingEventType.EGG_COLLECTED,
            message=f"You collected a {child_name}!",
            details={"child_name": child_name},
        )
        self._dispatch_event(event)
        self._show_notification(
            "Egg Collected!",
            "Pokete Care",
            f"You received a new {child_name}!",
        )

    def notify_incompatible_pair(self, reason: str) -> None:
        """Notifies that a breeding pair is incompatible."""
        event = BreedingEvent(
            event_type=BreedingEventType.INCOMPATIBLE_PAIR,
            message=f"These Poketes cannot breed: {reason}",
            details={"reason": reason},
        )
        self._dispatch_event(event)
        self._show_notification(
            "Incompatible Pair",
            "Pokete Care",
            reason,
        )

    def notify_breeding_cancelled(self) -> None:
        """Notifies that breeding has been cancelled."""
        event = BreedingEvent(
            event_type=BreedingEventType.BREEDING_CANCELLED,
            message="Breeding has been cancelled.",
            details={},
        )
        self._dispatch_event(event)

    def _dispatch_event(self, event: BreedingEvent) -> None:
        """Dispatches an event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def _show_notification(self, title: str, name: str, desc: str) -> None:
        """Shows a notification using the game's notification system."""
        try:
            notifier.notify(title, name, desc)
        except Exception:
            pass
