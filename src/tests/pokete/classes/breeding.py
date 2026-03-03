import unittest
from unittest.mock import patch, MagicMock

from pokete.classes.pokete_care.breeding import (
    BreedingManager,
    BreedingPair,
    BASE_HATCHING_TIME,
)


class MockPoke:
    """Mock Poke class for testing"""

    def __init__(
        self,
        identifier: str,
        types: list[str],
        level: int = 5,
        attacks: list[str] = None
    ):
        self.identifier = identifier
        self.types = [MockType(t) for t in types]
        self._level = level
        self.attacks = attacks or ["tackle"]
        self.name = identifier.capitalize()

    def lvl(self):
        return self._level

    def dict(self):
        return {
            "name": self.identifier,
            "xp": self._level ** 2,
            "hp": 20,
            "ap": [5],
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


class MockType:
    """Mock Type class for testing"""

    def __init__(self, name: str):
        self.name = name


class TestBreedingCompatibility(unittest.TestCase):
    def setUp(self):
        self.manager = BreedingManager()

    def test_compatible_with_shared_type(self):
        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])

        self.assertTrue(self.manager.are_compatible(poke1, poke2))

    def test_compatible_with_one_shared_type(self):
        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("wolfior", ["fire", "normal"])

        self.assertTrue(self.manager.are_compatible(poke1, poke2))

    def test_incompatible_no_shared_type(self):
        poke1 = MockPoke("steini", ["stone"])
        poke2 = MockPoke("wolfior", ["fire"])

        self.assertFalse(self.manager.are_compatible(poke1, poke2))

    def test_compatible_same_single_type(self):
        poke1 = MockPoke("rosi", ["plant"])
        poke2 = MockPoke("wheeto", ["plant"])

        self.assertTrue(self.manager.are_compatible(poke1, poke2))


class TestHatchingTime(unittest.TestCase):
    def setUp(self):
        self.manager = BreedingManager()

    def test_base_hatching_time_low_level(self):
        poke1 = MockPoke("steini", ["stone"], level=5)
        poke2 = MockPoke("lilstone", ["stone"], level=5)

        hatching_time = self.manager.compute_hatching_time(poke1, poke2)

        self.assertGreater(hatching_time, BASE_HATCHING_TIME * 0.4)
        self.assertLessEqual(hatching_time, BASE_HATCHING_TIME)

    def test_faster_hatching_high_level(self):
        low_level_poke1 = MockPoke("steini", ["stone"], level=5)
        low_level_poke2 = MockPoke("lilstone", ["stone"], level=5)

        high_level_poke1 = MockPoke("steini", ["stone"], level=50)
        high_level_poke2 = MockPoke("lilstone", ["stone"], level=50)

        low_time = self.manager.compute_hatching_time(
            low_level_poke1, low_level_poke2
        )
        high_time = self.manager.compute_hatching_time(
            high_level_poke1, high_level_poke2
        )

        self.assertLess(high_time, low_time)


class TestBreedingPair(unittest.TestCase):
    def test_is_ready_before_time(self):
        poke1 = MockPoke("steini", ["stone"])
        poke2 = MockPoke("lilstone", ["stone"])

        pair = BreedingPair(
            parent1=poke1,
            parent2=poke2,
            start_time=0,
            hatching_time=100,
        )

        self.assertFalse(pair.is_ready(50))

    def test_is_ready_after_time(self):
        poke1 = MockPoke("steini", ["stone"])
        poke2 = MockPoke("lilstone", ["stone"])

        pair = BreedingPair(
            parent1=poke1,
            parent2=poke2,
            start_time=0,
            hatching_time=100,
        )

        self.assertTrue(pair.is_ready(100))
        self.assertTrue(pair.is_ready(150))

    def test_time_remaining(self):
        poke1 = MockPoke("steini", ["stone"])
        poke2 = MockPoke("lilstone", ["stone"])

        pair = BreedingPair(
            parent1=poke1,
            parent2=poke2,
            start_time=0,
            hatching_time=100,
        )

        self.assertEqual(pair.time_remaining(0), 100)
        self.assertEqual(pair.time_remaining(50), 50)
        self.assertEqual(pair.time_remaining(100), 0)
        self.assertEqual(pair.time_remaining(150), 0)


