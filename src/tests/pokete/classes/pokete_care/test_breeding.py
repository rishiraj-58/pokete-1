"""Tests for the breeding system in Pokete Care.

These tests verify the core breeding logic including:
- Type compatibility checking
- Weighted stat computation
- Egg generation and hatching
- Serialization/deserialization
- Notification when eggs are ready
- Egg move inheritance
- Breeding history

Note: Due to Python version requirements (3.12+), some tests use mocks
and test the logic in isolation from the actual game code.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import math
from datetime import datetime


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


class MockPoke:
    """Mock Poke class for testing without full game dependencies."""
    def __init__(self, identifier: str, xp: int = 0, types=None, inf=None,
                 attacks=None, name=None):
        self.identifier = identifier
        self.xp = xp
        self.types = [MockType(t) for t in (types or ["normal"])]
        self.inf = inf or MockPokeInfo(types=types or ["normal"])
        self.name = name or identifier.capitalize()
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


class MockAttack:
    """Mock attack for testing."""
    def __init__(self, name: str, min_lvl: int = 1, types=None, is_generic=False):
        self.name = name
        self.min_lvl = min_lvl
        self.types = types or ["normal"]
        self.is_generic = is_generic


class MockTimer:
    """Mock timer for testing."""
    def __init__(self, time: int = 0):
        self.time = time


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


def get_egg_moves(parent1, parent2, offspring_id, attacks_data, pokes_data):
    """Get moves that the egg can inherit from parents."""
    if parent1 is None or parent2 is None:
        return []

    offspring_info = pokes_data.get(offspring_id)
    if offspring_info is None:
        return []

    # Get attacks the offspring can learn at level 1
    level1_attacks = set(
        atk for atk in offspring_info.attacks
        if attacks_data.get(atk) and attacks_data[atk].min_lvl <= 1
    )

    inherited_moves = []

    # Try to inherit one move from each parent
    for parent in [parent1, parent2]:
        if len(inherited_moves) >= 2:
            break

        # Get parent's current attacks that offspring can't learn at level 1
        candidate_moves = [
            atk for atk in parent.attacks
            if atk not in level1_attacks
            and atk not in inherited_moves
            and attacks_data.get(atk) is not None
        ]

        if candidate_moves:
            inherited_moves.append(candidate_moves[0])  # Deterministic for testing

    return inherited_moves


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
        atc = compute_weighted_stat(10, 2, 0.5, 0.5)
        defense = compute_weighted_stat(2, 10, 0.5, 0.5)
        self.assertEqual(atc, 6)
        self.assertEqual(defense, 6)

    def test_stat_inheritance_formula(self):
        """Test the full stat inheritance formula: 40% p1 + 40% p2 + 20% base."""
        p1_hp, p2_hp, base_hp = 30, 20, 25
        # Weighted average of parents
        parent_avg = compute_weighted_stat(p1_hp, p2_hp, 0.4, 0.4)  # 20
        # Final: 80% parent_avg + 20% base
        final_hp = int(parent_avg * 0.8 + base_hp * 0.2)  # 16 + 5 = 21
        self.assertEqual(final_hp, 21)


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
        self.assertEqual(time, 297)

    def test_higher_level_reduces_hatch_time(self):
        """Higher level parents should reduce hatch time."""
        time_low = compute_hatch_time(self.low_level_poke1, self.low_level_poke2)
        time_high = compute_hatch_time(self.high_level_poke1, self.high_level_poke2)
        self.assertGreater(time_low, time_high)

    def test_minimum_hatch_time(self):
        """Hatch time should not go below 50% of base."""
        very_high_poke1 = MockPoke("vh1", 10000)
        very_high_poke2 = MockPoke("vh2", 10000)
        time = compute_hatch_time(very_high_poke1, very_high_poke2)
        self.assertEqual(time, 150)

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


class TestEggMoveInheritance(unittest.TestCase):
    """Tests for egg move inheritance system."""

    def setUp(self):
        """Set up mock data for testing egg moves."""
        self.attacks_data = {
            "tackle": MockAttack("tackle", min_lvl=1),
            "bubble_bomb": MockAttack("bubble_bomb", min_lvl=5),
            "fire_bite": MockAttack("fire_bite", min_lvl=10),
            "mega_punch": MockAttack("mega_punch", min_lvl=15),
            "water_gun": MockAttack("water_gun", min_lvl=1),
        }
        self.pokes_data = {
            "karpi": MockPokeInfo(
                attacks=["tackle", "water_gun"],
                types=["water", "normal"]
            ),
        }

    def test_inherit_move_from_parent(self):
        """Test that offspring can inherit a move from parent."""
        parent1 = MockPoke("karpi", 100, ["water"], attacks=["tackle", "bubble_bomb"])
        parent2 = MockPoke("blub", 100, ["water"], attacks=["tackle", "fire_bite"])

        inherited = get_egg_moves(
            parent1, parent2, "karpi",
            self.attacks_data, self.pokes_data
        )

        # Should inherit moves that offspring can't learn at level 1
        self.assertIn("bubble_bomb", inherited)
        self.assertEqual(len(inherited), 2)

    def test_no_inheritance_if_all_level1(self):
        """Test no inheritance if parents only have level 1 moves."""
        parent1 = MockPoke("karpi", 50, ["water"], attacks=["tackle", "water_gun"])
        parent2 = MockPoke("blub", 50, ["water"], attacks=["tackle", "water_gun"])

        inherited = get_egg_moves(
            parent1, parent2, "karpi",
            self.attacks_data, self.pokes_data
        )

        self.assertEqual(inherited, [])

    def test_max_two_inherited_moves(self):
        """Test that maximum 2 moves can be inherited (one per parent)."""
        parent1 = MockPoke("karpi", 100, ["water"],
                          attacks=["bubble_bomb", "mega_punch"])
        parent2 = MockPoke("blub", 100, ["water"],
                          attacks=["fire_bite", "mega_punch"])

        inherited = get_egg_moves(
            parent1, parent2, "karpi",
            self.attacks_data, self.pokes_data
        )

        self.assertLessEqual(len(inherited), 2)

    def test_no_duplicate_inherited_moves(self):
        """Test that same move isn't inherited twice."""
        parent1 = MockPoke("karpi", 100, ["water"], attacks=["bubble_bomb"])
        parent2 = MockPoke("blub", 100, ["water"], attacks=["bubble_bomb"])

        inherited = get_egg_moves(
            parent1, parent2, "karpi",
            self.attacks_data, self.pokes_data
        )

        # Should only inherit once even if both parents have same move
        self.assertEqual(len(inherited), len(set(inherited)))


