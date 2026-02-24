"""Quest tracker for integrating with game events."""
from __future__ import annotations
import logging
from typing import Callable, List

from .quest_events import QuestEvent


class QuestTracker:
    """Tracks game events and notifies listeners for quest progress."""

    def __init__(self):
        self._listeners: list[Callable[[QuestEvent], None]] = []

    def add_listener(self, listener: Callable[[QuestEvent], None]):
        """Register a listener for quest events."""
        if listener is None:
            logging.warning("[QuestTracker] Attempted to add None listener")
            return
        if listener not in self._listeners:
            self._listeners.append(listener)
            logging.debug("[QuestTracker] Added listener: %s", listener)

    def remove_listener(self, listener: Callable[[QuestEvent], None]):
        """Remove a listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)
            logging.debug("[QuestTracker] Removed listener: %s", listener)

    def clear_listeners(self):
        """Remove all listeners."""
        self._listeners.clear()

    def emit(self, event: QuestEvent):
        """Emit an event to all listeners."""
        if event is None:
            logging.warning("[QuestTracker] Attempted to emit None event")
            return

        logging.debug(
            "[QuestTracker] Emitting event: %s with data: %s",
            event.event_type,
            event.data
        )

        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logging.error(
                    "[QuestTracker] Error in listener %s: %s",
                    listener,
                    e
                )


quest_tracker = QuestTracker()
