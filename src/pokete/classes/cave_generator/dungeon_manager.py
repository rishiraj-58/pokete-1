"""Dungeon manager for handling dungeon state and persistence."""

from typing import Optional
import random
import hashlib

import scrap_engine as se

from pokete.base.change import change_ctx
from pokete.base.context import Context
from pokete.base.input_loops import ask_ok
from pokete.classes import movemap as mvp
from pokete.classes import game
from pokete.classes import ob_maps as obmp
from pokete.classes.fight import Fight

from .dungeon_map import DungeonMap, DungeonFloor
from .doors import FloorExitDoor, FloorEntryDoor, DungeonExitDoor
from .dungeon_encounters import DungeonEncounterArea, DungeonItemPickup
from .boss_provider import BossProvider


class DungeonManager:
    """Manages dungeon instances and their state."""

    DEFAULT_POKETES = [
        "steini", "bato", "lilstone", "gobost", "rollator",
        "bigstone", "bator"
    ]

    def __init__(self):
        self.dungeons: dict[str, DungeonMap] = {}
        self.active_dungeon: Optional[str] = None
        self.dungeon_seeds: dict[str, int] = {}
        self.entrance_maps: dict[str, tuple[str, int, int]] = {}

    def create_dungeon(
        self,
        name: str,
        seed: Optional[int] = None,
        total_floors: int = 5,
        base_width: int = 60,
        base_height: int = 40,
        base_min_level: int = 100,
        base_max_level: int = 150,
        available_poketes: Optional[list[str]] = None,
        entrance_map: Optional[str] = None,
        entrance_x: int = 0,
        entrance_y: int = 0,
    ) -> DungeonMap:
        """Create a new dungeon instance."""
        if seed is None:
            if name in self.dungeon_seeds:
                seed = self.dungeon_seeds[name]
            else:
                seed = self._generate_seed(name)
                self.dungeon_seeds[name] = seed

        if available_poketes is None:
            available_poketes = self.DEFAULT_POKETES

        dungeon = DungeonMap(
            name=name,
            seed=seed,
            total_floors=total_floors,
            base_width=base_width,
            base_height=base_height,
            base_min_level=base_min_level,
            base_max_level=base_max_level,
            available_poketes=available_poketes,
        )

        self.dungeons[name] = dungeon

        if entrance_map:
            self.entrance_maps[name] = (entrance_map, entrance_x, entrance_y)

        self._setup_floor_connections(dungeon)
        return dungeon

    def _generate_seed(self, name: str) -> int:
        """Generate a deterministic seed from dungeon name."""
        hash_bytes = hashlib.sha256(name.encode()).digest()
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def _setup_floor_connections(self, dungeon: DungeonMap) -> None:
        """Set up door connections between floors."""
        entrance_info = self.entrance_maps.get(dungeon.name)

        for floor_num in range(1, dungeon.total_floors + 1):
            floor = dungeon.get_floor(floor_num)
            if floor is None:
                continue

            floor_data = dungeon.generated_data[floor_num]

            if floor_num == 1 and entrance_info:
                entry_pos = floor.get_entry_position()
                exit_door = DungeonExitDoor(
                    exit_map_name=entrance_info[0],
                    exit_x=entrance_info[1],
                    exit_y=entrance_info[2],
                )
                exit_door.add(floor, entry_pos[0] - 1, entry_pos[1])
                floor.register_obj("dungeon_exit", exit_door)

            if floor_num > 1:
                prev_floor = dungeon.get_floor(floor_num - 1)
                if prev_floor:
                    prev_exit = prev_floor.get_exit_position()
                    if prev_exit:
                        entry_pos = floor.get_entry_position()
                        back_door = FloorEntryDoor(
                            previous_map_name=prev_floor.name,
                            exit_x=prev_exit[0],
                            exit_y=prev_exit[1] + 1,
                            dungeon_manager=self,
                        )
                        back_door.add(floor, entry_pos[0], entry_pos[1] - 1)
                        floor.register_obj("back_door", back_door)

            if floor_num < dungeon.total_floors:
                next_floor = dungeon.get_floor(floor_num + 1)
                if next_floor:
                    exit_pos = floor.get_exit_position()
                    if exit_pos:
                        next_entry = next_floor.get_entry_position()
                        forward_door = FloorExitDoor(
                            next_floor_map_name=next_floor.name,
                            entry_x=next_entry[0],
                            entry_y=next_entry[1] + 1,
                            dungeon_manager=self,
                        )
                        forward_door.add(floor, exit_pos[0], exit_pos[1])
                        floor.register_obj("forward_door", forward_door)

            self._place_encounters(floor, floor_data)
            self._place_items(floor, floor_data, dungeon.name)

            if floor.is_boss_floor:
                self._setup_boss_room(floor, dungeon)

    def _place_encounters(
        self, floor: DungeonFloor, floor_data
    ) -> None:
        """Place encounter areas on the floor."""
        for x, y in floor_data.encounter_positions:
            encounter = DungeonEncounterArea(
                poke_args=floor.poke_args,
                encounter_rate=floor.encounter_rate,
            )
            encounter.add(floor, x, y)

    def _place_items(
        self, floor: DungeonFloor, floor_data, dungeon_name: str
    ) -> None:
        """Place item pickups on the floor."""
        for idx, (x, y) in enumerate(floor_data.item_positions):
            pickup_id = f"{dungeon_name}.floor_{floor.floor_number}.item_{idx}"
            item = DungeonItemPickup(
                pickup_id=pickup_id,
                floor_number=floor.floor_number,
            )
            item.add(floor, x, y)
            floor.register_obj(f"item_{idx}", item)

    def _setup_boss_room(
        self, floor: DungeonFloor, dungeon: DungeonMap
    ) -> None:
        """Set up the boss room with a boss trigger."""
        boss_pos = floor.get_boss_position()
        if boss_pos:
            boss_trigger = BossTrigger(
                dungeon_name=dungeon.name,
                floor_number=floor.floor_number,
                base_level=floor.poke_args.maxlvl,
            )
            boss_trigger.add(floor, boss_pos[0], boss_pos[1])
            floor.register_obj("boss_trigger", boss_trigger)

    def get_dungeon(self, name: str) -> Optional[DungeonMap]:
        """Get a dungeon by name."""
        return self.dungeons.get(name)

    def get_map(self, map_name: str) -> Optional[DungeonFloor]:
        """Get a floor map by its full name."""
        for dungeon in self.dungeons.values():
            floor_maps = dungeon.get_all_floor_maps()
            if map_name in floor_maps:
                return floor_maps[map_name]

        if map_name in obmp.ob_maps:
            return obmp.ob_maps[map_name]

        return None

    def enter_dungeon(
        self, ctx: Context, dungeon_name: str
    ) -> None:
        """Enter a dungeon from the overworld."""
        dungeon = self.get_dungeon(dungeon_name)
        if dungeon is None:
            return

        self.active_dungeon = dungeon_name
        entry_floor = dungeon.entry_map

        if entry_floor is None:
            return

        entry_pos = entry_floor.get_entry_position()

        figure = ctx.figure
        figure.remove()
        figure.add(entry_floor, entry_pos[0], entry_pos[1] + 1)
        figure.oldmap = figure.map

        raise game.MapChangeException(entry_floor)

    def reset_dungeon(self, name: str) -> None:
        """Reset a dungeon with a new seed."""
        if name not in self.dungeons:
            return

        old_dungeon = self.dungeons[name]
        entrance_info = self.entrance_maps.get(name)

        new_seed = random.randint(0, 2**31 - 1)
        self.dungeon_seeds[name] = new_seed

        self.create_dungeon(
            name=name,
            seed=new_seed,
            total_floors=old_dungeon.total_floors,
            entrance_map=entrance_info[0] if entrance_info else None,
            entrance_x=entrance_info[1] if entrance_info else 0,
            entrance_y=entrance_info[2] if entrance_info else 0,
        )

    def save_state(self) -> dict:
        """Save dungeon state for persistence."""
        return {
            "dungeon_seeds": self.dungeon_seeds.copy(),
            "entrance_maps": {
                k: list(v) for k, v in self.entrance_maps.items()
            },
        }

    def load_state(self, state: dict) -> None:
        """Load dungeon state from save data."""
        self.dungeon_seeds = state.get("dungeon_seeds", {})
        self.entrance_maps = {
            k: tuple(v) for k, v in state.get("entrance_maps", {}).items()
        }


