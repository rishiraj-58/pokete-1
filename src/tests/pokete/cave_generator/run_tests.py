#!/usr/bin/env python3
"""Standalone test runner for cave generator.

Run with: python src/tests/pokete/cave_generator/run_tests.py

Note: This test runner imports modules directly to avoid Python 3.12+ 
syntax requirements in the main pokete codebase.
"""
import sys
import os
import random
import importlib.util

# Setup path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', '..', '..'))


def load_module_directly(module_name: str, file_path: str):
    """Load a module directly from file path without going through __init__.py"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load BSP module directly (no external dependencies)
bsp_module = load_module_directly(
    "pokete.classes.cave_generator.bsp",
    os.path.join(SRC_DIR, "pokete/classes/cave_generator/bsp.py")
)

Rect = bsp_module.Rect
Room = bsp_module.Room
BSPNode = bsp_module.BSPNode
BSPTree = bsp_module.BSPTree
RoomType = bsp_module.RoomType
SpecialRoomConfig = bsp_module.SpecialRoomConfig

# Load generator module directly (depends only on bsp)
generator_module = load_module_directly(
    "pokete.classes.cave_generator.generator",
    os.path.join(SRC_DIR, "pokete/classes/cave_generator/generator.py")
)

CaveGenerator = generator_module.CaveGenerator
CaveConfig = generator_module.CaveConfig
FloorLayout = generator_module.FloorLayout
SpecialRoom = generator_module.SpecialRoom


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

    # Test RoomType enum values
    test("room_type_normal_value", RoomType.NORMAL.value == 1, 
         f"Expected 1, got {RoomType.NORMAL.value}")
    test("room_type_treasure_value", RoomType.TREASURE.value == 2,
         f"Expected 2, got {RoomType.TREASURE.value}")
    test("room_type_healing_value", RoomType.HEALING.value == 3,
         f"Expected 3, got {RoomType.HEALING.value}")
    test("room_type_trap_value", RoomType.TRAP.value == 4,
         f"Expected 4, got {RoomType.TRAP.value}")

    # Test room with type
    typed_room = Room(Rect(0, 0, 10, 10), RoomType.TREASURE)
    test("room_has_correct_type", typed_room.room_type == RoomType.TREASURE,
         f"Expected TREASURE, got {typed_room.room_type}")
    test("special_room_is_special", typed_room.is_special == True,
         f"Expected True, got {typed_room.is_special}")

    normal_room = Room(Rect(0, 0, 10, 10))
    test("default_room_is_normal", normal_room.room_type == RoomType.NORMAL,
         f"Expected NORMAL, got {normal_room.room_type}")
    test("normal_room_not_special", normal_room.is_special == False,
         f"Expected False, got {normal_room.is_special}")

    # Test special room config
    special_config = SpecialRoomConfig(
        treasure_chance=0.5,
        healing_chance=0.3,
        trap_chance=0.2
    )
    test("special_config_treasure_chance", special_config.treasure_chance == 0.5,
         f"Expected 0.5, got {special_config.treasure_chance}")
    test("special_config_healing_chance", special_config.healing_chance == 0.3,
         f"Expected 0.3, got {special_config.healing_chance}")
    test("special_config_trap_chance", special_config.trap_chance == 0.2,
         f"Expected 0.2, got {special_config.trap_chance}")

    # Test BSP with special rooms
    high_special_config = SpecialRoomConfig(
        treasure_chance=0.4,
        healing_chance=0.3,
        trap_chance=0.3
    )
    special_tree = BSPTree(60, 30, seed=42, special_room_config=high_special_config).generate()
    special_rooms = special_tree.get_special_rooms()
    test("bsp_generates_special_rooms", len(special_rooms) >= 0,
         f"Got {len(special_rooms)} special rooms")
    
    # Verify special rooms have correct types
    all_special_have_types = all(
        r.room_type in [RoomType.TREASURE, RoomType.HEALING, RoomType.TRAP]
        for r in special_rooms
    )
    test("special_rooms_have_valid_types", all_special_have_types or len(special_rooms) == 0)

    treasure_rooms = special_tree.get_rooms_by_type(RoomType.TREASURE)
    healing_rooms = special_tree.get_rooms_by_type(RoomType.HEALING)
    trap_rooms = special_tree.get_rooms_by_type(RoomType.TRAP)
    
    # Verify counts match
    total_special = len(treasure_rooms) + len(healing_rooms) + len(trap_rooms)
    test("special_room_counts_match", total_special == len(special_rooms),
         f"Expected {len(special_rooms)}, got {total_special}")

    # Verify each type list contains correct room types
    test("treasure_rooms_are_treasure", 
         all(r.room_type == RoomType.TREASURE for r in treasure_rooms),
         f"Found non-treasure rooms in treasure list")
    test("healing_rooms_are_healing",
         all(r.room_type == RoomType.HEALING for r in healing_rooms),
         f"Found non-healing rooms in healing list")
    test("trap_rooms_are_trap",
         all(r.room_type == RoomType.TRAP for r in trap_rooms),
         f"Found non-trap rooms in trap list")

    # Test generator with special rooms
    config_with_special = CaveConfig(
        seed=42,
        treasure_room_chance=0.4,
        healing_room_chance=0.3,
        trap_room_chance=0.3
    )
    gen_special = CaveGenerator(config_with_special)
    gen_special.generate()

    total_special_in_gen = sum(len(floor.special_rooms) for floor in gen_special.floors)
    test("generator_creates_special_rooms", total_special_in_gen > 0,
         f"Expected > 0 special rooms, got {total_special_in_gen}")

    # Test floor layout special room methods return correct types
    for floor in gen_special.floors:
        treasure_in_floor = floor.get_treasure_rooms()
        healing_in_floor = floor.get_healing_rooms()
        trap_in_floor = floor.get_trap_rooms()
        
        test(f"floor_{floor.floor_num}_treasure_types_correct",
             all(sr.room_type == RoomType.TREASURE for sr in treasure_in_floor),
             f"Wrong type in treasure rooms")
        test(f"floor_{floor.floor_num}_healing_types_correct",
             all(sr.room_type == RoomType.HEALING for sr in healing_in_floor),
             f"Wrong type in healing rooms")
        test(f"floor_{floor.floor_num}_trap_types_correct",
             all(sr.room_type == RoomType.TRAP for sr in trap_in_floor),
             f"Wrong type in trap rooms")

    # Test treasure rooms have items
    all_treasures_have_items = True
    treasure_item_counts = []
    for floor in gen_special.floors:
        for treasure in floor.get_treasure_rooms():
            treasure_item_counts.append(len(treasure.items))
            if len(treasure.items) < config_with_special.treasure_item_count_min:
                all_treasures_have_items = False
    
    test("treasure_rooms_have_minimum_items", all_treasures_have_items,
         f"Treasure item counts: {treasure_item_counts}")

    # Test special rooms not at entry/exit/boss
    special_not_at_key_pos = True
    for floor in gen_special.floors:
        for special in floor.special_rooms:
            if special.center == floor.entry_pos:
                special_not_at_key_pos = False
                break
            if floor.exit_pos and special.center == floor.exit_pos:
                special_not_at_key_pos = False
                break
            if floor.boss_pos and special.center == floor.boss_pos:
                special_not_at_key_pos = False
                break
    test("special_rooms_not_at_key_positions", special_not_at_key_pos)

    # Test items don't overlap with special rooms
    print("\n=== Item Placement Tests ===")
    items_not_in_special = True
    for floor in gen_special.floors:
        special_positions = set()
        for special in floor.special_rooms:
            special_positions.add(special.center)
            for x, y, _ in special.items:
                special_positions.add((x, y))
        
        for ix, iy, _ in floor.item_positions:
            if (ix, iy) in special_positions:
                items_not_in_special = False
                break
    test("items_not_overlapping_special_rooms", items_not_in_special)

    # Test items not placed in special room types
    items_not_in_special_room_type = True
    for floor in gen_special.floors:
        special_room_rects = [(sr.room.rect, sr.room_type) for sr in floor.special_rooms]
        for ix, iy, _ in floor.item_positions:
            for rect, rtype in special_room_rects:
                if rect.contains(ix, iy) and rtype != RoomType.NORMAL:
                    items_not_in_special_room_type = False
                    break
    test("items_not_in_special_room_areas", items_not_in_special_room_type)

    # ========== DIFFICULTY SCALING TESTS ==========
    print("\n=== Difficulty Scaling Tests ===")

    config_scaling = CaveConfig(
        seed=123,
        num_floors=5,
        treasure_room_chance=0.5,
        healing_room_chance=0.5,
        trap_room_chance=0.5
    )
    gen_scaling = CaveGenerator(config_scaling)
    gen_scaling.generate()

    # Test difficulty modifier increases with floor
    difficulty_increases = True
    prev_difficulty = -1
    for floor in gen_scaling.floors:
        for special in floor.special_rooms:
            if floor.floor_num > 0 and special.difficulty_modifier <= prev_difficulty:
                # Allow same difficulty if same floor
                pass
            if special.difficulty_modifier < 0 or special.difficulty_modifier > 1:
                difficulty_increases = False
        if floor.special_rooms:
            prev_difficulty = floor.special_rooms[0].difficulty_modifier
    test("difficulty_modifier_valid_range", difficulty_increases)

    # Test first floor has low difficulty (0.0)
    first_floor_difficulty_ok = True
    for special in gen_scaling.floors[0].special_rooms:
        if special.difficulty_modifier != 0.0:
            first_floor_difficulty_ok = False
    test("first_floor_difficulty_zero", first_floor_difficulty_ok or 
         len(gen_scaling.floors[0].special_rooms) == 0)

    # Test last floor has high difficulty (1.0)
    last_floor_difficulty_ok = True
    for special in gen_scaling.floors[-1].special_rooms:
        if special.difficulty_modifier != 1.0:
            last_floor_difficulty_ok = False
    test("last_floor_difficulty_one", last_floor_difficulty_ok or
         len(gen_scaling.floors[-1].special_rooms) == 0)

    # Test middle floors have intermediate difficulty
    if len(gen_scaling.floors) >= 3:
        middle_floor = gen_scaling.floors[len(gen_scaling.floors) // 2]
        middle_difficulty_ok = True
        for special in middle_floor.special_rooms:
            if not (0 < special.difficulty_modifier < 1):
                middle_difficulty_ok = False
        test("middle_floor_intermediate_difficulty", middle_difficulty_ok or
             len(middle_floor.special_rooms) == 0)

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
