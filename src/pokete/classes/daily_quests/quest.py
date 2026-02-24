"""Quest and QuestConfig classes for daily quest system."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict

from .quest_types import QuestType
from .quest_events import QuestEvent, QuestEventType


@dataclass
class QuestConfig:
    """Configuration for a quest loaded from data file.

    Attributes:
        identifier: Unique quest ID
        name: Display name
        desc: Description
        quest_type: Type of quest objective
        target: Target count to complete
        reward_money: Money reward
        reward_items: Item rewards as {item_name: count}
        type_filter: For CATCH_TYPE quests
        species_filter: For CATCH_SPECIFIC quests
        item_filter: For USE_ITEM quests
    """
    identifier: str
    name: str
    desc: str
    quest_type: QuestType
    target: int
    reward_money: int = 0
    reward_items: dict[str, int] = field(default_factory=dict)
    type_filter: str | None = None
    species_filter: str | None = None
    item_filter: list[str] | None = None

    def __post_init__(self):
        if self.reward_items is None:
            self.reward_items = {}
        if self.target is None or self.target < 1:
            self.target = 1
        if self.reward_money is None or self.reward_money < 0:
            self.reward_money = 0

    @classmethod
    def from_dict(
        cls, identifier: str, data: dict[str, Any]
    ) -> "QuestConfig | None":
        """Create QuestConfig from dictionary data. Returns None if invalid."""
        if not data or not isinstance(data, dict):
            return None
        if not identifier or not isinstance(identifier, str):
            return None

        name = data.get("name")
        desc = data.get("desc")
        quest_type = data.get("type")
        target = data.get("target")

        if not all([name, desc, quest_type, target]):
            return None

        if not isinstance(quest_type, QuestType):
            return None

        try:
            target_int = int(target)
            if target_int < 1:
                return None
        except (ValueError, TypeError):
            return None

        reward_money = data.get("reward_money", 0)
        try:
            reward_money = int(reward_money) if reward_money else 0
        except (ValueError, TypeError):
            reward_money = 0

        reward_items = data.get("reward_items", {})
        if not isinstance(reward_items, dict):
            reward_items = {}
        validated_items = {}
        for item_name, count in reward_items.items():
            if isinstance(item_name, str) and item_name:
                try:
                    validated_items[item_name] = max(0, int(count))
                except (ValueError, TypeError):
                    pass

        type_filter = data.get("type_filter")
        if type_filter is not None and not isinstance(type_filter, str):
            type_filter = None

        species_filter = data.get("species_filter")
        if species_filter is not None and not isinstance(species_filter, str):
            species_filter = None

        item_filter = data.get("item_filter")
        if item_filter is not None:
            if isinstance(item_filter, list):
                item_filter = [
                    i for i in item_filter if isinstance(i, str) and i
                ]
                if not item_filter:
                    item_filter = None
            else:
                item_filter = None

        return cls(
            identifier=identifier,
            name=str(name),
            desc=str(desc),
            quest_type=quest_type,
            target=target_int,
            reward_money=reward_money,
            reward_items=validated_items,
            type_filter=type_filter,
            species_filter=species_filter,
            item_filter=item_filter,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "identifier": self.identifier,
            "name": self.name,
            "desc": self.desc,
            "type": self.quest_type.name,
            "target": self.target,
            "reward_money": self.reward_money,
            "reward_items": dict(self.reward_items),
            "type_filter": self.type_filter,
            "species_filter": self.species_filter,
            "item_filter": list(self.item_filter) if self.item_filter else None,
        }


class Quest:
    """Active quest instance with progress tracking."""

    def __init__(self, config: QuestConfig):
        if config is None:
            raise ValueError("Quest config cannot be None")
        self._config = config
        self._progress: int = 0
        self._completed: bool = False
        self._claimed: bool = False
        self._maps_visited: set[str] = set()

    @property
    def config(self) -> QuestConfig:
        return self._config

    @property
    def identifier(self) -> str:
        return self._config.identifier

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def desc(self) -> str:
        return self._config.desc

    @property
    def quest_type(self) -> QuestType:
        return self._config.quest_type

    @property
    def target(self) -> int:
        return self._config.target

    @property
    def progress(self) -> int:
        return self._progress

    @property
    def is_completed(self) -> bool:
        return self._completed

    @property
    def is_claimed(self) -> bool:
        return self._claimed

    @property
    def progress_percent(self) -> float:
        """Return progress as percentage 0-100."""
        if self.target <= 0:
            return 100.0
        return min(100.0, (self._progress / self.target) * 100)

    @property
    def progress_display(self) -> str:
        """Return formatted progress string."""
        return f"{min(self._progress, self.target)}/{self.target}"

    def process_event(self, event: QuestEvent) -> bool:
        """Process a game event and update progress if applicable.

        Returns True if progress was made."""
        if self._completed or event is None:
            return False

        progress_made = self._check_event_matches(event)
        if progress_made:
            self._update_completion()

        return progress_made

    def _check_event_matches(self, event: QuestEvent) -> bool:
        """Check if event matches quest requirements and update progress."""
        qt = self._config.quest_type
        et = event.event_type

        if qt == QuestType.CATCH_ANY and et == QuestEventType.POKETE_CAUGHT:
            self._progress += 1
            return True

        if qt == QuestType.CATCH_TYPE and et == QuestEventType.POKETE_CAUGHT:
            types = event.get_data("types", [])
            if self._config.type_filter and self._config.type_filter in types:
                self._progress += 1
                return True

        if qt == QuestType.CATCH_SPECIFIC and et == QuestEventType.POKETE_CAUGHT:
            species = event.get_data("species", "")
            expected = self._config.species_filter
            if expected and species.lower() == expected.lower():
                self._progress += 1
                return True

        if qt == QuestType.WIN_TRAINER_BATTLE:
            if et == QuestEventType.TRAINER_BATTLE_WON:
                self._progress += 1
                return True

        if qt == QuestType.WIN_WILD_BATTLE:
            if et == QuestEventType.WILD_BATTLE_WON:
                self._progress += 1
                return True

        if qt == QuestType.COLLECT_COINS:
            if et == QuestEventType.COINS_COLLECTED:
                amount = event.get_data("amount", 0)
                if amount > 0:
                    self._progress += amount
                    return True

        if qt == QuestType.EVOLVE_POKETE:
            if et == QuestEventType.POKETE_EVOLVED:
                self._progress += 1
                return True

        if qt == QuestType.USE_ITEM and et == QuestEventType.ITEM_USED:
            item_name = event.get_data("item_name", "")
            filters = self._config.item_filter
            if filters is None or item_name in filters:
                self._progress += 1
                return True

        if qt == QuestType.VISIT_MAPS and et == QuestEventType.MAP_VISITED:
            map_name = event.get_data("map_name", "")
            if map_name and map_name not in self._maps_visited:
                self._maps_visited.add(map_name)
                self._progress = len(self._maps_visited)
                return True

        return False

    def _update_completion(self):
        """Check and update completion status."""
        if self._progress >= self._config.target:
            self._completed = True

    def mark_claimed(self):
        """Mark rewards as claimed."""
        self._claimed = True

    def set_progress(self, progress: int):
        """Set progress directly (for loading from save)."""
        self._progress = max(0, progress)
        self._update_completion()

    def set_maps_visited(self, maps: set[str] | list[str] | None):
        """Set visited maps (for loading from save)."""
        if maps is None:
            self._maps_visited = set()
        elif isinstance(maps, set):
            self._maps_visited = maps.copy()
        else:
            self._maps_visited = set(maps)

    def to_dict(self) -> dict[str, Any]:
        """Serialize quest state for saving."""
        return {
            "identifier": self._config.identifier,
            "progress": self._progress,
            "completed": self._completed,
            "claimed": self._claimed,
            "maps_visited": list(self._maps_visited),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        config: QuestConfig
    ) -> "Quest | None":
        """Restore quest from saved data."""
        if not data or not config:
            return None

        quest = cls(config)
        quest._progress = data.get("progress", 0)
        quest._completed = data.get("completed", False)
        quest._claimed = data.get("claimed", False)
        maps_visited = data.get("maps_visited", [])
        quest._maps_visited = set(maps_visited) if maps_visited else set()

        return quest
