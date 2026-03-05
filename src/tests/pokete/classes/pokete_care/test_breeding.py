"""Tests for the breeding system."""

import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


class MockResourcePoke:
    """Mock for asset_service poke data."""
    def __init__(
        self,
        name="TestPoke",
        hp=20,
        atc=5,
        defense=5,
        types=None,
        attacks=None,
        evolve_poke="",
        evolve_lvl=0,
        initiative=5,
        miss_chance=0,
        lose_xp=2,
        night_active=None,
        ico=None,
        pool=None,
        desc="A test pokete",
        rarity=1.0,
    ):
        self.name = name
        self.hp = hp
        self.atc = atc
        self.defense = defense
        self.types = types or ["normal"]
        self.attacks = attacks or ["tackle"]
        self.evolve_poke = evolve_poke
        self.evolve_lvl = evolve_lvl
        self.initiative = initiative
        self.miss_chance = miss_chance
        self.lose_xp = lose_xp
        self.night_active = night_active
        self.ico = ico or []
        self.pool = pool or []
        self.desc = desc
        self.rarity = rarity


class MockPoke:
    """Mock Poke class for testing."""
    def __init__(
        self,
        identifier: str,
        xp: int = 100,
        types: list[str] | None = None,
        shiny: bool = False,
        atc: int = 5,
        defense: int = 5,
        initiative: int = 5,
    ):
        self.identifier = identifier
        self.xp = xp
        self.inf = MockResourcePoke(
            name=identifier,
            types=types or ["normal"],
            atc=atc,
            defense=defense,
            initiative=initiative,
        )
        self.shiny = shiny
        self.name = identifier
        self.hp = 20
        self.atc = atc
        self.defense = defense
        self.initiative = initiative
        self.attacks = ["tackle"]
        self.effects = []
        self._nature_dict = {"nature": "normal", "grade": 1}
        self._stats_dict = {
            "ownership_date": None,
            "evolved_date": None,
            "total_battles": 0,
            "lost_battles": 0,
            "win_battles": 0,
            "earned_xp": 0,
            "caught_with": None,
            "run_away": 0,
        }

    def lvl(self) -> int:
        import math
        return int(math.sqrt(self.xp + 1))

    def dict(self) -> dict:
        return {
            "name": self.identifier,
            "xp": self.xp,
            "hp": self.hp,
            "ap": [10],
            "effects": [],
            "attacks": self.attacks,
            "shiny": self.shiny,
            "nature": self._nature_dict,
            "stats": self._stats_dict,
        }


class MockAssetService:
    """Mock asset service for testing."""
    def __init__(self):
        self._pokes = {
            "steini": MockResourcePoke(
                name="Steini", types=["stone", "normal"], atc=2, defense=4, initiative=5
            ),
            "mowcow": MockResourcePoke(
                name="Mowcow", types=["normal"], atc=2, defense=3, initiative=2
            ),
            "vogli": MockResourcePoke(
                name="Vogli",
                types=["flying", "normal", "bird"],
                evolve_poke="voglo",
                evolve_lvl=20,
                atc=6,
                defense=1,
                initiative=6,
            ),
            "voglo": MockResourcePoke(
                name="Voglo",
                types=["flying", "normal", "bird"],
                evolve_poke="voglus",
                evolve_lvl=35,
                atc=7,
                defense=1,
                initiative=7,
            ),
            "wolfior": MockResourcePoke(
                name="Wolfior", types=["fire", "normal"], atc=6, defense=3, initiative=4
            ),
            "karpi": MockResourcePoke(
                name="Karpi", types=["water", "normal"], atc=0, defense=0, initiative=0
            ),
            "__fallback__": MockResourcePoke(
                name="", types=["normal"]
            ),
        }

    def get_base_assets(self):
        return self

    @property
    def pokes(self):
        return self._pokes


