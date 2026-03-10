"""Binary Space Partitioning algorithm for dungeon generation."""

from dataclasses import dataclass
from typing import Optional
import random


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
    def center(self) -> tuple[int, int]:
        return (self.rect.center_x, self.rect.center_y)
    
    def __hash__(self):
        return self._id
    
    def __eq__(self, other):
        return self._id == other._id if isinstance(other, Room) else False


@dataclass
class Corridor:
    """A corridor connecting two rooms."""
    points: list[tuple[int, int]]


class BSPNode:
    """Node in the BSP tree."""

    def __init__(self, rect: Rect):
        self.rect = rect
        self.left: Optional[BSPNode] = None
        self.right: Optional[BSPNode] = None
        self.room: Optional[Room] = None

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
        self.rooms: list[Room] = []
        self.corridors: list[Corridor] = []

    def generate(self) -> tuple[list[Room], list[Corridor]]:
        """Generate dungeon using BSP algorithm."""
        root = BSPNode(Rect(1, 1, self.width - 2, self.height - 2))
        self._split_node(root)
        self._create_rooms(root)
        self._create_corridors(root)
        return self.rooms, self.corridors

    def _split_node(self, node: BSPNode, depth: int = 0) -> None:
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

    def _create_rooms(self, node: BSPNode) -> None:
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

    def _create_corridors(self, node: BSPNode) -> None:
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

    def _get_room(self, node: Optional[BSPNode]) -> Optional[Room]:
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

    def _horizontal_line(
        self, x1: int, x2: int, y: int
    ) -> list[tuple[int, int]]:
        """Generate points for a horizontal corridor."""
        points = []
        start = min(x1, x2)
        end = max(x1, x2)
        for x in range(start, end + 1):
            points.append((x, y))
        return points

    def _vertical_line(
        self, y1: int, y2: int, x: int
    ) -> list[tuple[int, int]]:
        """Generate points for a vertical corridor."""
        points = []
        start = min(y1, y2)
        end = max(y1, y2)
        for y in range(start, end + 1):
            points.append((x, y))
        return points
