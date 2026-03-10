"""Binary Space Partitioning algorithm for dungeon generation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class Rect:
    """A rectangle defined by position and size."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x2 and self.y <= y < self.y2

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.x2 <= other.x or other.x2 <= self.x or
            self.y2 <= other.y or other.y2 <= self.y
        )


class Room:
    """A room within the dungeon."""

    def __init__(self, rect: Rect):
        self.rect = rect
        self.connected_to: list["Room"] = []
        self._id = id(self)

    def __hash__(self):
        return self._id

    def __eq__(self, other):
        if not isinstance(other, Room):
            return False
        return self._id == other._id

    def connect(self, other: "Room"):
        if other not in self.connected_to:
            self.connected_to.append(other)
        if self not in other.connected_to:
            other.connected_to.append(self)


class BSPNode:
    """A node in the BSP tree representing a partition of space."""

    def __init__(self, rect: Rect):
        self.rect = rect
        self.left: Optional[BSPNode] = None
        self.right: Optional[BSPNode] = None
        self.room: Optional[Room] = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def split(self, rng: random.Random, min_size: int = 8) -> bool:
        """Split the node into two children.

        Returns True if split was successful, False otherwise.
        """
        if not self.is_leaf:
            return False

        split_h = rng.random() > 0.5

        if self.rect.width > self.rect.height and self.rect.width / self.rect.height >= 1.25:
            split_h = False
        elif self.rect.height > self.rect.width and self.rect.height / self.rect.width >= 1.25:
            split_h = True

        max_size = (self.rect.height if split_h else self.rect.width) - min_size
        if max_size <= min_size:
            return False

        split_pos = rng.randint(min_size, max_size)

        if split_h:
            self.left = BSPNode(Rect(
                self.rect.x, self.rect.y,
                self.rect.width, split_pos
            ))
            self.right = BSPNode(Rect(
                self.rect.x, self.rect.y + split_pos,
                self.rect.width, self.rect.height - split_pos
            ))
        else:
            self.left = BSPNode(Rect(
                self.rect.x, self.rect.y,
                split_pos, self.rect.height
            ))
            self.right = BSPNode(Rect(
                self.rect.x + split_pos, self.rect.y,
                self.rect.width - split_pos, self.rect.height
            ))

        return True

    def get_leaves(self) -> list["BSPNode"]:
        """Get all leaf nodes in this subtree."""
        if self.is_leaf:
            return [self]

        leaves = []
        if self.left:
            leaves.extend(self.left.get_leaves())
        if self.right:
            leaves.extend(self.right.get_leaves())
        return leaves

    def create_room(self, rng: random.Random, min_room_size: int = 4,
                    padding: int = 1) -> Optional[Room]:
        """Create a room within this leaf node."""
        if not self.is_leaf:
            return None

        available_width = self.rect.width - 2 * padding
        available_height = self.rect.height - 2 * padding

        if available_width < min_room_size or available_height < min_room_size:
            return None

        room_width = rng.randint(min_room_size, available_width)
        room_height = rng.randint(min_room_size, available_height)

        room_x = self.rect.x + padding + rng.randint(0, available_width - room_width)
        room_y = self.rect.y + padding + rng.randint(0, available_height - room_height)

        self.room = Room(Rect(room_x, room_y, room_width, room_height))
        return self.room

    def get_room(self) -> Optional[Room]:
        """Get the room in this node or a descendant."""
        if self.room:
            return self.room
        if self.left:
            left_room = self.left.get_room()
            if left_room:
                return left_room
        if self.right:
            right_room = self.right.get_room()
            if right_room:
                return right_room
        return None


