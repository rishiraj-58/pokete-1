"""Cave map classes that integrate with the existing map system."""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import random

import scrap_engine as se

from pokete.base.color import Color
from pokete.base.game_map import GameMap
from pokete.classes.classes import PlayMap
from pokete.classes.landscape import HighGrass, Meadow, Poketeball, MapInteract

from .generator import CaveGenerator, CaveConfig, FloorLayout, SpecialRoom
from .bsp import RoomType
from .boss_provider import BossProvider, create_boss

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


class TreasureChest(se.Object, MapInteract):
    """A treasure chest with valuable items.
    
    Items quality increases on deeper floors (difficulty_modifier 0->1).
    """

    def __init__(self, name: str, items: list[tuple[int, int, str]], 
                 difficulty_modifier: float = 0.0):
        super().__init__(
            Color.thicc + Color.yellow + "$" + Color.reset, state="float"
        )
        self.name = name
        self.items = items
        self.difficulty_modifier = difficulty_modifier
        self.opened = False

    def action(self, ob):
        """Open the treasure chest."""
        if self.opened:
            return

        from pokete.base.input_loops import ask_ok
        from pokete.classes.asset_service.service import asset_service
        from pokete.classes import movemap as mvp

        self.opened = True
        self.rechar(Color.white + "□" + Color.reset)

        item_names = []
        for _, _, item_name in self.items:
            self.ctx.figure.give_item(item_name, 1)
            item = asset_service.get_base_assets().items.get(item_name)
            item_names.append(item.pretty_name if item else item_name)

        mvp.movemap.full_show()
        ask_ok(self.ctx, f"You found treasure: {', '.join(item_names)}!")
        self.ctx.figure.used_npcs.append(self.name)


class HealingFountain(se.Object, MapInteract):
    """A healing fountain that restores HP.
    
    Healing amount decreases on deeper floors (difficulty_modifier 0->1).
    """

    def __init__(self, name: str, base_heal: float, min_heal: float, 
                 reduction_per_floor: float, difficulty_modifier: float):
        super().__init__(
            Color.thicc + Color.blue + "♥" + Color.reset, state="float"
        )
        self.name = name
        # Calculate actual heal percent based on floor difficulty
        reduction = reduction_per_floor * difficulty_modifier * 5  # Scale by ~5 floors
        self.heal_percent = max(min_heal, base_heal - reduction)
        self.used = False

    def action(self, ob):
        """Use the healing fountain."""
        if self.used:
            from pokete.base.input_loops import ask_ok
            ask_ok(self.ctx, "The fountain has dried up...")
            return

        from pokete.base.input_loops import ask_ok, ask_bool
        from pokete.classes import movemap as mvp

        heal_display = int(self.heal_percent * 100)
        if not ask_bool(self.ctx, f"Use the healing fountain? (Restores {heal_display}% HP)"):
            return

        self.used = True
        self.rechar(Color.white + "○" + Color.reset)

        healed_any = False
        for poke in self.ctx.figure.pokes[:6]:
            if poke.identifier != "__fallback__" and poke.hp < poke.full_hp:
                heal_amount = int(poke.full_hp * self.heal_percent)
                poke.hp = min(poke.hp + heal_amount, poke.full_hp)
                poke.text_hp.rechar(f"HP:{poke.hp}")
                poke.hp_bar.make(poke.hp)
                healed_any = True

        mvp.movemap.full_show()
        if healed_any:
            ask_ok(self.ctx, f"Your Poketes were healed by {heal_display}%!")
        else:
            ask_ok(self.ctx, "Your Poketes are already at full health!")

        self.ctx.figure.used_npcs.append(self.name)


