"""Dungeon map classes that integrate with the existing map system."""

from typing import Optional
import scrap_engine as se

from pokete.base.game_map import GameMap
from pokete.base.periodic_event_manager import PeriodicEvent
from pokete.classes.asset_service.resources import PokeArgs
from pokete.classes.weather import Weather

from .generator import CaveGenerator, FloorConfig, GeneratedFloor


class DungeonFloor(GameMap):
    """A single floor in a procedurally generated dungeon."""

    def __init__(
        self,
        floor_data: GeneratedFloor,
        dungeon_name: str,
        floor_number: int,
        total_floors: int,
    ):
        self.floor_data = floor_data
        self.dungeon_name = dungeon_name
        self.floor_number = floor_number
        self.total_floors = total_floors

        config = floor_data.config
        super().__init__(
            height=config.height,
            width=config.width,
            name=f"{dungeon_name}_floor_{floor_number}"
        )

        self.song = "02 Underclocked (underunderclocked mix).mp3"
        self.pretty_name = f"{dungeon_name.replace('_', ' ').title()} - Floor {floor_number}/{total_floors}"
        self.trainers = []
        self.registry = {}
        self.weather = None

        self.poke_args = PokeArgs(
            pokes=config.available_poketes,
            minlvl=config.min_enemy_level,
            maxlvl=config.max_enemy_level
        )
        self.w_poke_args = None

        self._extra_actions: list[PeriodicEvent] = []
        self.is_boss_floor = config.is_boss_floor
        self.encounter_rate = config.encounter_rate

        self._render_floor()

    def _render_floor(self) -> None:
        """Render the floor layout to the map."""
        grid = self.floor_data.grid
        wall_text = self._create_wall_text(grid)
        wall_obj = se.Text(wall_text, ignore=" ", state="float")
        wall_obj.add(self, 0, 0)
        self.register_obj("walls", wall_obj)

    def _create_wall_text(self, grid: list[list[str]]) -> str:
        """Create the wall text representation."""
        lines = []
        for row in grid:
            line = ""
            for cell in row:
                if cell == "#":
                    line += "#"
                else:
                    line += " "
            lines.append(line)
        return "\n".join(lines)

    def get_entry_position(self) -> tuple[int, int]:
        """Get the entry position for this floor."""
        room = self.floor_data.entry_room
        return (room.rect.center_x, room.rect.center_y)

    def get_exit_position(self) -> Optional[tuple[int, int]]:
        """Get the exit position for this floor."""
        room = self.floor_data.exit_room
        if room:
            return (room.rect.center_x, room.rect.center_y)
        return None

    def get_boss_position(self) -> Optional[tuple[int, int]]:
        """Get the boss room position."""
        room = self.floor_data.boss_room
        if room:
            return (room.rect.center_x, room.rect.center_y)
        return None

    def register_obj(self, name: str, obj) -> None:
        """Register an object in the floor's registry."""
        self.registry[name] = obj

    def get_obj(self, name: str):
        """Get an object from the registry."""
        return self.registry.get(name, None)

    def extra_actions(self) -> list[PeriodicEvent]:
        """Get extra actions for this floor."""
        return self._extra_actions


class DungeonMap:
    """Manager for a multi-floor dungeon."""

    def __init__(
        self,
        name: str,
        seed: int,
        total_floors: int = 5,
        base_width: int = 60,
        base_height: int = 40,
        base_min_level: int = 100,
        base_max_level: int = 150,
        available_poketes: Optional[list[str]] = None,
    ):
        self.name = name
        self.seed = seed
        self.total_floors = total_floors

        self.generator = CaveGenerator(seed)
        self.floor_configs = self.generator.create_dungeon_config(
            total_floors=total_floors,
            base_width=base_width,
            base_height=base_height,
            base_min_level=base_min_level,
            base_max_level=base_max_level,
            available_poketes=available_poketes,
        )

        self.floors: dict[int, DungeonFloor] = {}
        self.generated_data: dict[int, GeneratedFloor] = {}
        self._generate_all_floors()

    def _generate_all_floors(self) -> None:
        """Generate all floor data."""
        for config in self.floor_configs:
            floor_data = self.generator.generate_floor(config)
            self.generated_data[config.floor_number] = floor_data

    def get_floor(self, floor_number: int) -> Optional[DungeonFloor]:
        """Get or create a dungeon floor."""
        if floor_number < 1 or floor_number > self.total_floors:
            return None

        if floor_number not in self.floors:
            floor_data = self.generated_data.get(floor_number)
            if floor_data is None:
                return None

            self.floors[floor_number] = DungeonFloor(
                floor_data=floor_data,
                dungeon_name=self.name,
                floor_number=floor_number,
                total_floors=self.total_floors,
            )

        return self.floors[floor_number]

    def get_all_floor_maps(self) -> dict[str, DungeonFloor]:
        """Get all floor maps keyed by their name."""
        result = {}
        for floor_num in range(1, self.total_floors + 1):
            floor = self.get_floor(floor_num)
            if floor:
                result[floor.name] = floor
        return result

    @property
    def entry_map(self) -> Optional[DungeonFloor]:
        """Get the entry floor."""
        return self.get_floor(1)

    @property
    def boss_floor(self) -> Optional[DungeonFloor]:
        """Get the boss floor."""
        return self.get_floor(self.total_floors)
