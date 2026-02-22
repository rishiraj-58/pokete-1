"""Unit tests for the rematch system."""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Import only the rematch module without triggering the full package
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rematch",
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete', 'classes', 'npcs', 'rematch.py')
)
rematch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rematch_module)

REMATCH_LEVEL_THRESHOLD = rematch_module.REMATCH_LEVEL_THRESHOLD
REMATCH_STAT_MULTIPLIER = rematch_module.REMATCH_STAT_MULTIPLIER
RematchManager = rematch_module.RematchManager
get_highest_poke_level = rematch_module.get_highest_poke_level
is_rematch_eligible = rematch_module.is_rematch_eligible
scale_stat = rematch_module.scale_stat


class TestRematchThresholdCalculation(unittest.TestCase):
    """Tests for rematch eligibility threshold calculations."""

    def test_is_rematch_eligible_exact_threshold(self):
        """Player at exactly threshold levels above trainer should be eligible."""
        trainer_level = 10
        player_level = trainer_level + REMATCH_LEVEL_THRESHOLD
        self.assertTrue(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_above_threshold(self):
        """Player more than threshold levels above should be eligible."""
        trainer_level = 10
        player_level = trainer_level + REMATCH_LEVEL_THRESHOLD + 5
        self.assertTrue(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_below_threshold(self):
        """Player below threshold should not be eligible."""
        trainer_level = 10
        player_level = trainer_level + REMATCH_LEVEL_THRESHOLD - 1
        self.assertFalse(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_same_level(self):
        """Player at same level as trainer should not be eligible."""
        trainer_level = 10
        player_level = trainer_level
        self.assertFalse(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_player_lower(self):
        """Player at lower level than trainer should not be eligible."""
        trainer_level = 15
        player_level = 10
        self.assertFalse(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_low_levels(self):
        """Test with low level values."""
        trainer_level = 1
        player_level = 1 + REMATCH_LEVEL_THRESHOLD
        self.assertTrue(is_rematch_eligible(player_level, trainer_level))

    def test_is_rematch_eligible_high_levels(self):
        """Test with high level values."""
        trainer_level = 100
        player_level = 100 + REMATCH_LEVEL_THRESHOLD
        self.assertTrue(is_rematch_eligible(player_level, trainer_level))

    def test_threshold_constant_is_3(self):
        """Verify the threshold constant is set to 3."""
        self.assertEqual(REMATCH_LEVEL_THRESHOLD, 3)


class TestStatScaling(unittest.TestCase):
    """Tests for stat scaling during rematches."""

    def test_scale_stat_default_multiplier(self):
        """Test scaling with default multiplier (1.2x)."""
        original = 100
        scaled = scale_stat(original)
        self.assertEqual(scaled, 120)

    def test_scale_stat_custom_multiplier(self):
        """Test scaling with custom multiplier."""
        original = 100
        scaled = scale_stat(original, 1.5)
        self.assertEqual(scaled, 150)

    def test_scale_stat_rounds_down(self):
        """Test that scaling rounds down to int."""
        original = 99
        scaled = scale_stat(original)  # 99 * 1.2 = 118.8
        self.assertEqual(scaled, 118)

    def test_scale_stat_small_value(self):
        """Test scaling small values."""
        original = 5
        scaled = scale_stat(original)  # 5 * 1.2 = 6
        self.assertEqual(scaled, 6)

    def test_scale_stat_zero(self):
        """Test scaling zero value."""
        original = 0
        scaled = scale_stat(original)
        self.assertEqual(scaled, 0)

    def test_scale_stat_large_value(self):
        """Test scaling large values."""
        original = 1000
        scaled = scale_stat(original)
        self.assertEqual(scaled, 1200)

    def test_multiplier_constant_is_1_2(self):
        """Verify the multiplier constant is set to 1.2."""
        self.assertAlmostEqual(REMATCH_STAT_MULTIPLIER, 1.2)


class TestGetHighestPokeLevel(unittest.TestCase):
    """Tests for getting highest pokete level from a list."""

    def test_get_highest_single_poke(self):
        """Test with single pokete."""
        poke = MagicMock()
        poke.lvl.return_value = 15
        self.assertEqual(get_highest_poke_level([poke]), 15)

    def test_get_highest_multiple_pokes(self):
        """Test with multiple poketes."""
        pokes = [MagicMock(), MagicMock(), MagicMock()]
        pokes[0].lvl.return_value = 10
        pokes[1].lvl.return_value = 25
        pokes[2].lvl.return_value = 15
        self.assertEqual(get_highest_poke_level(pokes), 25)

    def test_get_highest_empty_list(self):
        """Test with empty list returns 0."""
        self.assertEqual(get_highest_poke_level([]), 0)

    def test_get_highest_all_same_level(self):
        """Test when all pokes have same level."""
        pokes = [MagicMock(), MagicMock()]
        pokes[0].lvl.return_value = 20
        pokes[1].lvl.return_value = 20
        self.assertEqual(get_highest_poke_level(pokes), 20)


class TestRematchManager(unittest.TestCase):
    """Tests for RematchManager class."""

    def setUp(self):
        """Set up a fresh RematchManager for each test."""
        self.manager = RematchManager()

    def test_register_defeated_trainer(self):
        """Test registering a defeated trainer."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.assertEqual(self.manager.get_trainer_original_level("Franz"), 10)

    def test_register_defeated_trainer_no_overwrite(self):
        """Test that registering same trainer twice doesn't overwrite."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.manager.register_defeated_trainer("Franz", 20)
        self.assertEqual(self.manager.get_trainer_original_level("Franz"), 10)

    def test_is_rematch_available_not_defeated(self):
        """Test rematch not available for non-defeated trainer."""
        self.assertFalse(self.manager.is_rematch_available("Unknown", 50))

    def test_is_rematch_available_not_high_enough(self):
        """Test rematch not available when player level too low."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.assertFalse(self.manager.is_rematch_available("Franz", 12))

    def test_is_rematch_available_high_enough(self):
        """Test rematch available when player level is high enough."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.assertTrue(self.manager.is_rematch_available("Franz", 13))

    def test_is_rematch_available_after_completion(self):
        """Test rematch not available after it's been completed."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.manager.complete_rematch("Franz")
        self.assertFalse(self.manager.is_rematch_available("Franz", 20))

    def test_complete_rematch(self):
        """Test completing a rematch."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.manager.complete_rematch("Franz")
        self.assertIn("Franz", self.manager._completed_rematches)

    def test_complete_rematch_no_duplicate(self):
        """Test completing same rematch twice doesn't create duplicate."""
        self.manager.complete_rematch("Franz")
        self.manager.complete_rematch("Franz")
        self.assertEqual(self.manager._completed_rematches.count("Franz"), 1)

    def test_get_trainer_original_level_not_found(self):
        """Test getting level for unknown trainer returns None."""
        self.assertIsNone(self.manager.get_trainer_original_level("Unknown"))


class TestRematchManagerSerialization(unittest.TestCase):
    """Tests for RematchManager save/load functionality."""

    def test_to_dict_empty(self):
        """Test serializing empty manager."""
        manager = RematchManager()
        data = manager.to_dict()
        self.assertEqual(data, {
            "trainer_data": {},
            "completed_rematches": []
        })

    def test_to_dict_with_data(self):
        """Test serializing manager with data."""
        manager = RematchManager()
        manager.register_defeated_trainer("Franz", 10)
        manager.register_defeated_trainer("Monica", 15)
        manager.complete_rematch("Franz")
        
        data = manager.to_dict()
        self.assertEqual(data["trainer_data"], {"Franz": 10, "Monica": 15})
        self.assertEqual(data["completed_rematches"], ["Franz"])

    def test_from_dict_empty(self):
        """Test deserializing empty data."""
        data = {"trainer_data": {}, "completed_rematches": []}
        manager = RematchManager.from_dict(data)
        self.assertEqual(manager._trainer_data, {})
        self.assertEqual(manager._completed_rematches, [])

    def test_from_dict_with_data(self):
        """Test deserializing manager with data."""
        data = {
            "trainer_data": {"Franz": 10, "Monica": 15},
            "completed_rematches": ["Franz"]
        }
        manager = RematchManager.from_dict(data)
        self.assertEqual(manager._trainer_data, {"Franz": 10, "Monica": 15})
        self.assertEqual(manager._completed_rematches, ["Franz"])

    def test_from_dict_missing_keys(self):
        """Test deserializing with missing keys uses defaults."""
        data = {}
        manager = RematchManager.from_dict(data)
        self.assertEqual(manager._trainer_data, {})
        self.assertEqual(manager._completed_rematches, [])

    def test_roundtrip_serialization(self):
        """Test that data survives a save/load roundtrip."""
        manager1 = RematchManager()
        manager1.register_defeated_trainer("Franz", 10)
        manager1.register_defeated_trainer("Monica", 15)
        manager1.complete_rematch("Franz")
        
        data = manager1.to_dict()
        manager2 = RematchManager.from_dict(data)
        
        self.assertEqual(manager1._trainer_data, manager2._trainer_data)
        self.assertEqual(manager1._completed_rematches, manager2._completed_rematches)

    def test_to_dict_returns_copy(self):
        """Test that to_dict returns copies, not references."""
        manager = RematchManager()
        manager.register_defeated_trainer("Franz", 10)
        
        data = manager.to_dict()
        data["trainer_data"]["Franz"] = 999
        data["completed_rematches"].append("Modified")
        
        # Original manager should be unaffected
        self.assertEqual(manager._trainer_data["Franz"], 10)
        self.assertNotIn("Modified", manager._completed_rematches)


class TestRematchManagerMultipleTrainers(unittest.TestCase):
    """Tests for managing multiple trainers."""

    def setUp(self):
        self.manager = RematchManager()

    def test_multiple_trainers_independent(self):
        """Test that multiple trainers are tracked independently."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.manager.register_defeated_trainer("Monica", 20)
        
        # Franz eligible, Monica not (at level 13)
        self.assertTrue(self.manager.is_rematch_available("Franz", 13))
        self.assertFalse(self.manager.is_rematch_available("Monica", 13))
        
        # Both eligible at level 23
        self.assertTrue(self.manager.is_rematch_available("Franz", 23))
        self.assertTrue(self.manager.is_rematch_available("Monica", 23))

    def test_completing_one_doesnt_affect_others(self):
        """Test that completing one rematch doesn't affect others."""
        self.manager.register_defeated_trainer("Franz", 10)
        self.manager.register_defeated_trainer("Monica", 10)
        
        self.manager.complete_rematch("Franz")
        
        self.assertFalse(self.manager.is_rematch_available("Franz", 20))
        self.assertTrue(self.manager.is_rematch_available("Monica", 20))


class TestRematchManagerConstructor(unittest.TestCase):
    """Tests for RematchManager constructor."""

    def test_constructor_with_no_args(self):
        """Test constructor with no arguments."""
        manager = RematchManager()
        self.assertEqual(manager._trainer_data, {})
        self.assertEqual(manager._completed_rematches, [])

    def test_constructor_with_trainer_data(self):
        """Test constructor with trainer data."""
        trainer_data = {"Franz": 10, "Monica": 15}
        manager = RematchManager(trainer_data=trainer_data)
        self.assertEqual(manager._trainer_data, trainer_data)
        self.assertEqual(manager._completed_rematches, [])

    def test_constructor_with_completed_rematches(self):
        """Test constructor with completed rematches."""
        completed = ["Franz", "Monica"]
        manager = RematchManager(completed_rematches=completed)
        self.assertEqual(manager._trainer_data, {})
        self.assertEqual(manager._completed_rematches, completed)

    def test_constructor_with_both_args(self):
        """Test constructor with both arguments."""
        trainer_data = {"Franz": 10}
        completed = ["Monica"]
        manager = RematchManager(trainer_data=trainer_data, completed_rematches=completed)
        self.assertEqual(manager._trainer_data, trainer_data)
        self.assertEqual(manager._completed_rematches, completed)


if __name__ == "__main__":
    unittest.main()