class TrapTile(se.Object, MapInteract):
    """A trap that damages the player's Poketes.
    
    Damage increases on deeper floors (difficulty_modifier 0->1).
    """

    def __init__(self, name: str, base_damage: float, max_damage: float,
                 damage_per_floor: float, difficulty_modifier: float):
        super().__init__(
            Color.thicc + Color.red + "▲" + Color.reset, state="float"
        )
        self.name = name
        # Calculate actual damage percent based on floor difficulty
        extra_damage = damage_per_floor * difficulty_modifier * 5  # Scale by ~5 floors
        self.damage_percent = min(max_damage, base_damage + extra_damage)
        self.triggered = False

    def action(self, ob):
        """Trigger the trap."""
        if self.triggered:
            return

        from pokete.base.input_loops import ask_ok
        from pokete.classes import movemap as mvp

        self.triggered = True
        self.rechar(Color.white + "x" + Color.reset)

        damaged_any = False
        for poke in self.ctx.figure.pokes[:6]:
            if poke.identifier != "__fallback__" and poke.hp > 0:
                damage = max(1, int(poke.full_hp * self.damage_percent))
                poke.hp = max(1, poke.hp - damage)
                poke.text_hp.rechar(f"HP:{poke.hp}")
                poke.hp_bar.make(poke.hp)
                damaged_any = True

        mvp.movemap.full_show()
        if damaged_any:
            ask_ok(self.ctx, f"It's a trap! Your Poketes took {int(self.damage_percent * 100)}% damage!")
        else:
            ask_ok(self.ctx, "You triggered a trap, but nothing happened...")

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
        from pokete.base.change import change_ctx
        from pokete.classes.general import check_walk_back
        from pokete.classes import movemap as mvp
        from pokete.base.input_loops import ask_ok

        boss = create_boss(
            self.boss_pokes,
            self.min_level,
            self.max_level,
            self.boss_name
        )

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

        special_room_positions = set()
        for special in self.layout.special_rooms:
            special_room_positions.add(special.center)
            for x, y, _ in special.items:
                special_room_positions.add((x, y))

        for x, y in self.layout.encounter_positions:
            if (x, y) not in [self.entry_pos, self.exit_pos, self.boss_pos]:
                if (x, y) not in special_room_positions:
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
                int(self.layout.max_level * self.config.boss_level_multiplier)
            )
            boss.add(self, self.boss_pos[0], self.boss_pos[1])
            self.register_obj("boss", boss)

    def _build_special_rooms(self):
        """Build special room features with floor-dependent difficulty."""
        for i, special in enumerate(self.layout.special_rooms):
            cx, cy = special.center

            if special.room_type == RoomType.TREASURE:
                chest = TreasureChest(
                    f"cave_{self.layout.floor_num}_treasure_{i}",
                    special.items,
                    special.difficulty_modifier
                )
                chest.add(self, cx, cy)
                self.register_obj(f"treasure_{i}", chest)

            elif special.room_type == RoomType.HEALING:
                fountain = HealingFountain(
                    f"cave_{self.layout.floor_num}_healing_{i}",
                    base_heal=self.config.healing_base,
                    min_heal=self.config.healing_min,
                    reduction_per_floor=self.config.healing_reduction_per_floor,
                    difficulty_modifier=special.difficulty_modifier
                )
                fountain.add(self, cx, cy)
                self.register_obj(f"healing_{i}", fountain)

            elif special.room_type == RoomType.TRAP:
                trap = TrapTile(
                    f"cave_{self.layout.floor_num}_trap_{i}",
                    base_damage=self.config.trap_damage_base,
                    max_damage=self.config.trap_damage_max,
                    damage_per_floor=self.config.trap_damage_per_floor,
                    difficulty_modifier=special.difficulty_modifier
                )
                trap.add(self, cx, cy)
                self.register_obj(f"trap_{i}", trap)


class CaveFloorManager:
    """Manages multiple cave floors as a complete dungeon.

    This is a singleton class - use CaveFloorManager.instance() to get
    the global instance, or create_cave() to generate a new dungeon.
    """

    _instance: Optional["CaveFloorManager"] = None

    def __init__(self, config: Optional[CaveConfig] = None,
                 entrance_map: Optional[str] = None):
        self.config = config or CaveConfig()
        self.entrance_map = entrance_map
        self.generator: Optional[CaveGenerator] = None
        self.floor_maps: dict[int, CaveMap] = {}
        self._generated = False

    @classmethod
    def instance(cls) -> Optional["CaveFloorManager"]:
        """Get the singleton instance."""
        return cls._instance

    @classmethod
    def create_cave(cls, config: Optional[CaveConfig] = None,
                    entrance_map: Optional[str] = None,
                    seed: Optional[int] = None) -> "CaveFloorManager":
        """Create and register a new cave dungeon.

        This creates a new singleton instance and automatically registers
        all floor maps to the game's ob_maps.

        Args:
            config: Cave configuration (optional)
            entrance_map: Name of the map that leads to the cave entrance
            seed: Random seed for reproducibility

        Returns:
            The new CaveFloorManager instance
        """
        manager = cls(config, entrance_map)
        manager.generate(seed)
        manager._register_to_game()
        cls._instance = manager
        return manager

    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        if cls._instance:
            cls._instance._unregister_from_game()
        cls._instance = None

    def generate(self, seed: Optional[int] = None) -> "CaveFloorManager":
        """Generate all floors of the dungeon."""
        if seed is not None:
            self.config.seed = seed

        self.generator = CaveGenerator(self.config)
        self.generator.generate()

        self.floor_maps = {}
        for floor in self.generator.floors:
            cave_map = CaveMap(floor, self.config, self)
            self.floor_maps[floor.floor_num] = cave_map

        self._generated = True
        return self

    def _register_to_game(self):
        """Register all floor maps to the game's ob_maps."""
        try:
            from pokete.classes import ob_maps as obmp
            for floor_num, cave_map in self.floor_maps.items():
                obmp.ob_maps[cave_map.name] = cave_map
        except (ImportError, AttributeError):
            pass

    def _unregister_from_game(self):
        """Unregister all floor maps from the game's ob_maps."""
        try:
            from pokete.classes import ob_maps as obmp
            for cave_map in self.floor_maps.values():
                if cave_map.name in obmp.ob_maps:
                    del obmp.ob_maps[cave_map.name]
        except (ImportError, AttributeError):
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
                "treasure_room_chance": self.config.treasure_room_chance,
                "healing_room_chance": self.config.healing_room_chance,
                "trap_room_chance": self.config.trap_room_chance,
            }
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "CaveFloorManager":
        """Recreate manager from saved data and register as singleton."""
        config = CaveConfig(
            seed=data.get("seed"),
            **data.get("config", {})
        )
        manager = cls(config, data.get("entrance_map"))
        manager.generate()
        manager._register_to_game()
        cls._instance = manager
        return manager

    def register_maps(self, ob_maps: dict):
        """Register all floor maps in a map registry (for manual registration)."""
        for floor_num, cave_map in self.floor_maps.items():
            ob_maps[cave_map.name] = cave_map


# Module-level convenience function
def get_cave_manager() -> Optional[CaveFloorManager]:
    """Get the current cave floor manager singleton."""
    return CaveFloorManager.instance()
