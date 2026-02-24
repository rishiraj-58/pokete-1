"""Tests for QuestManager."""
import unittest
from unittest.mock import Mock, patch
import datetime

from pokete.classes.daily_quests.quest_manager import QuestManager
from pokete.classes.daily_quests.quest_types import QuestType
from pokete.classes.daily_quests.quest_events import QuestEvent


class QuestManagerTest(unittest.TestCase):
    """Tests for the QuestManager class."""

    def setUp(self):
        """Create a fresh manager for each test."""
        self.manager = QuestManager()
        self.test_quest_data = {
            "catch_any": {
                "name": "Catch Any",
                "desc": "Catch any pokete",
                "type": QuestType.CATCH_ANY,
                "target": 1,
                "reward_money": 50,
                "reward_items": {"poketeball": 3},
            },
            "catch_3": {
                "name": "Catch Three",
                "desc": "Catch three poketes",
                "type": QuestType.CATCH_ANY,
                "target": 3,
                "reward_money": 100,
                "reward_items": {},
            },
            "trainer_battle": {
                "name": "Trainer Battle",
                "desc": "Win a trainer battle",
                "type": QuestType.WIN_TRAINER_BATTLE,
                "target": 1,
                "reward_money": 75,
                "reward_items": {"healing_potion": 1},
            },
        }

    def tearDown(self):
        """Clean up after tests."""
        # Reset the manager's state
        self.manager._quest_configs.clear()
        self.manager._current_quest = None
        self.manager._last_quest_date = None

    def test_initialize_loads_configs(self):
        """Test that initialize loads quest configs."""
        self.manager.initialize(self.test_quest_data)

        self.assertTrue(self.manager.is_initialized)
        self.assertEqual(len(self.manager.available_quests), 3)
        self.assertIn("catch_any", self.manager.available_quests)

    def test_initialize_with_none_data(self):
        """Test initialize with None data."""
        self.manager.initialize(None)
        self.assertTrue(self.manager.is_initialized)
        self.assertEqual(len(self.manager.available_quests), 0)

    def test_initialize_with_empty_data(self):
        """Test initialize with empty data."""
        self.manager.initialize({})
        self.assertTrue(self.manager.is_initialized)
        self.assertEqual(len(self.manager.available_quests), 0)

    def test_initialize_skips_invalid_quests(self):
        """Test that invalid quests are skipped."""
        data = {
            "valid": {
                "name": "Valid",
                "desc": "Valid quest",
                "type": QuestType.CATCH_ANY,
                "target": 1,
            },
            "invalid_missing_name": {
                "desc": "Missing name",
                "type": QuestType.CATCH_ANY,
                "target": 1,
            },
            "invalid_missing_type": {
                "name": "Missing type",
                "desc": "Desc",
                "target": 1,
            },
        }
        self.manager.initialize(data)
        self.assertEqual(len(self.manager.available_quests), 1)
        self.assertIn("valid", self.manager.available_quests)

    def test_get_quest_config(self):
        """Test getting a quest config by ID."""
        self.manager.initialize(self.test_quest_data)

        config = self.manager.get_quest_config("catch_any")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "Catch Any")

        self.assertIsNone(self.manager.get_quest_config("nonexistent"))

    def test_force_select_quest(self):
        """Test force selecting a specific quest."""
        self.manager.initialize(self.test_quest_data)

        quest = self.manager.force_select_quest("trainer_battle")
        self.assertIsNotNone(quest)
        self.assertEqual(quest.name, "Trainer Battle")
        self.assertEqual(self.manager.current_quest, quest)

    def test_force_select_nonexistent_quest(self):
        """Test force selecting a nonexistent quest."""
        self.manager.initialize(self.test_quest_data)

        quest = self.manager.force_select_quest("nonexistent")
        self.assertIsNone(quest)

    def test_select_random_quest(self):
        """Test selecting a random quest."""
        self.manager.initialize(self.test_quest_data)

        quest = self.manager.select_random_quest(seed=42)
        self.assertIsNotNone(quest)
        self.assertTrue(self.manager.has_active_quest)

    def test_select_random_quest_with_seed_is_deterministic(self):
        """Test that same seed gives same quest."""
        self.manager.initialize(self.test_quest_data)
        quest1 = self.manager.select_random_quest(seed=12345)

        # Reset and select again
        self.manager._current_quest = None
        quest2 = self.manager.select_random_quest(seed=12345)

        self.assertEqual(quest1.identifier, quest2.identifier)

    def test_select_random_quest_no_configs(self):
        """Test selecting random quest with no configs."""
        self.manager.initialize({})
        quest = self.manager.select_random_quest()
        self.assertIsNone(quest)

    @patch.object(QuestManager, '_get_current_date_string')
    def test_check_and_reset_daily_new_day(self, mock_date):
        """Test that new day resets quest."""
        self.manager.initialize(self.test_quest_data)
        mock_date.return_value = "2024-01-01"

        self.manager._last_quest_date = "2024-01-01"
        self.manager.force_select_quest("catch_any")

        # Simulate next day
        mock_date.return_value = "2024-01-02"
        was_reset = self.manager.check_and_reset_daily()

        self.assertTrue(was_reset)
        self.assertEqual(self.manager._last_quest_date, "2024-01-02")

    @patch.object(QuestManager, '_get_current_date_string')
    def test_check_and_reset_daily_same_day(self, mock_date):
        """Test that same day doesn't reset quest."""
        self.manager.initialize(self.test_quest_data)
        mock_date.return_value = "2024-01-01"

        self.manager._last_quest_date = "2024-01-01"
        self.manager.force_select_quest("catch_any")
        original_quest = self.manager.current_quest

        was_reset = self.manager.check_and_reset_daily()

        self.assertFalse(was_reset)

    @patch.object(QuestManager, '_get_current_date_string')
    def test_deterministic_quest_selection_by_date(self, mock_date):
        """Test that same date always gives same quest."""
        self.manager.initialize(self.test_quest_data)

        mock_date.return_value = "2024-06-15"
        self.manager._reset_for_new_day("2024-06-15")
        quest1_id = self.manager.current_quest.identifier if self.manager.current_quest else None

        # Reset and try again
        self.manager._current_quest = None
        self.manager._reset_for_new_day("2024-06-15")
        quest2_id = self.manager.current_quest.identifier if self.manager.current_quest else None

        self.assertEqual(quest1_id, quest2_id)

    def test_event_processing_updates_progress(self):
        """Test that events update quest progress."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.manager._on_event(event)

        self.assertEqual(self.manager.current_quest.progress, 1)
        self.assertTrue(self.manager.current_quest.is_completed)

    def test_event_processing_ignores_claimed_quest(self):
        """Test that events are ignored for claimed quests."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        # Complete and claim
        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.manager._on_event(event)
        self.manager.current_quest.mark_claimed()

        # Try to add more progress
        self.manager._on_event(event)
        self.assertEqual(self.manager.current_quest.progress, 1)

    def test_claim_reward_success(self):
        """Test successfully claiming rewards."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        # Complete quest
        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.manager._on_event(event)

        # Mock figure
        mock_figure = Mock()

        rewards = self.manager.claim_reward(mock_figure)

        self.assertIsNotNone(rewards)
        self.assertEqual(rewards["money"], 50)
        self.assertEqual(rewards["items"], {"poketeball": 3})
        mock_figure.add_money.assert_called_once_with(50)
        mock_figure.give_item.assert_called_once_with("poketeball", 3)
        self.assertTrue(self.manager.current_quest.is_claimed)

    def test_claim_reward_not_completed(self):
        """Test claiming rewards for incomplete quest."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_3")

        mock_figure = Mock()
        rewards = self.manager.claim_reward(mock_figure)

        self.assertIsNone(rewards)
        mock_figure.add_money.assert_not_called()

    def test_claim_reward_already_claimed(self):
        """Test claiming rewards for already claimed quest."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        # Complete and claim
        self.manager._on_event(QuestEvent.pokete_caught("steini", ["stone"]))
        mock_figure = Mock()
        self.manager.claim_reward(mock_figure)

        # Try to claim again
        rewards = self.manager.claim_reward(mock_figure)
        self.assertIsNone(rewards)

    def test_claim_reward_no_active_quest(self):
        """Test claiming with no active quest."""
        self.manager.initialize(self.test_quest_data)
        mock_figure = Mock()

        rewards = self.manager.claim_reward(mock_figure)
        self.assertIsNone(rewards)

    def test_claim_reward_none_figure(self):
        """Test claiming with None figure."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")
        self.manager._on_event(QuestEvent.pokete_caught("steini", ["stone"]))

        rewards = self.manager.claim_reward(None)
        self.assertIsNone(rewards)

    def test_on_progress_callback(self):
        """Test progress callback is called."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_3")

        callback = Mock()
        self.manager.add_on_progress_callback(callback)

        self.manager._on_event(QuestEvent.pokete_caught("steini", ["stone"]))

        callback.assert_called_once()

    def test_on_complete_callback(self):
        """Test completion callback is called."""
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        callback = Mock()
        self.manager.add_on_complete_callback(callback)

        self.manager._on_event(QuestEvent.pokete_caught("steini", ["stone"]))

        callback.assert_called_once()

    @patch.object(QuestManager, '_get_current_date_string')
    def test_to_dict(self, mock_date):
        """Test serializing manager state."""
        mock_date.return_value = "2024-01-15"
        self.manager.initialize(self.test_quest_data)
        self.manager.force_select_quest("catch_any")

        data = self.manager.to_dict()

        self.assertEqual(data["last_quest_date"], "2024-01-15")
        self.assertIsNotNone(data["current_quest"])
        self.assertEqual(data["current_quest"]["identifier"], "catch_any")

    def test_from_dict_restores_state(self):
        """Test restoring manager state from saved data."""
        self.manager.initialize(self.test_quest_data)

        saved_data = {
            "last_quest_date": datetime.date.today().isoformat(),
            "current_quest": {
                "identifier": "catch_3",
                "progress": 2,
                "completed": False,
                "claimed": False,
                "maps_visited": []
            }
        }

        self.manager.from_dict(saved_data)

        self.assertIsNotNone(self.manager.current_quest)
        self.assertEqual(self.manager.current_quest.identifier, "catch_3")
        self.assertEqual(self.manager.current_quest.progress, 2)

    def test_from_dict_with_none(self):
        """Test from_dict with None triggers daily reset."""
        self.manager.initialize(self.test_quest_data)

        with patch.object(self.manager, 'check_and_reset_daily') as mock_reset:
            mock_reset.return_value = True
            self.manager.from_dict(None)
            mock_reset.assert_called()

    def test_from_dict_old_date_triggers_reset(self):
        """Test that old saved date triggers reset."""
        self.manager.initialize(self.test_quest_data)

        old_data = {
            "last_quest_date": "2020-01-01",  # Old date
            "current_quest": {
                "identifier": "catch_any",
                "progress": 0,
                "completed": False,
                "claimed": False,
                "maps_visited": []
            }
        }

        self.manager.from_dict(old_data)

        # Should have reset to today
        self.assertNotEqual(self.manager._last_quest_date, "2020-01-01")


if __name__ == "__main__":
    unittest.main()
