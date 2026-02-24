"""Unit tests for the daily quest system

These tests require Python 3.12+ to run due to the codebase's use of modern
Python features like type union syntax (X | Y).

To run tests:
    python -m pytest src/tests/pokete/daily_quests/test_daily_quests.py -v
"""

import sys
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

# Skip the entire module if Python version is too low
# This prevents import errors from Python 3.12+ syntax in the main code
if sys.version_info >= (3, 12):
    from pokete.classes.daily_quests import (
        ActiveQuest,
        DailyQuestManager,
        Quest,
        QuestReward,
        QuestType,
    )
    from pokete.data.quests import quests as quest_definitions
    HAS_DEPS = True
else:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestQuestReward(unittest.TestCase):
    """Tests for QuestReward dataclass"""

    def test_from_dict_with_all_fields(self):
        data = {"money": 100, "items": {"poketeball": 5, "healing_potion": 2}}
        reward = QuestReward.from_dict(data)

        self.assertEqual(reward.money, 100)
        self.assertEqual(reward.items, {"poketeball": 5, "healing_potion": 2})

    def test_from_dict_with_defaults(self):
        reward = QuestReward.from_dict({})

        self.assertEqual(reward.money, 0)
        self.assertEqual(reward.items, {})


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestQuest(unittest.TestCase):
    """Tests for Quest dataclass"""

    def test_from_dict(self):
        data = {
            "title": "Test Quest",
            "description": "Test description",
            "quest_type": "catch",
            "target": 5,
            "reward": {"money": 50, "items": {"poketeball": 3}},
        }
        quest = Quest.from_dict("test_quest", data)

        self.assertEqual(quest.identifier, "test_quest")
        self.assertEqual(quest.title, "Test Quest")
        self.assertEqual(quest.description, "Test description")
        self.assertEqual(quest.quest_type, QuestType.CATCH)
        self.assertEqual(quest.target, 5)
        self.assertEqual(quest.reward.money, 50)
        self.assertEqual(quest.reward.items, {"poketeball": 3})


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestActiveQuest(unittest.TestCase):
    """Tests for ActiveQuest dataclass"""

    def setUp(self):
        self.quest = Quest(
            identifier="test_catch",
            title="Test Catch",
            description="Catch 3 poketes",
            quest_type=QuestType.CATCH,
            target=3,
            reward=QuestReward(money=50, items={"poketeball": 2}),
        )

    def test_add_progress_increments(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        completed = active.add_progress(1)

        self.assertEqual(active.progress, 1)
        self.assertFalse(completed)
        self.assertFalse(active.completed)

    def test_add_progress_completes_quest(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        completed = active.add_progress(1)

        self.assertEqual(active.progress, 3)
        self.assertTrue(completed)
        self.assertTrue(active.completed)

    def test_add_progress_caps_at_target(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        active.add_progress(5)

        self.assertEqual(active.progress, 3)

    def test_add_progress_returns_false_when_already_completed(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=3,
            completed=True,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        result = active.add_progress(1)

        self.assertFalse(result)
        self.assertEqual(active.progress, 3)

    def test_progress_text(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        self.assertEqual(active.progress_text(), "2/3")

    def test_to_dict(self):
        active = ActiveQuest(
            quest=self.quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-01",
        )

        result = active.to_dict()

        self.assertEqual(result["quest_id"], "test_catch")
        self.assertEqual(result["progress"], 2)
        self.assertFalse(result["completed"])
        self.assertFalse(result["rewarded"])
        self.assertEqual(result["assigned_date"], "2024-01-01")

    def test_from_dict(self):
        quests = {"test_catch": self.quest}
        data = {
            "quest_id": "test_catch",
            "progress": 2,
            "completed": False,
            "rewarded": False,
            "assigned_date": "2024-01-01",
        }

        active = ActiveQuest.from_dict(data, quests)

        self.assertIsNotNone(active)
        self.assertEqual(active.quest.identifier, "test_catch")
        self.assertEqual(active.progress, 2)

    def test_from_dict_returns_none_for_invalid_quest(self):
        quests = {"other_quest": self.quest}
        data = {"quest_id": "nonexistent"}

        active = ActiveQuest.from_dict(data, quests)

        self.assertIsNone(active)


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestDailyQuestManager(unittest.TestCase):
    """Tests for DailyQuestManager"""

    def setUp(self):
        self.manager = DailyQuestManager()

    def test_loads_quest_definitions(self):
        self.assertGreater(len(self.manager.quests), 0)
        for quest_id in quest_definitions:
            self.assertIn(quest_id, self.manager.quests)

    def test_select_random_quest_returns_quest(self):
        quest = self.manager.select_random_quest()

        self.assertIsInstance(quest, Quest)

    def test_select_random_quest_with_seed_is_deterministic(self):
        quest1 = self.manager.select_random_quest(seed="2024-01-15")
        quest2 = self.manager.select_random_quest(seed="2024-01-15")

        self.assertEqual(quest1.identifier, quest2.identifier)

    def test_select_random_quest_different_seeds_may_differ(self):
        # Run multiple times to reduce chance of coincidental equality
        results = set()
        for i in range(10):
            quest = self.manager.select_random_quest(seed=f"seed-{i}")
            results.add(quest.identifier)
        # Should have at least 2 different quests out of 10 tries
        self.assertGreater(len(results), 1)

    def test_check_new_day_assigns_quest_when_none(self):
        self.manager.active_quest = None

        with patch.object(
            self.manager, "get_today_str", return_value="2024-01-15"
        ):
            result = self.manager.check_new_day()

        self.assertTrue(result)
        self.assertIsNotNone(self.manager.active_quest)
        self.assertEqual(self.manager.active_quest.assigned_date, "2024-01-15")

    def test_check_new_day_resets_on_new_day(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-14",
        )

        with patch.object(
            self.manager, "get_today_str", return_value="2024-01-15"
        ):
            result = self.manager.check_new_day()

        self.assertTrue(result)
        self.assertEqual(self.manager.active_quest.assigned_date, "2024-01-15")
        self.assertEqual(self.manager.active_quest.progress, 0)

    def test_check_new_day_keeps_same_day_quest(self):
        quest = self.manager.quests["catch_3_poketes"]
        original = ActiveQuest(
            quest=quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )
        self.manager.active_quest = original

        with patch.object(
            self.manager, "get_today_str", return_value="2024-01-15"
        ):
            result = self.manager.check_new_day()

        self.assertFalse(result)
        self.assertEqual(self.manager.active_quest.progress, 2)

    def test_record_catch_increments_catch_quest(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_catch()

        self.assertEqual(self.manager.active_quest.progress, 1)

    def test_record_catch_ignores_non_catch_quest(self):
        quest = self.manager.quests["win_2_trainer_battles"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_catch()

        self.assertEqual(self.manager.active_quest.progress, 0)

    def test_record_trainer_battle_win_increments_trainer_quest(self):
        quest = self.manager.quests["win_2_trainer_battles"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_trainer_battle_win()

        self.assertEqual(self.manager.active_quest.progress, 1)

    def test_record_trainer_battle_win_increments_win_battles_quest(self):
        quest = self.manager.quests["win_3_battles"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_trainer_battle_win()

        self.assertEqual(self.manager.active_quest.progress, 1)

    def test_record_wild_battle_win_increments_win_battles_quest(self):
        quest = self.manager.quests["win_3_battles"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_wild_battle_win()

        self.assertEqual(self.manager.active_quest.progress, 1)

    def test_record_wild_battle_win_ignores_trainer_quest(self):
        quest = self.manager.quests["win_2_trainer_battles"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_wild_battle_win()

        self.assertEqual(self.manager.active_quest.progress, 0)

    def test_record_coins_collected_increments_coin_quest(self):
        quest = self.manager.quests["collect_100_coins"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_coins_collected(50)

        self.assertEqual(self.manager.active_quest.progress, 50)

    def test_record_coins_collected_can_complete_quest(self):
        quest = self.manager.quests["collect_100_coins"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=60,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_coins_collected(50)

        self.assertTrue(self.manager.active_quest.completed)

    def test_claim_reward_returns_false_when_no_quest(self):
        self.manager.active_quest = None

        result = self.manager.claim_reward()

        self.assertFalse(result)

    def test_claim_reward_returns_false_when_not_completed(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=1,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        result = self.manager.claim_reward()

        self.assertFalse(result)

    def test_claim_reward_returns_false_when_already_rewarded(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=3,
            completed=True,
            rewarded=True,
            assigned_date="2024-01-15",
        )

        result = self.manager.claim_reward()

        self.assertFalse(result)

    def test_claim_reward_succeeds_and_calls_callback(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=3,
            completed=True,
            rewarded=False,
            assigned_date="2024-01-15",
        )
        callback = MagicMock()
        self.manager.set_reward_callback(callback)

        result = self.manager.claim_reward()

        self.assertTrue(result)
        self.assertTrue(self.manager.active_quest.rewarded)
        callback.assert_called_once_with(
            quest.reward.money, quest.reward.items
        )

    def test_to_dict_empty_when_no_quest(self):
        self.manager.active_quest = None

        result = self.manager.to_dict()

        self.assertEqual(result, {})

    def test_to_dict_with_active_quest(self):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        result = self.manager.to_dict()

        self.assertIn("active_quest", result)
        self.assertEqual(result["active_quest"]["quest_id"], "catch_3_poketes")
        self.assertEqual(result["active_quest"]["progress"], 2)

    def test_from_dict_empty(self):
        self.manager.from_dict({})

        self.assertIsNone(self.manager.active_quest)

    def test_from_dict_restores_quest(self):
        data = {
            "active_quest": {
                "quest_id": "catch_3_poketes",
                "progress": 2,
                "completed": False,
                "rewarded": False,
                "assigned_date": "2024-01-15",
            }
        }

        self.manager.from_dict(data)

        self.assertIsNotNone(self.manager.active_quest)
        self.assertEqual(
            self.manager.active_quest.quest.identifier, "catch_3_poketes"
        )
        self.assertEqual(self.manager.active_quest.progress, 2)


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestQuestCompletionNotification(unittest.TestCase):
    """Tests for quest completion notifications"""

    def setUp(self):
        self.manager = DailyQuestManager()

    @patch("pokete.classes.daily_quests.notifier")
    def test_completion_triggers_notification(self, mock_notifier):
        quest = self.manager.quests["catch_3_poketes"]
        self.manager.active_quest = ActiveQuest(
            quest=quest,
            progress=2,
            completed=False,
            rewarded=False,
            assigned_date="2024-01-15",
        )

        self.manager.record_catch()

        mock_notifier.notify.assert_called_once()
        call_args = mock_notifier.notify.call_args
        self.assertIn("Quest Complete", call_args[0][0])


@unittest.skipUnless(HAS_DEPS, "Tests require Python 3.12+")
class TestQuestTypeMapping(unittest.TestCase):
    """Tests to verify quest types in definitions match the enum"""

    def test_all_quest_types_are_valid(self):
        valid_types = {qt.value for qt in QuestType}
        for quest_id, quest_data in quest_definitions.items():
            self.assertIn(
                quest_data["quest_type"],
                valid_types,
                f"Invalid quest type for {quest_id}",
            )


if __name__ == "__main__":
    unittest.main()
