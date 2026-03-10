"""Cave generator using BSP algorithm."""

from dataclasses import dataclass
from typing import Optional
import random

from .bsp import BSPGenerator, Room, Corridor, Rect


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
    available_poketes: list[str] = None

    def __post_init__(self):
        if self.available_poketes is None:
            self.available_poketes = []


@dataclass
class GeneratedFloor:
    """Result of floor generation."""
    grid: list[list[str]]
    rooms: list[Room]
    corridors: list[Corridor]
    entry_room: Room
    exit_room: Optional[Room]
    boss_room: Optional[Room]
    item_positions: list[tuple[int, int]]
    encounter_positions: list[tuple[int, int]]
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

    def _create_empty_grid(
        self, width: int, height: int
    ) -> list[list[str]]:
        """Create a grid filled with walls."""
        return [
            [self.WALL_CHAR for _ in range(width)]
            for _ in range(height)
        ]

    def _carve_room(self, grid: list[list[str]], room: Room) -> None:
        """Carve out a room in the grid."""
        for y in range(room.rect.y, room.rect.bottom):
            for x in range(room.rect.x, room.rect.right):
                if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                    grid[y][x] = self.FLOOR_CHAR

    def _carve_corridor(
        self, grid: list[list[str]], corridor: Corridor
    ) -> None:
        """Carve out a corridor in the grid."""
        for x, y in corridor.points:
            if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                grid[y][x] = self.CORRIDOR_CHAR
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < len(grid) and
                            0 <= nx < len(grid[0]) and
                            grid[ny][nx] == self.WALL_CHAR
                        ):
                            pass

    def _assign_special_rooms(
        self,
        rooms: list[Room],
        config: FloorConfig,
        rng: random.Random
    ) -> tuple[Room, Optional[Room], Optional[Room]]:
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

        exit_room: Optional[Room] = None
        boss_room: Optional[Room] = None

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
        grid: list[list[str]],
        rooms: list[Room],
        count: int,
        rng: random.Random
    ) -> list[tuple[int, int]]:
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
        grid: list[list[str]],
        rooms: list[Room],
        entry_room: Room,
        exit_room: Optional[Room],
        boss_room: Optional[Room],
        rng: random.Random
    ) -> list[tuple[int, int]]:
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

    def _create_fallback_rooms(
        self, config: FloorConfig, rng: random.Random
    ) -> list[Room]:
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

    def _create_fallback_corridors(
        self, rooms: list[Room], rng: random.Random
    ) -> list[Corridor]:
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
        available_poketes: Optional[list[str]] = None
    ) -> list[FloorConfig]:
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