class TestBreedingManager(unittest.TestCase):
    """Test cases for BreedingManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.mock_asset_service = self.asset_patcher.start()

        from pokete.classes.pokete_care.breeding import BreedingManager
        self.manager = BreedingManager()

    def tearDown(self):
        """Clean up patches."""
        self.asset_patcher.stop()

    def test_are_compatible_shared_type(self):
        """Test that poketes sharing a type are compatible."""
        poke1 = MockPoke("steini", types=["stone", "normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.assertTrue(self.manager.are_compatible(poke1, poke2))

    def test_are_compatible_no_shared_type(self):
        """Test that poketes with no shared types are incompatible."""
        poke1 = MockPoke("steini", types=["stone"])
        poke2 = MockPoke("karpi", types=["water"])

        self.assertFalse(self.manager.are_compatible(poke1, poke2))

    def test_are_compatible_multiple_shared_types(self):
        """Test poketes with multiple shared types."""
        poke1 = MockPoke("vogli", types=["flying", "normal", "bird"])
        poke2 = MockPoke("voglo", types=["flying", "normal", "bird"])

        self.assertTrue(self.manager.are_compatible(poke1, poke2))
        shared = self.manager.get_shared_types(poke1, poke2)
        self.assertEqual(len(shared), 3)

    def test_get_shared_types(self):
        """Test getting shared types between poketes."""
        poke1 = MockPoke("steini", types=["stone", "normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        shared = self.manager.get_shared_types(poke1, poke2)
        self.assertEqual(shared, ["normal"])

    def test_compute_hatch_time_basic(self):
        """Test basic hatch time computation."""
        poke1 = MockPoke("steini", xp=100, types=["stone", "normal"])
        poke2 = MockPoke("mowcow", xp=100, types=["normal"])

        hatch_time = self.manager.compute_hatch_time(poke1, poke2)

        self.assertGreater(hatch_time, 0)
        self.assertLessEqual(hatch_time, 300)

    def test_compute_hatch_time_more_shared_types_faster(self):
        """Test that more shared types result in faster hatching."""
        poke1_few = MockPoke("test1", types=["normal"])
        poke2_few = MockPoke("test2", types=["normal"])

        poke1_many = MockPoke("test3", types=["normal", "flying", "bird"])
        poke2_many = MockPoke("test4", types=["normal", "flying", "bird"])

        time_few = self.manager.compute_hatch_time(poke1_few, poke2_few)
        time_many = self.manager.compute_hatch_time(poke1_many, poke2_many)

        self.assertLess(time_many, time_few)

    def test_compute_hatch_time_higher_level_faster(self):
        """Test that higher level parents result in faster hatching."""
        poke1_low = MockPoke("test1", xp=10, types=["normal"])
        poke2_low = MockPoke("test2", xp=10, types=["normal"])

        poke1_high = MockPoke("test3", xp=2500, types=["normal"])
        poke2_high = MockPoke("test4", xp=2500, types=["normal"])

        time_low = self.manager.compute_hatch_time(poke1_low, poke2_low)
        time_high = self.manager.compute_hatch_time(poke1_high, poke2_high)

        self.assertLess(time_high, time_low)

    def test_start_breeding_success(self):
        """Test successful breeding start."""
        poke1 = MockPoke("steini", types=["stone", "normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        result = self.manager.start_breeding(poke1, poke2, current_time=1000)

        self.assertTrue(result)
        self.assertTrue(self.manager.has_breeding_pair)
        self.assertIsNotNone(self.manager.breeding_pair)

    def test_start_breeding_incompatible_fails(self):
        """Test that incompatible poketes cannot breed."""
        poke1 = MockPoke("steini", types=["stone"])
        poke2 = MockPoke("karpi", types=["water"])

        result = self.manager.start_breeding(poke1, poke2, current_time=1000)

        self.assertFalse(result)
        self.assertFalse(self.manager.has_breeding_pair)

    def test_start_breeding_already_breeding_fails(self):
        """Test that cannot start new breeding when one is in progress."""
        poke1 = MockPoke("steini", types=["stone", "normal"])
        poke2 = MockPoke("mowcow", types=["normal"])
        poke3 = MockPoke("vogli", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        result = self.manager.start_breeding(poke2, poke3, current_time=1000)

        self.assertFalse(result)

    def test_get_time_remaining(self):
        """Test getting remaining hatching time."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        remaining = self.manager.get_time_remaining(current_time=1000)
        self.assertEqual(remaining, hatch_time)

        remaining = self.manager.get_time_remaining(current_time=1100)
        self.assertEqual(remaining, hatch_time - 100)

    def test_get_time_remaining_no_breeding(self):
        """Test time remaining when no breeding is active."""
        remaining = self.manager.get_time_remaining(current_time=1000)
        self.assertEqual(remaining, -1)

    def test_is_egg_ready(self):
        """Test egg ready detection."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        self.assertFalse(self.manager.is_egg_ready(current_time=1000))
        self.assertTrue(self.manager.is_egg_ready(current_time=1000 + hatch_time))
        self.assertTrue(self.manager.is_egg_ready(current_time=1000 + hatch_time + 100))

    def test_should_notify_and_mark_notified(self):
        """Test notification logic."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        self.assertFalse(self.manager.should_notify(current_time=1000))

        ready_time = 1000 + hatch_time
        self.assertTrue(self.manager.should_notify(current_time=ready_time))

        self.manager.mark_notified()
        self.assertFalse(self.manager.should_notify(current_time=ready_time))

    def test_collect_egg_not_ready(self):
        """Test collecting egg before ready returns None."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)

        result = self.manager.collect_egg(current_time=1000)
        self.assertIsNone(result)

    def test_collect_egg_ready(self):
        """Test collecting ready egg returns offspring data."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ):
            result = self.manager.collect_egg(current_time=1000 + hatch_time)

        self.assertIsNotNone(result)
        self.assertIn("name", result)
        self.assertIn("xp", result)
        self.assertEqual(result["xp"], 0)
        self.assertFalse(self.manager.has_breeding_pair)

    def test_cancel_breeding(self):
        """Test canceling breeding returns parents."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)

        result = self.manager.cancel_breeding()

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertFalse(self.manager.has_breeding_pair)

    def test_cancel_breeding_no_breeding(self):
        """Test canceling when no breeding active."""
        result = self.manager.cancel_breeding()
        self.assertIsNone(result)

    def test_serialization_roundtrip(self):
        """Test that breeding state can be serialized and restored."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        original_data = self.manager.breeding_pair

        saved = self.manager.dict()

        from pokete.classes.pokete_care.breeding import BreedingManager
        new_manager = BreedingManager()
        new_manager.from_dict(saved)

        self.assertTrue(new_manager.has_breeding_pair)
        self.assertEqual(
            new_manager.breeding_pair.start_time,
            original_data.start_time
        )
        self.assertEqual(
            new_manager.breeding_pair.hatch_time,
            original_data.hatch_time
        )

    def test_serialization_no_breeding(self):
        """Test serialization with no active breeding."""
        saved = self.manager.dict()
        self.assertIsNone(saved["breeding_pair"])

        from pokete.classes.pokete_care.breeding import BreedingManager
        new_manager = BreedingManager()
        new_manager.from_dict(saved)

        self.assertFalse(new_manager.has_breeding_pair)


