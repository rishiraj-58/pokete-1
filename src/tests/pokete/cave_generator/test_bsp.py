"""Tests for the BSP algorithm.

Run with: python -m unittest tests.pokete.cave_generator.test_bsp
Or standalone: python src/tests/pokete/cave_generator/test_bsp.py
"""
import unittest
import random
import sys
import os

# Add src to path for standalone execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from pokete.classes.cave_generator.bsp import Rect, Room, BSPNode, BSPTree


class RectTest(unittest.TestCase):
    def test_center_calculation(self):
        rect = Rect(0, 0, 10, 10)
        self.assertEqual(rect.center, (5, 5))

    def test_center_odd_dimensions(self):
        rect = Rect(0, 0, 11, 11)
        self.assertEqual(rect.center, (5, 5))

    def test_center_with_offset(self):
        rect = Rect(10, 20, 10, 10)
        self.assertEqual(rect.center, (15, 25))

    def test_x2_y2(self):
        rect = Rect(5, 10, 15, 20)
        self.assertEqual(rect.x2, 20)
        self.assertEqual(rect.y2, 30)

    def test_contains_point_inside(self):
        rect = Rect(0, 0, 10, 10)
        self.assertTrue(rect.contains(5, 5))

    def test_contains_point_on_edge(self):
        rect = Rect(0, 0, 10, 10)
        self.assertTrue(rect.contains(0, 0))
        self.assertFalse(rect.contains(10, 10))

    def test_contains_point_outside(self):
        rect = Rect(0, 0, 10, 10)
        self.assertFalse(rect.contains(15, 15))

    def test_intersects_overlapping(self):
        rect1 = Rect(0, 0, 10, 10)
        rect2 = Rect(5, 5, 10, 10)
        self.assertTrue(rect1.intersects(rect2))

    def test_intersects_adjacent(self):
        rect1 = Rect(0, 0, 10, 10)
        rect2 = Rect(10, 0, 10, 10)
        self.assertFalse(rect1.intersects(rect2))

    def test_intersects_separate(self):
        rect1 = Rect(0, 0, 10, 10)
        rect2 = Rect(20, 20, 10, 10)
        self.assertFalse(rect1.intersects(rect2))


class RoomTest(unittest.TestCase):
    def test_room_creation(self):
        rect = Rect(5, 5, 10, 10)
        room = Room(rect)
        self.assertEqual(room.rect, rect)
        self.assertEqual(room.connected_to, [])

    def test_room_connect(self):
        room1 = Room(Rect(0, 0, 10, 10))
        room2 = Room(Rect(20, 0, 10, 10))
        room1.connect(room2)

        self.assertIn(room2, room1.connected_to)
        self.assertIn(room1, room2.connected_to)

    def test_room_connect_no_duplicates(self):
        room1 = Room(Rect(0, 0, 10, 10))
        room2 = Room(Rect(20, 0, 10, 10))
        room1.connect(room2)
        room1.connect(room2)

        self.assertEqual(len(room1.connected_to), 1)
        self.assertEqual(len(room2.connected_to), 1)


