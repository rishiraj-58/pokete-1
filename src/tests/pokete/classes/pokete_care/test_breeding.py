"""Tests for the breeding system.

These tests are designed to work with Python 3.12+ and test the breeding
system components in isolation using mocks for external dependencies.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))


def create_mock_poke(
    identifier: str = "steini",
    name: str = "Steini",
    types: list[str] = None,
    xp: int = 50,
    shiny: bool = False,
    attacks: list[str] = None,
    hp: int = 25,
    atc: int = 2,
    defense: int = 4,
    initiative: int = 5,
    rarity: float = 1.0,
    miss_chance: float = 0.0,
):
    """Creates a mock Poke object for testing."""
    if types is None:
        types = ["stone", "normal"]
    if attacks is None:
        attacks = ["tackle", "politure"]

    mock_type = Mock()
    mock_type.name = types[0]

    mock_types = [Mock() for t in types]
    for i, t in enumerate(types):
        mock_types[i].name = t

    mock_inf = Mock()
    mock_inf.hp = hp
    mock_inf.atc = atc
    mock_inf.defense = defense
    mock_inf.initiative = initiative
    mock_inf.rarity = rarity
    mock_inf.miss_chance = miss_chance
    mock_inf.attacks = attacks

    mock_poke = Mock()
    mock_poke.identifier = identifier
    mock_poke.name = name
    mock_poke.types = mock_types
    mock_poke.type = mock_type
    mock_poke.xp = xp
    mock_poke.shiny = shiny
    mock_poke.attacks = attacks
    mock_poke.inf = mock_inf
    mock_poke.lvl = Mock(return_value=int((xp + 1) ** 0.5))
    mock_poke.dict = Mock(return_value={
        "name": identifier,
        "xp": xp,
        "hp": hp,
        "ap": [10, 10],
        "effects": [],
        "attacks": attacks,
        "shiny": shiny,
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
    })

    return mock_poke


# Conditionally import based on Python version
if sys.version_info >= (3, 12):
    from pokete.classes.pokete_care.breeding.breeding_config import (
        BreedingConfig,
        HatchTimeStrategy,
        StatInheritanceStrategy,
    )
    from pokete.classes.pokete_care.breeding.compatibility_checker import (
        CompatibilityChecker,
        CompatibilityStatus,
    )
    from pokete.classes.pokete_care.breeding.stat_calculator import (
        StatCalculator,
        CalculatedStats,
    )
    from pokete.classes.pokete_care.breeding.egg_generator import (
        EggGenerator,
        EggPokete,
    )
    from pokete.classes.pokete_care.breeding.breeding_pair import BreedingPair
    from pokete.classes.pokete_care.breeding.breeding_manager import BreedingManager
    from pokete.classes.pokete_care.breeding.breeding_notification_service import (
        BreedingNotificationService,
        BreedingEventType,
    )

    class TestBreedingConfig(unittest.TestCase):
        """Tests for BreedingConfig."""

        def test_default_config_values(self):
            config = BreedingConfig()
            self.assertEqual(config.base_hatch_time, 300)
            self.assertEqual(config.hatch_time_strategy, HatchTimeStrategy.COMBINED)
            self.assertEqual(
                config.stat_inheritance_strategy, StatInheritanceStrategy.WEIGHTED_AVERAGE
            )
            self.assertEqual(config.parent1_weight, 0.5)
            self.assertEqual(config.parent2_weight, 0.5)
            self.assertEqual(config.minimum_shared_types, 1)
            self.assertEqual(config.egg_starting_xp, 0)

        def test_config_serialization(self):
            config = BreedingConfig()
            config_dict = config.to_dict()

            self.assertIn("base_hatch_time", config_dict)
            self.assertIn("hatch_time_strategy", config_dict)
            self.assertIn("stat_inheritance_strategy", config_dict)

        def test_config_deserialization(self):
            config_dict = {
                "base_hatch_time": 500,
                "hatch_time_strategy": "fixed",
                "stat_inheritance_strategy": "average",
                "parent1_weight": 0.6,
                "parent2_weight": 0.4,
                "minimum_shared_types": 2,
                "egg_starting_xp": 10,
            }
            config = BreedingConfig.from_dict(config_dict)

            self.assertEqual(config.base_hatch_time, 500)
            self.assertEqual(config.hatch_time_strategy, HatchTimeStrategy.FIXED)
            self.assertEqual(
                config.stat_inheritance_strategy, StatInheritanceStrategy.AVERAGE
            )

        def test_config_with_base_hatch_time(self):
            config = BreedingConfig()
            new_config = config.with_base_hatch_time(600)

            self.assertEqual(new_config.base_hatch_time, 600)
            self.assertEqual(config.base_hatch_time, 300)


    class TestCompatibilityChecker(unittest.TestCase):
        """Tests for CompatibilityChecker."""

        def setUp(self):
            self.config = BreedingConfig()
            self.checker = CompatibilityChecker(self.config)

        def test_compatible_poketes_with_shared_type(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            result = self.checker.check_compatibility(poke1, poke2)

            self.assertTrue(result.is_compatible)
            self.assertEqual(result.status, CompatibilityStatus.COMPATIBLE)
            self.assertIn("stone", result.shared_types)

        def test_incompatible_poketes_no_shared_types(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone"])
            poke2 = create_mock_poke(identifier="rosi", types=["plant"])

            result = self.checker.check_compatibility(poke1, poke2)

            self.assertFalse(result.is_compatible)
            self.assertEqual(
                result.status, CompatibilityStatus.INCOMPATIBLE_NO_SHARED_TYPES
            )

        def test_same_pokete_cannot_breed(self):
            poke1 = create_mock_poke()

            result = self.checker.check_compatibility(poke1, poke1)

            self.assertFalse(result.is_compatible)
            self.assertEqual(result.status, CompatibilityStatus.INCOMPATIBLE_SAME_POKETE)

        def test_null_pokete_cannot_breed(self):
            poke1 = create_mock_poke()

            result = self.checker.check_compatibility(poke1, None)

            self.assertFalse(result.is_compatible)
            self.assertEqual(result.status, CompatibilityStatus.INCOMPATIBLE_NULL_POKETE)

        def test_fallback_pokete_cannot_breed(self):
            poke1 = create_mock_poke(identifier="__fallback__")
            poke2 = create_mock_poke(identifier="steini", types=["stone"])

            result = self.checker.check_compatibility(poke1, poke2)

            self.assertFalse(result.is_compatible)
            self.assertEqual(result.status, CompatibilityStatus.INCOMPATIBLE_FALLBACK)

        def test_get_shared_types(self):
            poke1 = create_mock_poke(types=["stone", "normal", "flying"])
            poke2 = create_mock_poke(types=["normal", "flying", "water"])

            shared = self.checker.get_shared_types(poke1, poke2)

            self.assertIn("normal", shared)
            self.assertIn("flying", shared)
            self.assertNotIn("stone", shared)
            self.assertNotIn("water", shared)


    class TestStatCalculator(unittest.TestCase):
        """Tests for StatCalculator."""

        def setUp(self):
            self.config = BreedingConfig()
            self.calculator = StatCalculator(self.config)

        def test_weighted_average_calculation(self):
            poke1 = create_mock_poke(atc=4, defense=6, initiative=8, hp=30, miss_chance=0.1)
            poke2 = create_mock_poke(atc=2, defense=2, initiative=2, hp=20, miss_chance=0.3)

            stats = self.calculator.calculate_offspring_stats(poke1, poke2)

            self.assertEqual(stats.atc, 3)
            self.assertEqual(stats.defense, 4)
            self.assertEqual(stats.initiative, 5)
            self.assertEqual(stats.hp, 25)
            self.assertAlmostEqual(stats.miss_chance, 0.2, places=2)

        def test_average_strategy(self):
            config = BreedingConfig(
                _stat_inheritance_strategy=StatInheritanceStrategy.AVERAGE
            )
            calculator = StatCalculator(config)

            poke1 = create_mock_poke(atc=10, defense=10, initiative=10, hp=30)
            poke2 = create_mock_poke(atc=0, defense=0, initiative=0, hp=20)

            stats = calculator.calculate_offspring_stats(poke1, poke2)

            self.assertEqual(stats.atc, 5)
            self.assertEqual(stats.defense, 5)
            self.assertEqual(stats.initiative, 5)
            self.assertEqual(stats.hp, 25)

        def test_best_parent_strategy(self):
            config = BreedingConfig(
                _stat_inheritance_strategy=StatInheritanceStrategy.BEST_PARENT
            )
            calculator = StatCalculator(config)

            poke1 = create_mock_poke(atc=10, defense=5, initiative=8, hp=30, miss_chance=0.5)
            poke2 = create_mock_poke(atc=5, defense=10, initiative=4, hp=25, miss_chance=0.1)

            stats = calculator.calculate_offspring_stats(poke1, poke2)

            self.assertEqual(stats.atc, 10)
            self.assertEqual(stats.defense, 10)
            self.assertEqual(stats.initiative, 8)
            self.assertEqual(stats.hp, 30)
            self.assertAlmostEqual(stats.miss_chance, 0.1, places=2)


    class TestEggGenerator(unittest.TestCase):
        """Tests for EggGenerator."""

        def setUp(self):
            self.config = BreedingConfig()
            self.generator = EggGenerator(self.config)

        @patch("pokete.classes.pokete_care.breeding.egg_generator.random.choice")
        @patch("pokete.classes.pokete_care.breeding.egg_generator.random.random")
        def test_generate_egg(self, mock_random, mock_choice):
            mock_choice.side_effect = lambda x: x[0]
            mock_random.return_value = 1.0

            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                egg = self.generator.generate_egg(poke1, poke2, current_time=100)

            self.assertEqual(egg.parent1_identifier, "steini")
            self.assertEqual(egg.parent2_identifier, "bigstone")
            self.assertEqual(egg.child_identifier, "steini")
            self.assertEqual(egg.created_at, 100)
            self.assertFalse(egg.child_shiny)

        def test_fixed_hatch_time(self):
            config = BreedingConfig(_hatch_time_strategy=HatchTimeStrategy.FIXED)
            generator = EggGenerator(config)

            poke1 = create_mock_poke(xp=100)
            poke2 = create_mock_poke(xp=100)

            hatch_time = generator.calculate_hatch_time(poke1, poke2)

            self.assertEqual(hatch_time, config.base_hatch_time)

        def test_level_based_hatch_time(self):
            config = BreedingConfig(
                _hatch_time_strategy=HatchTimeStrategy.LEVEL_BASED,
                _base_hatch_time=100,
                _level_hatch_time_multiplier=10.0,
            )
            generator = EggGenerator(config)

            poke1 = create_mock_poke(xp=100)
            poke2 = create_mock_poke(xp=100)

            hatch_time = generator.calculate_hatch_time(poke1, poke2)

            self.assertGreater(hatch_time, config.base_hatch_time)

        def test_egg_serialization(self):
            egg = EggPokete(
                parent1_identifier="steini",
                parent2_identifier="bigstone",
                child_identifier="steini",
                child_xp=0,
                child_hp=25,
                child_attacks=["tackle", "politure"],
                child_shiny=False,
                child_nature={"nature": "normal", "grade": 1},
                base_atc=3,
                base_defense=4,
                base_initiative=5,
                created_at=100,
                hatch_time=300,
            )

            egg_dict = egg.dict()
            restored_egg = EggPokete.from_dict(egg_dict)

            self.assertEqual(restored_egg.parent1_identifier, egg.parent1_identifier)
            self.assertEqual(restored_egg.child_identifier, egg.child_identifier)
            self.assertEqual(restored_egg.hatch_time, egg.hatch_time)

        def test_egg_ready_to_hatch(self):
            egg = EggPokete(
                parent1_identifier="steini",
                parent2_identifier="bigstone",
                child_identifier="steini",
                child_xp=0,
                child_hp=25,
                child_attacks=["tackle"],
                child_shiny=False,
                child_nature={"nature": "normal", "grade": 1},
                base_atc=3,
                base_defense=4,
                base_initiative=5,
                created_at=100,
                hatch_time=300,
            )

            self.assertFalse(egg.is_ready_to_hatch(200))
            self.assertTrue(egg.is_ready_to_hatch(400))
            self.assertTrue(egg.is_ready_to_hatch(500))


    class TestBreedingPair(unittest.TestCase):
        """Tests for BreedingPair."""

        def test_create_empty_pair(self):
            pair = BreedingPair.create_empty()

            self.assertIsNone(pair.parent1)
            self.assertIsNone(pair.parent2)
            self.assertFalse(pair.is_complete())
            self.assertFalse(pair.is_ready)

        def test_complete_pair(self):
            poke1 = create_mock_poke(identifier="steini")
            poke2 = create_mock_poke(identifier="bigstone")

            pair = BreedingPair(
                parent1=poke1,
                parent2=poke2,
                start_time=100,
                hatch_time=300,
                egg=None,
                is_ready=False,
            )

            self.assertTrue(pair.is_complete())

        def test_remaining_time_calculation(self):
            egg = EggPokete(
                parent1_identifier="steini",
                parent2_identifier="bigstone",
                child_identifier="steini",
                child_xp=0,
                child_hp=25,
                child_attacks=["tackle"],
                child_shiny=False,
                child_nature={"nature": "normal", "grade": 1},
                base_atc=3,
                base_defense=4,
                base_initiative=5,
                created_at=100,
                hatch_time=300,
            )

            pair = BreedingPair(
                parent1=create_mock_poke(),
                parent2=create_mock_poke(),
                start_time=100,
                hatch_time=300,
                egg=egg,
                is_ready=False,
            )

            self.assertEqual(pair.get_remaining_time(200), 200)
            self.assertEqual(pair.get_remaining_time(400), 0)
            self.assertEqual(pair.get_remaining_time(500), 0)


    class TestBreedingNotificationService(unittest.TestCase):
        """Tests for BreedingNotificationService."""

        def setUp(self):
            self.service = BreedingNotificationService()

        def test_register_and_dispatch_handler(self):
            received_events = []

            def handler(event):
                received_events.append(event)

            self.service.register_handler(handler)

            with patch.object(self.service, "_show_notification"):
                self.service.notify_breeding_started("Steini", "Bigstone", 300)

            self.assertEqual(len(received_events), 1)
            self.assertEqual(
                received_events[0].event_type, BreedingEventType.BREEDING_STARTED
            )

        def test_unregister_handler(self):
            received_events = []

            def handler(event):
                received_events.append(event)

            self.service.register_handler(handler)
            self.service.unregister_handler(handler)

            with patch.object(self.service, "_show_notification"):
                self.service.notify_breeding_started("Steini", "Bigstone", 300)

            self.assertEqual(len(received_events), 0)


    class TestBreedingManager(unittest.TestCase):
        """Tests for BreedingManager."""

        def setUp(self):
            self.config = BreedingConfig()
            self.mock_notification_service = Mock(spec=BreedingNotificationService)
            self.manager = BreedingManager(
                config=self.config,
                notification_service=self.mock_notification_service,
            )

        def test_initial_state(self):
            self.assertFalse(self.manager.has_active_breeding)
            self.assertIsNone(self.manager.active_breeding_pair)
            self.assertEqual(self.manager.pending_eggs_count, 0)
            self.assertEqual(self.manager.collected_eggs_count, 0)

        def test_start_breeding_compatible_poketes(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                result = self.manager.start_breeding(poke1, poke2, current_time=100)

            self.assertTrue(result)
            self.assertTrue(self.manager.has_active_breeding)
            self.mock_notification_service.notify_breeding_started.assert_called_once()

        def test_start_breeding_incompatible_poketes(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone"])
            poke2 = create_mock_poke(identifier="rosi", types=["plant"])

            result = self.manager.start_breeding(poke1, poke2, current_time=100)

            self.assertFalse(result)
            self.assertFalse(self.manager.has_active_breeding)
            self.mock_notification_service.notify_incompatible_pair.assert_called_once()

        def test_cannot_start_breeding_when_already_breeding(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])
            poke3 = create_mock_poke(identifier="poundi", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)
                result = self.manager.start_breeding(poke1, poke3, current_time=100)

            self.assertFalse(result)

        def test_update_marks_egg_ready(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)

            self.manager.update(current_time=150)
            self.assertFalse(self.manager.is_egg_ready(150))

            self.manager.update(current_time=1000)
            self.assertTrue(self.manager.is_egg_ready(1000))
            self.mock_notification_service.notify_egg_ready.assert_called_once()

        def test_collect_egg(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)

            self.manager.update(current_time=1000)

            with patch(
                "pokete.classes.pokete_care.breeding.breeding_manager.Poke"
            ) as mock_poke_cls:
                mock_hatched_poke = Mock()
                mock_hatched_poke.name = "Steini"
                mock_poke_cls.return_value = mock_hatched_poke

                with patch(
                    "pokete.classes.pokete_care.breeding.breeding_manager.Stats"
                ) as mock_stats_cls:
                    mock_stats = Mock()
                    mock_stats_cls.return_value = mock_stats

                    poke = self.manager.collect_egg(current_time=1000)

            self.assertIsNotNone(poke)
            self.assertEqual(self.manager.collected_eggs_count, 1)
            self.assertFalse(self.manager.has_active_breeding)
            self.mock_notification_service.notify_egg_collected.assert_called_once()

        def test_cancel_breeding(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)

            parent1, parent2 = self.manager.cancel_breeding()

            self.assertIsNotNone(parent1)
            self.assertIsNotNone(parent2)
            self.assertFalse(self.manager.has_active_breeding)
            self.mock_notification_service.notify_breeding_cancelled.assert_called_once()

        def test_get_breeding_status_no_breeding(self):
            status = self.manager.get_breeding_status(current_time=100)

            self.assertFalse(status["active"])
            self.assertIsNone(status["parent1"])
            self.assertIsNone(status["parent2"])
            self.assertEqual(status["remaining_time"], 0)
            self.assertFalse(status["is_ready"])

        def test_get_breeding_status_active_breeding(self):
            poke1 = create_mock_poke(identifier="steini", name="Steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", name="Bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)

            status = self.manager.get_breeding_status(current_time=200)

            self.assertTrue(status["active"])
            self.assertEqual(status["parent1"], "Steini")
            self.assertEqual(status["parent2"], "Bigstone")
            self.assertGreater(status["remaining_time"], 0)
            self.assertFalse(status["is_ready"])

        def test_serialization_no_active_breeding(self):
            state = self.manager.dict()

            self.assertIsNone(state["active_breeding_pair"])
            self.assertEqual(state["pending_eggs"], [])
            self.assertEqual(state["collected_eggs_count"], 0)

        def test_serialization_with_active_breeding(self):
            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                self.manager.start_breeding(poke1, poke2, current_time=100)

            state = self.manager.dict()

            self.assertIsNotNone(state["active_breeding_pair"])
            self.assertIn("parent1", state["active_breeding_pair"])
            self.assertIn("parent2", state["active_breeding_pair"])
            self.assertIn("egg", state["active_breeding_pair"])

        def test_deserialization(self):
            state = {
                "active_breeding_pair": None,
                "pending_eggs": [],
                "collected_eggs_count": 5,
            }

            new_manager = BreedingManager()
            new_manager.from_dict(state)

            self.assertFalse(new_manager.has_active_breeding)
            self.assertEqual(new_manager.collected_eggs_count, 5)


    class TestBreedingIntegration(unittest.TestCase):
        """Integration tests for the breeding system."""

        def test_full_breeding_cycle(self):
            config = BreedingConfig(_base_hatch_time=100)
            manager = BreedingManager(config=config)

            poke1 = create_mock_poke(identifier="steini", types=["stone", "normal"])
            poke2 = create_mock_poke(identifier="bigstone", types=["stone", "normal"])

            with patch(
                "pokete.classes.pokete_care.breeding.egg_generator.PokeNature"
            ) as mock_nature_cls:
                mock_nature = Mock()
                mock_nature.dict.return_value = {"nature": "normal", "grade": 1}
                mock_nature_cls.random.return_value = mock_nature

                result = manager.start_breeding(poke1, poke2, current_time=0)
                self.assertTrue(result)

            manager.update(current_time=50)
            self.assertFalse(manager.is_egg_ready(50))

            manager.update(current_time=500)
            self.assertTrue(manager.is_egg_ready(500))

            with patch(
                "pokete.classes.pokete_care.breeding.breeding_manager.Poke"
            ) as mock_poke_cls:
                mock_hatched_poke = Mock()
                mock_hatched_poke.name = "Steini"
                mock_poke_cls.return_value = mock_hatched_poke

                with patch(
                    "pokete.classes.pokete_care.breeding.breeding_manager.Stats"
                ) as mock_stats_cls:
                    mock_stats = Mock()
                    mock_stats_cls.return_value = mock_stats

                    new_poke = manager.collect_egg(current_time=500)

            self.assertIsNotNone(new_poke)
            self.assertEqual(manager.collected_eggs_count, 1)
            self.assertFalse(manager.has_active_breeding)

else:
    class TestBreedingSkipped(unittest.TestCase):
        """Tests skipped due to Python version requirements."""

        def test_skip_message(self):
            self.skipTest("Breeding tests require Python 3.12+")


if __name__ == "__main__":
    unittest.main()
