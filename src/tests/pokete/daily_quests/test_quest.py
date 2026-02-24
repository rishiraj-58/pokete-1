"""Tests for Quest and QuestConfig classes."""
import unittest

from pokete.classes.daily_quests.quest_types import QuestType
from pokete.classes.daily_quests.quest import Quest, QuestConfig
from pokete.classes.daily_quests.quest_events import QuestEvent


class QuestConfigTest(unittest.TestCase):
    """Tests for the QuestConfig dataclass."""

    def test_create_basic_config(self):
        """Test creating a basic quest config."""
        config = QuestConfig(
            identifier="test_quest",
            name="Test Quest",
            desc="Test description",
            quest_type=QuestType.CATCH_ANY,
            target=3
        )
        self.assertEqual(config.identifier, "test_quest")
        self.assertEqual(config.name, "Test Quest")
        self.assertEqual(config.desc, "Test description")
        self.assertEqual(config.quest_type, QuestType.CATCH_ANY)
        self.assertEqual(config.target, 3)

    def test_config_defaults(self):
        """Test default values in config."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_ANY,
            target=1
        )
        self.assertEqual(config.reward_money, 0)
        self.assertEqual(config.reward_items, {})
        self.assertIsNone(config.type_filter)
        self.assertIsNone(config.species_filter)
        self.assertIsNone(config.item_filter)

    def test_config_with_rewards(self):
        """Test config with reward values."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_ANY,
            target=1,
            reward_money=100,
            reward_items={"poketeball": 5}
        )
        self.assertEqual(config.reward_money, 100)
        self.assertEqual(config.reward_items, {"poketeball": 5})

    def test_config_post_init_fixes_none_target(self):
        """Test that None target is fixed."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_ANY,
            target=None
        )
        self.assertEqual(config.target, 1)

    def test_config_post_init_fixes_negative_target(self):
        """Test that negative target is fixed."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_ANY,
            target=-5
        )
        self.assertEqual(config.target, 1)

    def test_config_post_init_fixes_none_reward_items(self):
        """Test that None reward_items is fixed."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_ANY,
            target=1,
            reward_items=None
        )
        self.assertEqual(config.reward_items, {})

    def test_from_dict_valid(self):
        """Test creating config from valid dictionary."""
        data = {
            "name": "Test Quest",
            "desc": "Test description",
            "type": QuestType.WIN_TRAINER_BATTLE,
            "target": 5,
            "reward_money": 200,
            "reward_items": {"healing_potion": 2},
        }
        config = QuestConfig.from_dict("test_id", data)
        self.assertIsNotNone(config)
        self.assertEqual(config.identifier, "test_id")
        self.assertEqual(config.name, "Test Quest")
        self.assertEqual(config.target, 5)
        self.assertEqual(config.reward_money, 200)

    def test_from_dict_missing_required_fields(self):
        """Test that missing required fields return None."""
        self.assertIsNone(QuestConfig.from_dict("test", {}))
        self.assertIsNone(QuestConfig.from_dict("test", {"name": "Test"}))
        self.assertIsNone(QuestConfig.from_dict("test", {
            "name": "Test",
            "desc": "Desc"
        }))

    def test_from_dict_invalid_identifier(self):
        """Test that invalid identifier returns None."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": QuestType.CATCH_ANY,
            "target": 1
        }
        self.assertIsNone(QuestConfig.from_dict(None, data))
        self.assertIsNone(QuestConfig.from_dict("", data))
        self.assertIsNone(QuestConfig.from_dict(123, data))

    def test_from_dict_invalid_target(self):
        """Test that invalid target returns None."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": QuestType.CATCH_ANY,
            "target": "invalid"
        }
        self.assertIsNone(QuestConfig.from_dict("test", data))

        data["target"] = 0
        self.assertIsNone(QuestConfig.from_dict("test", data))

        data["target"] = -1
        self.assertIsNone(QuestConfig.from_dict("test", data))

    def test_from_dict_invalid_quest_type(self):
        """Test that invalid quest type returns None."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": "invalid",
            "target": 1
        }
        self.assertIsNone(QuestConfig.from_dict("test", data))

    def test_from_dict_validates_reward_items(self):
        """Test that reward items are validated."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": QuestType.CATCH_ANY,
            "target": 1,
            "reward_items": {"valid": 5, "invalid_count": "not_a_number", "": 10}
        }
        config = QuestConfig.from_dict("test", data)
        self.assertIsNotNone(config)
        self.assertEqual(config.reward_items, {"valid": 5})

    def test_from_dict_with_filters(self):
        """Test that filters are properly parsed."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": QuestType.CATCH_TYPE,
            "target": 1,
            "type_filter": "water",
            "species_filter": "steini",
            "item_filter": ["healing_potion", "super_potion"]
        }
        config = QuestConfig.from_dict("test", data)
        self.assertEqual(config.type_filter, "water")
        self.assertEqual(config.species_filter, "steini")
        self.assertEqual(config.item_filter, ["healing_potion", "super_potion"])

    def test_from_dict_invalid_filters_become_none(self):
        """Test that invalid filters become None."""
        data = {
            "name": "Test",
            "desc": "Desc",
            "type": QuestType.CATCH_ANY,
            "target": 1,
            "type_filter": 123,
            "species_filter": [],
            "item_filter": "not_a_list"
        }
        config = QuestConfig.from_dict("test", data)
        self.assertIsNone(config.type_filter)
        self.assertIsNone(config.species_filter)
        self.assertIsNone(config.item_filter)

    def test_to_dict(self):
        """Test serializing config to dictionary."""
        config = QuestConfig(
            identifier="test",
            name="Test",
            desc="Desc",
            quest_type=QuestType.CATCH_TYPE,
            target=3,
            reward_money=100,
            reward_items={"poketeball": 5},
            type_filter="water"
        )
        data = config.to_dict()
        self.assertEqual(data["identifier"], "test")
        self.assertEqual(data["name"], "Test")
        self.assertEqual(data["type"], "CATCH_TYPE")
        self.assertEqual(data["target"], 3)
        self.assertEqual(data["reward_money"], 100)
        self.assertEqual(data["type_filter"], "water")


