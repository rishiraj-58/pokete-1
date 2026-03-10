"""Tests for cave map integration.

Note: These tests require the full pokete environment due to map dependencies.
Run with: python -m unittest tests.pokete.cave_generator.test_cave_map
"""
import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

try:
    from pokete.classes.cave_generator.generator import CaveGenerator, CaveConfig
    from pokete.classes.cave_generator.cave_map import (
        CaveFloorManager, CaveMap, CaveDoor, CaveTile
    )
    CAVE_MAP_AVAILABLE = True
except (ImportError, TypeError) as e:
    CAVE_MAP_AVAILABLE = False
    print(f"Skipping cave_map tests due to import issues: {e}")


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveFloorManagerTest(unittest.TestCase):
    def test_generate_creates_floors(self):
        manager = CaveFloorManager(CaveConfig(num_floors=5, seed=42))
        manager.generate()

        self.assertEqual(manager.num_floors, 5)

    def test_generate_with_seed(self):
        manager = CaveFloorManager()
        manager.generate(seed=12345)

        self.assertEqual(manager.seed, 12345)

    def test_deterministic_generation(self):
        manager1 = CaveFloorManager()
        manager2 = CaveFloorManager()

        manager1.generate(seed=54321)
        manager2.generate(seed=54321)

        for i in range(manager1.num_floors):
            map1 = manager1.get_floor_map(i)
            map2 = manager2.get_floor_map(i)
            self.assertEqual(map1.entry_pos, map2.entry_pos)

    def test_get_floor_map(self):
        manager = CaveFloorManager(CaveConfig(num_floors=3, seed=42))
        manager.generate()

        floor_map = manager.get_floor_map(1)
        self.assertIsNotNone(floor_map)
        self.assertEqual(floor_map.layout.floor_num, 1)

    def test_get_floor_map_invalid(self):
        manager = CaveFloorManager(CaveConfig(num_floors=3, seed=42))
        manager.generate()

        self.assertIsNone(manager.get_floor_map(10))

    def test_get_entry_map(self):
        manager = CaveFloorManager(CaveConfig(seed=42))
        manager.generate()

        entry = manager.get_entry_map()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.layout.floor_num, 0)

    def test_save_data(self):
        manager = CaveFloorManager(
            CaveConfig(width=80, height=40, num_floors=7, seed=99999),
            entrance_map="playmap_1"
        )
        manager.generate()

        data = manager.get_save_data()

        self.assertEqual(data["seed"], 99999)
        self.assertEqual(data["entrance_map"], "playmap_1")
        self.assertEqual(data["config"]["num_floors"], 7)

    def test_from_save_data(self):
        original = CaveFloorManager(CaveConfig(seed=11111, num_floors=4))
        original.generate()
        data = original.get_save_data()

        restored = CaveFloorManager.from_save_data(data)

        self.assertEqual(restored.num_floors, original.num_floors)
        self.assertEqual(restored.seed, original.seed)

    def test_register_maps(self):
        manager = CaveFloorManager(CaveConfig(num_floors=3, seed=42))
        manager.generate()

        ob_maps = {}
        manager.register_maps(ob_maps)

        self.assertEqual(len(ob_maps), 3)
        for floor_map in manager.floor_maps.values():
            self.assertIn(floor_map.name, ob_maps)


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveMapTest(unittest.TestCase):
    def setUp(self):
        self.manager = CaveFloorManager(CaveConfig(seed=42))
        self.manager.generate()
        self.floor_map = self.manager.get_floor_map(0)

    def test_map_has_entry_pos(self):
        self.assertIsNotNone(self.floor_map.entry_pos)

    def test_map_name_format(self):
        self.assertTrue(self.floor_map.name.startswith("cave_floor_"))

    def test_map_pretty_name(self):
        self.assertIn("Cave", self.floor_map.pretty_name)

    def test_boss_map_pretty_name(self):
        boss_map = self.manager.get_floor_map(self.manager.num_floors - 1)
        self.assertIn("Boss", boss_map.pretty_name)

    def test_map_dimensions(self):
        self.assertEqual(self.floor_map.height, 30)
        self.assertEqual(self.floor_map.width, 60)

    def test_map_has_poke_args(self):
        self.assertIsNotNone(self.floor_map.poke_args)
        self.assertGreater(self.floor_map.poke_args.minlvl, 0)


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveDoorTest(unittest.TestCase):
    def test_door_creation(self):
        door = CaveDoor(target_floor=1)
        self.assertEqual(door.target_floor, 1)
        self.assertFalse(door.is_exit)

    def test_exit_door_creation(self):
        door = CaveDoor(target_floor=0, target_map="playmap_1", is_exit=True)
        self.assertTrue(door.is_exit)
        self.assertEqual(door.target_map, "playmap_1")


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveTileTest(unittest.TestCase):
    def test_walkable_tile(self):
        tile = CaveTile(".", walkable=True)
        self.assertTrue(tile.walkable)
        self.assertEqual(tile.state, "float")

    def test_wall_tile(self):
        tile = CaveTile("#", walkable=False)
        self.assertFalse(tile.walkable)
        self.assertEqual(tile.state, "solid")


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveFloorConnectivityTest(unittest.TestCase):
    """Integration tests for floor connectivity."""

    def test_floors_linked_correctly(self):
        manager = CaveFloorManager(CaveConfig(num_floors=5, seed=42))
        manager.generate()

        for i in range(manager.num_floors - 1):
            floor_map = manager.get_floor_map(i)
            exit_door = floor_map.get_obj("exit_door")

            if exit_door:
                self.assertEqual(exit_door.target_floor, i + 1)

    def test_all_floors_have_valid_entry(self):
        for seed in range(20):
            manager = CaveFloorManager(CaveConfig(seed=seed))
            manager.generate()

            for i in range(manager.num_floors):
                floor_map = manager.get_floor_map(i)
                entry = floor_map.entry_pos
                self.assertIsNotNone(
                    entry,
                    f"Seed {seed} floor {i} missing entry"
                )
                x, y = entry
                self.assertGreaterEqual(x, 0)
                self.assertLess(x, floor_map.width)
                self.assertGreaterEqual(y, 0)
                self.assertLess(y, floor_map.height)


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveMapItemTest(unittest.TestCase):
    """Tests for item placement in cave maps."""

    def test_items_registered(self):
        manager = CaveFloorManager(CaveConfig(
            items_per_floor_min=2,
            items_per_floor_max=2,
            seed=42
        ))
        manager.generate()

        floor_map = manager.get_floor_map(0)

        item_count = 0
        for key in floor_map.registry:
            if key.startswith("item_"):
                item_count += 1

        self.assertGreater(item_count, 0)


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveMapBossTest(unittest.TestCase):
    """Tests for boss floor configuration."""

    def test_boss_floor_has_boss_registered(self):
        manager = CaveFloorManager(CaveConfig(seed=42))
        manager.generate()

        boss_floor = manager.get_floor_map(manager.num_floors - 1)
        boss_obj = boss_floor.get_obj("boss")

        self.assertIsNotNone(boss_obj)

    def test_non_boss_floors_no_boss(self):
        manager = CaveFloorManager(CaveConfig(num_floors=5, seed=42))
        manager.generate()

        for i in range(manager.num_floors - 1):
            floor_map = manager.get_floor_map(i)
            boss_obj = floor_map.get_obj("boss")
            self.assertIsNone(boss_obj)


