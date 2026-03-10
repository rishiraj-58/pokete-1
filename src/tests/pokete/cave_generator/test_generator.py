"""Tests for the CaveGenerator.

Run with: python -m unittest tests.pokete.cave_generator.test_generator
Or standalone: python src/tests/pokete/cave_generator/test_generator.py
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from pokete.classes.cave_generator.generator import (
    CaveGenerator, CaveConfig, FloorLayout
)


class CaveConfigTest(unittest.TestCase):
    def test_default_config(self):
        config = CaveConfig()
        self.assertEqual(config.width, 60)
        self.assertEqual(config.height, 30)
        self.assertEqual(config.num_floors, 5)
        self.assertEqual(config.base_level, 100)

    def test_custom_config(self):
        config = CaveConfig(
            width=80,
            height=40,
            num_floors=10,
            seed=12345
        )
        self.assertEqual(config.width, 80)
        self.assertEqual(config.height, 40)
        self.assertEqual(config.num_floors, 10)
        self.assertEqual(config.seed, 12345)

    def test_default_pokes(self):
        config = CaveConfig()
        self.assertIn("steini", config.pokes)
        self.assertIn("bato", config.pokes)

    def test_default_boss_pokes(self):
        config = CaveConfig()
        self.assertIn("bigstone", config.boss_pokes)
        self.assertIn("lindemon", config.boss_pokes)


class FloorLayoutTest(unittest.TestCase):
    def test_floor_dimensions(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        floor = generator.floors[0]
        self.assertEqual(floor.width, 60)
        self.assertEqual(floor.height, 30)

    def test_boss_floor_identified(self):
        config = CaveConfig(num_floors=5, seed=42)
        generator = CaveGenerator(config)
        generator.generate()

        for i, floor in enumerate(generator.floors):
            if i == config.num_floors - 1:
                self.assertTrue(floor.is_boss_floor)
            else:
                self.assertFalse(floor.is_boss_floor)


class CaveGeneratorTest(unittest.TestCase):
    def test_generates_correct_number_of_floors(self):
        config = CaveConfig(num_floors=5, seed=42)
        generator = CaveGenerator(config)
        floors = generator.generate()

        self.assertEqual(len(floors), 5)

    def test_deterministic_generation(self):
        config1 = CaveConfig(seed=12345)
        config2 = CaveConfig(seed=12345)

        gen1 = CaveGenerator(config1)
        gen2 = CaveGenerator(config2)

        gen1.generate()
        gen2.generate()

        for f1, f2 in zip(gen1.floors, gen2.floors):
            self.assertEqual(f1.entry_pos, f2.entry_pos)
            self.assertEqual(f1.exit_pos, f2.exit_pos)
            self.assertEqual(len(f1.rooms), len(f2.rooms))

    def test_different_seeds_different_layouts(self):
        gen1 = CaveGenerator(CaveConfig(seed=111))
        gen2 = CaveGenerator(CaveConfig(seed=222))

        gen1.generate()
        gen2.generate()

        floors_match = all(
            f1.entry_pos == f2.entry_pos
            for f1, f2 in zip(gen1.floors, gen2.floors)
        )
        self.assertFalse(floors_match)

    def test_every_floor_has_entry_position(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for floor in generator.floors:
            self.assertIsNotNone(floor.entry_pos)

    def test_non_boss_floors_have_exit(self):
        config = CaveConfig(num_floors=5, seed=42)
        generator = CaveGenerator(config)
        generator.generate()

        for floor in generator.floors[:-1]:
            self.assertIsNotNone(floor.exit_pos)

    def test_boss_floor_has_boss_position(self):
        config = CaveConfig(num_floors=5, seed=42)
        generator = CaveGenerator(config)
        generator.generate()

        boss_floor = generator.floors[-1]
        self.assertIsNotNone(boss_floor.boss_pos)
        self.assertTrue(boss_floor.is_boss_floor)

    def test_boss_floor_no_exit(self):
        config = CaveConfig(num_floors=5, seed=42)
        generator = CaveGenerator(config)
        generator.generate()

        boss_floor = generator.floors[-1]
        self.assertIsNone(boss_floor.exit_pos)

    def test_floor_levels_increase(self):
        config = CaveConfig(
            num_floors=5,
            base_level=100,
            level_increment=50,
            seed=42
        )
        generator = CaveGenerator(config)
        generator.generate()

        prev_min = 0
        for floor in generator.floors:
            self.assertGreater(floor.min_level, prev_min)
            self.assertGreater(floor.max_level, floor.min_level)
            prev_min = floor.min_level

    def test_items_placed_on_floors(self):
        config = CaveConfig(
            items_per_floor_min=1,
            items_per_floor_max=3,
            seed=42
        )
        generator = CaveGenerator(config)
        generator.generate()

        for floor in generator.floors:
            self.assertGreaterEqual(len(floor.item_positions), 1)
            self.assertLessEqual(len(floor.item_positions), 3)

    def test_item_positions_valid(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for floor in generator.floors:
            for x, y, item_name in floor.item_positions:
                self.assertGreaterEqual(x, 0)
                self.assertLess(x, floor.width)
                self.assertGreaterEqual(y, 0)
                self.assertLess(y, floor.height)
                self.assertIsInstance(item_name, str)

    def test_items_not_on_entry_exit(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for floor in generator.floors:
            positions = {(x, y) for x, y, _ in floor.item_positions}
            self.assertNotIn(floor.entry_pos, positions)
            if floor.exit_pos:
                self.assertNotIn(floor.exit_pos, positions)
            if floor.boss_pos:
                self.assertNotIn(floor.boss_pos, positions)

    def test_encounter_positions_created(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for floor in generator.floors:
            self.assertGreater(len(floor.encounter_positions), 0)

    def test_all_floors_connected(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for floor in generator.floors:
            self.assertTrue(floor.bsp.is_connected())

    def test_get_floor_valid_index(self):
        generator = CaveGenerator(CaveConfig(num_floors=5, seed=42))
        generator.generate()

        floor = generator.get_floor(2)
        self.assertIsNotNone(floor)
        self.assertEqual(floor.floor_num, 2)

    def test_get_floor_invalid_index(self):
        generator = CaveGenerator(CaveConfig(num_floors=5, seed=42))
        generator.generate()

        self.assertIsNone(generator.get_floor(10))
        self.assertIsNone(generator.get_floor(-1))

    def test_save_data(self):
        config = CaveConfig(
            width=80,
            height=40,
            num_floors=7,
            seed=12345
        )
        generator = CaveGenerator(config)
        generator.generate()

        save_data = generator.get_save_data()

        self.assertEqual(save_data["seed"], 12345)
        self.assertEqual(save_data["config"]["width"], 80)
        self.assertEqual(save_data["config"]["height"], 40)
        self.assertEqual(save_data["config"]["num_floors"], 7)

    def test_from_save_data(self):
        original = CaveGenerator(CaveConfig(seed=54321, num_floors=3))
        original.generate()
        save_data = original.get_save_data()

        restored = CaveGenerator.from_save_data(save_data)

        self.assertEqual(len(restored.floors), len(original.floors))
        for f1, f2 in zip(original.floors, restored.floors):
            self.assertEqual(f1.entry_pos, f2.entry_pos)
            self.assertEqual(f1.exit_pos, f2.exit_pos)


class CaveGeneratorConnectivityTest(unittest.TestCase):
    """Tests ensuring proper floor connectivity across multiple seeds."""

    def test_all_floors_reachable_various_seeds(self):
        for seed in range(50):
            generator = CaveGenerator(CaveConfig(num_floors=5, seed=seed))
            generator.generate()

            for i, floor in enumerate(generator.floors[:-1]):
                self.assertIsNotNone(
                    floor.exit_pos,
                    f"Seed {seed} floor {i} missing exit"
                )

    def test_boss_always_reachable(self):
        for seed in range(50):
            generator = CaveGenerator(CaveConfig(num_floors=5, seed=seed))
            generator.generate()

            boss_floor = generator.floors[-1]
            self.assertIsNotNone(
                boss_floor.boss_pos,
                f"Seed {seed} boss floor missing boss"
            )

    def test_no_isolated_rooms_any_floor(self):
        for seed in range(50):
            generator = CaveGenerator(CaveConfig(seed=seed))
            generator.generate()

            for i, floor in enumerate(generator.floors):
                self.assertFalse(
                    floor.bsp.has_isolated_rooms(),
                    f"Seed {seed} floor {i} has isolated rooms"
                )


class CaveGeneratorDifficultyTest(unittest.TestCase):
    """Tests for difficulty scaling."""

    def test_boss_floor_higher_levels(self):
        config = CaveConfig(
            num_floors=5,
            base_level=100,
            level_increment=50,
            boss_level_multiplier=1.5,
            seed=42
        )
        generator = CaveGenerator(config)
        generator.generate()

        regular_floor = generator.floors[-2]
        boss_floor = generator.floors[-1]

        self.assertGreater(boss_floor.max_level, regular_floor.max_level)

    def test_deeper_floors_harder(self):
        generator = CaveGenerator(CaveConfig(seed=42))
        generator.generate()

        for i in range(1, len(generator.floors)):
            self.assertGreater(
                generator.floors[i].min_level,
                generator.floors[i-1].min_level
            )


class CaveGeneratorItemTest(unittest.TestCase):
    """Tests for item placement."""

    def test_items_from_configured_pool(self):
        config = CaveConfig(
            item_pool=["test_item1", "test_item2"],
            seed=42
        )
        generator = CaveGenerator(config)
        generator.generate()

        for floor in generator.floors:
            for _, _, item_name in floor.item_positions:
                self.assertIn(item_name, config.item_pool)

    def test_item_count_respects_config(self):
        config = CaveConfig(
            items_per_floor_min=2,
            items_per_floor_max=2,
            seed=42
        )
        generator = CaveGenerator(config)
        generator.generate()

        for floor in generator.floors:
            self.assertEqual(len(floor.item_positions), 2)


if __name__ == "__main__":
    unittest.main()
