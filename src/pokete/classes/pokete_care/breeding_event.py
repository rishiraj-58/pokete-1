"""Periodic event for checking breeding status and sending notifications."""

from pokete.base.context import Context
from pokete.base.periodic_event_manager import PeriodicEvent
from pokete.base.ui.notify import notifier

from .. import timer
from .breeding import breeding_manager


class BreedingCheckEvent(PeriodicEvent):
    """Periodic event that checks breeding status and notifies when egg is ready."""

    def __init__(self):
        self.manager = breeding_manager

    def tick(self, ctx: Context, tick: int):
        # Check every 10 ticks to avoid excessive checking
        if tick % 10 != 0:
            return

        # Check if egg just became ready
        if self.manager.check_and_notify(timer.time.time):
            notifier.notify(
                "Egg Ready!",
                "Breeding",
                "Your egg at the breeding facility is ready to be collected!"
            )
