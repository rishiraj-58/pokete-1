"""Quest manager handles daily quest selection, progress, and rewards."""
from __future__ import annotations
import datetime
import hashlib
import logging
import random
from typing import Any, Callable, Optional, Dict, List

from .quest_types import QuestType
from .quest import Quest, QuestConfig
from .quest_events import QuestEvent
from .quest_tracker import quest_tracker


class QuestManager:
    """Manages the daily quest system."""

    QUEST_RESET_HOUR = 0  # Reset at midnight

    def __init__(self):
        self._quest_configs: dict[str, QuestConfig] = {}
        self._current_quest: Quest | None = None
        self._last_quest_date: str | None = None
        self._on_progress_callbacks: list[Callable[[Quest], None]] = []
        self._on_complete_callbacks: list[Callable[[Quest], None]] = []
        self._initialized = False

    def initialize(self, quest_data: dict[str, dict[str, Any]] | None = None):
        """Initialize the quest manager with quest configurations."""
        if quest_data is None:
            logging.warning(
                "[QuestManager] No quest data provided, using empty config"
            )
            quest_data = {}

        self._quest_configs.clear()

        for quest_id, data in quest_data.items():
            if not quest_id or not isinstance(data, dict):
                logging.warning(
                    "[QuestManager] Skipping invalid quest entry: %s",
                    quest_id
                )
                continue

            config = QuestConfig.from_dict(quest_id, data)
            if config:
                self._quest_configs[quest_id] = config
                logging.debug("[QuestManager] Loaded quest config: %s", quest_id)
            else:
                logging.warning(
                    "[QuestManager] Failed to load quest config: %s",
                    quest_id
                )

        logging.info(
            "[QuestManager] Initialized with %d quest configs",
            len(self._quest_configs)
        )

        quest_tracker.add_listener(self._on_event)
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def current_quest(self) -> Quest | None:
        return self._current_quest

    @property
    def has_active_quest(self) -> bool:
        return self._current_quest is not None

    @property
    def available_quests(self) -> list[str]:
        return list(self._quest_configs.keys())

    def add_on_progress_callback(self, callback: Callable[[Quest], None]):
        """Register callback for quest progress updates."""
        if callback and callback not in self._on_progress_callbacks:
            self._on_progress_callbacks.append(callback)

    def add_on_complete_callback(self, callback: Callable[[Quest], None]):
        """Register callback for quest completion."""
        if callback and callback not in self._on_complete_callbacks:
            self._on_complete_callbacks.append(callback)

    def check_and_reset_daily(self) -> bool:
        """Check if quest needs to be reset for new day.

        Returns True if quest was reset."""
        current_date = self._get_current_date_string()

        if self._last_quest_date != current_date:
            logging.info(
                "[QuestManager] New day detected (%s -> %s), resetting quest",
                self._last_quest_date,
                current_date
            )
            self._reset_for_new_day(current_date)
            return True

        return False

    def _reset_for_new_day(self, date_string: str):
        """Reset quest state for a new day."""
        self._last_quest_date = date_string
        self._current_quest = None
        self._select_daily_quest(date_string)

    def _select_daily_quest(self, date_string: str):
        """Select a quest for the day using deterministic seed."""
        if not self._quest_configs:
            logging.warning(
                "[QuestManager] No quest configs available for selection"
            )
            return

        quest_id = self._get_deterministic_quest_id(date_string)
        if quest_id and quest_id in self._quest_configs:
            config = self._quest_configs[quest_id]
            self._current_quest = Quest(config)
            logging.info(
                "[QuestManager] Selected daily quest: %s (%s)",
                quest_id,
                config.name
            )
        else:
            logging.warning(
                "[QuestManager] Failed to select quest for date: %s",
                date_string
            )

    def _get_deterministic_quest_id(self, date_string: str) -> str | None:
        """Get a deterministic quest ID based on date."""
        if not self._quest_configs:
            return None

        seed_string = f"pokete_daily_quest_{date_string}"
        hash_bytes = hashlib.sha256(seed_string.encode()).digest()
        seed_value = int.from_bytes(hash_bytes[:8], byteorder='big')

        quest_ids = sorted(self._quest_configs.keys())
        rng = random.Random(seed_value)
        return rng.choice(quest_ids)

    def select_random_quest(self, seed: int | None = None) -> Quest | None:
        """Select a random quest (for testing or special cases)."""
        if not self._quest_configs:
            return None

        rng = random.Random(seed) if seed is not None else random
        quest_id = rng.choice(list(self._quest_configs.keys()))
        config = self._quest_configs[quest_id]
        self._current_quest = Quest(config)
        return self._current_quest

    def force_select_quest(self, quest_id: str) -> Quest | None:
        """Force select a specific quest by ID (for testing/debug)."""
        if quest_id not in self._quest_configs:
            logging.warning(
                "[QuestManager] Quest ID not found: %s",
                quest_id
            )
            return None

        config = self._quest_configs[quest_id]
        self._current_quest = Quest(config)
        self._last_quest_date = self._get_current_date_string()
        logging.info("[QuestManager] Force selected quest: %s", quest_id)
        return self._current_quest

    def _on_event(self, event: QuestEvent):
        """Handle quest events and update progress."""
        if not self._current_quest or self._current_quest.is_claimed:
            return

        was_completed = self._current_quest.is_completed
        progress_made = self._current_quest.process_event(event)

        if progress_made:
            logging.debug(
                "[QuestManager] Quest progress: %s",
                self._current_quest.progress_display
            )
            self._notify_progress()

            if not was_completed and self._current_quest.is_completed:
                logging.info(
                    "[QuestManager] Quest completed: %s",
                    self._current_quest.name
                )
                self._notify_complete()

    def _notify_progress(self):
        """Notify all progress callbacks."""
        if not self._current_quest:
            return
        for callback in self._on_progress_callbacks:
            try:
                callback(self._current_quest)
            except Exception as e:
                logging.error(
                    "[QuestManager] Error in progress callback: %s",
                    e
                )

    def _notify_complete(self):
        """Notify all completion callbacks."""
        if not self._current_quest:
            return
        for callback in self._on_complete_callbacks:
            try:
                callback(self._current_quest)
            except Exception as e:
                logging.error(
                    "[QuestManager] Error in complete callback: %s",
                    e
                )

    def claim_reward(self, figure) -> dict[str, Any] | None:
        """Claim rewards for completed quest.

        Returns dict with reward details or None if not claimable."""
        if not self._current_quest:
            logging.warning("[QuestManager] No active quest to claim")
            return None

        if not self._current_quest.is_completed:
            logging.warning("[QuestManager] Quest not completed")
            return None

        if self._current_quest.is_claimed:
            logging.warning("[QuestManager] Quest already claimed")
            return None

        if figure is None:
            logging.error("[QuestManager] Figure is None, cannot claim reward")
            return None

        config = self._current_quest.config
        rewards = {
            "money": config.reward_money,
            "items": dict(config.reward_items),
        }

        try:
            if config.reward_money > 0:
                figure.add_money(config.reward_money)

            for item_name, count in config.reward_items.items():
                if count > 0:
                    figure.give_item(item_name, count)

            self._current_quest.mark_claimed()
            logging.info(
                "[QuestManager] Claimed rewards for quest: %s - "
                "Money: %d, Items: %s",
                self._current_quest.name,
                config.reward_money,
                config.reward_items
            )
            return rewards

        except Exception as e:
            logging.error(
                "[QuestManager] Error claiming rewards: %s",
                e
            )
            return None

    def _get_current_date_string(self) -> str:
        """Get current date as string for comparison."""
        return datetime.date.today().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize manager state for saving."""
        return {
            "last_quest_date": self._last_quest_date,
            "current_quest": (
                self._current_quest.to_dict()
                if self._current_quest else None
            ),
        }

    def from_dict(self, data: dict[str, Any] | None):
        """Restore manager state from saved data."""
        if not data:
            self.check_and_reset_daily()
            return

        self._last_quest_date = data.get("last_quest_date")
        quest_data = data.get("current_quest")

        if quest_data and self._last_quest_date:
            quest_id = quest_data.get("identifier")
            if quest_id and quest_id in self._quest_configs:
                config = self._quest_configs[quest_id]
                self._current_quest = Quest.from_dict(quest_data, config)
                logging.info(
                    "[QuestManager] Restored quest: %s (progress: %s)",
                    quest_id,
                    self._current_quest.progress_display
                    if self._current_quest else "N/A"
                )

        self.check_and_reset_daily()

    def get_quest_config(self, quest_id: str) -> QuestConfig | None:
        """Get a quest configuration by ID."""
        return self._quest_configs.get(quest_id)

    def get_all_configs(self) -> dict[str, QuestConfig]:
        """Get all quest configurations."""
        return dict(self._quest_configs)


daily_quest_manager = QuestManager()
