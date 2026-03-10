"""Cave map classes that integrate with the existing map system."""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import random

import scrap_engine as se

from pokete.base.color import Color
from pokete.base.game_map import GameMap
from pokete.classes.classes import PlayMap
from pokete.classes.landscape import HighGrass, Meadow, Poketeball, MapInteract

from .generator import CaveGenerator, CaveConfig, FloorLayout, SpecialRoomData
from .bsp import RoomType
from .boss_provider import BossProvider

if TYPE_CHECKING:
    from pokete.base.context import Context
    from pokete.classes.fight import Provider
    from pokete.classes.poke import Poke


class CaveTile(se.Object):
    """A tile in the cave that can be a wall or floor."""

    def __init__(self, char: str, walkable: bool = True):
        state = "float" if walkable else "solid"
        super().__init__(char, state=state)
        self.walkable = walkable


class CaveHighGrass(se.Object, MapInteract):
    """Encounter zone in the cave."""

    def __init__(self, poke_args: dict, char: str = ";"):
        super().__init__(Color.green + char + Color.reset, state="float")
        self.arg_proto = type('PokeArgs', (), poke_args)()

    def action(self, ob):
        """Trigger random encounter."""
        from pokete.classes.fight import Fight, NatureProvider
        from pokete.classes.poke import Poke
        from pokete.classes.general import check_walk_back
        from pokete.base.change import change_ctx

        pokes = self.arg_proto.pokes
        if random.randint(0, 8) == 0:
            Fight()(
                self.ctx,
                [
                    self.ctx.figure,
                    NatureProvider(
                        Poke.wild(
                            random.choice(pokes),
                            random.randint(
                                self.arg_proto.minlvl,
                                self.arg_proto.maxlvl
                            ),
                        )
                    ),
                ],
            )
            change_ctx(self.ctx, self.ctx.overview)
            check_walk_back(self.ctx)


class CaveItem(se.Object, MapInteract):
    """An item pickup in the cave."""

    def __init__(self, name: str, item_name: str):
        super().__init__(
            Color.thicc + Color.red + "o" + Color.reset, state="float"
        )
        self.name = name
        self.item_name = item_name

    def action(self, ob):
        """Pick up the item."""
        from pokete.base.input_loops import ask_ok
        from pokete.classes.asset_service.service import asset_service
        from pokete.classes import movemap as mvp

        item = asset_service.get_base_assets().items.get(self.item_name)
        pretty_name = item.pretty_name if item else self.item_name

        self.ctx.figure.give_item(self.item_name, 1)
        self.remove()
        mvp.movemap.full_show()
        ask_ok(self.ctx, f"You found a {pretty_name}!")
        self.ctx.figure.used_npcs.append(self.name)


