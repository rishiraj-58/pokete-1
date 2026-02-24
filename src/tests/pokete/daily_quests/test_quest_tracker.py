"""Tests for QuestTracker."""
import unittest
from unittest.mock import Mock, patch

from pokete.classes.daily_quests.quest_tracker import QuestTracker
from pokete.classes.daily_quests.quest_events import QuestEvent, QuestEventType


class QuestTrackerTest(unittest.TestCase):
    """Tests for the QuestTracker class."""

    def setUp(self):
        """Create a fresh tracker for each test."""
        self.tracker = QuestTracker()

    def test_add_listener(self):
        """Test adding a listener."""
        callback = Mock()
        self.tracker.add_listener(callback)

        event = QuestEvent.trainer_battle_won()
        self.tracker.emit(event)

        callback.assert_called_once_with(event)

    def test_add_listener_none_ignored(self):
        """Test that None listener is ignored."""
        self.tracker.add_listener(None)
        # Should not raise

    def test_add_listener_duplicate_ignored(self):
        """Test that duplicate listeners are ignored."""
        callback = Mock()
        self.tracker.add_listener(callback)
        self.tracker.add_listener(callback)

        event = QuestEvent.trainer_battle_won()
        self.tracker.emit(event)

        callback.assert_called_once()

    def test_remove_listener(self):
        """Test removing a listener."""
        callback = Mock()
        self.tracker.add_listener(callback)
        self.tracker.remove_listener(callback)

        self.tracker.emit(QuestEvent.trainer_battle_won())

        callback.assert_not_called()

    def test_remove_nonexistent_listener(self):
        """Test removing a non-existent listener doesn't raise."""
        callback = Mock()
        self.tracker.remove_listener(callback)  # Should not raise

    def test_clear_listeners(self):
        """Test clearing all listeners."""
        callback1 = Mock()
        callback2 = Mock()
        self.tracker.add_listener(callback1)
        self.tracker.add_listener(callback2)

        self.tracker.clear_listeners()
        self.tracker.emit(QuestEvent.trainer_battle_won())

        callback1.assert_not_called()
        callback2.assert_not_called()

    def test_emit_to_multiple_listeners(self):
        """Test emitting to multiple listeners."""
        callback1 = Mock()
        callback2 = Mock()
        self.tracker.add_listener(callback1)
        self.tracker.add_listener(callback2)

        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.tracker.emit(event)

        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)

    def test_emit_none_event_ignored(self):
        """Test that None event is ignored."""
        callback = Mock()
        self.tracker.add_listener(callback)

        self.tracker.emit(None)

        callback.assert_not_called()

    def test_emit_continues_on_listener_error(self):
        """Test that emission continues if a listener raises."""
        error_callback = Mock(side_effect=Exception("Test error"))
        good_callback = Mock()

        self.tracker.add_listener(error_callback)
        self.tracker.add_listener(good_callback)

        event = QuestEvent.trainer_battle_won()
        self.tracker.emit(event)

        # Both should be called, second should succeed
        error_callback.assert_called_once()
        good_callback.assert_called_once()

    def test_emit_different_event_types(self):
        """Test emitting different event types."""
        events = []
        callback = lambda e: events.append(e)
        self.tracker.add_listener(callback)

        self.tracker.emit(QuestEvent.trainer_battle_won())
        self.tracker.emit(QuestEvent.wild_battle_won())
        self.tracker.emit(QuestEvent.pokete_caught("steini", []))
        self.tracker.emit(QuestEvent.coins_collected(100))

        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].event_type, QuestEventType.TRAINER_BATTLE_WON)
        self.assertEqual(events[1].event_type, QuestEventType.WILD_BATTLE_WON)
        self.assertEqual(events[2].event_type, QuestEventType.POKETE_CAUGHT)
        self.assertEqual(events[3].event_type, QuestEventType.COINS_COLLECTED)


if __name__ == "__main__":
    unittest.main()
