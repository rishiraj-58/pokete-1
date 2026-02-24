"""Tests for QuestType enumeration."""
import unittest

from pokete.classes.daily_quests.quest_types import QuestType


class QuestTypeTest(unittest.TestCase):
    """Tests for the QuestType enum."""

    def test_all_quest_types_exist(self):
        """Verify all expected quest types are defined."""
        expected_types = [
            "CATCH_ANY",
            "CATCH_TYPE",
            "CATCH_SPECIFIC",
            "WIN_TRAINER_BATTLE",
            "WIN_WILD_BATTLE",
            "COLLECT_COINS",
            "EVOLVE_POKETE",
            "USE_ITEM",
            "VISIT_MAPS",
        ]
        for type_name in expected_types:
            self.assertTrue(
                hasattr(QuestType, type_name),
                f"QuestType.{type_name} should exist"
            )

    def test_quest_types_are_unique(self):
        """Verify all quest types have unique values."""
        values = [qt.value for qt in QuestType]
        self.assertEqual(len(values), len(set(values)))

    def test_from_string_valid(self):
        """Test parsing valid quest type strings."""
        self.assertEqual(
            QuestType.from_string("CATCH_ANY"),
            QuestType.CATCH_ANY
        )
        self.assertEqual(
            QuestType.from_string("WIN_TRAINER_BATTLE"),
            QuestType.WIN_TRAINER_BATTLE
        )

    def test_from_string_case_insensitive(self):
        """Test that from_string handles different cases."""
        self.assertEqual(
            QuestType.from_string("catch_any"),
            QuestType.CATCH_ANY
        )
        self.assertEqual(
            QuestType.from_string("Catch_Any"),
            QuestType.CATCH_ANY
        )

    def test_from_string_with_whitespace(self):
        """Test that from_string handles whitespace."""
        self.assertEqual(
            QuestType.from_string("  CATCH_ANY  "),
            QuestType.CATCH_ANY
        )

    def test_from_string_invalid_returns_none(self):
        """Test that invalid strings return None."""
        self.assertIsNone(QuestType.from_string("INVALID_TYPE"))
        self.assertIsNone(QuestType.from_string(""))
        self.assertIsNone(QuestType.from_string("123"))

    def test_from_string_none_returns_none(self):
        """Test that None input returns None."""
        self.assertIsNone(QuestType.from_string(None))

    def test_from_string_non_string_returns_none(self):
        """Test that non-string input returns None."""
        self.assertIsNone(QuestType.from_string(123))
        self.assertIsNone(QuestType.from_string([]))

    def test_str_representation(self):
        """Test string representation of quest types."""
        self.assertEqual(str(QuestType.CATCH_ANY), "CATCH_ANY")
        self.assertEqual(str(QuestType.WIN_TRAINER_BATTLE), "WIN_TRAINER_BATTLE")


if __name__ == "__main__":
    unittest.main()
