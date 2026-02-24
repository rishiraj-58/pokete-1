"""Quest event types for tracking player actions."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, List


class QuestEventType(Enum):
    """Types of events that can contribute to quest progress."""
    POKETE_CAUGHT = auto()
    TRAINER_BATTLE_WON = auto()
    WILD_BATTLE_WON = auto()
    COINS_COLLECTED = auto()
    POKETE_EVOLVED = auto()
    ITEM_USED = auto()
    MAP_VISITED = auto()


@dataclass(frozen=True)
class QuestEvent:
    """Represents a game event that may contribute to quest progress.

    Attributes:
        event_type: The type of event
        data: Additional data about the event (pokete name, type, amount, etc.)
    """
    event_type: QuestEventType
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.data is None:
            object.__setattr__(self, 'data', {})

    def get_data(self, key: str, default: Any = None) -> Any:
        """Safely retrieve data value with default."""
        if self.data is None:
            return default
        return self.data.get(key, default)

    @classmethod
    def pokete_caught(
        cls,
        species: str,
        types: list[str] | None = None
    ) -> "QuestEvent":
        """Create event for catching a pokete."""
        return cls(
            event_type=QuestEventType.POKETE_CAUGHT,
            data={
                "species": species or "",
                "types": types if types is not None else []
            }
        )

    @classmethod
    def trainer_battle_won(cls) -> "QuestEvent":
        """Create event for winning a trainer battle."""
        return cls(event_type=QuestEventType.TRAINER_BATTLE_WON)

    @classmethod
    def wild_battle_won(cls) -> "QuestEvent":
        """Create event for winning a wild battle."""
        return cls(event_type=QuestEventType.WILD_BATTLE_WON)

    @classmethod
    def coins_collected(cls, amount: int) -> "QuestEvent":
        """Create event for collecting coins."""
        safe_amount = max(0, int(amount)) if amount is not None else 0
        return cls(
            event_type=QuestEventType.COINS_COLLECTED,
            data={"amount": safe_amount}
        )

    @classmethod
    def pokete_evolved(cls, from_species: str, to_species: str) -> "QuestEvent":
        """Create event for evolving a pokete."""
        return cls(
            event_type=QuestEventType.POKETE_EVOLVED,
            data={
                "from_species": from_species or "",
                "to_species": to_species or ""
            }
        )

    @classmethod
    def item_used(cls, item_name: str) -> "QuestEvent":
        """Create event for using an item."""
        return cls(
            event_type=QuestEventType.ITEM_USED,
            data={"item_name": item_name or ""}
        )

    @classmethod
    def map_visited(cls, map_name: str) -> "QuestEvent":
        """Create event for visiting a map."""
        return cls(
            event_type=QuestEventType.MAP_VISITED,
            data={"map_name": map_name or ""}
        )
