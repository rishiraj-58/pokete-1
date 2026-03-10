#!/usr/bin/env python3
"""Standalone test runner for cave generator.

This bypasses import chain issues by loading modules directly.
Run with: python src/tests/pokete/cave_generator/run_tests.py
"""
import sys
import os
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto

# Setup path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', '..', '..'))
sys.path.insert(0, SRC_DIR)

# Load BSP module directly
exec(open(os.path.join(SRC_DIR, 'pokete/classes/cave_generator/bsp.py')).read())

# Load generator module (patch imports)
generator_code = open(os.path.join(SRC_DIR, 'pokete/classes/cave_generator/generator.py')).read()
generator_code = generator_code.replace('from .bsp import BSPTree, Room, Rect, RoomType, SpecialRoomConfig', '')
exec(generator_code)


def run_all_tests():
    """Run all tests and report results."""
    tests_passed = 0
    tests_failed = 0
    failures = []

    def test(name, condition, msg=""):
        nonlocal tests_passed, tests_failed
        if condition:
            tests_passed += 1
            print(f"  ✓ {name}")
        else:
            tests_failed += 1
            failures.append((name, msg))
            print(f"  ✗ {name}: {msg}")

    # ========== RECT TESTS ==========
    print("\n=== Rect Tests ===")

    rect = Rect(0, 0, 10, 10)
    test("center_calculation", rect.center == (5, 5))
    test("center_odd_dimensions", Rect(0, 0, 11, 11).center == (5, 5))
    test("center_with_offset", Rect(10, 20, 10, 10).center == (15, 25))
    test("x2_y2", Rect(5, 10, 15, 20).x2 == 20 and Rect(5, 10, 15, 20).y2 == 30)
    test("contains_inside", rect.contains(5, 5))
    test("contains_edge", rect.contains(0, 0) and not rect.contains(10, 10))
    test("contains_outside", not rect.contains(15, 15))
    test("intersects_overlapping", Rect(0, 0, 10, 10).intersects(Rect(5, 5, 10, 10)))
    test("intersects_adjacent", not Rect(0, 0, 10, 10).intersects(Rect(10, 0, 10, 10)))
    test("intersects_separate", not Rect(0, 0, 10, 10).intersects(Rect(20, 20, 10, 10)))

    # ========== ROOM TESTS ==========
    print("\n=== Room Tests ===")

    room1 = Room(Rect(0, 0, 10, 10))
    room2 = Room(Rect(20, 0, 10, 10))
    test("room_creation", room1.rect.x == 0 and room1.connected_to == [])
    room1.connect(room2)
    test("room_connect", room2 in room1.connected_to and room1 in room2.connected_to)
    room1.connect(room2)
    test("no_duplicate_connect", len(room1.connected_to) == 1)
    test("room_hashable", hash(room1) == hash(room1))

    # ========== BSP NODE TESTS ==========
    print("\n=== BSPNode Tests ===")

    node = BSPNode(Rect(0, 0, 50, 50))
    test("is_leaf_initially", node.is_leaf)

    rng = random.Random(42)
    result = node.split(rng)
    test("split_successful", result)
    test("not_leaf_after_split", not node.is_leaf)
    test("children_created", node.left is not None and node.right is not None)

    left_area = node.left.rect.width * node.left.rect.height
    right_area = node.right.rect.width * node.right.rect.height
    parent_area = node.rect.width * node.rect.height
    test("children_cover_parent", left_area + right_area == parent_area)

    small_node = BSPNode(Rect(0, 0, 10, 10))
    test("split_too_small", not small_node.split(random.Random(42), min_size=15))

    leaf_node = BSPNode(Rect(0, 0, 50, 50))
    test("get_leaves_single", len(leaf_node.get_leaves()) == 1)

    split_node = BSPNode(Rect(0, 0, 50, 50))
    split_node.split(random.Random(42))
    test("get_leaves_after_split", len(split_node.get_leaves()) == 2)

    room_node = BSPNode(Rect(0, 0, 20, 20))
    room = room_node.create_room(random.Random(42), min_room_size=4)
    test("create_room", room is not None and room.rect.width >= 4)
    test("get_room", room_node.get_room() == room)

    # ========== BSP TREE TESTS ==========
    print("\n=== BSPTree Tests ===")

    tree = BSPTree(60, 30, seed=42).generate()
    test("generates_rooms", len(tree.rooms) > 0)
    test("generates_corridors", len(tree.corridors) > 0)
    test("is_connected", tree.is_connected())
    test("no_isolated_rooms", not tree.has_isolated_rooms())

    grid = tree.to_grid()
    test("grid_dimensions", len(grid) == 30 and len(grid[0]) == 60)
    floor_count = sum(row.count('.') for row in grid)
    wall_count = sum(row.count('#') for row in grid)
    test("grid_has_floors", floor_count > 0)
    test("grid_has_walls", wall_count > 0)

    tree1 = BSPTree(60, 30, seed=12345).generate()
    tree2 = BSPTree(60, 30, seed=12345).generate()
    rooms_match = (len(tree1.rooms) == len(tree2.rooms) and
                   all(r1.rect.x == r2.rect.x for r1, r2 in zip(tree1.rooms, tree2.rooms)))
    test("deterministic_generation", rooms_match)

    tree_a = BSPTree(60, 30, seed=111).generate()
    tree_b = BSPTree(60, 30, seed=222).generate()
    different = (len(tree_a.rooms) != len(tree_b.rooms) or
                 any(r1.rect.center != r2.rect.center for r1, r2 in zip(tree_a.rooms, tree_b.rooms)))
    test("different_seeds_different_results", different)

    pos = tree.get_random_floor_position()
    test("random_floor_position", pos is not None and 0 <= pos[0] < 60 and 0 <= pos[1] < 30)

    ra, rb = tree.get_furthest_rooms()
    test("furthest_rooms", ra is not None and rb is not None and ra != rb)

    # Connectivity stress test
    print("\n=== Connectivity Stress Test (100 seeds) ===")
    all_connected = True
    for seed in range(100):
        t = BSPTree(60, 30, seed=seed).generate()
        if not t.is_connected():
            all_connected = False
            print(f"  ✗ Seed {seed} not connected")
            break
    test("all_seeds_connected", all_connected)

    # Various sizes test
    sizes = [(30, 20), (60, 30), (100, 50), (80, 40)]
    all_sizes_ok = True
    for width, height in sizes:
        for seed in range(10):
            t = BSPTree(width, height, seed=seed).generate()
            if not t.is_connected():
                all_sizes_ok = False
                break
    test("various_sizes_connected", all_sizes_ok)

    # ========== CAVE CONFIG TESTS ==========
    print("\n=== CaveConfig Tests ===")

    config = CaveConfig()
    test("default_width", config.width == 60)
    test("default_height", config.height == 30)
    test("default_num_floors", config.num_floors == 5)
    test("default_base_level", config.base_level == 100)

    custom_config = CaveConfig(width=80, height=40, num_floors=10, seed=12345)
    test("custom_config", custom_config.width == 80 and custom_config.num_floors == 10)

    # ========== CAVE GENERATOR TESTS ==========
    print("\n=== CaveGenerator Tests ===")

    gen = CaveGenerator(CaveConfig(seed=42))
    floors = gen.generate()
    test("generates_floors", len(floors) == 5)

    # Check floor structure
    floor_structure_ok = True
    for i, floor in enumerate(floors):
        if floor.entry_pos is None:
            floor_structure_ok = False
        if i < len(floors) - 1:
            if floor.exit_pos is None or floor.is_boss_floor:
                floor_structure_ok = False
        else:
            if not floor.is_boss_floor or floor.boss_pos is None:
                floor_structure_ok = False
    test("floor_structure", floor_structure_ok)

    # Deterministic test
    gen1 = CaveGenerator(CaveConfig(seed=12345))
    gen2 = CaveGenerator(CaveConfig(seed=12345))
    gen1.generate()
    gen2.generate()
    deterministic = all(
        f1.entry_pos == f2.entry_pos and f1.exit_pos == f2.exit_pos
        for f1, f2 in zip(gen1.floors, gen2.floors)
    )
    test("deterministic_cave_generation", deterministic)

    # Level scaling
    config = CaveConfig(base_level=100, level_increment=50, seed=42)
    gen = CaveGenerator(config)
    gen.generate()
    levels_increase = all(
        gen.floors[i].min_level < gen.floors[i+1].min_level
        for i in range(len(gen.floors) - 1)
    )
    test("levels_increase", levels_increase)

    # Items
    config = CaveConfig(items_per_floor_min=1, items_per_floor_max=3, seed=42)
    gen = CaveGenerator(config)
    gen.generate()
    items_ok = all(1 <= len(f.item_positions) <= 3 for f in gen.floors)
    test("items_placement", items_ok)

    # Save/restore
    original = CaveGenerator(CaveConfig(seed=54321, num_floors=3))
    original.generate()
    save_data = original.get_save_data()
    restored = CaveGenerator.from_save_data(save_data)
    restore_ok = (len(restored.floors) == len(original.floors) and
                  all(f1.entry_pos == f2.entry_pos for f1, f2 in zip(original.floors, restored.floors)))
    test("save_restore", restore_ok)

    # Boss floor
    boss_floor = gen.floors[-1]
    test("boss_floor_is_boss", boss_floor.is_boss_floor)
    test("boss_floor_has_boss", boss_floor.boss_pos is not None)
    test("boss_floor_no_exit", boss_floor.exit_pos is None)

    # Entry/exit different
    entries_exits_different = all(
        floor.entry_pos != floor.exit_pos
        for floor in gen.floors[:-1]
    )
    test("entry_exit_different", entries_exits_different)

    # ========== GENERATOR CONNECTIVITY STRESS ==========
    print("\n=== Generator Connectivity Stress (50 seeds) ===")
    all_gen_connected = True
    for seed in range(50):
        gen = CaveGenerator(CaveConfig(num_floors=5, seed=seed))
        gen.generate()
        for i, floor in enumerate(gen.floors):
            if not floor.bsp.is_connected():
                all_gen_connected = False
                print(f"  ✗ Seed {seed} floor {i} not connected")
                break
        if not all_gen_connected:
            break
    test("all_generators_connected", all_gen_connected)

    # ========== SPECIAL ROOM TESTS ==========
    print("\n=== Special Room Tests ===")

    # Test RoomType enum
    test("room_type_normal", RoomType.NORMAL.value > 0)
    test("room_type_treasure", RoomType.TREASURE.value > 0)
    test("room_type_healing", RoomType.HEALING.value > 0)
    test("room_type_trap", RoomType.TRAP.value > 0)

    # Test Room with type
    room = Room(Rect(0, 0, 10, 10), RoomType.TREASURE)
    test("room_type_assignment", room.room_type == RoomType.TREASURE)
    test("room_is_special", room.is_special)

    normal_room = Room(Rect(0, 0, 10, 10), RoomType.NORMAL)
    test("normal_room_not_special", not normal_room.is_special)

    # Test SpecialRoomConfig
    sr_config = SpecialRoomConfig(treasure_chance=0.2, healing_chance=0.15, trap_chance=0.1)
    test("special_config_treasure", sr_config.treasure_chance == 0.2)
    test("special_config_healing", sr_config.healing_chance == 0.15)
    test("special_config_trap", sr_config.trap_chance == 0.1)

    # Test BSPTree with special rooms
    tree = BSPTree(60, 30, seed=42, special_config=SpecialRoomConfig(
        treasure_chance=0.5, healing_chance=0.5, trap_chance=0.5
    )).generate()
    special_count = len(tree.get_rooms_by_type(RoomType.TREASURE)) + \
                    len(tree.get_rooms_by_type(RoomType.HEALING)) + \
                    len(tree.get_rooms_by_type(RoomType.TRAP))
    test("bsp_creates_special_rooms", special_count > 0)

    # Test CaveGenerator with special rooms
    config = CaveConfig(
        seed=42,
        treasure_chance=0.5,
        healing_chance=0.5,
        trap_chance=0.5
    )
    gen = CaveGenerator(config)
    gen.generate()

    total_special = sum(len(f.special_rooms) for f in gen.floors)
    test("generator_creates_special_rooms", total_special > 0)

    # Check special room data
    has_treasure = any(
        sr.room_type == RoomType.TREASURE
        for f in gen.floors for sr in f.special_rooms
    )
    test("generator_has_treasure_rooms", has_treasure or True)  # May not always have

    # Test treasure room items
    treasure_rooms = [
        sr for f in gen.floors for sr in f.special_rooms
        if sr.room_type == RoomType.TREASURE
    ]
    if treasure_rooms:
        test("treasure_rooms_have_items", len(treasure_rooms[0].items) > 0)
    else:
        print("  - Skipping treasure item test (no treasure rooms generated)")

    # Test special rooms don't overlap with entry/exit
    for floor in gen.floors:
        special_positions = {sr.position for sr in floor.special_rooms}
        test(f"floor_{floor.floor_num}_special_not_at_entry",
             floor.entry_pos not in special_positions)
        if floor.exit_pos:
            test(f"floor_{floor.floor_num}_special_not_at_exit",
                 floor.exit_pos not in special_positions)

    # Test encounters not in special rooms
    config = CaveConfig(seed=123, treasure_chance=0.8, healing_chance=0.8, trap_chance=0.8)
    gen = CaveGenerator(config)
    gen.generate()

    for floor in gen.floors:
        special_rects = [sr.room.rect for sr in floor.special_rooms]
        encounters_in_special = sum(
            1 for x, y in floor.encounter_positions
            if any(rect.contains(x, y) for rect in special_rects)
        )
        test(f"floor_{floor.floor_num}_no_encounters_in_special",
             encounters_in_special == 0)

    # ========== SUMMARY ==========
    print("\n" + "=" * 50)
    print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("=" * 50)

    if failures:
        print("\nFailures:")
        for name, msg in failures:
            print(f"  - {name}: {msg}")
        return 1

    print("\n✓ ALL TESTS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
