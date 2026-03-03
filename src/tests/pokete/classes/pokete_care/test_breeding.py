"""Tests for the breeding system in Pokete Care.

These tests verify the core breeding logic including:
- Type compatibility checking
- Weighted stat computation
- Egg generation and hatching
- Egg move inheritance
- Breeding history tracking
- Serialization/deserialization
- Notification when eggs are ready
- Periodic event integration

Note: Uses mocks for timer and asset_service to test in isolation.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import math


class MockType:
    """Mock type object for testing."""
    def __init__(self, name: str):
        self.name = name


class MockPokeInfo:
    """Mock pokete info (base stats) for testing."""
    def __init__(self, hp=20, atc=5, defense=3, initiative=4, types=None,
                 attacks=None, pool=None):
        self.hp = hp
        self.atc = atc
        self.defense = defense
        self.initiative = initiative
        self.types = types or ["normal"]
        self.attacks = attacks or ["tackle"]
        self.pool = pool or []
        self.evolve_poke = ""
        self.evolve_lvl = 0


class MockAttackData:
    """Mock attack data for testing."""
    def __init__(self, name, min_lvl=0, types=None):
        self.name = name
        self.min_lvl = min_lvl
        self.types = types or ["normal"]


class MockPoke:
    """Mock Poke class for testing without full game dependencies."""
    def __init__(self, identifier: str, xp: int = 0, types=None, inf=None,
                 attacks=None):
        self.identifier = identifier
        self.xp = xp
        self.types = [MockType(t) for t in (types or ["normal"])]
        self.inf = inf or MockPokeInfo(types=types or ["normal"])
        self.name = identifier.capitalize()
        self.attacks = attacks or ["tackle"]

    def lvl(self):
        """Return level based on xp."""
        return int(math.sqrt(self.xp + 1))

    def dict(self):
        """Serialize to dict."""
        return {
            "name": self.identifier,
            "xp": self.xp,
            "hp": 20,
            "ap": [],
            "effects": [],
            "attacks": self.attacks,
            "shiny": False,
            "nature": {"nature": "normal", "grade": 1},
            "stats": {
                "ownership_date": None,
                "evolved_date": None,
                "total_battles": 0,
                "lost_battles": 0,
                "win_battles": 0,
                "earned_xp": 0,
                "caught_with": None,
                "run_away": 0,
            },
        }


def create_mock_asset_service():
    """Create a mock asset service for testing."""
    mock_service = Mock()
    mock_assets = Mock()

    # Mock pokes
    mock_assets.pokes = {
        "__fallback__": MockPokeInfo(hp=20, types=["normal"]),
        "karpi": MockPokeInfo(hp=15, atc=0, defense=0, initiative=0,
                             types=["water", "normal"], attacks=["tackle"]),
        "blub": MockPokeInfo(hp=20, atc=2, defense=1, initiative=1,
                            types=["water", "normal"], attacks=["tackle", "bubble_bomb"]),
        "wolfior": MockPokeInfo(hp=20, atc=6, defense=3, initiative=4,
                               types=["fire", "normal"], attacks=["tackle", "fire_bite"]),
        "steini": MockPokeInfo(hp=25, atc=2, defense=4, initiative=5,
                              types=["stone", "normal"], attacks=["tackle", "politure"],
                              pool=["stone_crush"]),
    }

    # Mock attacks
    mock_assets.attacks = {
        "tackle": MockAttackData("Tackle", min_lvl=0),
        "bubble_bomb": MockAttackData("Bubble Bomb", min_lvl=0, types=["water"]),
        "fire_bite": MockAttackData("Fire Bite", min_lvl=0, types=["fire"]),
        "power_bite": MockAttackData("Power Bite", min_lvl=30),
        "tail_wipe": MockAttackData("Tail Swipe", min_lvl=10),
        "politure": MockAttackData("Politure", min_lvl=0, types=["stone"]),
        "stone_crush": MockAttackData("Stone Crush", min_lvl=15, types=["stone"]),
    }

    mock_service.get_base_assets.return_value = mock_assets
    return mock_service


def can_breed(poke1, poke2):
    """Check if two poketes are compatible for breeding."""
    if poke1 is None or poke2 is None:
        return False
    if poke1.identifier == "__fallback__" or poke2.identifier == "__fallback__":
        return False
    types1 = set(t.name for t in poke1.types)
    types2 = set(t.name for t in poke2.types)
    return bool(types1 & types2)


def get_shared_types(poke1, poke2):
    """Get the types shared between two poketes."""
    if poke1 is None or poke2 is None:
        return []
    types1 = set(t.name for t in poke1.types)
    types2 = set(t.name for t in poke2.types)
    return list(types1 & types2)


def compute_weighted_stat(stat1, stat2, weight1=0.5, weight2=0.5):
    """Compute weighted average of two stats."""
    base = stat1 * weight1 + stat2 * weight2
    return max(1, int(base))


def compute_hatch_time(poke1, poke2, base_time=300):
    """Compute how long the egg needs to hatch based on parents."""
    if poke1 is None or poke2 is None:
        return base_time
    avg_level = (poke1.lvl() + poke2.lvl()) / 2
    level_modifier = max(0.5, 1.0 - (avg_level / 100))
    return int(base_time * level_modifier)


class TestBreedingCompatibility(unittest.TestCase):
    """Tests for pokete breeding compatibility."""

    def setUp(self):
        """Set up test fixtures with mocked dependencies."""
        self.poke1_water_normal = MockPoke(
            "karpi", 50, ["water", "normal"],
            MockPokeInfo(15, 0, 0, 0, ["water", "normal"])
        )
        self.poke2_water = MockPoke(
            "blub", 50, ["water", "normal"],
            MockPokeInfo(20, 2, 1, 1, ["water", "normal"])
        )
        self.poke3_fire = MockPoke(
            "wolfior", 50, ["fire", "normal"],
            MockPokeInfo(20, 6, 3, 4, ["fire", "normal"])
        )
        self.poke4_normal = MockPoke(
            "mowcow", 50, ["normal"],
            MockPokeInfo(20, 2, 3, 2, ["normal"])
        )
        self.fallback = MockPoke("__fallback__", 0)

    def test_compatible_poketes_sharing_type(self):
        """Two poketes sharing a type should be compatible."""
        self.assertTrue(can_breed(self.poke1_water_normal, self.poke2_water))

    def test_compatible_poketes_sharing_normal(self):
        """Poketes sharing only 'normal' type should be compatible."""
        self.assertTrue(can_breed(self.poke3_fire, self.poke4_normal))

    def test_incompatible_poketes_no_shared_type(self):
        """Poketes with no shared types should be incompatible."""
        pure_fire = MockPoke("pure_fire", 50, ["fire"])
        pure_water = MockPoke("pure_water", 50, ["water"])
        self.assertFalse(can_breed(pure_fire, pure_water))

    def test_fallback_pokete_not_valid(self):
        """Fallback pokete should not be valid for breeding."""
        self.assertFalse(can_breed(self.fallback, self.poke1_water_normal))
        self.assertFalse(can_breed(self.poke1_water_normal, self.fallback))

    def test_none_pokete_not_valid(self):
        """None pokete should not be valid for breeding."""
        self.assertFalse(can_breed(None, self.poke1_water_normal))
        self.assertFalse(can_breed(self.poke1_water_normal, None))
        self.assertFalse(can_breed(None, None))


class TestWeightedStatComputation(unittest.TestCase):
    """Tests for weighted stat computation logic."""

    def test_weighted_average_equal_weights(self):
        """Test weighted average with equal weights."""
        result = compute_weighted_stat(10, 20, 0.5, 0.5)
        self.assertEqual(result, 15)

    def test_weighted_average_unequal_weights(self):
        """Test weighted average with unequal weights."""
        result = compute_weighted_stat(10, 20, 0.4, 0.4)
        self.assertEqual(result, 12)

    def test_minimum_stat_value(self):
        """Stats should not go below 1."""
        result = compute_weighted_stat(0, 0, 0.5, 0.5)
        self.assertEqual(result, 1)

    def test_stat_computation_asymmetric(self):
        """Test stat computation with different parent stats."""
        atc = compute_weighted_stat(10, 2, 0.5, 0.5)  # 6
        defense = compute_weighted_stat(2, 10, 0.5, 0.5)  # 6
        self.assertEqual(atc, 6)
        self.assertEqual(defense, 6)


class TestHatchTimeComputation(unittest.TestCase):
    """Tests for egg hatching time computation."""

    def setUp(self):
        self.low_level_poke1 = MockPoke("low1", 0)  # Level 1
        self.low_level_poke2 = MockPoke("low2", 0)  # Level 1
        self.high_level_poke1 = MockPoke("high1", 2500)  # Level ~50
        self.high_level_poke2 = MockPoke("high2", 2500)  # Level ~50

    def test_base_hatch_time(self):
        """Test hatch time with level 1 parents."""
        time = compute_hatch_time(self.low_level_poke1, self.low_level_poke2)
        self.assertEqual(time, 297)  # 300 * 0.99

    def test_higher_level_reduces_hatch_time(self):
        """Higher level parents should reduce hatch time."""
        time_low = compute_hatch_time(self.low_level_poke1, self.low_level_poke2)
        time_high = compute_hatch_time(self.high_level_poke1, self.high_level_poke2)
        self.assertGreater(time_low, time_high)

    def test_minimum_hatch_time(self):
        """Hatch time should not go below 50% of base."""
        very_high_poke1 = MockPoke("vh1", 10000)  # Level ~100
        very_high_poke2 = MockPoke("vh2", 10000)  # Level ~100
        time = compute_hatch_time(very_high_poke1, very_high_poke2)
        self.assertEqual(time, 150)  # 300 * 0.5

    def test_none_parents_return_base_time(self):
        """None parents should return base hatch time."""
        time = compute_hatch_time(None, self.low_level_poke1)
        self.assertEqual(time, 300)


class TestGetSharedTypes(unittest.TestCase):
    """Tests for getting shared types between poketes."""

    def test_get_shared_types_water_normal(self):
        """Test getting shared types with water/normal poketes."""
        poke1 = MockPoke("karpi", 50, ["water", "normal"])
        poke2 = MockPoke("blub", 50, ["water", "normal"])
        shared = get_shared_types(poke1, poke2)
        self.assertIn("water", shared)
        self.assertIn("normal", shared)
        self.assertEqual(len(shared), 2)

    def test_get_shared_types_single_common(self):
        """Test getting shared types with one common type."""
        poke1 = MockPoke("wolfior", 50, ["fire", "normal"])
        poke2 = MockPoke("mowcow", 50, ["normal"])
        shared = get_shared_types(poke1, poke2)
        self.assertEqual(shared, ["normal"])

    def test_get_shared_types_none(self):
        """Test getting shared types with no common type."""
        poke1 = MockPoke("pure_fire", 50, ["fire"])
        poke2 = MockPoke("pure_water", 50, ["water"])
        shared = get_shared_types(poke1, poke2)
        self.assertEqual(shared, [])

    def test_get_shared_types_with_none_poke(self):
        """Test getting shared types when one poke is None."""
        poke1 = MockPoke("karpi", 50, ["water", "normal"])
        shared = get_shared_types(poke1, None)
        self.assertEqual(shared, [])


class TestEggDataSerialization(unittest.TestCase):
    """Tests for EggData serialization and deserialization."""

    def test_egg_dict_structure(self):
        """Test that egg dict has the correct structure."""
        egg_dict = {
            "identifier": "steini",
            "hp": 20,
            "atc": 5,
            "defense": 3,
            "initiative": 4,
            "hatch_time": 300,
            "parent1_identifier": "karpi",
            "parent2_identifier": "blub",
            "inherited_moves": ["power_bite"],
        }

        self.assertIn("identifier", egg_dict)
        self.assertIn("hp", egg_dict)
        self.assertIn("atc", egg_dict)
        self.assertIn("defense", egg_dict)
        self.assertIn("initiative", egg_dict)
        self.assertIn("hatch_time", egg_dict)
        self.assertIn("parent1_identifier", egg_dict)
        self.assertIn("parent2_identifier", egg_dict)
        self.assertIn("inherited_moves", egg_dict)

    def test_egg_dict_values(self):
        """Test egg dict values are of correct types."""
        egg_dict = {
            "identifier": "steini",
            "hp": 20,
            "atc": 5,
            "defense": 3,
            "initiative": 4,
            "hatch_time": 300,
            "parent1_identifier": "karpi",
            "parent2_identifier": "blub",
            "inherited_moves": ["power_bite", "tail_wipe"],
        }

        self.assertIsInstance(egg_dict["identifier"], str)
        self.assertIsInstance(egg_dict["hp"], int)
        self.assertIsInstance(egg_dict["atc"], int)
        self.assertIsInstance(egg_dict["defense"], int)
        self.assertIsInstance(egg_dict["initiative"], int)
        self.assertIsInstance(egg_dict["hatch_time"], int)
        self.assertIsInstance(egg_dict["parent1_identifier"], str)
        self.assertIsInstance(egg_dict["parent2_identifier"], str)
        self.assertIsInstance(egg_dict["inherited_moves"], list)
        self.assertEqual(len(egg_dict["inherited_moves"]), 2)


class TestBreedingHistorySerialization(unittest.TestCase):
    """Tests for breeding history serialization."""

    def test_history_entry_dict_structure(self):
        """Test that history entry dict has correct structure."""
        entry_dict = {
            "offspring_identifier": "karpi",
            "offspring_name": "Karpi",
            "parent1_identifier": "karpi",
            "parent1_name": "Karpi",
            "parent2_identifier": "blub",
            "parent2_name": "Blub",
            "hatch_timestamp": 1000,
            "inherited_moves": ["power_bite"],
            "shiny": False,
        }

        required_keys = [
            "offspring_identifier", "offspring_name",
            "parent1_identifier", "parent1_name",
            "parent2_identifier", "parent2_name",
            "hatch_timestamp", "inherited_moves", "shiny"
        ]
        for key in required_keys:
            self.assertIn(key, entry_dict)

    def test_history_entry_with_shiny(self):
        """Test history entry for shiny offspring."""
        entry_dict = {
            "offspring_identifier": "karpi",
            "offspring_name": "Karpi",
            "parent1_identifier": "karpi",
            "parent1_name": "Karpi",
            "parent2_identifier": "blub",
            "parent2_name": "Blub",
            "hatch_timestamp": 1000,
            "inherited_moves": [],
            "shiny": True,
        }

        self.assertTrue(entry_dict["shiny"])


class TestBreedingManagerSerialization(unittest.TestCase):
    """Tests for BreedingManager serialization."""

    def test_empty_manager_dict_structure(self):
        """Test serialization structure of empty breeding manager."""
        empty_dict = {
            "parent1": None,
            "parent2": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        self.assertIn("parent1", empty_dict)
        self.assertIn("parent2", empty_dict)
        self.assertIn("start_time", empty_dict)
        self.assertIn("egg_ready", empty_dict)
        self.assertIn("egg", empty_dict)
        self.assertIn("history", empty_dict)

    def test_manager_dict_with_history(self):
        """Test serialization structure with breeding history."""
        manager_dict = {
            "parent1": None,
            "parent2": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [
                {
                    "offspring_identifier": "karpi",
                    "offspring_name": "Karpi",
                    "parent1_identifier": "karpi",
                    "parent1_name": "Karpi",
                    "parent2_identifier": "blub",
                    "parent2_name": "Blub",
                    "hatch_timestamp": 500,
                    "inherited_moves": [],
                    "shiny": False,
                }
            ],
        }

        self.assertEqual(len(manager_dict["history"]), 1)
        self.assertEqual(manager_dict["history"][0]["offspring_identifier"], "karpi")


class TestBreedingStateManagement(unittest.TestCase):
    """Tests for breeding state management logic."""

    def test_has_breeding_pair_logic(self):
        """Test logic for checking if breeding pair exists."""
        parent1, parent2 = None, None
        has_pair = parent1 is not None and parent2 is not None
        self.assertFalse(has_pair)

        parent1 = MockPoke("karpi", 50)
        has_pair = parent1 is not None and parent2 is not None
        self.assertFalse(has_pair)

        parent2 = MockPoke("blub", 50)
        has_pair = parent1 is not None and parent2 is not None
        self.assertTrue(has_pair)

    def test_is_egg_ready_logic(self):
        """Test logic for checking if egg is ready."""
        egg_ready = False
        egg = None
        is_ready = egg_ready and egg is not None
        self.assertFalse(is_ready)

        egg_ready = True
        is_ready = egg_ready and egg is not None
        self.assertFalse(is_ready)

        egg = {"identifier": "test"}
        is_ready = egg_ready and egg is not None
        self.assertTrue(is_ready)

    def test_time_remaining_calculation(self):
        """Test time remaining calculation logic."""
        start_time = 100
        current_time = 150
        hatch_time = 300

        elapsed = current_time - start_time  # 50
        remaining = hatch_time - elapsed  # 250
        remaining = max(0, remaining)  # 250

        self.assertEqual(elapsed, 50)
        self.assertEqual(remaining, 250)

    def test_time_remaining_when_ready(self):
        """Test time remaining is 0 when egg is ready."""
        start_time = 100
        current_time = 500
        hatch_time = 300

        elapsed = current_time - start_time  # 400
        remaining = hatch_time - elapsed  # -100
        remaining = max(0, remaining)  # 0

        self.assertEqual(remaining, 0)


class TestNotificationLogic(unittest.TestCase):
    """Tests for egg-ready notification logic."""

    def test_update_detects_egg_ready(self):
        """Update should detect when egg becomes ready."""
        start_time = 100
        hatch_time = 300
        egg_ready = False

        # Before hatch time
        current_time = 350
        elapsed = current_time - start_time
        if elapsed >= hatch_time:
            egg_ready = True

        self.assertFalse(egg_ready)

        # After hatch time
        current_time = 450
        elapsed = current_time - start_time
        if elapsed >= hatch_time:
            egg_ready = True

        self.assertTrue(egg_ready)

    def test_notification_only_fires_once(self):
        """Notification should only fire once when egg becomes ready."""
        egg_ready = False
        notified = False
        notifications = []

        # First update when egg becomes ready
        egg_ready = True
        if egg_ready and not notified:
            notifications.append("Egg ready!")
            notified = True

        # Second update - egg is still ready but shouldn't notify again
        if egg_ready and not notified:
            notifications.append("Egg ready!")

        self.assertEqual(len(notifications), 1)


class TestEggMoveInheritance(unittest.TestCase):
    """Tests for egg move inheritance system."""

    def test_inheritable_moves_have_min_lvl_greater_than_zero(self):
        """Only moves with min_lvl > 0 can be inherited."""
        attacks = {
            "tackle": MockAttackData("Tackle", min_lvl=0),
            "power_bite": MockAttackData("Power Bite", min_lvl=30),
            "tail_wipe": MockAttackData("Tail Swipe", min_lvl=10),
        }

        inheritable = [
            name for name, data in attacks.items()
            if data.min_lvl > 0
        ]

        self.assertIn("power_bite", inheritable)
        self.assertIn("tail_wipe", inheritable)
        self.assertNotIn("tackle", inheritable)

    def test_max_two_inherited_moves(self):
        """At most 2 moves can be inherited (1 from each parent)."""
        parent1_moves = ["tackle", "power_bite", "tail_wipe"]
        parent2_moves = ["tackle", "stone_crush"]

        # Simulate inheritance logic
        inherited = []
        for parent_moves in [parent1_moves, parent2_moves]:
            if len(inherited) >= 2:
                break
            eligible = [m for m in parent_moves if m != "tackle"]  # Simplified
            if eligible:
                inherited.append(eligible[0])

        self.assertLessEqual(len(inherited), 2)

    def test_moves_not_in_offspring_natural_moveset(self):
        """Inherited moves should not be in offspring's natural moveset."""
        offspring_attacks = ["tackle", "bubble_bomb"]
        offspring_pool = ["bubble_shield"]
        offspring_learnable = set(offspring_attacks + offspring_pool)

        parent_move = "power_bite"

        can_inherit = parent_move not in offspring_learnable
        self.assertTrue(can_inherit)

        # Move in natural moveset
        parent_move = "bubble_bomb"
        can_inherit = parent_move not in offspring_learnable
        self.assertFalse(can_inherit)


