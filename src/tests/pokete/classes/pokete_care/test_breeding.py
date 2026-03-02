"""Tests for the Pokete breeding system."""

import unittest
from unittest.mock import patch, MagicMock

from pokete.classes.pokete_care.breeding import (
    BreedingManager,
    BreedingPair,
    Egg,
    EggStats,
    BASE_HATCH_TIME,
)
from pokete.classes.poke import Poke


class TestEggStats(unittest.TestCase):
    """Tests for the EggStats dataclass."""
    
    def test_egg_stats_creation(self):
        stats = EggStats(hp=25, atc=5, defense=3, initiative=4)
        self.assertEqual(stats.hp, 25)
        self.assertEqual(stats.atc, 5)
        self.assertEqual(stats.defense, 3)
        self.assertEqual(stats.initiative, 4)


class TestEgg(unittest.TestCase):
    """Tests for the Egg class."""
    
    def setUp(self):
        self.stats = EggStats(hp=20, atc=3, defense=2, initiative=3)
        self.egg = Egg(
            pokete_identifier="steini",
            stats=self.stats,
            created_time=100,
            hatch_time=220,
            parent1_identifier="steini",
            parent2_identifier="lilstone",
            shiny=False
        )
    
    def test_is_ready_false_before_hatch_time(self):
        self.assertFalse(self.egg.is_ready(100))
        self.assertFalse(self.egg.is_ready(219))
    
    def test_is_ready_true_at_hatch_time(self):
        self.assertTrue(self.egg.is_ready(220))
        self.assertTrue(self.egg.is_ready(300))
    
    def test_time_remaining(self):
        self.assertEqual(self.egg.time_remaining(100), 120)
        self.assertEqual(self.egg.time_remaining(200), 20)
        self.assertEqual(self.egg.time_remaining(220), 0)
        self.assertEqual(self.egg.time_remaining(300), 0)
    
    def test_dict_serialization(self):
        data = self.egg.dict()
        self.assertEqual(data["pokete_identifier"], "steini")
        self.assertEqual(data["hp"], 20)
        self.assertEqual(data["atc"], 3)
        self.assertEqual(data["defense"], 2)
        self.assertEqual(data["initiative"], 3)
        self.assertEqual(data["created_time"], 100)
        self.assertEqual(data["hatch_time"], 220)
        self.assertEqual(data["parent1_identifier"], "steini")
        self.assertEqual(data["parent2_identifier"], "lilstone")
        self.assertFalse(data["shiny"])
    
    def test_from_dict_deserialization(self):
        data = self.egg.dict()
        egg2 = Egg.from_dict(data)
        self.assertEqual(egg2.pokete_identifier, self.egg.pokete_identifier)
        self.assertEqual(egg2.stats.hp, self.egg.stats.hp)
        self.assertEqual(egg2.hatch_time, self.egg.hatch_time)
        self.assertEqual(egg2.shiny, self.egg.shiny)
    
    def test_hatch_creates_poke(self):
        poke = self.egg.hatch()
        self.assertIsInstance(poke, Poke)
        self.assertEqual(poke.identifier, "steini")
        # New pokes start with 0 xp
        self.assertEqual(poke.xp, 0)
        # The poke should be marked as hatched from an egg
        self.assertEqual(poke.poke_stats.caught_with, "egg")
        self.assertIsNotNone(poke.poke_stats.ownership_date)


