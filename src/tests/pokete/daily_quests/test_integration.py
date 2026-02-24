"""Integration tests for the daily quest system."""
import unittest
from unittest.mock import Mock, patch
import datetime

from pokete.classes.daily_quests.quest_manager import QuestManager
from pokete.classes.daily_quests.quest_tracker import QuestTracker
from pokete.classes.daily_quests.quest_types import QuestType
from pokete.classes.daily_quests.quest_events import QuestEvent


class DailyQuestIntegrationTest(unittest.TestCase):
    """Integration tests for the complete daily quest system."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = QuestTracker()
        self.manager = QuestManager()

        self.quest_data = {
            "catch_3_poketes": {
                "name": "Catch Three",
                "desc": "Catch 3 wild Poketes",
                "type": QuestType.CATCH_ANY,
                "target": 3,
                "reward_money": 100,
                "reward_items": {"poketeball": 5},
            },
            "trainer_master": {
                "name": "Trainer Master",
                "desc": "Win 2 trainer battles",
                "type": QuestType.WIN_TRAINER_BATTLE,
                "target": 2,
                "reward_money": 200,
                "reward_items": {"healing_potion": 3},
            },
            "coin_collector": {
                "name": "Coin Collector",
                "desc": "Collect 500 coins",
                "type": QuestType.COLLECT_COINS,
                "target": 500,
                "reward_money": 100,
                "reward_items": {},
            },
            "water_catcher": {
                "name": "Water Catcher",
                "desc": "Catch a water type",
                "type": QuestType.CATCH_TYPE,
                "type_filter": "water",
                "target": 1,
                "reward_money": 75,
                "reward_items": {"superball": 2},
            },
        }

        self.manager.initialize(self.quest_data)
        self.tracker.add_listener(self.manager._on_event)

    def tearDown(self):
        """Clean up after tests."""
        self.tracker.clear_listeners()

    def test_full_quest_completion_flow(self):
        """Test complete flow: select, progress, complete, claim."""
        self.manager.force_select_quest("catch_3_poketes")

        # Progress through catching
        self.tracker.emit(QuestEvent.pokete_caught("steini", ["stone"]))
        self.assertEqual(self.manager.current_quest.progress, 1)
        self.assertFalse(self.manager.current_quest.is_completed)

        self.tracker.emit(QuestEvent.pokete_caught("mowcow", ["normal"]))
        self.assertEqual(self.manager.current_quest.progress, 2)
        self.assertFalse(self.manager.current_quest.is_completed)

        self.tracker.emit(QuestEvent.pokete_caught("poundi", ["ground"]))
        self.assertEqual(self.manager.current_quest.progress, 3)
        self.assertTrue(self.manager.current_quest.is_completed)

        # Claim rewards
        mock_figure = Mock()
        rewards = self.manager.claim_reward(mock_figure)

        self.assertIsNotNone(rewards)
        self.assertEqual(rewards["money"], 100)
        self.assertEqual(rewards["items"], {"poketeball": 5})
        self.assertTrue(self.manager.current_quest.is_claimed)

    def test_trainer_battle_quest_flow(self):
        """Test trainer battle quest progression."""
        self.manager.force_select_quest("trainer_master")

        # Wild battles don't count
        self.tracker.emit(QuestEvent.wild_battle_won())
        self.assertEqual(self.manager.current_quest.progress, 0)

        # Trainer battles count
        self.tracker.emit(QuestEvent.trainer_battle_won())
        self.assertEqual(self.manager.current_quest.progress, 1)

        self.tracker.emit(QuestEvent.trainer_battle_won())
        self.assertTrue(self.manager.current_quest.is_completed)

    def test_coin_collection_quest_flow(self):
        """Test coin collection quest with multiple gains."""
        self.manager.force_select_quest("coin_collector")

        self.tracker.emit(QuestEvent.coins_collected(100))
        self.assertEqual(self.manager.current_quest.progress, 100)

        self.tracker.emit(QuestEvent.coins_collected(200))
        self.assertEqual(self.manager.current_quest.progress, 300)

        self.tracker.emit(QuestEvent.coins_collected(250))
        self.assertEqual(self.manager.current_quest.progress, 550)
        self.assertTrue(self.manager.current_quest.is_completed)

    def test_type_specific_catch_quest(self):
        """Test catching specific type quest."""
        self.manager.force_select_quest("water_catcher")

        # Wrong types don't count
        self.tracker.emit(QuestEvent.pokete_caught("steini", ["stone"]))
        self.assertEqual(self.manager.current_quest.progress, 0)

        self.tracker.emit(QuestEvent.pokete_caught("poundi", ["ground"]))
        self.assertEqual(self.manager.current_quest.progress, 0)

        # Correct type counts
        self.tracker.emit(QuestEvent.pokete_caught("bator", ["water"]))
        self.assertEqual(self.manager.current_quest.progress, 1)
        self.assertTrue(self.manager.current_quest.is_completed)

    def test_progress_callbacks_during_completion(self):
        """Test that callbacks fire during quest progression."""
        self.manager.force_select_quest("catch_3_poketes")

        progress_calls = []
        complete_calls = []

        self.manager.add_on_progress_callback(
            lambda q: progress_calls.append(q.progress)
        )
        self.manager.add_on_complete_callback(
            lambda q: complete_calls.append(q.progress)
        )

        self.tracker.emit(QuestEvent.pokete_caught("a", []))
        self.tracker.emit(QuestEvent.pokete_caught("b", []))
        self.tracker.emit(QuestEvent.pokete_caught("c", []))

        self.assertEqual(progress_calls, [1, 2, 3])
        self.assertEqual(complete_calls, [3])

    def test_save_and_restore_mid_progress(self):
        """Test saving and restoring quest in progress."""
        self.manager.force_select_quest("catch_3_poketes")

        self.tracker.emit(QuestEvent.pokete_caught("steini", ["stone"]))
        self.tracker.emit(QuestEvent.pokete_caught("mowcow", ["normal"]))

        # Save state
        saved_data = self.manager.to_dict()
        self.assertEqual(saved_data["current_quest"]["progress"], 2)

        # Create new manager and restore
        new_manager = QuestManager()
        new_manager.initialize(self.quest_data)

        # Mock today's date to match saved
        with patch.object(new_manager, '_get_current_date_string') as mock_date:
            mock_date.return_value = saved_data["last_quest_date"]
            new_manager.from_dict(saved_data)

        self.assertEqual(new_manager.current_quest.progress, 2)
        self.assertEqual(new_manager.current_quest.identifier, "catch_3_poketes")

    def test_claimed_quest_cannot_progress_further(self):
        """Test that claimed quests ignore further events."""
        self.manager.force_select_quest("catch_3_poketes")

        # Complete and claim
        for _ in range(3):
            self.tracker.emit(QuestEvent.pokete_caught("x", []))

        mock_figure = Mock()
        self.manager.claim_reward(mock_figure)

        # Try to add more progress
        self.tracker.emit(QuestEvent.pokete_caught("extra", []))
        self.assertEqual(self.manager.current_quest.progress, 3)

    def test_multiple_events_same_frame(self):
        """Test handling multiple rapid events."""
        self.manager.force_select_quest("catch_3_poketes")

        events = [
            QuestEvent.pokete_caught("a", []),
            QuestEvent.pokete_caught("b", []),
            QuestEvent.pokete_caught("c", []),
            QuestEvent.pokete_caught("d", []),  # Beyond target
        ]

        for event in events:
            self.tracker.emit(event)

        # Should be at target, not beyond (completion stops further progress)
        self.assertEqual(self.manager.current_quest.progress, 3)
        self.assertTrue(self.manager.current_quest.is_completed)

    @patch.object(QuestManager, '_get_current_date_string')
    def test_daily_reset_preserves_system_integrity(self, mock_date):
        """Test that daily reset works correctly."""
        mock_date.return_value = "2024-01-01"

        self.manager.force_select_quest("catch_3_poketes")
        self.tracker.emit(QuestEvent.pokete_caught("steini", ["stone"]))
        self.assertEqual(self.manager.current_quest.progress, 1)

        # Simulate new day
        mock_date.return_value = "2024-01-02"
        self.manager.check_and_reset_daily()

        # Quest should be reset
        self.assertEqual(self.manager.current_quest.progress, 0)
        self.assertFalse(self.manager.current_quest.is_completed)

    def test_quest_with_empty_reward_items(self):
        """Test claiming quest with no item rewards."""
        self.manager.force_select_quest("coin_collector")

        # Complete quest
        self.tracker.emit(QuestEvent.coins_collected(500))

        mock_figure = Mock()
        rewards = self.manager.claim_reward(mock_figure)

        self.assertEqual(rewards["money"], 100)
        self.assertEqual(rewards["items"], {})
        mock_figure.add_money.assert_called_once_with(100)
        mock_figure.give_item.assert_not_called()


class EdgeCaseIntegrationTest(unittest.TestCase):
    """Tests for edge cases and error conditions."""

    def test_uninitialized_manager_operations(self):
        """Test operations on uninitialized manager."""
        manager = QuestManager()

        self.assertFalse(manager.is_initialized)
        self.assertFalse(manager.has_active_quest)
        self.assertIsNone(manager.current_quest)
        self.assertEqual(manager.available_quests, [])

    def test_tracker_with_erroring_listeners(self):
        """Test tracker continues with erroring listeners."""
        tracker = QuestTracker()

        results = []
        def error_listener(e):
            raise ValueError("Test error")

        def good_listener(e):
            results.append(e)

        tracker.add_listener(error_listener)
        tracker.add_listener(good_listener)

        tracker.emit(QuestEvent.trainer_battle_won())

        # Good listener should still have received event
        self.assertEqual(len(results), 1)

    def test_quest_progress_boundary_conditions(self):
        """Test quest progress at exact boundaries."""
        manager = QuestManager()
        manager.initialize({
            "exact_target": {
                "name": "Exact",
                "desc": "Exact target test",
                "type": QuestType.COLLECT_COINS,
                "target": 100,
                "reward_money": 10,
                "reward_items": {},
            }
        })
        manager.force_select_quest("exact_target")

        tracker = QuestTracker()
        tracker.add_listener(manager._on_event)

        # Hit exact target
        tracker.emit(QuestEvent.coins_collected(100))

        self.assertEqual(manager.current_quest.progress, 100)
        self.assertTrue(manager.current_quest.is_completed)
        self.assertEqual(manager.current_quest.progress_percent, 100.0)

    def test_concurrent_events_different_types(self):
        """Test receiving events that don't match quest type."""
        manager = QuestManager()
        manager.initialize({
            "trainer_only": {
                "name": "Trainer",
                "desc": "Trainer battles only",
                "type": QuestType.WIN_TRAINER_BATTLE,
                "target": 1,
                "reward_money": 50,
                "reward_items": {},
            }
        })
        manager.force_select_quest("trainer_only")

        tracker = QuestTracker()
        tracker.add_listener(manager._on_event)

        # Send various non-matching events
        tracker.emit(QuestEvent.wild_battle_won())
        tracker.emit(QuestEvent.pokete_caught("x", []))
        tracker.emit(QuestEvent.coins_collected(100))
        tracker.emit(QuestEvent.pokete_evolved("a", "b"))

        self.assertEqual(manager.current_quest.progress, 0)

        # Matching event
        tracker.emit(QuestEvent.trainer_battle_won())
        self.assertEqual(manager.current_quest.progress, 1)


if __name__ == "__main__":
    unittest.main()
