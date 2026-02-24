"""Quest type enumeration defining all possible quest objectives."""
from __future__ import annotations
from enum import Enum, auto


class QuestType(Enum):
    """Defines the different types of quests available."""
    CATCH_ANY = auto()           # Catch any pokete
    CATCH_TYPE = auto()          # Catch pokete of specific type
    CATCH_SPECIFIC = auto()      # Catch specific species
    WIN_TRAINER_BATTLE = auto()  # Win battle against trainer
    WIN_WILD_BATTLE = auto()     # Win battle against wild pokete
    COLLECT_COINS = auto()       # Collect N coins
    EVOLVE_POKETE = auto()       # Evolve a pokete
    USE_ITEM = auto()            # Use specific item(s)
    VISIT_MAPS = auto()          # Visit N different maps

    @classmethod
    def from_string(cls, value: str) -> "QuestType | None":
        """Safely convert string to QuestType, returns None if invalid."""
        if value is None:
            return None
        try:
            normalized = value.upper().strip()
            for member in cls:
                if member.name == normalized:
                    return member
            return None
        except (AttributeError, TypeError):
            return None

    def __str__(self) -> str:
        return self.name
