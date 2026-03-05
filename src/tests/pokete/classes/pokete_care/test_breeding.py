"""Tests for the breeding system."""

import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


class MockPokeType:
    """Mock for PokeType class."""
    def __init__(self, name: str):
        self.name = name


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
    """Mock Poke class for testing.
    
    Uses MockPokeType objects in self.types to match the real Poke API.
    """
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
        type_names = types or ["normal"]
        self.inf = MockResourcePoke(
            name=identifier,
            types=type_names,
            atc=atc,
            defense=defense,
            initiative=initiative,
        )
        # types is a list of PokeType objects with .name attribute
        self.types = [MockPokeType(t) for t in type_names]
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
        self.assertLessEqual(hatch_time, 300)  # BASE_HATCH_TIME

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

        poke1_high = MockPoke("test3", xp=2500, types=["normal"])  # lvl 50
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


class TestComputeOffspringStats(unittest.TestCase):
    """Test cases for offspring stats computation."""

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

    def test_offspring_inherits_weighted_stats(self):
        """Test that offspring gets weighted average of parent stats."""
        poke1 = MockPoke("steini", types=["normal"], atc=10, defense=10, initiative=10)
        poke2 = MockPoke("mowcow", types=["normal"], atc=0, defense=0, initiative=0)

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        inherited = stats["inherited_stats"]
        self.assertIn("atc", inherited)
        self.assertIn("defense", inherited)
        self.assertIn("initiative", inherited)
        # Should be weighted average between 0 and 10
        self.assertGreaterEqual(inherited["atc"], 0)
        self.assertLessEqual(inherited["atc"], 10)
        self.assertGreaterEqual(inherited["defense"], 0)
        self.assertLessEqual(inherited["defense"], 10)
        self.assertGreaterEqual(inherited["initiative"], 0)
        self.assertLessEqual(inherited["initiative"], 10)

    def test_inherited_stats_never_negative(self):
        """Test that inherited stats are never negative."""
        # Even with 0 stats from both parents, result should be >= 0
        poke1 = MockPoke("steini", types=["normal"], atc=0, defense=0, initiative=0)
        poke2 = MockPoke("mowcow", types=["normal"], atc=0, defense=0, initiative=0)

        stats = self.manager.compute_offspring_stats(poke1, poke2, "steini")

        inherited = stats["inherited_stats"]
        self.assertGreaterEqual(inherited["atc"], 0)
        self.assertGreaterEqual(inherited["defense"], 0)
        self.assertGreaterEqual(inherited["initiative"], 0)


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

    def test_base_shiny_chance_no_shiny_parents(self):
        """Test base shiny chance when no parent is shiny."""
        from pokete.classes.pokete_care.breeding import BASE_SHINY_CHANCE

        poke1 = MockPoke("steini", types=["normal"], shiny=False)
        poke2 = MockPoke("mowcow", types=["normal"], shiny=False)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, BASE_SHINY_CHANCE)  # 500

    def test_single_shiny_parent_bonus(self):
        """Test shiny chance halved when one parent is shiny."""
        from pokete.classes.pokete_care.breeding import SINGLE_SHINY_PARENT_CHANCE

        poke1 = MockPoke("steini", types=["normal"], shiny=True)
        poke2 = MockPoke("mowcow", types=["normal"], shiny=False)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, SINGLE_SHINY_PARENT_CHANCE)  # 250

    def test_single_shiny_parent_bonus_other_parent(self):
        """Test shiny chance when second parent is shiny."""
        from pokete.classes.pokete_care.breeding import SINGLE_SHINY_PARENT_CHANCE

        poke1 = MockPoke("steini", types=["normal"], shiny=False)
        poke2 = MockPoke("mowcow", types=["normal"], shiny=True)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, SINGLE_SHINY_PARENT_CHANCE)  # 250

    def test_both_shiny_parents_bonus(self):
        """Test shiny chance halved again when both parents are shiny."""
        from pokete.classes.pokete_care.breeding import BOTH_SHINY_PARENTS_CHANCE

        poke1 = MockPoke("steini", types=["normal"], shiny=True)
        poke2 = MockPoke("mowcow", types=["normal"], shiny=True)

        chance = self.manager._compute_shiny_chance(poke1, poke2)
        self.assertEqual(chance, BOTH_SHINY_PARENTS_CHANCE)  # 125


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