class BSPTree:
    """A complete BSP tree for dungeon generation."""

    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)
        self.root = BSPNode(Rect(0, 0, width, height))
        self.rooms: list[Room] = []
        self.corridors: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def generate(self, max_depth: int = 4, min_size: int = 8,
                 min_room_size: int = 4) -> "BSPTree":
        """Generate the complete dungeon layout."""
        self._split_recursive(self.root, 0, max_depth, min_size)
        self._create_rooms(min_room_size)
        self._connect_rooms()
        return self

    def _split_recursive(self, node: BSPNode, depth: int,
                         max_depth: int, min_size: int):
        """Recursively split nodes up to max_depth."""
        if depth >= max_depth:
            return

        if node.split(self.rng, min_size):
            self._split_recursive(node.left, depth + 1, max_depth, min_size)
            self._split_recursive(node.right, depth + 1, max_depth, min_size)

    def _create_rooms(self, min_room_size: int):
        """Create rooms in all leaf nodes."""
        for leaf in self.root.get_leaves():
            room = leaf.create_room(self.rng, min_room_size)
            if room:
                self.rooms.append(room)

    def _connect_rooms(self):
        """Connect all rooms with corridors."""
        self._connect_recursive(self.root)

    def _connect_recursive(self, node: BSPNode):
        """Recursively connect rooms in the BSP tree."""
        if node.is_leaf:
            return

        if node.left and node.right:
            self._connect_recursive(node.left)
            self._connect_recursive(node.right)

            left_room = node.left.get_room()
            right_room = node.right.get_room()

            if left_room and right_room:
                self._create_corridor(left_room, right_room)

    def _create_corridor(self, room1: Room, room2: Room):
        """Create a corridor between two rooms."""
        room1.connect(room2)

        x1, y1 = room1.rect.center
        x2, y2 = room2.rect.center

        if self.rng.random() > 0.5:
            self.corridors.append(((x1, y1), (x2, y1)))
            self.corridors.append(((x2, y1), (x2, y2)))
        else:
            self.corridors.append(((x1, y1), (x1, y2)))
            self.corridors.append(((x1, y2), (x2, y2)))

    def to_grid(self) -> list[list[str]]:
        """Convert the dungeon to a 2D character grid."""
        grid = [['#' for _ in range(self.width)] for _ in range(self.height)]

        for room in self.rooms:
            r = room.rect
            for y in range(r.y, r.y2):
                for x in range(r.x, r.x2):
                    if 0 <= y < self.height and 0 <= x < self.width:
                        grid[y][x] = '.'

        for (x1, y1), (x2, y2) in self.corridors:
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)

            for x in range(min_x, max_x + 1):
                if 0 <= y1 < self.height and 0 <= x < self.width:
                    grid[y1][x] = '.'

            for y in range(min_y, max_y + 1):
                if 0 <= y < self.height and 0 <= x2 < self.width:
                    grid[y][x2] = '.'

        return grid

    def get_random_floor_position(self) -> Optional[tuple[int, int]]:
        """Get a random walkable position in the dungeon."""
        if not self.rooms:
            return None

        room = self.rng.choice(self.rooms)
        r = room.rect
        x = self.rng.randint(r.x + 1, r.x2 - 2) if r.width > 2 else r.x + r.width // 2
        y = self.rng.randint(r.y + 1, r.y2 - 2) if r.height > 2 else r.y + r.height // 2
        return (x, y)

    def get_furthest_rooms(self) -> tuple[Optional[Room], Optional[Room]]:
        """Get the two rooms that are furthest apart."""
        if len(self.rooms) < 2:
            return (self.rooms[0] if self.rooms else None, None)

        max_dist = -1
        room_a, room_b = None, None

        for i, r1 in enumerate(self.rooms):
            for r2 in self.rooms[i+1:]:
                c1, c2 = r1.rect.center, r2.rect.center
                dist = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
                if dist > max_dist:
                    max_dist = dist
                    room_a, room_b = r1, r2

        return (room_a, room_b)

    def is_connected(self) -> bool:
        """Check if all rooms are connected (reachable from each other)."""
        if len(self.rooms) <= 1:
            return True

        visited = set()
        to_visit = [self.rooms[0]]

        while to_visit:
            room = to_visit.pop()
            if room in visited:
                continue
            visited.add(room)
            for connected in room.connected_to:
                if connected not in visited:
                    to_visit.append(connected)

        return len(visited) == len(self.rooms)

    def has_isolated_rooms(self) -> bool:
        """Check if there are any isolated (unreachable) rooms."""
        return not self.is_connected()