class TestShinyChance(unittest.TestCase):
    """Test cases for shiny chance computation."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

        from pokete.classes.pokete_care.breeding import BreedingManager
        self.manager = BreedingManager()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_no_shiny_parents_base_chance(self):
        """Test base shiny chance with no shiny parents (1/500)."""
        poke1 = MockPoke("steini", shiny=False)
        poke2 = MockPoke("mowcow", shiny=False)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, 500)

    def test_one_shiny_parent_halved_chance(self):
        """Test halved shiny chance with one shiny parent (1/250)."""
        poke1 = MockPoke("steini", shiny=True)
        poke2 = MockPoke("mowcow", shiny=False)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, 250)

        # Test reverse order
        poke3 = MockPoke("steini", shiny=False)
        poke4 = MockPoke("mowcow", shiny=True)

        chance2 = self.manager._compute_shiny_chance(poke3, poke4)
        self.assertEqual(chance2, 250)

    def test_both_shiny_parents_quarter_chance(self):
        """Test quarter shiny chance with both shiny parents (1/125)."""
        poke1 = MockPoke("steini", shiny=True)
        poke2 = MockPoke("mowcow", shiny=True)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, 125)


class TestInheritedStats(unittest.TestCase):
    """Test cases for inherited stats computation."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

        from pokete.classes.pokete_care.breeding import BreedingManager
        self.manager = BreedingManager()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_offspring_has_inherited_stats(self):
        """Test that offspring stats dict includes inherited_stats."""
        poke1 = MockPoke("steini", types=["normal"], atc=10, defense=8, initiative=6)
        poke2 = MockPoke("mowcow", types=["normal"], atc=4, defense=2, initiative=4)

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        self.assertIn("inherited_stats", stats)
        self.assertIn("atc", stats["inherited_stats"])
        self.assertIn("defense", stats["inherited_stats"])
        self.assertIn("initiative", stats["inherited_stats"])

    def test_inherited_stats_are_weighted_average(self):
        """Test that inherited stats are between parent values."""
        poke1 = MockPoke("steini", types=["normal"], atc=10, defense=10, initiative=10)
        poke2 = MockPoke("mowcow", types=["normal"], atc=0, defense=0, initiative=0)

        # Run multiple times to account for random weight
        for _ in range(10):
            stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")
            inherited = stats["inherited_stats"]

            # Values should be between 0 and 10 (weighted average)
            self.assertGreaterEqual(inherited["atc"], 0)
            self.assertLessEqual(inherited["atc"], 10)
            self.assertGreaterEqual(inherited["defense"], 0)
            self.assertLessEqual(inherited["defense"], 10)
            self.assertGreaterEqual(inherited["initiative"], 0)
            self.assertLessEqual(inherited["initiative"], 10)

    def test_offspring_starts_at_level_1(self):
        """Test that offspring starts at level 1 (xp=0)."""
        poke1 = MockPoke("steini", xp=1000, types=["normal"])
        poke2 = MockPoke("mowcow", xp=2000, types=["normal"])

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        self.assertEqual(stats["xp"], 0)

    def test_offspring_has_required_fields(self):
        """Test that offspring stats have all required fields."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        required_fields = ["name", "xp", "hp", "attacks", "shiny", "stats", "inherited_stats"]
        for field in required_fields:
            self.assertIn(field, stats)

    def test_offspring_stats_has_breeding_origin(self):
        """Test that offspring stats indicate breeding as origin."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        self.assertEqual(stats["stats"]["caught_with"], "breeding")