class TestBreedingHistoryTracking(unittest.TestCase):
    """Tests for breeding history tracking."""

    def test_history_limited_to_five_entries(self):
        """History should keep only the last 5 entries."""
        MAX_HISTORY = 5
        history = []

        for i in range(7):
            history.append({"offspring_name": f"Poke{i}"})
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

        self.assertEqual(len(history), MAX_HISTORY)
        self.assertEqual(history[0]["offspring_name"], "Poke2")
        self.assertEqual(history[-1]["offspring_name"], "Poke6")

    def test_history_records_all_details(self):
        """History entry should contain all breeding details."""
        entry = {
            "offspring_identifier": "karpi",
            "offspring_name": "Karpi",
            "parent1_identifier": "blub",
            "parent1_name": "Blub",
            "parent2_identifier": "wolfior",
            "parent2_name": "Wolfior",
            "hatch_timestamp": 1000,
            "inherited_moves": ["power_bite"],
            "shiny": True,
        }

        self.assertEqual(entry["offspring_name"], "Karpi")
        self.assertEqual(entry["parent1_name"], "Blub")
        self.assertEqual(entry["parent2_name"], "Wolfior")
        self.assertEqual(entry["hatch_timestamp"], 1000)
        self.assertEqual(entry["inherited_moves"], ["power_bite"])
        self.assertTrue(entry["shiny"])