class QuestTest(unittest.TestCase):
    """Tests for the Quest class."""

    def _create_config(
        self,
        quest_type=QuestType.CATCH_ANY,
        target=3,
        **kwargs
    ):
        """Helper to create test configs."""
        return QuestConfig(
            identifier="test_quest",
            name="Test Quest",
            desc="Test description",
            quest_type=quest_type,
            target=target,
            **kwargs
        )

    def test_create_quest(self):
        """Test creating a quest from config."""
        config = self._create_config()
        quest = Quest(config)
        self.assertEqual(quest.config, config)
        self.assertEqual(quest.progress, 0)
        self.assertFalse(quest.is_completed)
        self.assertFalse(quest.is_claimed)

    def test_quest_with_none_config_raises(self):
        """Test that None config raises ValueError."""
        with self.assertRaises(ValueError):
            Quest(None)

    def test_quest_properties(self):
        """Test quest property accessors."""
        config = self._create_config(
            quest_type=QuestType.WIN_TRAINER_BATTLE,
            target=5
        )
        quest = Quest(config)
        self.assertEqual(quest.identifier, "test_quest")
        self.assertEqual(quest.name, "Test Quest")
        self.assertEqual(quest.desc, "Test description")
        self.assertEqual(quest.quest_type, QuestType.WIN_TRAINER_BATTLE)
        self.assertEqual(quest.target, 5)

    def test_progress_display(self):
        """Test progress display string."""
        quest = Quest(self._create_config(target=10))
        self.assertEqual(quest.progress_display, "0/10")
        quest.set_progress(5)
        self.assertEqual(quest.progress_display, "5/10")
        quest.set_progress(15)
        self.assertEqual(quest.progress_display, "10/10")

    def test_progress_percent(self):
        """Test progress percentage calculation."""
        quest = Quest(self._create_config(target=10))
        self.assertEqual(quest.progress_percent, 0.0)
        quest.set_progress(5)
        self.assertEqual(quest.progress_percent, 50.0)
        quest.set_progress(10)
        self.assertEqual(quest.progress_percent, 100.0)
        quest.set_progress(15)
        self.assertEqual(quest.progress_percent, 100.0)

    def test_process_event_catch_any(self):
        """Test processing CATCH_ANY events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.CATCH_ANY,
            target=2
        ))

        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 1)
        self.assertFalse(quest.is_completed)

        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 2)
        self.assertTrue(quest.is_completed)

    def test_process_event_catch_type(self):
        """Test processing CATCH_TYPE events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.CATCH_TYPE,
            target=1,
            type_filter="water"
        ))

        # Wrong type should not progress
        event = QuestEvent.pokete_caught("steini", ["stone"])
        self.assertFalse(quest.process_event(event))
        self.assertEqual(quest.progress, 0)

        # Correct type should progress
        event = QuestEvent.pokete_caught("bator", ["water"])
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 1)
        self.assertTrue(quest.is_completed)

    def test_process_event_catch_specific(self):
        """Test processing CATCH_SPECIFIC events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.CATCH_SPECIFIC,
            target=1,
            species_filter="steini"
        ))

        # Wrong species should not progress
        event = QuestEvent.pokete_caught("mowcow", ["normal"])
        self.assertFalse(quest.process_event(event))

        # Correct species should progress (case insensitive)
        event = QuestEvent.pokete_caught("Steini", ["stone"])
        self.assertTrue(quest.process_event(event))
        self.assertTrue(quest.is_completed)

    def test_process_event_trainer_battle(self):
        """Test processing WIN_TRAINER_BATTLE events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.WIN_TRAINER_BATTLE,
            target=2
        ))

        # Wild battle should not count
        event = QuestEvent.wild_battle_won()
        self.assertFalse(quest.process_event(event))
        self.assertEqual(quest.progress, 0)

        # Trainer battle should count
        event = QuestEvent.trainer_battle_won()
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 1)

    def test_process_event_wild_battle(self):
        """Test processing WIN_WILD_BATTLE events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.WIN_WILD_BATTLE,
            target=1
        ))

        # Trainer battle should not count
        event = QuestEvent.trainer_battle_won()
        self.assertFalse(quest.process_event(event))

        # Wild battle should count
        event = QuestEvent.wild_battle_won()
        self.assertTrue(quest.process_event(event))
        self.assertTrue(quest.is_completed)

    def test_process_event_collect_coins(self):
        """Test processing COLLECT_COINS events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.COLLECT_COINS,
            target=100
        ))

        event = QuestEvent.coins_collected(50)
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 50)

        event = QuestEvent.coins_collected(60)
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 110)
        self.assertTrue(quest.is_completed)

    def test_process_event_coins_zero_does_not_progress(self):
        """Test that zero coins does not count as progress."""
        quest = Quest(self._create_config(
            quest_type=QuestType.COLLECT_COINS,
            target=100
        ))

        event = QuestEvent.coins_collected(0)
        self.assertFalse(quest.process_event(event))
        self.assertEqual(quest.progress, 0)

    def test_process_event_evolve(self):
        """Test processing EVOLVE_POKETE events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.EVOLVE_POKETE,
            target=1
        ))

        event = QuestEvent.pokete_evolved("steini", "bigstone")
        self.assertTrue(quest.process_event(event))
        self.assertTrue(quest.is_completed)

    def test_process_event_use_item(self):
        """Test processing USE_ITEM events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.USE_ITEM,
            target=1,
            item_filter=["healing_potion", "super_potion"]
        ))

        # Wrong item should not count
        event = QuestEvent.item_used("poketeball")
        self.assertFalse(quest.process_event(event))

        # Correct item should count
        event = QuestEvent.item_used("healing_potion")
        self.assertTrue(quest.process_event(event))
        self.assertTrue(quest.is_completed)

    def test_process_event_use_item_no_filter(self):
        """Test USE_ITEM without filter counts any item."""
        quest = Quest(self._create_config(
            quest_type=QuestType.USE_ITEM,
            target=1,
            item_filter=None
        ))

        event = QuestEvent.item_used("any_item")
        self.assertTrue(quest.process_event(event))
        self.assertTrue(quest.is_completed)

    def test_process_event_visit_maps(self):
        """Test processing VISIT_MAPS events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.VISIT_MAPS,
            target=2
        ))

        # First map
        event = QuestEvent.map_visited("playmap_1")
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 1)

        # Same map doesn't count twice
        event = QuestEvent.map_visited("playmap_1")
        self.assertFalse(quest.process_event(event))
        self.assertEqual(quest.progress, 1)

        # Second different map
        event = QuestEvent.map_visited("playmap_2")
        self.assertTrue(quest.process_event(event))
        self.assertEqual(quest.progress, 2)
        self.assertTrue(quest.is_completed)

    def test_process_event_none_returns_false(self):
        """Test that None event returns False."""
        quest = Quest(self._create_config())
        self.assertFalse(quest.process_event(None))

    def test_process_event_completed_quest_ignores_events(self):
        """Test that completed quests don't process events."""
        quest = Quest(self._create_config(
            quest_type=QuestType.CATCH_ANY,
            target=1
        ))

        event = QuestEvent.pokete_caught("steini", ["stone"])
        quest.process_event(event)
        self.assertTrue(quest.is_completed)

        # Additional events should not increase progress
        quest.process_event(event)
        self.assertEqual(quest.progress, 1)

    def test_mark_claimed(self):
        """Test marking quest as claimed."""
        quest = Quest(self._create_config())
        self.assertFalse(quest.is_claimed)
        quest.mark_claimed()
        self.assertTrue(quest.is_claimed)

    def test_set_progress(self):
        """Test setting progress directly."""
        quest = Quest(self._create_config(target=10))
        quest.set_progress(5)
        self.assertEqual(quest.progress, 5)
        self.assertFalse(quest.is_completed)

        quest.set_progress(10)
        self.assertTrue(quest.is_completed)

    def test_set_progress_negative_becomes_zero(self):
        """Test that negative progress becomes zero."""
        quest = Quest(self._create_config())
        quest.set_progress(-5)
        self.assertEqual(quest.progress, 0)

    def test_set_maps_visited(self):
        """Test setting visited maps."""
        quest = Quest(self._create_config(
            quest_type=QuestType.VISIT_MAPS,
            target=2
        ))

        # Use process_event to properly track maps
        quest.process_event(QuestEvent.map_visited("map1"))
        quest.process_event(QuestEvent.map_visited("map2"))
        self.assertEqual(quest.progress, 2)

        # set_maps_visited is for loading from save
        quest2 = Quest(self._create_config(
            quest_type=QuestType.VISIT_MAPS,
            target=3
        ))
        quest2.set_maps_visited(["a", "b"])
        quest2.set_progress(2)  # Must also set progress when loading
        self.assertEqual(quest2.progress, 2)

    def test_to_dict(self):
        """Test serializing quest state."""
        quest = Quest(self._create_config(target=5))
        quest.set_progress(3)

        data = quest.to_dict()
        self.assertEqual(data["identifier"], "test_quest")
        self.assertEqual(data["progress"], 3)
        self.assertFalse(data["completed"])
        self.assertFalse(data["claimed"])

    def test_from_dict(self):
        """Test restoring quest from saved data."""
        config = self._create_config(target=5)
        data = {
            "identifier": "test_quest",
            "progress": 3,
            "completed": False,
            "claimed": False,
            "maps_visited": []
        }

        quest = Quest.from_dict(data, config)
        self.assertIsNotNone(quest)
        self.assertEqual(quest.progress, 3)
        self.assertFalse(quest.is_completed)

    def test_from_dict_restores_completion(self):
        """Test that completion state is restored."""
        config = self._create_config(target=5)
        data = {
            "identifier": "test_quest",
            "progress": 5,
            "completed": True,
            "claimed": True,
            "maps_visited": []
        }

        quest = Quest.from_dict(data, config)
        self.assertTrue(quest.is_completed)
        self.assertTrue(quest.is_claimed)

    def test_from_dict_with_none_returns_none(self):
        """Test that None data returns None."""
        config = self._create_config()
        self.assertIsNone(Quest.from_dict(None, config))
        self.assertIsNone(Quest.from_dict({}, None))


if __name__ == "__main__":
    unittest.main()