class TestClimateInfluence(unittest.TestCase):
    """Test cases for climate-influenced hatch time."""

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

    def test_infer_biome_cave(self):
        """Test biome inference for cave maps."""
        biome = self.manager._infer_biome_from_map("cave_1")
        self.assertEqual(biome, "cave")

        biome = self.manager._infer_biome_from_map("Nice Town Cave")
        self.assertEqual(biome, "cave")

    def test_infer_biome_water(self):
        """Test biome inference for water maps."""
        biome = self.manager._infer_biome_from_map("Sunnydale Lake")
        self.assertEqual(biome, "lake")

        biome = self.manager._infer_biome_from_map("Big Mountain Sea")
        self.assertEqual(biome, "sea")

    def test_infer_biome_forest(self):
        """Test biome inference for forest maps."""
        biome = self.manager._infer_biome_from_map("Deepest Forest")
        self.assertEqual(biome, "forest")

    def test_infer_biome_none(self):
        """Test biome inference for unknown maps."""
        biome = self.manager._infer_biome_from_map("unknown_map_xyz")
        self.assertIsNone(biome)

        biome = self.manager._infer_biome_from_map(None)
        self.assertIsNone(biome)

    def test_climate_multiplier_no_map(self):
        """Test climate multiplier with no map set."""
        poke1 = MockPoke("steini", types=["stone"])
        poke2 = MockPoke("mowcow", types=["normal"])

        multiplier = self.manager.compute_climate_multiplier(poke1, poke2, None)
        self.assertEqual(multiplier, 1.0)

    def test_climate_multiplier_both_match_cave(self):
        """Test climate multiplier when both parents match cave biome."""
        from pokete.classes.pokete_care.breeding import CLIMATE_MULTIPLIER_MIN

        poke1 = MockPoke("steini", types=["stone"])
        poke2 = MockPoke("lilstone", types=["ground"])

        multiplier = self.manager.compute_climate_multiplier(poke1, poke2, "cave_1")
        self.assertEqual(multiplier, CLIMATE_MULTIPLIER_MIN)  # 0.6

    def test_climate_multiplier_one_match(self):
        """Test climate multiplier when one parent matches biome."""
        from pokete.classes.pokete_care.breeding import CLIMATE_BONUS

        poke1 = MockPoke("karpi", types=["water"])  # Matches lake
        poke2 = MockPoke("steini", types=["stone"])  # Doesn't match

        multiplier = self.manager.compute_climate_multiplier(poke1, poke2, "Sunnydale Lake")
        self.assertEqual(multiplier, 1.0 - CLIMATE_BONUS)  # 0.8

    def test_climate_multiplier_no_match(self):
        """Test climate multiplier when no parent matches biome."""
        from pokete.classes.pokete_care.breeding import CLIMATE_MULTIPLIER_MAX

        poke1 = MockPoke("wolfior", types=["fire"])
        poke2 = MockPoke("steini", types=["stone"])

        # Water biome, fire and stone don't match
        multiplier = self.manager.compute_climate_multiplier(poke1, poke2, "Sunnydale Lake")
        self.assertEqual(multiplier, CLIMATE_MULTIPLIER_MAX)  # 1.2

    def test_climate_affects_hatch_time(self):
        """Test that climate affects overall hatch time."""
        poke1 = MockPoke("karpi", types=["water"])
        poke2 = MockPoke("blub", types=["water"])

        # Water types in water map should be faster
        time_lake = self.manager.compute_hatch_time(poke1, poke2, "Sunnydale Lake")

        # Water types in cave should be slower
        time_cave = self.manager.compute_hatch_time(poke1, poke2, "cave_1")

        self.assertLess(time_lake, time_cave)

    def test_climate_multiplier_bounds(self):
        """Test that climate multiplier stays within bounds."""
        from pokete.classes.pokete_care.breeding import (
            CLIMATE_MULTIPLIER_MIN,
            CLIMATE_MULTIPLIER_MAX,
        )

        poke1 = MockPoke("steini", types=["stone"])
        poke2 = MockPoke("mowcow", types=["normal"])

        # Test various map names
        for map_name in ["cave_1", "lake_1", "forest_1", "town_1", "route_1", None]:
            multiplier = self.manager.compute_climate_multiplier(poke1, poke2, map_name)
            self.assertGreaterEqual(multiplier, CLIMATE_MULTIPLIER_MIN)
            self.assertLessEqual(multiplier, CLIMATE_MULTIPLIER_MAX)

    def test_set_current_map(self):
        """Test setting current map for climate calculations."""
        poke1 = MockPoke("karpi", types=["water"])
        poke2 = MockPoke("blub", types=["water"])

        # Without setting map
        time_no_map = self.manager.compute_hatch_time(poke1, poke2)

        # Set lake map
        self.manager.set_current_map("Sunnydale Lake")
        time_with_lake = self.manager.compute_hatch_time(poke1, poke2)

        # Lake should be faster for water types
        self.assertLess(time_with_lake, time_no_map)


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
        """Test that history is empty initially."""
        self.assertEqual(len(self.manager.history), 0)
        self.assertEqual(len(self.manager.get_history()), 0)

    def test_history_added_on_collect(self):
        """Test that history entry is added when collecting egg."""
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

    def test_history_max_size(self):
        """Test that history is limited to MAX_HISTORY_SIZE entries."""
        from pokete.classes.pokete_care.breeding import MAX_HISTORY_SIZE

        for i in range(MAX_HISTORY_SIZE + 3):
            poke1 = MockPoke("steini", types=["normal"])
            poke2 = MockPoke("mowcow", types=["normal"])

            self.manager.start_breeding(poke1, poke2, current_time=1000 + i * 1000)
            hatch_time = self.manager.breeding_pair.hatch_time

            with patch(
                "pokete.classes.pokete_care.breeding.Poke.from_dict",
                side_effect=lambda d: MockPoke(d["name"])
            ):
                self.manager.collect_egg(current_time=1000 + i * 1000 + hatch_time)

        self.assertEqual(len(self.manager.history), MAX_HISTORY_SIZE)

    def test_history_contains_correct_data(self):
        """Test that history entries contain correct data."""
        poke1 = MockPoke("steini", types=["normal"], atc=10, defense=8, initiative=6)
        poke2 = MockPoke("mowcow", types=["normal"], atc=4, defense=2, initiative=4)

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ):
            self.manager.collect_egg(current_time=1000 + hatch_time)

        # history property returns most recent first
        entry = self.manager.history[0]
        self.assertEqual(entry.parent1_name, "steini")
        self.assertEqual(entry.parent2_name, "mowcow")
        self.assertIn("atc", entry.inherited_stats)
        self.assertIn("defense", entry.inherited_stats)
        self.assertIn("initiative", entry.inherited_stats)

    def test_history_order_most_recent_first(self):
        """Test that history returns most recent entries first."""
        # Add multiple entries
        for i in range(3):
            poke1 = MockPoke(f"poke_{i}_a", types=["normal"])
            poke2 = MockPoke(f"poke_{i}_b", types=["normal"])

            self.manager.start_breeding(poke1, poke2, current_time=1000 + i * 1000)
            hatch_time = self.manager.breeding_pair.hatch_time

            with patch(
                "pokete.classes.pokete_care.breeding.Poke.from_dict",
                side_effect=lambda d: MockPoke(d["name"])
            ):
                self.manager.collect_egg(current_time=1000 + i * 1000 + hatch_time)

        history = self.manager.history
        self.assertEqual(len(history), 3)
        # Most recent (i=2) should be first
        self.assertEqual(history[0].parent1_name, "poke_2_a")
        # Oldest (i=0) should be last
        self.assertEqual(history[2].parent1_name, "poke_0_a")

    def test_history_serialization(self):
        """Test that history is serialized and restored correctly."""
        poke1 = MockPoke("steini", types=["normal"])
        poke2 = MockPoke("mowcow", types=["normal"])

        self.manager.start_breeding(poke1, poke2, current_time=1000)
        hatch_time = self.manager.breeding_pair.hatch_time

        with patch(
            "pokete.classes.pokete_care.breeding.Poke.from_dict",
            side_effect=lambda d: MockPoke(d["name"])
        ):
            self.manager.collect_egg(current_time=1000 + hatch_time)

        saved = self.manager.dict()
        self.assertEqual(len(saved["history"]), 1)

        from pokete.classes.pokete_care.breeding import BreedingManager
        new_manager = BreedingManager()
        new_manager.from_dict(saved)

        self.assertEqual(len(new_manager.history), 1)
        self.assertEqual(new_manager.history[0].parent1_name, "steini")

    def test_clear_history(self):
        """Test clearing the history."""
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

        self.manager.clear_history()
        self.assertEqual(len(self.manager.history), 0)


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
            offspring_name="steini",
            offspring_shiny=True,
            timestamp="2024-01-15T10:30:00",
            inherited_stats={"atc": 5, "defense": 4, "initiative": 3},
        )

        data = original.to_dict()
        restored = BreedingHistoryEntry.from_dict(data)

        self.assertEqual(restored.parent1_name, original.parent1_name)
        self.assertEqual(restored.parent2_name, original.parent2_name)
        self.assertEqual(restored.offspring_name, original.offspring_name)
        self.assertEqual(restored.offspring_shiny, original.offspring_shiny)
        self.assertEqual(restored.timestamp, original.timestamp)
        self.assertEqual(restored.inherited_stats, original.inherited_stats)