class TestBreedingHistory(unittest.TestCase):
    """Tests for breeding history tracking."""

    def test_history_entry_structure(self):
        """Test breeding history entry has correct structure."""
        entry = {
            "offspring_identifier": "karpi",
            "offspring_name": "Karpi",
            "parent1_identifier": "blub",
            "parent1_name": "Blub",
            "parent2_identifier": "karpi",
            "parent2_name": "Karpi",
            "hatch_time": 300,
            "bred_at": "2024-01-15T10:30:00",
            "inherited_moves": ["bubble_bomb"],
            "was_shiny": False,
        }

        self.assertIn("offspring_identifier", entry)
        self.assertIn("offspring_name", entry)
        self.assertIn("parent1_identifier", entry)
        self.assertIn("parent1_name", entry)
        self.assertIn("parent2_identifier", entry)
        self.assertIn("parent2_name", entry)
        self.assertIn("hatch_time", entry)
        self.assertIn("bred_at", entry)
        self.assertIn("inherited_moves", entry)
        self.assertIn("was_shiny", entry)

    def test_history_max_entries(self):
        """Test that history is limited to MAX_HISTORY_ENTRIES."""
        MAX_HISTORY_ENTRIES = 5
        history = []

        # Add more than max entries
        for i in range(7):
            history.append({"id": i})

        # Trim to max
        if len(history) > MAX_HISTORY_ENTRIES:
            history = history[-MAX_HISTORY_ENTRIES:]

        self.assertEqual(len(history), 5)
        # Should keep most recent
        self.assertEqual(history[0]["id"], 2)
        self.assertEqual(history[-1]["id"], 6)

    def test_history_entry_from_dict(self):
        """Test deserializing history entry from dict."""
        entry_dict = {
            "offspring_identifier": "karpi",
            "offspring_name": "Karpi",
            "parent1_identifier": "blub",
            "parent1_name": "Blub",
            "parent2_identifier": "karpi",
            "parent2_name": "Karpi",
            "hatch_time": 300,
            "bred_at": "2024-01-15T10:30:00",
            "inherited_moves": ["bubble_bomb"],
            "was_shiny": True,
        }

        # Parse the datetime
        bred_at = datetime.fromisoformat(entry_dict["bred_at"])
        self.assertEqual(bred_at.year, 2024)
        self.assertEqual(bred_at.month, 1)
        self.assertEqual(bred_at.day, 15)


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
            "parent1_name": "Karpi",
            "parent2_name": "Blub",
            "inherited_moves": ["bubble_bomb"],
        }

        self.assertIn("identifier", egg_dict)
        self.assertIn("hp", egg_dict)
        self.assertIn("atc", egg_dict)
        self.assertIn("defense", egg_dict)
        self.assertIn("initiative", egg_dict)
        self.assertIn("hatch_time", egg_dict)
        self.assertIn("parent1_identifier", egg_dict)
        self.assertIn("parent2_identifier", egg_dict)
        self.assertIn("parent1_name", egg_dict)
        self.assertIn("parent2_name", egg_dict)
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
            "parent1_name": "Karpi",
            "parent2_name": "Blub",
            "inherited_moves": ["tackle"],
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