class BSPNodeTest(unittest.TestCase):
    def test_node_is_leaf_initially(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        self.assertTrue(node.is_leaf)

    def test_node_not_leaf_after_split(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        rng = random.Random(42)
        node.split(rng)
        self.assertFalse(node.is_leaf)

    def test_split_creates_children(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        rng = random.Random(42)
        result = node.split(rng)

        self.assertTrue(result)
        self.assertIsNotNone(node.left)
        self.assertIsNotNone(node.right)

    def test_split_children_cover_parent(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        rng = random.Random(42)
        node.split(rng)

        left_area = node.left.rect.width * node.left.rect.height
        right_area = node.right.rect.width * node.right.rect.height
        parent_area = node.rect.width * node.rect.height

        self.assertEqual(left_area + right_area, parent_area)

    def test_split_too_small(self):
        node = BSPNode(Rect(0, 0, 10, 10))
        rng = random.Random(42)
        result = node.split(rng, min_size=15)
        self.assertFalse(result)

    def test_get_leaves_single_node(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        leaves = node.get_leaves()
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0], node)

    def test_get_leaves_after_split(self):
        node = BSPNode(Rect(0, 0, 50, 50))
        rng = random.Random(42)
        node.split(rng)
        leaves = node.get_leaves()
        self.assertEqual(len(leaves), 2)

    def test_create_room(self):
        node = BSPNode(Rect(0, 0, 20, 20))
        rng = random.Random(42)
        room = node.create_room(rng, min_room_size=4)

        self.assertIsNotNone(room)
        self.assertIsNotNone(node.room)
        self.assertGreaterEqual(room.rect.width, 4)
        self.assertGreaterEqual(room.rect.height, 4)

    def test_create_room_within_bounds(self):
        node = BSPNode(Rect(10, 10, 20, 20))
        rng = random.Random(42)
        room = node.create_room(rng, min_room_size=4, padding=1)

        self.assertGreaterEqual(room.rect.x, 11)
        self.assertGreaterEqual(room.rect.y, 11)
        self.assertLess(room.rect.x2, 30)
        self.assertLess(room.rect.y2, 30)

    def test_get_room_returns_own_room(self):
        node = BSPNode(Rect(0, 0, 20, 20))
        rng = random.Random(42)
        room = node.create_room(rng)
        self.assertEqual(node.get_room(), room)

    def test_get_room_returns_descendant_room(self):
        root = BSPNode(Rect(0, 0, 50, 50))
        rng = random.Random(42)
        root.split(rng)
        room = root.left.create_room(rng)

        self.assertEqual(root.get_room(), room)


class BSPTreeTest(unittest.TestCase):
    def test_tree_creation(self):
        tree = BSPTree(60, 30, seed=42)
        self.assertEqual(tree.width, 60)
        self.assertEqual(tree.height, 30)
        self.assertEqual(tree.seed, 42)

    def test_generate_creates_rooms(self):
        tree = BSPTree(60, 30, seed=42).generate()
        self.assertGreater(len(tree.rooms), 0)

    def test_generate_creates_corridors(self):
        tree = BSPTree(60, 30, seed=42).generate()
        self.assertGreater(len(tree.corridors), 0)

    def test_deterministic_generation(self):
        tree1 = BSPTree(60, 30, seed=12345).generate()
        tree2 = BSPTree(60, 30, seed=12345).generate()

        self.assertEqual(len(tree1.rooms), len(tree2.rooms))
        for r1, r2 in zip(tree1.rooms, tree2.rooms):
            self.assertEqual(r1.rect.x, r2.rect.x)
            self.assertEqual(r1.rect.y, r2.rect.y)

    def test_different_seeds_different_results(self):
        tree1 = BSPTree(60, 30, seed=111).generate()
        tree2 = BSPTree(60, 30, seed=222).generate()

        rooms_match = all(
            r1.rect.center == r2.rect.center
            for r1, r2 in zip(tree1.rooms, tree2.rooms)
        ) if len(tree1.rooms) == len(tree2.rooms) else False

        self.assertFalse(rooms_match and len(tree1.rooms) == len(tree2.rooms))

    def test_to_grid_dimensions(self):
        tree = BSPTree(60, 30, seed=42).generate()
        grid = tree.to_grid()

        self.assertEqual(len(grid), 30)
        self.assertEqual(len(grid[0]), 60)

    def test_to_grid_has_floors(self):
        tree = BSPTree(60, 30, seed=42).generate()
        grid = tree.to_grid()

        floor_count = sum(row.count('.') for row in grid)
        self.assertGreater(floor_count, 0)

    def test_to_grid_has_walls(self):
        tree = BSPTree(60, 30, seed=42).generate()
        grid = tree.to_grid()

        wall_count = sum(row.count('#') for row in grid)
        self.assertGreater(wall_count, 0)

    def test_rooms_within_grid(self):
        tree = BSPTree(60, 30, seed=42).generate()
        for room in tree.rooms:
            self.assertGreaterEqual(room.rect.x, 0)
            self.assertGreaterEqual(room.rect.y, 0)
            self.assertLessEqual(room.rect.x2, 60)
            self.assertLessEqual(room.rect.y2, 30)

    def test_get_random_floor_position(self):
        tree = BSPTree(60, 30, seed=42).generate()
        pos = tree.get_random_floor_position()

        self.assertIsNotNone(pos)
        x, y = pos
        self.assertGreaterEqual(x, 0)
        self.assertLess(x, 60)
        self.assertGreaterEqual(y, 0)
        self.assertLess(y, 30)

    def test_get_furthest_rooms_returns_two(self):
        tree = BSPTree(60, 30, seed=42).generate()
        room_a, room_b = tree.get_furthest_rooms()

        self.assertIsNotNone(room_a)
        self.assertIsNotNone(room_b)
        self.assertNotEqual(room_a, room_b)

    def test_all_rooms_connected(self):
        tree = BSPTree(60, 30, seed=42).generate()
        self.assertTrue(tree.is_connected())

    def test_no_isolated_rooms(self):
        tree = BSPTree(60, 30, seed=42).generate()
        self.assertFalse(tree.has_isolated_rooms())

    def test_multiple_generations_all_connected(self):
        for seed in range(100):
            tree = BSPTree(60, 30, seed=seed).generate()
            self.assertTrue(
                tree.is_connected(),
                f"Tree with seed {seed} has isolated rooms"
            )


class BSPConnectivityStressTest(unittest.TestCase):
    """Stress tests for BSP connectivity."""

    def test_various_sizes_connected(self):
        sizes = [
            (30, 20),
            (60, 30),
            (100, 50),
            (80, 40),
        ]
        for width, height in sizes:
            for seed in range(10):
                tree = BSPTree(width, height, seed=seed).generate()
                self.assertTrue(
                    tree.is_connected(),
                    f"Tree {width}x{height} seed {seed} not connected"
                )

    def test_various_depths_connected(self):
        for depth in range(2, 6):
            for seed in range(10):
                tree = BSPTree(80, 40, seed=seed).generate(max_depth=depth)
                self.assertTrue(
                    tree.is_connected(),
                    f"Tree depth {depth} seed {seed} not connected"
                )

    def test_minimum_rooms_created(self):
        tree = BSPTree(60, 30, seed=42).generate(max_depth=4)
        self.assertGreaterEqual(len(tree.rooms), 2)

    def test_corridor_endpoints_valid(self):
        tree = BSPTree(60, 30, seed=42).generate()
        for (x1, y1), (x2, y2) in tree.corridors:
            self.assertGreaterEqual(x1, 0)
            self.assertLess(x1, tree.width)
            self.assertGreaterEqual(y1, 0)
            self.assertLess(y1, tree.height)
            self.assertGreaterEqual(x2, 0)
            self.assertLess(x2, tree.width)
            self.assertGreaterEqual(y2, 0)
            self.assertLess(y2, tree.height)


if __name__ == "__main__":
    unittest.main()