class TestBreedingHistory(unittest.TestCase):
    """Test cases for breeding history."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

        from pokete.classes.pokete_care.breeding import BreedingManager
        self.manager = BreedingManager()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_history_empty_initially(self):
        """Test that history starts empty."""
        self.assertEqual(len(self.manager.history), 0)

    def test_history_added_after_collection(self):
        """Test that collecting egg adds to history."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ):
            self.manager.collect_egg(current_time=1000 + hatch_time)

        self.assertEqual(len(self.manager.history), 1)
        entry = self.manager.history[0]
        self.assertEqual(entry.parent1_name, "steini")
        self.assertEqual(entry.parent2_name, "mowcow")

    def test_history_max_entries(self):
        """Test that history keeps only last 5 entries."""
        from pokete.classes.pokete_care.breeding import MAX_BREEDING_HISTORY

        for i in range(MAX_BREEDING_HISTORY + 3):
            poke1 = MockPoke(f"poke_{i}_1", types=["normal"])
            poke2 = MockPoke(f"poke_{i}_2", types=["normal"])

            self.manager.start_breeding(poke1, poke2, current_time=1000 + i * 1000)
            hatch_time = self.manager.breeding_pair.hatch_time

            with patch(
                "pokete.classes.pokete_care.breeding.Poke.from_dict",
                side_effect=lambda d: MockPoke(d["name"])
            ):
                self.manager.collect_egg(current_time=1000 + i * 1000 + hatch_time)

        self.assertEqual(len(self.manager.history), MAX_BREEDING_HISTORY)

    def test_history_most_recent_first(self):
        """Test that history returns most recent first."""
        for i in range(3):
            poke1 = MockPoke(f"poke_{i}_1", types=["normal"])
            poke2 = MockPoke(f"poke_{i}_2", types=["normal"])

            self.manager.start_breeding(poke1, poke2, current_time=1000 + i * 1000)
            hatch_time = self.manager.breeding_pair.hatch_time

            with patch(
                "pokete.classes.pokete_care.breeding.Poke.from_dict",
                side_effect=lambda d: MockPoke(d["name"])
            ):
                self.manager.collect_egg(current_time=1000 + i * 1000 + hatch_time)

        # Most recent should be first
        self.assertEqual(self.manager.history[0].parent1_name, "poke_2_1")
        self.assertEqual(self.manager.history[2].parent1_name, "poke_0_1")

    def test_history_serialization(self):
        """Test that history is serialized and restored."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ):
            self.manager.collect_egg(current_time=1000 + hatch_time)

        # Serialize
        saved = self.manager.dict()
        self.assertIn("history", saved)
        self.assertEqual(len(saved["history"]), 1)

        # Restore
        from pokete.classes.pokete_care.breeding import BreedingManager
        new_manager = BreedingManager()
        new_manager.from_dict(saved)

        self.assertEqual(len(new_manager.history), 1)
        self.assertEqual(new_manager.history[0].parent1_name, "steini")

    def test_history_records_shiny(self):
        """Test that history records shiny offspring."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        # Force shiny by patching random
        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ), patch(
            "pokete.classes.pokete_care.breeding.random.randint",
            return_value=0  # Makes shiny check pass
        ):
            self.manager.collect_egg(current_time=1000 + hatch_time)

        self.assertTrue(self.manager.history[0].was_shiny)


