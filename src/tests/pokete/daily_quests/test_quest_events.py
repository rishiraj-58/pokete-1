"""Tests for QuestEvent and QuestEventType."""
import unittest

from pokete.classes.daily_quests.quest_events import QuestEvent, QuestEventType


class QuestEventTypeTest(unittest.TestCase):
    """Tests for the QuestEventType enum."""

    def test_all_event_types_exist(self):
        """Verify all expected event types are defined."""
        expected_types = [
            "POKETE_CAUGHT",
            "TRAINER_BATTLE_WON",
            "WILD_BATTLE_WON",
            "COINS_COLLECTED",
            "POKETE_EVOLVED",
            "ITEM_USED",
            "MAP_VISITED",
        ]
        for type_name in expected_types:
            self.assertTrue(
                hasattr(QuestEventType, type_name),
                f"QuestEventType.{type_name} should exist"
            )

    def test_event_types_are_unique(self):
        """Verify all event types have unique values."""
        values = [et.value for et in QuestEventType]
        self.assertEqual(len(values), len(set(values)))


class QuestEventTest(unittest.TestCase):
    """Tests for the QuestEvent dataclass."""

    def test_create_basic_event(self):
        """Test creating a basic event."""
        event = QuestEvent(QuestEventType.TRAINER_BATTLE_WON)
        self.assertEqual(event.event_type, QuestEventType.TRAINER_BATTLE_WON)
        self.assertEqual(event.data, {})

    def test_create_event_with_data(self):
        """Test creating an event with data."""
        event = QuestEvent(
            QuestEventType.POKETE_CAUGHT,
            {"species": "steini", "types": ["stone"]}
        )
        self.assertEqual(event.event_type, QuestEventType.POKETE_CAUGHT)
        self.assertEqual(event.data["species"], "steini")
        self.assertEqual(event.data["types"], ["stone"])

    def test_get_data_with_default(self):
        """Test get_data with default values."""
        event = QuestEvent(QuestEventType.POKETE_CAUGHT, {"species": "steini"})
        self.assertEqual(event.get_data("species"), "steini")
        self.assertIsNone(event.get_data("missing_key"))
        self.assertEqual(event.get_data("missing_key", "default"), "default")

    def test_get_data_with_none_data(self):
        """Test get_data when data is None."""
        event = QuestEvent(QuestEventType.TRAINER_BATTLE_WON, None)
        self.assertEqual(event.get_data("any_key", "default"), "default")

    def test_event_is_immutable(self):
        """Test that event is frozen (immutable)."""
        event = QuestEvent(QuestEventType.TRAINER_BATTLE_WON)
        with self.assertRaises(Exception):
            event.event_type = QuestEventType.WILD_BATTLE_WON

    # Factory method tests
    def test_pokete_caught_factory(self):
        """Test pokete_caught factory method."""
        event = QuestEvent.pokete_caught("steini", ["stone", "normal"])
        self.assertEqual(event.event_type, QuestEventType.POKETE_CAUGHT)
        self.assertEqual(event.get_data("species"), "steini")
        self.assertEqual(event.get_data("types"), ["stone", "normal"])

    def test_pokete_caught_with_none_types(self):
        """Test pokete_caught with None types."""
        event = QuestEvent.pokete_caught("steini", None)
        self.assertEqual(event.get_data("types"), [])

    def test_pokete_caught_with_none_species(self):
        """Test pokete_caught with None species."""
        event = QuestEvent.pokete_caught(None, ["water"])
        self.assertEqual(event.get_data("species"), "")

    def test_trainer_battle_won_factory(self):
        """Test trainer_battle_won factory method."""
        event = QuestEvent.trainer_battle_won()
        self.assertEqual(event.event_type, QuestEventType.TRAINER_BATTLE_WON)

    def test_wild_battle_won_factory(self):
        """Test wild_battle_won factory method."""
        event = QuestEvent.wild_battle_won()
        self.assertEqual(event.event_type, QuestEventType.WILD_BATTLE_WON)

    def test_coins_collected_factory(self):
        """Test coins_collected factory method."""
        event = QuestEvent.coins_collected(100)
        self.assertEqual(event.event_type, QuestEventType.COINS_COLLECTED)
        self.assertEqual(event.get_data("amount"), 100)

    def test_coins_collected_with_negative(self):
        """Test coins_collected with negative amount."""
        event = QuestEvent.coins_collected(-50)
        self.assertEqual(event.get_data("amount"), 0)

    def test_coins_collected_with_none(self):
        """Test coins_collected with None amount."""
        event = QuestEvent.coins_collected(None)
        self.assertEqual(event.get_data("amount"), 0)

    def test_pokete_evolved_factory(self):
        """Test pokete_evolved factory method."""
        event = QuestEvent.pokete_evolved("steini", "bigstone")
        self.assertEqual(event.event_type, QuestEventType.POKETE_EVOLVED)
        self.assertEqual(event.get_data("from_species"), "steini")
        self.assertEqual(event.get_data("to_species"), "bigstone")

    def test_pokete_evolved_with_none_values(self):
        """Test pokete_evolved with None values."""
        event = QuestEvent.pokete_evolved(None, None)
        self.assertEqual(event.get_data("from_species"), "")
        self.assertEqual(event.get_data("to_species"), "")

    def test_item_used_factory(self):
        """Test item_used factory method."""
        event = QuestEvent.item_used("healing_potion")
        self.assertEqual(event.event_type, QuestEventType.ITEM_USED)
        self.assertEqual(event.get_data("item_name"), "healing_potion")

    def test_item_used_with_none(self):
        """Test item_used with None item name."""
        event = QuestEvent.item_used(None)
        self.assertEqual(event.get_data("item_name"), "")

    def test_map_visited_factory(self):
        """Test map_visited factory method."""
        event = QuestEvent.map_visited("playmap_1")
        self.assertEqual(event.event_type, QuestEventType.MAP_VISITED)
        self.assertEqual(event.get_data("map_name"), "playmap_1")

    def test_map_visited_with_none(self):
        """Test map_visited with None map name."""
        event = QuestEvent.map_visited(None)
        self.assertEqual(event.get_data("map_name"), "")


if __name__ == "__main__":
    unittest.main()