class BossTrigger(se.Object):
    """Trigger that starts the boss fight."""

    def __init__(
        self,
        dungeon_name: str,
        floor_number: int,
        base_level: int,
    ):
        super().__init__("B", state="float")
        self.dungeon_name = dungeon_name
        self.floor_number = floor_number
        self.base_level = base_level
        self.defeated = False

    def action(self, ob) -> None:
        """Start the boss fight."""
        if self.defeated:
            return

        from pokete.classes.landscape import MapInteract

        ctx = MapInteract.ctx
        boss_name = f"{self.dungeon_name.replace('_', ' ').title()} Guardian"

        ask_ok(ctx, f"You've reached the final floor!\n{boss_name} blocks your path!")

        boss = BossProvider(
            boss_name=boss_name,
            floor_number=self.floor_number,
            base_level=self.base_level,
        )

        winner = Fight()(ctx, [ctx.figure, boss])

        if winner == ctx.figure:
            self.defeated = True
            ctx.figure.used_npcs.append(
                f"{self.dungeon_name}.boss"
            )
            self.remove()
            mvp.movemap.full_show()

            reward_money = self.floor_number * 100
            ctx.figure.add_money(reward_money)

            ask_ok(
                ctx,
                f"You defeated the dungeon boss!\n"
                f"You received ${reward_money} as a reward!"
            )

            ctx.figure.give_item("hyperball", 3)
            ctx.figure.give_item("treat", 1)
            ask_ok(
                ctx,
                "You also found 3 Hyperballs and a Treat!"
            )
        else:
            ask_ok(ctx, "You were defeated by the boss...")

        change_ctx(ctx, ctx.overview)


dungeon_manager = DungeonManager()