class CaveDoor(se.Object):
    """Door to transition between cave floors or exit."""

    def __init__(self, target_floor: int, target_map: Optional[str] = None,
                 is_exit: bool = False):
        char = ">" if not is_exit else "<"
        super().__init__(Color.thicc + Color.yellow + char + Color.reset, state="float")
        self.target_floor = target_floor
        self.target_map = target_map
        self.is_exit = is_exit
        self.floor_manager: Optional[CaveFloorManager] = None

    def action(self, ob):
        """Transition to target floor or exit."""
        from pokete.classes import game

        if self.floor_manager is None:
            return

        if self.is_exit:
            if self.target_map:
                from pokete.classes import ob_maps as obmp
                ob.remove()
                target = obmp.ob_maps.get(self.target_map)
                if target:
                    ob.add(target, target.width // 2, target.height // 2)
                    ob.oldmap = ob.map
                    raise game.MapChangeException(target)
        else:
            next_map = self.floor_manager.get_floor_map(self.target_floor)
            if next_map:
                ob.remove()
                entry = next_map.entry_pos
                ob.add(next_map, entry[0], entry[1])
                ob.oldmap = ob.map
                raise game.MapChangeException(next_map)


class TreasureRoomTrigger(se.Object, MapInteract):
    """Trigger for treasure room - gives valuable items."""

    def __init__(self, name: str, items: list[str]):
        super().__init__(Color.thicc + Color.yellow + "$" + Color.reset, state="float")
        self.name = name
        self.items = items
        self.looted = False

    def action(self, ob):
        """Loot the treasure."""
        if self.looted:
            return

        from pokete.base.input_loops import ask_ok
        from pokete.classes.asset_service.service import asset_service
        from pokete.classes import movemap as mvp

        self.looted = True
        self.rechar(Color.white + "." + Color.reset)

        item_names = []
        for item_name in self.items:
            self.ctx.figure.give_item(item_name, 1)
            item = asset_service.get_base_assets().items.get(item_name)
            item_names.append(item.pretty_name if item else item_name)

        mvp.movemap.full_show()
        ask_ok(self.ctx, f"You found treasure: {', '.join(item_names)}!")
        self.ctx.figure.used_npcs.append(self.name)


class HealingRoomTrigger(se.Object, MapInteract):
    """Trigger for healing room - heals the player's Poketes."""

    def __init__(self, name: str, heal_percent: float = 0.5):
        super().__init__(Color.thicc + Color.green + "+" + Color.reset, state="float")
        self.name = name
        self.heal_percent = heal_percent
        self.used = False

    def action(self, ob):
        """Heal the player's Poketes."""
        if self.used:
            return

        from pokete.base.input_loops import ask_ok, ask_bool
        from pokete.classes import movemap as mvp

        if not ask_bool(
            self.ctx,
            f"A healing spring! Restore {int(self.heal_percent * 100)}% HP to all Poketes?"
        ):
            return

        self.used = True
        self.rechar(Color.white + "~" + Color.reset)

        healed_count = 0
        for poke in self.ctx.figure.pokes[:6]:
            if hasattr(poke, 'hp') and hasattr(poke, 'full_hp'):
                if poke.hp < poke.full_hp:
                    heal_amount = int(poke.full_hp * self.heal_percent)
                    poke.hp = min(poke.hp + heal_amount, poke.full_hp)
                    if hasattr(poke, 'text_hp'):
                        poke.text_hp.rechar(f"HP:{poke.hp}")
                    if hasattr(poke, 'hp_bar'):
                        poke.hp_bar.make(poke.hp)
                    healed_count += 1

        mvp.movemap.full_show()
        if healed_count > 0:
            ask_ok(self.ctx, f"Your Poketes feel refreshed! ({healed_count} healed)")
        else:
            ask_ok(self.ctx, "Your Poketes are already at full health!")

        self.ctx.figure.used_npcs.append(self.name)


class TrapRoomTrigger(se.Object, MapInteract):
    """Trigger for trap room - damages the player's active Pokete."""

    def __init__(self, name: str, damage_percent: float = 0.25):
        super().__init__(Color.thicc + Color.red + "!" + Color.reset, state="float")
        self.name = name
        self.damage_percent = damage_percent
        self.triggered = False

    def action(self, ob):
        """Trigger the trap."""
        if self.triggered:
            return

        from pokete.base.input_loops import ask_ok
        from pokete.classes import movemap as mvp

        self.triggered = True
        self.rechar(Color.white + "x" + Color.reset)

        pokes = [p for p in self.ctx.figure.pokes[:6]
                 if hasattr(p, 'hp') and p.hp > 0]

        if pokes:
            target = random.choice(pokes)
            damage = max(1, int(target.full_hp * self.damage_percent))
            target.hp = max(1, target.hp - damage)

            if hasattr(target, 'text_hp'):
                target.text_hp.rechar(f"HP:{target.hp}")
            if hasattr(target, 'hp_bar'):
                target.hp_bar.make(target.hp)

            mvp.movemap.full_show()
            ask_ok(
                self.ctx,
                f"It's a trap! {target.name} took {damage} damage!"
            )
        else:
            mvp.movemap.full_show()
            ask_ok(self.ctx, "You triggered a trap, but escaped unharmed!")

        self.ctx.figure.used_npcs.append(self.name)


class BossTrigger(se.Object, MapInteract):
    """Trigger for the boss fight."""

    def __init__(self, boss_pokes: list[str], min_level: int, max_level: int,
                 boss_name: str = "Cave Guardian"):
        super().__init__(Color.thicc + Color.red + "B" + Color.reset, state="float")
        self.boss_pokes = boss_pokes
        self.min_level = min_level
        self.max_level = max_level
        self.boss_name = boss_name
        self.defeated = False

    def action(self, ob):
        """Trigger boss fight."""
        if self.defeated:
            return

        from pokete.classes.fight import Fight
        from pokete.classes.poke import Poke
        from pokete.base.change import change_ctx
        from pokete.classes.general import check_walk_back
        from pokete.classes import movemap as mvp
        from pokete.base.input_loops import ask_ok

        boss_poke_name = random.choice(self.boss_pokes)
        boss_level = random.randint(self.min_level, self.max_level)

        pokes = [Poke.wild(boss_poke_name, boss_level)]
        boss = BossProvider(pokes, self.boss_name)

        mvp.movemap.text(
            self.ctx,
            ob.x, ob.y,
            ["You've reached the depths of the cave!",
             "A powerful guardian blocks your path!"]
        )

        winner = Fight()(self.ctx, [self.ctx.figure, boss])

        if winner == self.ctx.figure:
            self.defeated = True
            self.rechar(Color.thicc + Color.green + "V" + Color.reset)
            ask_ok(self.ctx, "You defeated the Cave Boss! The dungeon is cleared!")
        else:
            ask_ok(self.ctx, "The boss was too powerful...")

        change_ctx(self.ctx, self.ctx.overview)
        check_walk_back(self.ctx)


class CaveMap(PlayMap):
    """A procedurally generated cave floor map."""

    def __init__(self, layout: FloorLayout, config: CaveConfig,
                 floor_manager: "CaveFloorManager"):
        name = f"cave_floor_{layout.floor_num}"
        pretty_name = f"Cave Floor {layout.floor_num + 1}"

        if layout.is_boss_floor:
            pretty_name = f"Cave Depths (Boss)"

        poke_args = {
            "pokes": config.boss_pokes if layout.is_boss_floor else config.pokes,
            "minlvl": layout.min_level,
            "maxlvl": layout.max_level
        }

        super().__init__(
            height=layout.height,
            width=layout.width,
            name=name,
            pretty_name=pretty_name,
            poke_args=type('PokeArgs', (), poke_args)(),
            song="08 Ascending.mp3"
        )

        self.layout = layout
        self.config = config
        self.floor_manager = floor_manager
        self.entry_pos = layout.entry_pos
        self.exit_pos = layout.exit_pos
        self.boss_pos = layout.boss_pos

        self._build_map()

    def _build_map(self):
        """Build the map from the layout grid."""
        grid = self.layout.grid

        wall_chars = ['#', '█', '▓', '▒']

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == '#':
                    wall = CaveTile(
                        Color.white + random.choice(wall_chars) + Color.reset,
                        walkable=False
                    )
                    wall.add(self, x, y)

        for x, y in self.layout.encounter_positions:
            if (x, y) not in [self.entry_pos, self.exit_pos, self.boss_pos]:
                grass = CaveHighGrass({
                    "pokes": self.config.pokes,
                    "minlvl": self.layout.min_level,
                    "maxlvl": self.layout.max_level
                })
                grass.add(self, x, y)

        for i, (x, y, item_name) in enumerate(self.layout.item_positions):
            item = CaveItem(f"cave_{self.layout.floor_num}_item_{i}", item_name)
            item.add(self, x, y)
            self.register_obj(f"item_{i}", item)

        self._build_special_rooms()

        if self.exit_pos and not self.layout.is_boss_floor:
            door = CaveDoor(self.layout.floor_num + 1)
            door.floor_manager = self.floor_manager
            door.add(self, self.exit_pos[0], self.exit_pos[1])
            self.register_obj("exit_door", door)

        if self.layout.floor_num > 0:
            entry_door = CaveDoor(
                self.layout.floor_num - 1,
                is_exit=(self.layout.floor_num == 0)
            )
            entry_door.floor_manager = self.floor_manager
            entry_pos = self.entry_pos
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = entry_pos[0] + dx, entry_pos[1] + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.layout.grid[ny][nx] == '.':
                        entry_door.add(self, nx, ny)
                        self.register_obj("entry_door", entry_door)
                        break

        if self.boss_pos and self.layout.is_boss_floor:
            boss = BossTrigger(
                self.config.boss_pokes,
                self.layout.min_level,
                int(self.layout.max_level * self.config.boss_level_multiplier),
                boss_name="Cave Guardian"
            )
            boss.add(self, self.boss_pos[0], self.boss_pos[1])
            self.register_obj("boss", boss)

    def _build_special_rooms(self):
        """Build special room triggers."""
        for i, sr in enumerate(self.layout.special_rooms):
            x, y = sr.position
            name = f"cave_{self.layout.floor_num}_special_{i}"

            if sr.room_type == RoomType.TREASURE:
                trigger = TreasureRoomTrigger(name, sr.items)
                trigger.add(self, x, y)
                self.register_obj(f"treasure_{i}", trigger)

            elif sr.room_type == RoomType.HEALING:
                trigger = HealingRoomTrigger(name, self.config.healing_percent)
                trigger.add(self, x, y)
                self.register_obj(f"healing_{i}", trigger)

            elif sr.room_type == RoomType.TRAP:
                trigger = TrapRoomTrigger(name, self.config.trap_damage_percent)
                trigger.add(self, x, y)
                self.register_obj(f"trap_{i}", trigger)


class CaveFloorManager:
    """Singleton manager for multiple cave floors as a complete dungeon.

    Auto-registers generated maps to the game's ob_maps registry.
    """

    _instance: Optional["CaveFloorManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[CaveConfig] = None,
                 entrance_map: Optional[str] = None):
        if self._initialized:
            return

        self.config = config or CaveConfig()
        self.entrance_map = entrance_map
        self.generator: Optional[CaveGenerator] = None
        self.floor_maps: dict[int, CaveMap] = {}
        self._generated = False
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "CaveFloorManager":
        """Get the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing or new game)."""
        cls._instance = None

    def generate(self, seed: Optional[int] = None) -> "CaveFloorManager":
        """Generate all floors of the dungeon and register to ob_maps."""
        if seed is not None:
            self.config.seed = seed

        self.generator = CaveGenerator(self.config)
        self.generator.generate()

        self.floor_maps = {}
        for floor in self.generator.floors:
            cave_map = CaveMap(floor, self.config, self)
            self.floor_maps[floor.floor_num] = cave_map

        self._generated = True

        self._auto_register_maps()

        return self

    def _auto_register_maps(self):
        """Automatically register maps to the game's ob_maps."""
        try:
            from pokete.classes import ob_maps as obmp
            if hasattr(obmp, 'ob_maps') and obmp.ob_maps is not None:
                for floor_num, cave_map in self.floor_maps.items():
                    obmp.ob_maps[cave_map.name] = cave_map
        except ImportError:
            pass

    def get_floor_map(self, floor_num: int) -> Optional[CaveMap]:
        """Get the map for a specific floor."""
        return self.floor_maps.get(floor_num)

    def get_entry_map(self) -> Optional[CaveMap]:
        """Get the first floor map (entry point)."""
        return self.get_floor_map(0)

    @property
    def num_floors(self) -> int:
        return len(self.floor_maps)

    @property
    def seed(self) -> Optional[int]:
        return self.generator.seed if self.generator else None

    def get_save_data(self) -> dict:
        """Get data for saving."""
        return {
            "seed": self.seed,
            "entrance_map": self.entrance_map,
            "config": {
                "width": self.config.width,
                "height": self.config.height,
                "num_floors": self.config.num_floors,
                "base_level": self.config.base_level,
                "level_increment": self.config.level_increment,
                "treasure_chance": self.config.treasure_chance,
                "healing_chance": self.config.healing_chance,
                "trap_chance": self.config.trap_chance,
            }
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "CaveFloorManager":
        """Recreate manager from saved data."""
        cls.reset_instance()

        config = CaveConfig(
            seed=data.get("seed"),
            **data.get("config", {})
        )
        manager = cls(config, data.get("entrance_map"))
        manager.generate()
        return manager

    def register_maps(self, ob_maps: dict):
        """Manually register all floor maps to a map registry."""
        for floor_num, cave_map in self.floor_maps.items():
            ob_maps[cave_map.name] = cave_map


cave_floor_manager: CaveFloorManager = CaveFloorManager.get_instance()
