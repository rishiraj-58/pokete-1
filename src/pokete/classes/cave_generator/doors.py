"""Door classes for dungeon navigation."""

import scrap_engine as se

from pokete.classes import game


class DungeonDoor(se.Object):
    """Base class for dungeon doors."""

    def __init__(
        self,
        char: str,
        target_map_name: str,
        target_x: int,
        target_y: int,
        dungeon_manager: "DungeonManager" = None,
    ):
        super().__init__(char, state="float")
        self.target_map_name = target_map_name
        self.target_x = target_x
        self.target_y = target_y
        self.dungeon_manager = dungeon_manager

    def action(self, ob) -> None:
        """Trigger door transition."""
        from .dungeon_manager import dungeon_manager as dm

        manager = self.dungeon_manager or dm

        target_map = manager.get_map(self.target_map_name)
        if target_map is None:
            return

        ob.remove()
        i = ob.map.name
        ob.add(target_map, self.target_x, self.target_y)
        ob.oldmap = manager.get_map(i)

        raise game.MapChangeException(target_map)


class FloorExitDoor(DungeonDoor):
    """Door that leads to the next floor."""

    def __init__(
        self,
        next_floor_map_name: str,
        entry_x: int,
        entry_y: int,
        dungeon_manager: "DungeonManager" = None,
    ):
        super().__init__(
            char=">",
            target_map_name=next_floor_map_name,
            target_x=entry_x,
            target_y=entry_y,
            dungeon_manager=dungeon_manager,
        )


class FloorEntryDoor(DungeonDoor):
    """Door that leads back to the previous floor or dungeon entrance."""

    def __init__(
        self,
        previous_map_name: str,
        exit_x: int,
        exit_y: int,
        dungeon_manager: "DungeonManager" = None,
    ):
        super().__init__(
            char="<",
            target_map_name=previous_map_name,
            target_x=exit_x,
            target_y=exit_y,
            dungeon_manager=dungeon_manager,
        )


class BossRoomDoor(DungeonDoor):
    """Door leading to the boss room."""

    def __init__(
        self,
        boss_room_map_name: str,
        boss_x: int,
        boss_y: int,
        dungeon_manager: "DungeonManager" = None,
    ):
        super().__init__(
            char="!",
            target_map_name=boss_room_map_name,
            target_x=boss_x,
            target_y=boss_y,
            dungeon_manager=dungeon_manager,
        )


class DungeonExitDoor(se.Object):
    """Door that exits the dungeon back to the overworld."""

    def __init__(
        self,
        exit_map_name: str,
        exit_x: int,
        exit_y: int,
    ):
        super().__init__("^", state="float")
        self.exit_map_name = exit_map_name
        self.exit_x = exit_x
        self.exit_y = exit_y

    def action(self, ob) -> None:
        """Exit the dungeon."""
        from pokete.classes import ob_maps as obmp

        target_map = obmp.ob_maps.get(self.exit_map_name)
        if target_map is None:
            return

        ob.remove()
        ob.add(target_map, self.exit_x, self.exit_y)
        ob.oldmap = target_map

        raise game.MapChangeException(target_map)