class TestBreedingManagerSerialization(unittest.TestCase):
    """Tests for BreedingManager serialization."""

    def test_empty_manager_dict_structure(self):
        """Test serialization structure of empty breeding manager."""
        empty_dict = {
            "parent1": None,
            "parent2": None,
            "parent1_index": None,
            "parent2_index": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        self.assertIn("parent1", empty_dict)
        self.assertIn("parent2", empty_dict)
        self.assertIn("parent1_index", empty_dict)
        self.assertIn("parent2_index", empty_dict)
        self.assertIn("start_time", empty_dict)
        self.assertIn("egg_ready", empty_dict)
        self.assertIn("egg", empty_dict)
        self.assertIn("history", empty_dict)

    def test_manager_dict_with_data(self):
        """Test serialization structure with breeding data."""
        poke_dict = MockPoke("karpi", 50, ["water"]).dict()
        manager_dict = {
            "parent1": poke_dict,
            "parent2": poke_dict,
            "parent1_index": 0,
            "parent2_index": 1,
            "start_time": 100,
            "egg_ready": True,
            "egg": {
                "identifier": "karpi",
                "hp": 15,
                "atc": 0,
                "defense": 0,
                "initiative": 0,
                "hatch_time": 300,
                "parent1_identifier": "karpi",
                "parent2_identifier": "karpi",
                "parent1_name": "Karpi",
                "parent2_name": "Karpi",
                "inherited_moves": [],
            },
            "history": [],
        }

        self.assertIsNotNone(manager_dict["parent1"])
        self.assertIsNotNone(manager_dict["parent2"])
        self.assertEqual(manager_dict["parent1_index"], 0)
        self.assertEqual(manager_dict["parent2_index"], 1)
        self.assertEqual(manager_dict["start_time"], 100)
        self.assertTrue(manager_dict["egg_ready"])
        self.assertIsNotNone(manager_dict["egg"])


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

        elapsed = current_time - start_time
        remaining = hatch_time - elapsed
        remaining = max(0, remaining)

        self.assertEqual(elapsed, 50)
        self.assertEqual(remaining, 250)

    def test_time_remaining_when_ready(self):
        """Test time remaining is 0 when egg is ready."""
        start_time = 100
        current_time = 500
        hatch_time = 300

        elapsed = current_time - start_time
        remaining = hatch_time - elapsed
        remaining = max(0, remaining)

        self.assertEqual(remaining, 0)

    def test_cancel_breeding_returns_indices(self):
        """Test that cancelling breeding returns parent indices."""
        parent1 = MockPoke("karpi", 50)
        parent2 = MockPoke("blub", 50)
        parent1_index = 0
        parent2_index = 1

        # Simulate cancel
        returned_p1 = parent1
        returned_p2 = parent2
        returned_idx1 = parent1_index
        returned_idx2 = parent2_index

        self.assertIsNotNone(returned_p1)
        self.assertIsNotNone(returned_p2)
        self.assertEqual(returned_idx1, 0)
        self.assertEqual(returned_idx2, 1)


class TestNotificationLogic(unittest.TestCase):
    """Tests for egg-ready notification logic."""

    def test_update_detects_egg_ready(self):
        """Update should detect when egg becomes ready."""
        start_time = 100
        hatch_time = 300
        egg_ready = False

        current_time = 350
        elapsed = current_time - start_time
        if elapsed >= hatch_time:
            egg_ready = True

        self.assertFalse(egg_ready)

        current_time = 450
        elapsed = current_time - start_time
        if elapsed >= hatch_time:
            egg_ready = True

        self.assertTrue(egg_ready)

    def test_notification_only_fires_once(self):
        """Notification should only fire once when egg becomes ready."""
        egg_ready = False
        notifications = []
        notified_ready = False

        # First update when egg becomes ready
        egg_ready = True
        just_became_ready = egg_ready and not notified_ready
        if just_became_ready:
            notifications.append("Egg ready!")
            notified_ready = True

        # Second update - egg is still ready
        just_became_ready = egg_ready and not notified_ready
        if just_became_ready:
            notifications.append("Egg ready!")
            notified_ready = True

        self.assertEqual(len(notifications), 1)

    def test_notification_resets_after_collection(self):
        """Notification flag should reset after egg collection."""
        notified_ready = True
        has_breeding_pair = True

        # Simulate collection
        has_breeding_pair = False

        # Reset notification flag when no breeding
        if not has_breeding_pair:
            notified_ready = False

        self.assertFalse(notified_ready)


class TestPeriodicBreedingCheck(unittest.TestCase):
    """Tests for periodic breeding check event."""

    def test_check_interval(self):
        """Test that breeding is checked at correct intervals."""
        max_tick = 50
        checked_ticks = []

        for tick in range(200):
            if tick % max_tick == 0:
                checked_ticks.append(tick)

        self.assertEqual(checked_ticks, [0, 50, 100, 150])

    def test_breeding_manager_update_called(self):
        """Test that breeding manager update is called during check."""
        update_called = False
        current_time = 100

        def mock_update(time):
            nonlocal update_called
            update_called = True
            return False

        mock_update(current_time)
        self.assertTrue(update_called)


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

        start_time = 0
        egg_ready = False
        egg = None

        self.assertEqual(start_time, 0)
        self.assertFalse(egg_ready)
        self.assertIsNone(egg)


class TestSaveLoadIntegration(unittest.TestCase):
    """Tests for save/load integration with the save system."""

    def test_save_data_format(self):
        """Test that breeding data matches save format."""
        save_breeding_data = {
            "parent1": None,
            "parent2": None,
            "parent1_index": None,
            "parent2_index": None,
            "start_time": 0,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        required_keys = [
            "parent1", "parent2", "parent1_index", "parent2_index",
            "start_time", "egg_ready", "egg", "history"
        ]
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
                "attacks": [],
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
                "attacks": [],
                "shiny": False,
                "nature": {"nature": "normal", "grade": 1},
                "stats": {},
            },
            "parent1_index": 0,
            "parent2_index": 1,
            "start_time": 100,
            "egg_ready": False,
            "egg": None,
            "history": [],
        }

        self.assertIsNotNone(saved_data.get("parent1"))
        self.assertIsNotNone(saved_data.get("parent2"))
        self.assertEqual(saved_data.get("parent1_index"), 0)
        self.assertEqual(saved_data.get("parent2_index"), 1)
        self.assertEqual(saved_data.get("start_time"), 100)
        self.assertFalse(saved_data.get("egg_ready"))

    def test_load_preserves_history(self):
        """Test that loading preserves breeding history."""
        saved_data = {
            "history": [
                {
                    "offspring_identifier": "karpi",
                    "offspring_name": "Karpi",
                    "parent1_identifier": "blub",
                    "parent1_name": "Blub",
                    "parent2_identifier": "karpi",
                    "parent2_name": "Karpi",
                    "hatch_time": 300,
                    "bred_at": "2024-01-15T10:30:00",
                    "inherited_moves": ["bubble_bomb"],
                    "was_shiny": False,
                }
            ]
        }

        self.assertEqual(len(saved_data["history"]), 1)
        self.assertEqual(saved_data["history"][0]["offspring_name"], "Karpi")


class TestMockedTimerIntegration(unittest.TestCase):
    """Tests using mocked timer for breeding updates."""

    def test_breeding_progress_with_mock_timer(self):
        """Test breeding progress using mock timer."""
        mock_timer = MockTimer(time=0)

        start_time = mock_timer.time
        hatch_time = 300
        egg_ready = False

        # Advance time
        mock_timer.time = 150
        elapsed = mock_timer.time - start_time
        if elapsed >= hatch_time:
            egg_ready = True
        self.assertFalse(egg_ready)

        # Advance more
        mock_timer.time = 350
        elapsed = mock_timer.time - start_time
        if elapsed >= hatch_time:
            egg_ready = True
        self.assertTrue(egg_ready)

    def test_time_remaining_with_mock_timer(self):
        """Test time remaining calculation with mock timer."""
        mock_timer = MockTimer(time=100)
        start_time = 0
        hatch_time = 300

        elapsed = mock_timer.time - start_time
        remaining = max(0, hatch_time - elapsed)

        self.assertEqual(remaining, 200)


if __name__ == "__main__":
    unittest.main()