@unittest.skipUnless(CAVE_MAP_AVAILABLE, "Requires Python 3.12+ for full imports")
class CaveMapStressTest(unittest.TestCase):
    """Stress tests for cave map generation."""

    def test_many_seeds_generate_valid_maps(self):
        for seed in range(100):
            manager = CaveFloorManager(CaveConfig(seed=seed))
            try:
                manager.generate()
                self.assertEqual(manager.num_floors, 5)
            except Exception as e:
                self.fail(f"Seed {seed} failed: {e}")

    def test_various_configurations(self):
        configs = [
            CaveConfig(num_floors=3, width=40, height=20, seed=42),
            CaveConfig(num_floors=7, width=80, height=40, seed=42),
            CaveConfig(num_floors=10, width=100, height=50, seed=42),
        ]

        for config in configs:
            manager = CaveFloorManager(config)
            manager.generate()
            self.assertEqual(manager.num_floors, config.num_floors)

    def test_floor_entry_exit_different(self):
        """Entry and exit should be in different positions."""
        for seed in range(50):
            manager = CaveFloorManager(CaveConfig(seed=seed))
            manager.generate()

            for i in range(manager.num_floors - 1):
                floor = manager.generator.floors[i]
                self.assertNotEqual(
                    floor.entry_pos,
                    floor.exit_pos,
                    f"Seed {seed} floor {i}: entry equals exit"
                )


if __name__ == "__main__":
    unittest.main()