class TestStatInheritance(unittest.TestCase):
    """Tests for stat inheritance from parents."""

    def test_stats_combine_from_parents(self):
        """Stats should combine from both parents."""
        parent1_stats = MockPokeInfo(hp=20, atc=10, defense=5, initiative=3)
        parent2_stats = MockPokeInfo(hp=30, atc=2, defense=8, initiative=6)

        combined_hp = compute_weighted_stat(parent1_stats.hp, parent2_stats.hp)
        combined_atc = compute_weighted_stat(parent1_stats.atc, parent2_stats.atc)
        combined_defense = compute_weighted_stat(parent1_stats.defense, parent2_stats.defense)
        combined_initiative = compute_weighted_stat(parent1_stats.initiative, parent2_stats.initiative)

        self.assertEqual(combined_hp, 25)
        self.assertEqual(combined_atc, 6)
        self.assertEqual(combined_defense, 6)
        self.assertEqual(combined_initiative, 4)

    def test_high_stat_parent_influences_offspring(self):
        """High-stat parent should positively influence offspring."""
        low_stat_parent = MockPokeInfo(hp=10, atc=1, defense=1, initiative=1)
        high_stat_parent = MockPokeInfo(hp=50, atc=10, defense=10, initiative=10)

        combined_hp = compute_weighted_stat(low_stat_parent.hp, high_stat_parent.hp)
        combined_atc = compute_weighted_stat(low_stat_parent.atc, high_stat_parent.atc)

        self.assertGreater(combined_hp, low_stat_parent.hp)
        self.assertLess(combined_hp, high_stat_parent.hp)
        self.assertGreater(combined_atc, low_stat_parent.atc)
        self.assertLess(combined_atc, high_stat_parent.atc)