class TestBreedingPairData(unittest.TestCase):
    """Test cases for BreedingPairData."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_to_dict_and_from_dict(self):
        """Test BreedingPairData serialization."""
        from pokete.classes.pokete_care.breeding import BreedingPairData

        original = BreedingPairData(
            parent1_dict={"name": "steini", "xp": 100},
            parent2_dict={"name": "mowcow", "xp": 100},
            start_time=1000,
            hatch_time=300,
            offspring_identifier="steini",
            notified=False,
        )

        data = original.to_dict()
        restored = BreedingPairData.from_dict(data)

        self.assertEqual(restored.parent1_dict, original.parent1_dict)
        self.assertEqual(restored.parent2_dict, original.parent2_dict)
        self.assertEqual(restored.start_time, original.start_time)
        self.assertEqual(restored.hatch_time, original.hatch_time)
        self.assertEqual(restored.offspring_identifier, original.offspring_identifier)
        self.assertEqual(restored.notified, original.notified)


class TestBreedingHistoryEntry(unittest.TestCase):
    """Test cases for BreedingHistoryEntry."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_to_dict_and_from_dict(self):
        """Test BreedingHistoryEntry serialization."""
        from pokete.classes.pokete_care.breeding import BreedingHistoryEntry

        original = BreedingHistoryEntry(
            parent1_name="Steini",
            parent2_name="Mowcow",
            offspring_name="Steini",
            offspring_identifier="steini",
            completed_time="2024-01-01T12:00:00",
            was_shiny=True,
        )

        data = original.to_dict()
        restored = BreedingHistoryEntry.from_dict(data)

        self.assertEqual(restored.parent1_name, original.parent1_name)
        self.assertEqual(restored.parent2_name, original.parent2_name)
        self.assertEqual(restored.offspring_name, original.offspring_name)
        self.assertEqual(restored.offspring_identifier, original.offspring_identifier)
        self.assertEqual(restored.completed_time, original.completed_time)
        self.assertEqual(restored.was_shiny, original.was_shiny)


class TestFindBaseForm(unittest.TestCase):
    """Test cases for base form finding."""

    def setUp(self):
        """Set up test fixtures."""
        self.asset_patcher = patch(
            "pokete.classes.pokete_care.breeding.asset_service",
            MockAssetService()
        )
        self.asset_patcher.start()

        from pokete.classes.pokete_care.breeding import BreedingManager
        self.manager = BreedingManager()

    def tearDown(self):
        self.asset_patcher.stop()

    def test_find_base_form_single_evolution(self):
        """Test finding base form for single evolution chain."""
        base = self.manager._find_base_form("voglo")
        self.assertEqual(base, "vogli")

    def test_find_base_form_no_evolution(self):
        """Test finding base form for non-evolved pokete."""
        base = self.manager._find_base_form("steini")
        self.assertIsNone(base)

    def test_find_base_form_multi_stage(self):
        """Test finding base form for multi-stage evolution."""
        base = self.manager._find_base_form("voglus")
        self.assertEqual(base, "vogli")


class TestApplyInheritedStats(unittest.TestCase):
    """Test cases for apply_inherited_stats function."""

    def test_apply_inherited_stats_positive_bonus(self):
        """Test applying positive stat bonuses."""
        from pokete.classes.pokete_care.npc_action import apply_inherited_stats

        poke = MockPoke("steini", atc=5, defense=5, initiative=5)
        poke.inf.atc = 5
        poke.inf.defense = 5
        poke.inf.initiative = 5

        inherited = {"atc": 8, "defense": 7, "initiative": 6}
        apply_inherited_stats(poke, inherited)

        self.assertEqual(poke.atc, 8)  # 5 + (8-5) = 8
        self.assertEqual(poke.defense, 7)  # 5 + (7-5) = 7
        self.assertEqual(poke.initiative, 6)  # 5 + (6-5) = 6

    def test_apply_inherited_stats_negative_bonus(self):
        """Test applying negative stat bonuses (doesn't go below 0)."""
        from pokete.classes.pokete_care.npc_action import apply_inherited_stats

        poke = MockPoke("steini", atc=5, defense=5, initiative=5)
        poke.inf.atc = 10
        poke.inf.defense = 10
        poke.inf.initiative = 10

        inherited = {"atc": 2, "defense": 3, "initiative": 1}
        apply_inherited_stats(poke, inherited)

        # Bonuses are negative: atc = 5 + (2-10) = -3 -> 0
        self.assertEqual(poke.atc, 0)
        self.assertEqual(poke.defense, 0)
        self.assertEqual(poke.initiative, 0)

    def test_apply_inherited_stats_empty_dict(self):
        """Test that empty inherited_stats doesn't change poke."""
        from pokete.classes.pokete_care.npc_action import apply_inherited_stats

        poke = MockPoke("steini", atc=5, defense=5, initiative=5)
        original_atc = poke.atc

        apply_inherited_stats(poke, {})

        self.assertEqual(poke.atc, original_atc)


if __name__ == "__main__":
    unittest.main()
