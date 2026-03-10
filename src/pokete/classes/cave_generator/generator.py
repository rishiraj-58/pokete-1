"""Cave generator using BSP algorithm."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import random

from .bsp import BSPTree, Room, Rect, RoomType, SpecialRoomConfig


@dataclass
class CaveConfig:
    """Configuration for cave generation."""
    width: int = 60
    height: int = 30
    max_depth: int = 4
    min_partition_size: int = 8
    min_room_size: int = 4
    num_floors: int = 5
    base_level: int = 100
    level_increment: int = 50
    items_per_floor_min: int = 1
    items_per_floor_max: int = 3
    encounter_rate: float = 0.15
    boss_level_multiplier: float = 1.5
    seed: Optional[int] = None
    pokes: list[str] = field(default_factory=lambda: [
        "steini", "bato", "lilstone", "gobost", "rato"
    ])
    boss_pokes: list[str] = field(default_factory=lambda: [
        "bigstone", "lindemon", "rollator", "poundi"
    ])
    item_pool: list[str] = field(default_factory=lambda: [
        "poketeball", "superball", "hyperball",
        "healing_potion", "super_potion", "treat"
    ])
    item_weights: list[float] = field(default_factory=lambda: [
        10.0, 3.0, 1.0, 5.0, 2.0, 0.5
    ])
    treasure_room_items: list[str] = field(default_factory=lambda: [
        "hyperball", "super_potion", "treat", "ap_potion"
    ])
    treasure_room_item_count: int = 3
    treasure_chance: float = 0.15
    healing_chance: float = 0.10
    trap_chance: float = 0.12
    trap_damage_percent: float = 0.25
    healing_percent: float = 0.5


@dataclass
class SpecialRoomData:
    """Data for a special room."""
    room: Room
    room_type: RoomType
    position: tuple[int, int]
    items: list[str] = field(default_factory=list)


@dataclass
class FloorLayout:
    """Layout information for a single floor."""
    floor_num: int
    grid: list[list[str]]
    rooms: list[Room]
    entry_pos: tuple[int, int]
    exit_pos: Optional[tuple[int, int]]
    item_positions: list[tuple[int, int, str]]
    encounter_positions: list[tuple[int, int]]
    boss_pos: Optional[tuple[int, int]]
    min_level: int
    max_level: int
    is_boss_floor: bool
    bsp: BSPTree
    special_rooms: list[SpecialRoomData] = field(default_factory=list)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        return len(self.grid)

    def get_special_rooms_by_type(self, room_type: RoomType) -> list[SpecialRoomData]:
        """Get all special rooms of a specific type."""
        return [r for r in self.special_rooms if r.room_type == room_type]


class CaveGenerator:
    """Generates procedural cave dungeons using BSP."""

    def __init__(self, config: Optional[CaveConfig] = None):
        self.config = config or CaveConfig()
        self.seed = self.config.seed if self.config.seed is not None else random.randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)
        self.floors: list[FloorLayout] = []

    def generate(self) -> list[FloorLayout]:
        """Generate all floors of the dungeon."""
        self.floors = []

        for floor_num in range(self.config.num_floors):
            floor = self._generate_floor(floor_num)
            self.floors.append(floor)

        self._validate_connectivity()
        return self.floors

    def _generate_floor(self, floor_num: int) -> FloorLayout:
        """Generate a single floor."""
        is_boss_floor = floor_num == self.config.num_floors - 1
        floor_seed = self.seed + floor_num * 1000

        special_config = SpecialRoomConfig(
            treasure_chance=self.config.treasure_chance,
            healing_chance=self.config.healing_chance,
            trap_chance=self.config.trap_chance,
        )

        bsp = BSPTree(
            self.config.width,
            self.config.height,
            seed=floor_seed,
            special_config=special_config
        ).generate(
            max_depth=self.config.max_depth,
            min_size=self.config.min_partition_size,
            min_room_size=self.config.min_room_size
        )

        grid = bsp.to_grid()

        entry_room, exit_room = bsp.get_furthest_rooms()
        if not entry_room:
            entry_room = bsp.rooms[0] if bsp.rooms else None

        if entry_room:
            entry_room.room_type = RoomType.ENTRY
        if exit_room and exit_room != entry_room:
            exit_room.room_type = RoomType.EXIT if not is_boss_floor else RoomType.BOSS

        entry_pos = self._get_room_position(entry_room, bsp.rng)
        exit_pos = None
        boss_pos = None

        if is_boss_floor:
            boss_pos = self._get_room_position(exit_room, bsp.rng) if exit_room else None
        else:
            exit_pos = self._get_room_position(exit_room, bsp.rng) if exit_room else None

        special_rooms_data = self._create_special_room_data(bsp)

        item_positions = self._place_items(bsp, entry_pos, exit_pos, boss_pos, special_rooms_data)
        encounter_positions = self._place_encounters(bsp, entry_pos, special_rooms_data)

        min_level = self.config.base_level + floor_num * self.config.level_increment
        max_level = min_level + self.config.level_increment

        if is_boss_floor:
            max_level = int(max_level * self.config.boss_level_multiplier)

        return FloorLayout(
            floor_num=floor_num,
            grid=grid,
            rooms=bsp.rooms,
            entry_pos=entry_pos,
            exit_pos=exit_pos,
            item_positions=item_positions,
            encounter_positions=encounter_positions,
            boss_pos=boss_pos,
            min_level=min_level,
            max_level=max_level,
            is_boss_floor=is_boss_floor,
            bsp=bsp,
            special_rooms=special_rooms_data
        )

    def _create_special_room_data(self, bsp: BSPTree) -> list[SpecialRoomData]:
        """Create SpecialRoomData for all special rooms."""
        special_rooms = []

        for room_type in [RoomType.TREASURE, RoomType.HEALING, RoomType.TRAP]:
            for room in bsp.get_rooms_by_type(room_type):
                pos = self._get_room_position(room, bsp.rng)

                items = []
                if room_type == RoomType.TREASURE:
                    items = bsp.rng.choices(
                        self.config.treasure_room_items,
                        k=self.config.treasure_room_item_count
                    )

                special_rooms.append(SpecialRoomData(
                    room=room,
                    room_type=room_type,
                    position=pos,
                    items=items
                ))

        return special_rooms

    def _get_room_position(self, room: Optional[Room], rng: random.Random) -> tuple[int, int]:
        """Get a safe position within a room."""
        if not room:
            return (self.config.width // 2, self.config.height // 2)

        r = room.rect
        x = r.x + r.width // 2
        y = r.y + r.height // 2

        if r.width > 2:
            x = rng.randint(r.x + 1, r.x + r.width - 2)
        if r.height > 2:
            y = rng.randint(r.y + 1, r.y + r.height - 2)

        return (x, y)

    def _place_items(self, bsp: BSPTree, entry_pos: tuple[int, int],
                     exit_pos: Optional[tuple[int, int]],
                     boss_pos: Optional[tuple[int, int]],
                     special_rooms: list[SpecialRoomData]) -> list[tuple[int, int, str]]:
        """Place items randomly in the dungeon."""
        items = []
        excluded = {entry_pos}
        if exit_pos:
            excluded.add(exit_pos)
        if boss_pos:
            excluded.add(boss_pos)

        for sr in special_rooms:
            excluded.add(sr.position)

        special_room_set = {sr.room for sr in special_rooms}

        num_items = bsp.rng.randint(
            self.config.items_per_floor_min,
            self.config.items_per_floor_max
        )

        available_rooms = [
            r for r in bsp.rooms
            if r.rect.width > 2 and r.rect.height > 2
            and r not in special_room_set
            and r.room_type == RoomType.NORMAL
        ]

        for _ in range(num_items):
            if not available_rooms:
                break

            room = bsp.rng.choice(available_rooms)
            r = room.rect

            for _ in range(10):
                x = bsp.rng.randint(r.x + 1, r.x + r.width - 2)
                y = bsp.rng.randint(r.y + 1, r.y + r.height - 2)

                if (x, y) not in excluded:
                    item_name = bsp.rng.choices(
                        self.config.item_pool,
                        weights=self.config.item_weights
                    )[0]
                    items.append((x, y, item_name))
                    excluded.add((x, y))
                    break

        return items

    def _place_encounters(self, bsp: BSPTree,
                          entry_pos: tuple[int, int],
                          special_rooms: list[SpecialRoomData]) -> list[tuple[int, int]]:
        """Place encounter zones (high grass equivalent)."""
        encounters = []
        grid = bsp.to_grid()

        special_rects = [sr.room.rect for sr in special_rooms]

        def in_special_room(x: int, y: int) -> bool:
            return any(rect.contains(x, y) for rect in special_rects)

        for y in range(len(grid)):
            for x in range(len(grid[0])):
                if grid[y][x] == '.' and (x, y) != entry_pos:
                    if not in_special_room(x, y):
                        if bsp.rng.random() < self.config.encounter_rate:
                            encounters.append((x, y))

        return encounters

    def _validate_connectivity(self):
        """Ensure all floors are properly connected."""
        for i, floor in enumerate(self.floors):
            if not floor.bsp.is_connected():
                raise ValueError(f"Floor {i} has isolated rooms")

            if i < len(self.floors) - 1 and floor.exit_pos is None:
                raise ValueError(f"Non-boss floor {i} missing exit")

            if floor.is_boss_floor and floor.boss_pos is None:
                raise ValueError(f"Boss floor {i} missing boss position")

    def get_floor(self, floor_num: int) -> Optional[FloorLayout]:
        """Get a specific floor by number."""
        if 0 <= floor_num < len(self.floors):
            return self.floors[floor_num]
        return None

    def get_save_data(self) -> dict:
        """Get data to save for reproducibility."""
        return {
            "seed": self.seed,
            "config": {
                "width": self.config.width,
                "height": self.config.height,
                "num_floors": self.config.num_floors,
                "base_level": self.config.base_level,
                "level_increment": self.config.level_increment,
            }
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "CaveGenerator":
        """Recreate a generator from saved data."""
        config = CaveConfig(
            seed=data["seed"],
            **data.get("config", {})
        )
        generator = cls(config)
        generator.generate()
        return generator