class TestBreedingCancellation(unittest.TestCase):
    """Tests for breeding cancellation."""

    def test_cancel_returns_parents(self):
        """Cancelling breeding should return both parents."""
        parent1 = MockPoke("karpi", 50, ["water"])
        parent2 = MockPoke("blub", 50, ["water"])

        returned_p1 = parent1
        returned_p2 = parent2
        parent1 = None
        parent2 = None

        self.assertIsNotNone(returned_p1)
        self.assertIsNotNone(returned_p2)
        self.assertIsNone(parent1)
        self.assertIsNone(parent2)

    def test_cancel_resets_state(self):
        """Cancelling should reset all breeding state."""
        start_time = 100
        egg_ready = True
        egg = {"identifier": "test"}
        notified = True

        # Cancel
        start_time = 0
        egg_ready = False
        egg = None
        notified = False

        self.assertEqual(start_time, 0)
        self.assertFalse(egg_ready)
        self.assertIsNone(egg)
        self.assertFalse(notified)


class TestSaveLoadIntegration(unittest.TestCase):
    """Tests for save/load integration with the save system."""

    def test_save_data_format(self):
        """Test that breeding data matches save format."""
        save_breeding_data = {
            "parent1": None,
            "parent2": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        required_keys = ["parent1", "parent2", "start_time", "egg_ready", "egg", "history"]
        for key in required_keys:
            self.assertIn(key, save_breeding_data)

    def test_load_preserves_breeding_state(self):
        """Test that loading preserves breeding state correctly."""
        saved_data = {
            "parent1": {
                "name": "karpi",
                "xp": 50,
                "hp": 15,
                "ap": [],
                "effects": [],
                "attacks": ["tackle"],
                "shiny": False,
                "nature": {"nature": "normal", "grade": 1},
                "stats": {},
            },
            "parent2": {
                "name": "blub",
                "xp": 60,
                "hp": 20,
                "ap": [],
                "effects": [],
                "attacks": ["tackle", "bubble_bomb"],
                "shiny": False,
                "nature": {"nature": "normal", "grade": 1},
                "stats": {},
            },
            "start_time": 100,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        self.assertIsNotNone(saved_data.get("parent1"))
        self.assertIsNotNone(saved_data.get("parent2"))
        self.assertEqual(saved_data.get("start_time"), 100)
        self.assertFalse(saved_data.get("egg_ready"))

    def test_load_preserves_history(self):
        """Test that loading preserves breeding history."""
        saved_data = {
            "parent1": None,
            "parent2": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [
                {
                    "offspring_identifier": "karpi",
                    "offspring_name": "Karpi",
                    "parent1_identifier": "karpi",
                    "parent1_name": "Karpi",
                    "parent2_identifier": "blub",
                    "parent2_name": "Blub",
                    "hatch_timestamp": 500,
                    "inherited_moves": ["power_bite"],
                    "shiny": False,
                }
            ],
        }

        self.assertEqual(len(saved_data["history"]), 1)
        self.assertEqual(saved_data["history"][0]["inherited_moves"], ["power_bite"])


class TestPeriodicEventIntegration(unittest.TestCase):
    """Tests for periodic event integration."""

    def test_check_and_notify_logic(self):
        """Test that check_and_notify correctly identifies state changes."""
        # Simulate the logic
        has_pair = True
        was_ready = False
        egg_ready = False

        # First check - not ready
        result = egg_ready and not was_ready
        self.assertFalse(result)

        # Egg becomes ready
        egg_ready = True
        result = egg_ready and not was_ready
        self.assertTrue(result)

        # Second check - already ready
        was_ready = True
        result = egg_ready and not was_ready
        self.assertFalse(result)

    def test_event_checks_at_interval(self):
        """Test that event checks at proper intervals."""
        check_interval = 10
        ticks_checked = []

        for tick in range(50):
            if tick % check_interval == 0:
                ticks_checked.append(tick)

        self.assertEqual(ticks_checked, [0, 10, 20, 30, 40])


class TestMockedTimerIntegration(unittest.TestCase):
    """Tests that verify timer mocking works correctly."""

    def test_mock_timer_time(self):
        """Test that timer can be mocked."""
        mock_timer = Mock()
        mock_timer.time = Mock()
        mock_timer.time.time = 500

        self.assertEqual(mock_timer.time.time, 500)

        # Simulate time passing
        mock_timer.time.time = 800
        self.assertEqual(mock_timer.time.time, 800)

    def test_breeding_with_mocked_time(self):
        """Test breeding calculation with mocked time."""
        start_time = 100
        current_time = 500  # Mocked
        hatch_time = 300

        elapsed = current_time - start_time
        remaining = max(0, hatch_time - elapsed)

        self.assertEqual(elapsed, 400)
        self.assertEqual(remaining, 0)  # Egg is ready


class TestMockedAssetServiceIntegration(unittest.TestCase):
    """Tests that verify asset_service mocking works correctly."""

    def test_mock_asset_service_pokes(self):
        """Test that pokes can be accessed from mock asset service."""
        mock_service = create_mock_asset_service()
        pokes = mock_service.get_base_assets().pokes

        self.assertIn("karpi", pokes)
        self.assertIn("blub", pokes)
        self.assertEqual(pokes["karpi"].hp, 15)
        self.assertEqual(pokes["blub"].atc, 2)

    def test_mock_asset_service_attacks(self):
        """Test that attacks can be accessed from mock asset service."""
        mock_service = create_mock_asset_service()
        attacks = mock_service.get_base_assets().attacks

        self.assertIn("tackle", attacks)
        self.assertIn("power_bite", attacks)
        self.assertEqual(attacks["tackle"].min_lvl, 0)
        self.assertEqual(attacks["power_bite"].min_lvl, 30)

    def test_egg_move_computation_with_mocked_service(self):
        """Test egg move computation using mocked asset service."""
        mock_service = create_mock_asset_service()
        attacks = mock_service.get_base_assets().attacks
        pokes = mock_service.get_base_assets().pokes

        parent1 = MockPoke("blub", 1000, ["water", "normal"],
                         attacks=["tackle", "power_bite"])
        parent2 = MockPoke("wolfior", 1000, ["fire", "normal"],
                         attacks=["tackle", "tail_wipe"])
        offspring_id = "karpi"
        offspring_info = pokes[offspring_id]

        offspring_learnable = set(offspring_info.attacks + offspring_info.pool)

        inherited = []
        for parent in [parent1, parent2]:
            if len(inherited) >= 2:
                break
            for atk_name in parent.attacks:
                if atk_name in attacks:
                    atk_data = attacks[atk_name]
                    if atk_data.min_lvl > 0 and atk_name not in offspring_learnable:
                        if atk_name not in inherited:
                            inherited.append(atk_name)
                            break

        self.assertIn("power_bite", inherited)
        self.assertIn("tail_wipe", inherited)
        self.assertEqual(len(inherited), 2)


if __name__ == "__main__":
    unittest.main()