class TestBreedingManager(unittest.TestCase):
    def setUp(self):
        self.manager = BreedingManager()

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_start_breeding_compatible(self, mock_timer):
        mock_timer.time.time = 0

        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])

        result = self.manager.start_breeding(poke1, poke2)

        self.assertTrue(result)
        self.assertIsNotNone(self.manager.breeding_pair)

    def test_start_breeding_incompatible(self):
        poke1 = MockPoke("steini", ["stone"])
        poke2 = MockPoke("wolfior", ["fire"])

        result = self.manager.start_breeding(poke1, poke2)

        self.assertFalse(result)
        self.assertIsNone(self.manager.breeding_pair)

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_cannot_start_while_breeding(self, mock_timer):
        mock_timer.time.time = 0

        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])
        poke3 = MockPoke("poundi", ["stone", "normal"])

        self.manager.start_breeding(poke1, poke2)
        result = self.manager.start_breeding(poke1, poke3)

        self.assertFalse(result)

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_cancel_breeding(self, mock_timer):
        mock_timer.time.time = 0

        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])

        self.manager.start_breeding(poke1, poke2)
        parents = self.manager.cancel_breeding()

        self.assertIsNotNone(parents)
        self.assertIsNone(self.manager.breeding_pair)

    def test_cancel_breeding_when_not_breeding(self):
        result = self.manager.cancel_breeding()

        self.assertIsNone(result)

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_get_status_idle(self, mock_timer):
        status = self.manager.get_status()

        self.assertEqual(status["status"], "idle")

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_get_status_breeding(self, mock_timer):
        mock_timer.time.time = 0

        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])

        self.manager.start_breeding(poke1, poke2)
        mock_timer.time.time = 50

        status = self.manager.get_status()

        self.assertEqual(status["status"], "breeding")
        self.assertIn("time_remaining", status)
        self.assertIn("progress", status)


class TestBreedingManagerSerialization(unittest.TestCase):
    def setUp(self):
        self.manager = BreedingManager()

    def test_dict_empty(self):
        data = self.manager.dict()

        self.assertIsNone(data["breeding_pair"])
        self.assertIsNone(data["egg"])
        self.assertFalse(data["egg_ready"])
        self.assertFalse(data["notified"])

    @patch('pokete.classes.pokete_care.breeding.timer')
    def test_dict_with_breeding(self, mock_timer):
        mock_timer.time.time = 0

        poke1 = MockPoke("steini", ["stone", "normal"])
        poke2 = MockPoke("lilstone", ["stone", "normal"])

        self.manager.start_breeding(poke1, poke2)
        data = self.manager.dict()

        self.assertIsNotNone(data["breeding_pair"])
        self.assertEqual(data["breeding_pair"]["parent1"]["name"], "steini")
        self.assertEqual(data["breeding_pair"]["parent2"]["name"], "lilstone")

    def test_from_dict_empty(self):
        data = {
            "breeding_pair": None,
            "egg": None,
            "egg_ready": False,
            "notified": False,
        }

        self.manager.from_dict(data)

        self.assertIsNone(self.manager.breeding_pair)
        self.assertIsNone(self.manager.egg)
        self.assertFalse(self.manager.egg_ready)


class TestEggCollection(unittest.TestCase):
    def setUp(self):
        self.manager = BreedingManager()

    def test_collect_egg_when_not_ready(self):
        result = self.manager.collect_egg()

        self.assertIsNone(result)

    @patch('pokete.classes.pokete_care.breeding.timer')
    @patch('pokete.classes.pokete_care.breeding.Poke')
    def test_collect_egg_when_ready(self, mock_poke_class, mock_timer):
        mock_timer.time.time = 0

        mock_egg = MagicMock()
        mock_poke_class.return_value = mock_egg

        self.manager.egg = mock_egg
        self.manager.egg_ready = True
        self.manager.breeding_pair = MagicMock()

        result = self.manager.collect_egg()

        self.assertEqual(result, mock_egg)
        self.assertIsNone(self.manager.egg)
        self.assertFalse(self.manager.egg_ready)
        self.assertIsNone(self.manager.breeding_pair)


if __name__ == "__main__":
    unittest.main()