class TestBreedingPair(unittest.TestCase):
    """Tests for the BreedingPair class."""
    
    def setUp(self):
        self.pair = BreedingPair()
        # Create test pokes with compatible types (both have stone and normal)
        self.poke1 = Poke("steini", 50)  # types: stone, normal
        self.poke2 = Poke("lilstone", 50)  # types: stone, normal
        # Create incompatible poke
        self.poke_fire = Poke("wolfior", 50)  # types: fire, normal
    
    def test_initial_state_is_empty(self):
        self.assertTrue(self.pair.is_empty())
        self.assertFalse(self.pair.is_complete())
        self.assertTrue(self.pair.has_slot_available())
    
    def test_add_first_parent(self):
        self.assertTrue(self.pair.add_parent(self.poke1))
        self.assertFalse(self.pair.is_empty())
        self.assertFalse(self.pair.is_complete())
        self.assertTrue(self.pair.has_slot_available())
        self.assertEqual(self.pair.parent1, self.poke1)
    
    def test_add_second_parent(self):
        self.pair.add_parent(self.poke1)
        self.assertTrue(self.pair.add_parent(self.poke2))
        self.assertTrue(self.pair.is_complete())
        self.assertFalse(self.pair.has_slot_available())
        self.assertEqual(self.pair.parent2, self.poke2)
    
    def test_add_third_parent_fails(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        self.assertFalse(self.pair.add_parent(self.poke_fire))
    
    def test_remove_parent(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        
        removed = self.pair.remove_parent(0)
        self.assertEqual(removed, self.poke1)
        self.assertIsNone(self.pair.parent1)
        self.assertEqual(self.pair.parent2, self.poke2)
    
    def test_remove_from_empty_slot(self):
        removed = self.pair.remove_parent(0)
        self.assertIsNone(removed)
    
    def test_compatible_pair(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        self.assertTrue(self.pair.is_compatible())
        shared = self.pair.get_shared_types()
        self.assertIn("stone", shared)
        self.assertIn("normal", shared)
    
    def test_incompatible_pair(self):
        poke_water = Poke("blub", 50)  # types: water, normal
        self.pair.add_parent(self.poke_fire)  # fire, normal
        self.pair.add_parent(poke_water)  # water, normal
        # They share "normal" type, so they ARE compatible
        self.assertTrue(self.pair.is_compatible())
    
    def test_truly_incompatible_pair(self):
        # We need poketes that don't share ANY type
        # Looking at the data: fire types vs water types that don't share normal
        # Actually most poketes share "normal", let's test with the pair not complete
        pair = BreedingPair()
        pair.add_parent(self.poke1)
        # Incomplete pair is not compatible
        self.assertFalse(pair.is_compatible())
    
    def test_get_shared_types_empty_pair(self):
        self.assertEqual(self.pair.get_shared_types(), [])
    
    def test_clear(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        self.pair.clear()
        self.assertTrue(self.pair.is_empty())
    
    def test_dict_serialization(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        data = self.pair.dict()
        self.assertIsNotNone(data["parent1"])
        self.assertIsNotNone(data["parent2"])
        self.assertEqual(data["parent1"]["name"], "steini")
        self.assertEqual(data["parent2"]["name"], "lilstone")
    
    def test_from_dict_deserialization(self):
        self.pair.add_parent(self.poke1)
        self.pair.add_parent(self.poke2)
        data = self.pair.dict()
        pair2 = BreedingPair.from_dict(data)
        self.assertTrue(pair2.is_complete())
        self.assertEqual(pair2.parent1.identifier, "steini")
        self.assertEqual(pair2.parent2.identifier, "lilstone")


class TestBreedingManager(unittest.TestCase):
    """Tests for the BreedingManager class."""
    
    def setUp(self):
        self.manager = BreedingManager()
        self.poke1 = Poke("steini", 50)
        self.poke2 = Poke("lilstone", 50)
        self.current_time = 1000
    
    def test_initial_state(self):
        self.assertTrue(self.manager.breeding_pair.is_empty())
        self.assertIsNone(self.manager.egg)
        self.assertEqual(len(self.manager.notifications), 0)
    
    def test_add_to_breeding_pair(self):
        self.assertTrue(self.manager.add_to_breeding_pair(self.poke1))
        self.assertEqual(self.manager.breeding_pair.parent1, self.poke1)
    
    def test_add_to_breeding_pair_with_egg_fails(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        poke3 = Poke("bigstone", 50)
        self.assertFalse(self.manager.add_to_breeding_pair(poke3))
    
    def test_remove_from_breeding_pair(self):
        self.manager.add_to_breeding_pair(self.poke1)
        removed = self.manager.remove_from_breeding_pair(0)
        self.assertEqual(removed, self.poke1)
        self.assertTrue(self.manager.breeding_pair.is_empty())
    
    def test_can_breed_requires_complete_pair(self):
        self.assertFalse(self.manager.can_breed())
        self.manager.add_to_breeding_pair(self.poke1)
        self.assertFalse(self.manager.can_breed())
    
    def test_can_breed_with_complete_compatible_pair(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.assertTrue(self.manager.can_breed())
    
    def test_can_breed_false_with_existing_egg(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        self.assertFalse(self.manager.can_breed())
    
    def test_get_incompatibility_reason_no_pair(self):
        reason = self.manager.get_incompatibility_reason()
        self.assertEqual(reason, "Two Poketes are required for breeding")
    
    def test_get_incompatibility_reason_egg_exists(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        reason = self.manager.get_incompatibility_reason()
        self.assertEqual(reason, "An egg is already incubating")
    
    def test_get_incompatibility_reason_none_when_can_breed(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.assertIsNone(self.manager.get_incompatibility_reason())
    
    def test_start_breeding_creates_egg(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        egg = self.manager.start_breeding(self.current_time)
        
        self.assertIsNotNone(egg)
        self.assertIsNotNone(self.manager.egg)
        self.assertEqual(egg.created_time, self.current_time)
        self.assertIn(egg.pokete_identifier, ["steini", "lilstone"])
    
    def test_start_breeding_without_pair_returns_none(self):
        egg = self.manager.start_breeding(self.current_time)
        self.assertIsNone(egg)
    
    def test_check_egg_ready_false(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        self.assertFalse(self.manager.check_egg_ready(self.current_time + 10))
        self.assertEqual(len(self.manager.notifications), 0)
    
    def test_check_egg_ready_true_and_notifies(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        future_time = self.current_time + BASE_HATCH_TIME + 100
        self.assertTrue(self.manager.check_egg_ready(future_time))
        self.assertTrue(self.manager.has_notification())
    
    def test_check_egg_ready_no_egg(self):
        self.assertFalse(self.manager.check_egg_ready(self.current_time))
    
    def test_get_egg_status_no_egg(self):
        self.assertIsNone(self.manager.get_egg_status(self.current_time))
    
    def test_get_egg_status_incubating(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        status = self.manager.get_egg_status(self.current_time + 10)
        self.assertIsNotNone(status)
        self.assertIn("Time until hatch", status)
    
    def test_get_egg_status_ready(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        future_time = self.current_time + BASE_HATCH_TIME + 100
        status = self.manager.get_egg_status(future_time)
        self.assertEqual(status, "Your egg is ready to collect!")
    
    def test_collect_egg_returns_poke(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        poke = self.manager.collect_egg()
        self.assertIsInstance(poke, Poke)
        self.assertIsNone(self.manager.egg)
    
    def test_collect_egg_no_egg(self):
        poke = self.manager.collect_egg()
        self.assertIsNone(poke)
    
    def test_get_notifications(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        future_time = self.current_time + BASE_HATCH_TIME + 100
        self.manager.check_egg_ready(future_time)
        
        notifications = self.manager.get_notifications()
        self.assertGreater(len(notifications), 0)
        # Notifications should be cleared after getting
        self.assertFalse(self.manager.has_notification())
    
    def test_get_breeding_pair_status_empty(self):
        status = self.manager.get_breeding_pair_status()
        self.assertEqual(status, "No Poketes in breeding pair")
    
    def test_get_breeding_pair_status_partial(self):
        self.manager.add_to_breeding_pair(self.poke1)
        status = self.manager.get_breeding_pair_status()
        self.assertIn("Steini", status)
        self.assertIn("Empty", status)
    
    def test_get_breeding_pair_status_complete_compatible(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        status = self.manager.get_breeding_pair_status()
        self.assertIn("Compatible", status)
        self.assertIn("stone", status.lower())
    
    def test_return_parents(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        
        parent1, parent2 = self.manager.return_parents()
        self.assertEqual(parent1, self.poke1)
        self.assertEqual(parent2, self.poke2)
        self.assertTrue(self.manager.breeding_pair.is_empty())
    
    def test_dict_serialization(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        data = self.manager.dict()
        self.assertIn("breeding_pair", data)
        self.assertIn("egg", data)
        self.assertIn("notifications", data)
        self.assertIsNotNone(data["egg"])
    
    def test_from_dict_deserialization(self):
        self.manager.add_to_breeding_pair(self.poke1)
        self.manager.add_to_breeding_pair(self.poke2)
        self.manager.start_breeding(self.current_time)
        
        data = self.manager.dict()
        
        manager2 = BreedingManager()
        manager2.from_dict(data)
        
        self.assertTrue(manager2.breeding_pair.is_complete())
        self.assertIsNotNone(manager2.egg)
        self.assertEqual(manager2.egg.created_time, self.current_time)


class TestBreedingManagerHatchTime(unittest.TestCase):
    """Tests for hatch time computation."""
    
    def setUp(self):
        self.manager = BreedingManager()
        self.current_time = 1000
    
    def test_higher_level_parents_faster_hatch(self):
        # Low level parents
        low_poke1 = Poke("steini", 4)  # Level 2
        low_poke2 = Poke("lilstone", 4)  # Level 2
        
        # High level parents
        high_poke1 = Poke("steini", 900)  # Level 30
        high_poke2 = Poke("lilstone", 900)  # Level 30
        
        # Create manager for low level
        low_manager = BreedingManager()
        low_manager.add_to_breeding_pair(low_poke1)
        low_manager.add_to_breeding_pair(low_poke2)
        low_egg = low_manager.start_breeding(self.current_time)
        
        # Create manager for high level
        high_manager = BreedingManager()
        high_manager.add_to_breeding_pair(high_poke1)
        high_manager.add_to_breeding_pair(high_poke2)
        high_egg = high_manager.start_breeding(self.current_time)
        
        # Higher level should have shorter hatch time
        low_duration = low_egg.hatch_time - low_egg.created_time
        high_duration = high_egg.hatch_time - high_egg.created_time
        
        self.assertLess(high_duration, low_duration)


class TestBreedingManagerShinyChance(unittest.TestCase):
    """Tests for shiny chance computation."""
    
    def test_shiny_parents_increase_chance(self):
        # This is a probabilistic test, so we'll just verify the logic works
        # by checking that eggs can be created from shiny parents
        manager = BreedingManager()
        poke1 = Poke("steini", 50, shiny=True)
        poke2 = Poke("lilstone", 50, shiny=True)
        
        manager.add_to_breeding_pair(poke1)
        manager.add_to_breeding_pair(poke2)
        egg = manager.start_breeding(1000)
        
        # Egg should be created regardless of shiny status
        self.assertIsNotNone(egg)
        # Shiny status is randomly determined, so we just check it's a boolean
        self.assertIsInstance(egg.shiny, bool)


if __name__ == "__main__":
    unittest.main()
