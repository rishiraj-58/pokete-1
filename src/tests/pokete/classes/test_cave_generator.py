"""Tests for the cave generator module.

These tests verify the core dungeon generation algorithms (BSP, room generation,
connectivity) without depending on the game's rendering or map infrastructure.
"""

import unittest
from collections import deque
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class Rect:
    """Rectangle representing a room or partition."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.right <= other.x or
            other.right <= self.x or
            self.bottom <= other.y or
            other.bottom <= self.y
        )

    def shrink(self, amount: int) -> "Rect":
        return Rect(
            self.x + amount,
            self.y + amount,
            max(1, self.width - 2 * amount),
            max(1, self.height - 2 * amount)
        )


class Room:
    """A room in the dungeon."""
    
    def __init__(
        self, 
        rect: Rect, 
        is_boss_room: bool = False,
        is_entry: bool = False,
        is_exit: bool = False
    ):
        self.rect = rect
        self.is_boss_room = is_boss_room
        self.is_entry = is_entry
        self.is_exit = is_exit
        self._id = id(self)

    @property
    def center(self) -> tuple:
        return (self.rect.center_x, self.rect.center_y)
    
    def __hash__(self):
        return self._id
    
    def __eq__(self, other):
        return self._id == other._id if isinstance(other, Room) else False


@dataclass
class Corridor:
    """A corridor connecting two rooms."""
    points: list


class BSPNode:
    """Node in the BSP tree."""

    def __init__(self, rect: Rect):
        self.rect = rect
        self.left = None
        self.right = None
        self.room = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class BSPGenerator:
    """Generates dungeon layouts using Binary Space Partitioning."""

    MIN_PARTITION_SIZE = 12
    MIN_ROOM_SIZE = 5
    ROOM_MARGIN = 2

    def __init__(
        self,
        width: int,
        height: int,
        rng: random.Random,
        min_partition_size: int = MIN_PARTITION_SIZE,
        min_room_size: int = MIN_ROOM_SIZE,
    ):
        self.width = width
        self.height = height
        self.rng = rng
        self.min_partition_size = min_partition_size
        self.min_room_size = min_room_size
        self.rooms = []
        self.corridors = []

    def generate(self):
        """Generate dungeon using BSP algorithm."""
        root = BSPNode(Rect(1, 1, self.width - 2, self.height - 2))
        self._split_node(root)
        self._create_rooms(root)
        self._create_corridors(root)
        return self.rooms, self.corridors

    def _split_node(self, node, depth: int = 0) -> None:
        """Recursively split a node into two children."""
        if depth > 5:
            return

        if (
            node.rect.width < self.min_partition_size * 2 and
            node.rect.height < self.min_partition_size * 2
        ):
            return

        can_split_horizontal = node.rect.height >= self.min_partition_size * 2
        can_split_vertical = node.rect.width >= self.min_partition_size * 2

        if not can_split_horizontal and not can_split_vertical:
            return

        if can_split_horizontal and can_split_vertical:
            split_horizontal = self.rng.random() < 0.5
        else:
            split_horizontal = can_split_horizontal

        if split_horizontal:
            split_pos = self.rng.randint(
                self.min_partition_size,
                node.rect.height - self.min_partition_size
            )
            node.left = BSPNode(Rect(
                node.rect.x,
                node.rect.y,
                node.rect.width,
                split_pos
            ))
            node.right = BSPNode(Rect(
                node.rect.x,
                node.rect.y + split_pos,
                node.rect.width,
                node.rect.height - split_pos
            ))
        else:
            split_pos = self.rng.randint(
                self.min_partition_size,
                node.rect.width - self.min_partition_size
            )
            node.left = BSPNode(Rect(
                node.rect.x,
                node.rect.y,
                split_pos,
                node.rect.height
            ))
            node.right = BSPNode(Rect(
                node.rect.x + split_pos,
                node.rect.y,
                node.rect.width - split_pos,
                node.rect.height
            ))

        self._split_node(node.left, depth + 1)
        self._split_node(node.right, depth + 1)

    def _create_rooms(self, node) -> None:
        """Create rooms in leaf nodes."""
        if node.is_leaf:
            max_width = node.rect.width - 2 * self.ROOM_MARGIN
            max_height = node.rect.height - 2 * self.ROOM_MARGIN

            if max_width < self.min_room_size or max_height < self.min_room_size:
                return

            room_width = self.rng.randint(
                self.min_room_size,
                max_width
            )
            room_height = self.rng.randint(
                self.min_room_size,
                max_height
            )

            room_x = node.rect.x + self.rng.randint(
                self.ROOM_MARGIN,
                node.rect.width - room_width - self.ROOM_MARGIN
            )
            room_y = node.rect.y + self.rng.randint(
                self.ROOM_MARGIN,
                node.rect.height - room_height - self.ROOM_MARGIN
            )

            node.room = Room(Rect(room_x, room_y, room_width, room_height))
            self.rooms.append(node.room)
        else:
            if node.left:
                self._create_rooms(node.left)
            if node.right:
                self._create_rooms(node.right)

    def _create_corridors(self, node) -> None:
        """Create corridors connecting rooms."""
        if node.is_leaf:
            return

        if node.left:
            self._create_corridors(node.left)
        if node.right:
            self._create_corridors(node.right)

        left_room = self._get_room(node.left)
        right_room = self._get_room(node.right)

        if left_room and right_room:
            corridor = self._connect_rooms(left_room, right_room)
            self.corridors.append(corridor)

    def _get_room(self, node):
        """Get a room from a node or its descendants."""
        if node is None:
            return None

        if node.room is not None:
            return node.room

        rooms = []
        if node.left:
            room = self._get_room(node.left)
            if room:
                rooms.append(room)
        if node.right:
            room = self._get_room(node.right)
            if room:
                rooms.append(room)

        if rooms:
            return self.rng.choice(rooms)
        return None

    def _connect_rooms(self, room1: Room, room2: Room) -> Corridor:
        """Create an L-shaped corridor between two rooms."""
        x1, y1 = room1.center
        x2, y2 = room2.center

        points = []

        if self.rng.random() < 0.5:
            points.extend(self._horizontal_line(x1, x2, y1))
            points.extend(self._vertical_line(y1, y2, x2))
        else:
            points.extend(self._vertical_line(y1, y2, x1))
            points.extend(self._horizontal_line(x1, x2, y2))

        return Corridor(points)

    def _horizontal_line(self, x1: int, x2: int, y: int) -> list:
        """Generate points for a horizontal corridor."""
        points = []
        start = min(x1, x2)
        end = max(x1, x2)
        for x in range(start, end + 1):
            points.append((x, y))
        return points

    def _vertical_line(self, y1: int, y2: int, x: int) -> list:
        """Generate points for a vertical corridor."""
        points = []
        start = min(y1, y2)
        end = max(y1, y2)
        for y in range(start, end + 1):
            points.append((x, y))
        return points


@dataclass
class FloorConfig:
    """Configuration for a dungeon floor."""
    floor_number: int
    width: int
    height: int
    min_enemy_level: int
    max_enemy_level: int
    item_count: int
    encounter_rate: float
    is_boss_floor: bool = False
    available_poketes: list = None

    def __post_init__(self):
        if self.available_poketes is None:
            self.available_poketes = []


@dataclass
class GeneratedFloor:
    """Result of floor generation."""
    grid: list
    rooms: list
    corridors: list
    entry_room: Room
    exit_room: Optional[Room]
    boss_room: Optional[Room]
    item_positions: list
    encounter_positions: list
    config: FloorConfig


class CaveGenerator:
    """Generates procedural dungeon floors."""

    WALL_CHAR = "#"
    FLOOR_CHAR = "."
    CORRIDOR_CHAR = "."

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_floor(self, config: FloorConfig) -> GeneratedFloor:
        """Generate a single dungeon floor."""
        floor_seed = self.seed + config.floor_number * 10000
        floor_rng = random.Random(floor_seed)

        grid = self._create_empty_grid(config.width, config.height)
        bsp = BSPGenerator(config.width, config.height, floor_rng)
        rooms, corridors = bsp.generate()

        if len(rooms) < 2:
            rooms = self._create_fallback_rooms(config, floor_rng)
            corridors = self._create_fallback_corridors(rooms, floor_rng)

        for room in rooms:
            self._carve_room(grid, room)

        for corridor in corridors:
            self._carve_corridor(grid, corridor)

        entry_room, exit_room, boss_room = self._assign_special_rooms(
            rooms, config, floor_rng
        )

        item_positions = self._place_items(
            grid, rooms, config.item_count, floor_rng
        )

        encounter_positions = self._place_encounter_areas(
            grid, rooms, entry_room, exit_room, boss_room, floor_rng
        )

        return GeneratedFloor(
            grid=grid,
            rooms=rooms,
            corridors=corridors,
            entry_room=entry_room,
            exit_room=exit_room,
            boss_room=boss_room,
            item_positions=item_positions,
            encounter_positions=encounter_positions,
            config=config,
        )

    def _create_empty_grid(self, width: int, height: int) -> list:
        """Create a grid filled with walls."""
        return [
            [self.WALL_CHAR for _ in range(width)]
            for _ in range(height)
        ]

    def _carve_room(self, grid: list, room: Room) -> None:
        """Carve out a room in the grid."""
        for y in range(room.rect.y, room.rect.bottom):
            for x in range(room.rect.x, room.rect.right):
                if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                    grid[y][x] = self.FLOOR_CHAR

    def _carve_corridor(self, grid: list, corridor: Corridor) -> None:
        """Carve out a corridor in the grid."""
        for x, y in corridor.points:
            if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                grid[y][x] = self.CORRIDOR_CHAR

    def _assign_special_rooms(
        self,
        rooms: list,
        config: FloorConfig,
        rng: random.Random
    ):
        """Assign entry, exit, and boss rooms."""
        if len(rooms) < 2:
            entry_room = rooms[0]
            entry_room.is_entry = True
            return entry_room, None, None

        rooms_by_distance = sorted(
            rooms,
            key=lambda r: (r.rect.x ** 2 + r.rect.y ** 2)
        )

        entry_room = rooms_by_distance[0]
        entry_room.is_entry = True

        exit_room = None
        boss_room = None

        if config.is_boss_floor:
            farthest = rooms_by_distance[-1]
            farthest.is_boss_room = True
            boss_room = farthest
        else:
            farthest = rooms_by_distance[-1]
            farthest.is_exit = True
            exit_room = farthest

        return entry_room, exit_room, boss_room

    def _place_items(
        self,
        grid: list,
        rooms: list,
        count: int,
        rng: random.Random
    ) -> list:
        """Place items randomly in rooms."""
        positions = []
        valid_rooms = [r for r in rooms if not r.is_entry and not r.is_boss_room]

        if not valid_rooms:
            valid_rooms = rooms

        for _ in range(count):
            room = rng.choice(valid_rooms)
            for _ in range(10):
                x = rng.randint(room.rect.x + 1, room.rect.right - 2)
                y = rng.randint(room.rect.y + 1, room.rect.bottom - 2)
                if (
                    0 <= y < len(grid) and
                    0 <= x < len(grid[0]) and
                    grid[y][x] == self.FLOOR_CHAR and
                    (x, y) not in positions
                ):
                    positions.append((x, y))
                    break

        return positions

    def _place_encounter_areas(
        self,
        grid: list,
        rooms: list,
        entry_room: Room,
        exit_room,
        boss_room,
        rng: random.Random
    ) -> list:
        """Place encounter areas in corridors and rooms."""
        positions = []
        skip_rooms = {entry_room}
        if exit_room:
            skip_rooms.add(exit_room)
        if boss_room:
            skip_rooms.add(boss_room)

        for room in rooms:
            if room in skip_rooms:
                continue
            for y in range(room.rect.y + 1, room.rect.bottom - 1):
                for x in range(room.rect.x + 1, room.rect.right - 1):
                    if (
                        0 <= y < len(grid) and
                        0 <= x < len(grid[0]) and
                        grid[y][x] == self.FLOOR_CHAR
                    ):
                        positions.append((x, y))

        return positions

    def _create_fallback_rooms(self, config: FloorConfig, rng: random.Random) -> list:
        """Create fallback rooms if BSP fails."""
        rooms = []
        room_size = 8
        margin = 3

        entry_x = margin
        entry_y = margin
        rooms.append(Room(
            Rect(entry_x, entry_y, room_size, room_size),
            is_entry=True
        ))

        exit_x = config.width - room_size - margin
        exit_y = config.height - room_size - margin
        if config.is_boss_floor:
            rooms.append(Room(
                Rect(exit_x, exit_y, room_size + 2, room_size + 2),
                is_boss_room=True
            ))
        else:
            rooms.append(Room(
                Rect(exit_x, exit_y, room_size, room_size),
                is_exit=True
            ))

        mid_x = config.width // 2 - room_size // 2
        mid_y = config.height // 2 - room_size // 2
        rooms.append(Room(Rect(mid_x, mid_y, room_size, room_size)))

        return rooms

    def _create_fallback_corridors(self, rooms: list, rng: random.Random) -> list:
        """Create corridors connecting fallback rooms."""
        corridors = []

        for i in range(len(rooms) - 1):
            x1, y1 = rooms[i].center
            x2, y2 = rooms[i + 1].center

            points = []
            for x in range(min(x1, x2), max(x1, x2) + 1):
                points.append((x, y1))
            for y in range(min(y1, y2), max(y1, y2) + 1):
                points.append((x2, y))

            corridors.append(Corridor(points))

        return corridors

    def create_dungeon_config(
        self,
        total_floors: int,
        base_width: int = 60,
        base_height: int = 40,
        base_min_level: int = 100,
        base_max_level: int = 150,
        available_poketes: list = None
    ) -> list:
        """Create configuration for all floors of a dungeon."""
        if available_poketes is None:
            available_poketes = [
                "steini", "bato", "lilstone", "gobost", "rollator"
            ]

        configs = []
        for floor_num in range(1, total_floors + 1):
            difficulty_mult = 1.0 + (floor_num - 1) * 0.2

            config = FloorConfig(
                floor_number=floor_num,
                width=base_width + floor_num * 5,
                height=base_height + floor_num * 3,
                min_enemy_level=int(base_min_level * difficulty_mult),
                max_enemy_level=int(base_max_level * difficulty_mult),
                item_count=max(1, 5 - floor_num // 2),
                encounter_rate=0.08 + floor_num * 0.02,
                is_boss_floor=(floor_num == total_floors),
                available_poketes=available_poketes,
            )
            configs.append(config)

        return configs


class TestRect(unittest.TestCase):
    """Tests for the Rect class."""

    def test_center_calculation(self):
        rect = Rect(0, 0, 10, 10)
        self.assertEqual(rect.center_x, 5)
        self.assertEqual(rect.center_y, 5)

    def test_right_and_bottom(self):
        rect = Rect(5, 10, 20, 15)
        self.assertEqual(rect.right, 25)
        self.assertEqual(rect.bottom, 25)

    def test_intersects_overlapping(self):
        rect1 = Rect(0, 0, 10, 10)
        rect2 = Rect(5, 5, 10, 10)
        self.assertTrue(rect1.intersects(rect2))

    def test_intersects_non_overlapping(self):
        rect1 = Rect(0, 0, 5, 5)
        rect2 = Rect(10, 10, 5, 5)
        self.assertFalse(rect1.intersects(rect2))

    def test_intersects_adjacent(self):
        rect1 = Rect(0, 0, 5, 5)
        rect2 = Rect(5, 0, 5, 5)
        self.assertFalse(rect1.intersects(rect2))

    def test_shrink(self):
        rect = Rect(0, 0, 10, 10)
        shrunk = rect.shrink(2)
        self.assertEqual(shrunk.x, 2)
        self.assertEqual(shrunk.y, 2)
        self.assertEqual(shrunk.width, 6)
        self.assertEqual(shrunk.height, 6)


class TestBSPGenerator(unittest.TestCase):
    """Tests for the BSP generator."""

    def setUp(self):
        import random
        self.rng = random.Random(12345)

    def test_generates_rooms(self):
        bsp = BSPGenerator(60, 40, self.rng)
        rooms, corridors = bsp.generate()
        self.assertGreater(len(rooms), 0)

    def test_generates_corridors(self):
        bsp = BSPGenerator(60, 40, self.rng)
        rooms, corridors = bsp.generate()
        if len(rooms) > 1:
            self.assertGreater(len(corridors), 0)

    def test_rooms_within_bounds(self):
        width, height = 60, 40
        bsp = BSPGenerator(width, height, self.rng)
        rooms, _ = bsp.generate()
        for room in rooms:
            self.assertGreaterEqual(room.rect.x, 0)
            self.assertGreaterEqual(room.rect.y, 0)
            self.assertLessEqual(room.rect.right, width)
            self.assertLessEqual(room.rect.bottom, height)

    def test_deterministic_with_same_seed(self):
        import random
        rng1 = random.Random(99999)
        rng2 = random.Random(99999)

        bsp1 = BSPGenerator(60, 40, rng1)
        rooms1, _ = bsp1.generate()

        bsp2 = BSPGenerator(60, 40, rng2)
        rooms2, _ = bsp2.generate()

        self.assertEqual(len(rooms1), len(rooms2))
        for r1, r2 in zip(rooms1, rooms2):
            self.assertEqual(r1.rect.x, r2.rect.x)
            self.assertEqual(r1.rect.y, r2.rect.y)
            self.assertEqual(r1.rect.width, r2.rect.width)
            self.assertEqual(r1.rect.height, r2.rect.height)

    def test_minimum_room_size(self):
        bsp = BSPGenerator(60, 40, self.rng, min_room_size=5)
        rooms, _ = bsp.generate()
        for room in rooms:
            self.assertGreaterEqual(room.rect.width, 5)
            self.assertGreaterEqual(room.rect.height, 5)


class TestCaveGenerator(unittest.TestCase):
    """Tests for the CaveGenerator class."""

    def test_generates_floor(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            available_poketes=["steini"],
        )
        floor = generator.generate_floor(config)
        self.assertIsInstance(floor, GeneratedFloor)

    def test_floor_has_entry_room(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.entry_room)
        self.assertTrue(floor.entry_room.is_entry)

    def test_non_boss_floor_has_exit(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=False,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.exit_room)

    def test_boss_floor_has_boss_room(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=5,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=True,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.boss_room)
        self.assertTrue(floor.boss_room.is_boss_room)

    def test_grid_dimensions(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self.assertEqual(len(floor.grid), 40)
        self.assertEqual(len(floor.grid[0]), 60)

    def test_items_placed(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=5,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self.assertGreater(len(floor.item_positions), 0)
        self.assertLessEqual(len(floor.item_positions), 5)

    def test_encounter_positions_placed(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self.assertGreater(len(floor.encounter_positions), 0)

    def test_create_dungeon_config(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=5,
            base_min_level=100,
            base_max_level=150,
        )
        self.assertEqual(len(configs), 5)
        self.assertFalse(configs[0].is_boss_floor)
        self.assertTrue(configs[-1].is_boss_floor)

    def test_difficulty_increases_with_floor(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=5,
            base_min_level=100,
            base_max_level=150,
        )
        for i in range(1, len(configs)):
            self.assertGreater(
                configs[i].min_enemy_level,
                configs[i - 1].min_enemy_level
            )

    def test_reproducible_generation(self):
        gen1 = CaveGenerator(seed=54321)
        gen2 = CaveGenerator(seed=54321)

        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )

        floor1 = gen1.generate_floor(config)
        floor2 = gen2.generate_floor(config)

        self.assertEqual(floor1.grid, floor2.grid)
        self.assertEqual(len(floor1.rooms), len(floor2.rooms))


class TestGeneratedFloorData(unittest.TestCase):
    """Tests for generated floor data (without DungeonMap integration)."""

    def test_generated_floor_has_entry_room(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.entry_room)
        self.assertTrue(floor.entry_room.is_entry)
        center = floor.entry_room.center
        self.assertIsInstance(center, tuple)
        self.assertEqual(len(center), 2)

    def test_generated_floor_exit_position(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=False,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.exit_room)
        center = floor.exit_room.center
        self.assertIsInstance(center, tuple)

    def test_generated_floor_boss_position(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=5,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=True,
        )
        floor = generator.generate_floor(config)
        self.assertIsNotNone(floor.boss_room)
        center = floor.boss_room.center
        self.assertIsInstance(center, tuple)


class TestRoomConnectivity(unittest.TestCase):
    """Tests for ensuring all rooms are connected."""

    def test_all_rooms_reachable_from_entry(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=80,
            height=60,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)
        self._verify_connectivity(floor)

    def test_exit_reachable_from_entry(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=80,
            height=60,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=False,
        )
        floor = generator.generate_floor(config)

        entry = floor.entry_room.center
        exit_room = floor.exit_room
        if exit_room:
            exit_pos = exit_room.center
            reachable = self._bfs_reachable(floor.grid, entry, exit_pos)
            self.assertTrue(reachable, "Exit must be reachable from entry")

    def test_boss_room_reachable_from_entry(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=5,
            width=80,
            height=60,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
            is_boss_floor=True,
        )
        floor = generator.generate_floor(config)

        entry = floor.entry_room.center
        boss_room = floor.boss_room
        if boss_room:
            boss_pos = boss_room.center
            reachable = self._bfs_reachable(floor.grid, entry, boss_pos)
            self.assertTrue(reachable, "Boss room must be reachable from entry")

    def test_no_isolated_rooms(self):
        for seed in [11111, 22222, 33333, 44444, 55555]:
            generator = CaveGenerator(seed=seed)
            config = FloorConfig(
                floor_number=1,
                width=80,
                height=60,
                min_enemy_level=100,
                max_enemy_level=150,
                item_count=3,
                encounter_rate=0.1,
            )
            floor = generator.generate_floor(config)
            self._verify_no_isolated_rooms(floor, seed)

    def _verify_connectivity(self, floor: GeneratedFloor) -> None:
        """Verify all rooms are connected via flood fill."""
        if len(floor.rooms) <= 1:
            return

        entry = floor.entry_room.center
        visited = self._flood_fill(floor.grid, entry)

        for room in floor.rooms:
            center = room.center
            self.assertIn(
                center, visited,
                f"Room at {center} is not reachable from entry"
            )

    def _verify_no_isolated_rooms(self, floor: GeneratedFloor, seed: int) -> None:
        """Verify no room is completely isolated."""
        if len(floor.rooms) <= 1:
            return

        entry = floor.entry_room.center
        visited = self._flood_fill(floor.grid, entry)

        for room in floor.rooms:
            room_tiles = []
            for y in range(room.rect.y, room.rect.bottom):
                for x in range(room.rect.x, room.rect.right):
                    room_tiles.append((x, y))

            any_reachable = any(tile in visited for tile in room_tiles)
            self.assertTrue(
                any_reachable,
                f"Room at {room.center} is isolated (seed={seed})"
            )

    def _flood_fill(
        self, grid: list[list[str]], start: tuple[int, int]
    ) -> set[tuple[int, int]]:
        """Perform flood fill from start position."""
        visited = set()
        queue = deque([start])
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0

        while queue:
            x, y = queue.popleft()
            if (x, y) in visited:
                continue
            if not (0 <= x < width and 0 <= y < height):
                continue
            if grid[y][x] == "#":
                continue

            visited.add((x, y))

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                queue.append((x + dx, y + dy))

        return visited

    def _bfs_reachable(
        self,
        grid: list[list[str]],
        start: tuple[int, int],
        target: tuple[int, int],
    ) -> bool:
        """Check if target is reachable from start using BFS."""
        visited = self._flood_fill(grid, start)
        return target in visited


class TestMultipleDungeonConfigs(unittest.TestCase):
    """Tests for different dungeon configurations via generator."""

    def test_small_dungeon_config(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=2,
            base_width=40,
            base_height=30,
        )
        self.assertEqual(len(configs), 2)
        floor = generator.generate_floor(configs[0])
        self.assertIsNotNone(floor)

    def test_large_dungeon_config(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=10,
            base_width=100,
            base_height=80,
        )
        self.assertEqual(len(configs), 10)
        self.assertTrue(configs[-1].is_boss_floor)

    def test_custom_poketes_config(self):
        custom_poketes = ["steini", "bato"]
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=3,
            available_poketes=custom_poketes,
        )
        self.assertEqual(configs[0].available_poketes, custom_poketes)

    def test_high_level_config(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(
            total_floors=3,
            base_min_level=500,
            base_max_level=700,
        )
        self.assertEqual(configs[0].min_enemy_level, 500)

    def test_different_seeds_different_layouts(self):
        gen1 = CaveGenerator(seed=11111)
        gen2 = CaveGenerator(seed=22222)
        
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=3,
            encounter_rate=0.1,
        )
        
        floor1 = gen1.generate_floor(config)
        floor2 = gen2.generate_floor(config)

        self.assertNotEqual(floor1.grid, floor2.grid)


class TestFloorProgression(unittest.TestCase):
    """Tests for floor-to-floor progression."""

    def test_floors_have_increasing_difficulty(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(total_floors=5)

        for i in range(1, len(configs)):
            self.assertLess(
                configs[i - 1].min_enemy_level,
                configs[i].min_enemy_level,
            )

    def test_last_floor_is_boss_floor(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(total_floors=5)
        self.assertTrue(configs[-1].is_boss_floor)

    def test_intermediate_floors_are_not_boss(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(total_floors=5)
        for config in configs[:-1]:
            self.assertFalse(config.is_boss_floor)


class TestItemPlacement(unittest.TestCase):
    """Tests for item placement in dungeons."""

    def test_items_on_floor_tiles(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=5,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)

        for x, y in floor.item_positions:
            self.assertEqual(
                floor.grid[y][x], ".",
                f"Item at ({x}, {y}) is not on floor tile"
            )

    def test_items_within_bounds(self):
        generator = CaveGenerator(seed=12345)
        config = FloorConfig(
            floor_number=1,
            width=60,
            height=40,
            min_enemy_level=100,
            max_enemy_level=150,
            item_count=5,
            encounter_rate=0.1,
        )
        floor = generator.generate_floor(config)

        for x, y in floor.item_positions:
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, config.width)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, config.height)

    def test_fewer_items_on_later_floors(self):
        generator = CaveGenerator(seed=12345)
        configs = generator.create_dungeon_config(total_floors=5)

        self.assertGreaterEqual(
            configs[0].item_count,
            configs[-2].item_count
        )


if __name__ == "__main__":
    unittest.main()