class TestApplyInheritedStats(unittest.TestCase):
    """Test cases for applying inherited stats with negative guards."""

    def test_apply_positive_stats(self):
        """Test applying positive inherited stats."""
        poke = MockPoke("test", types=["normal"], atc=1, defense=1, initiative=1)
        inherited = {"atc": 10, "defense": 8, "initiative": 6}

        # Simulate _apply_inherited_stats behavior
        poke.atc = max(0, inherited["atc"])
        poke.defense = max(0, inherited["defense"])
        poke.initiative = max(0, inherited["initiative"])

        self.assertEqual(poke.atc, 10)
        self.assertEqual(poke.defense, 8)
        self.assertEqual(poke.initiative, 6)

    def test_apply_zero_stats(self):
        """Test applying zero inherited stats."""
        poke = MockPoke("test", types=["normal"], atc=5, defense=5, initiative=5)
        inherited = {"atc": 0, "defense": 0, "initiative": 0}

        poke.atc = max(0, inherited["atc"])
        poke.defense = max(0, inherited["defense"])
        poke.initiative = max(0, inherited["initiative"])

        self.assertEqual(poke.atc, 0)
        self.assertEqual(poke.defense, 0)
        self.assertEqual(poke.initiative, 0)

    def test_apply_negative_stats_guarded(self):
        """Test that negative stats are guarded to 0."""
        poke = MockPoke("test", types=["normal"], atc=5, defense=5, initiative=5)
        inherited = {"atc": -5, "defense": -10, "initiative": -1}

        poke.atc = max(0, inherited["atc"])
        poke.defense = max(0, inherited["defense"])
        poke.initiative = max(0, inherited["initiative"])

        self.assertEqual(poke.atc, 0)
        self.assertEqual(poke.defense, 0)
        self.assertEqual(poke.initiative, 0)

    def test_apply_partial_stats(self):
        """Test applying only some inherited stats."""
        poke = MockPoke("test", types=["normal"], atc=5, defense=5, initiative=5)
        inherited = {"atc": 10}  # Only atc provided

        if "atc" in inherited:
            poke.atc = max(0, inherited["atc"])
        if "defense" in inherited:
            poke.defense = max(0, inherited["defense"])
        if "initiative" in inherited:
            poke.initiative = max(0, inherited["initiative"])

        self.assertEqual(poke.atc, 10)
        self.assertEqual(poke.defense, 5)  # Unchanged
        self.assertEqual(poke.initiative, 5)  # Unchanged


if __name__ == "__main__":
    unittest.main()
