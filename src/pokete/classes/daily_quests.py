"""Daily quest system for Pokete"""

import datetime
import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import scrap_engine as se

from pokete.base import loops
from pokete.base.change import change_ctx
from pokete.base.color import Color
from pokete.base.context import Context
from pokete.base.ui.elements.labels import CloseLabel
from pokete.base.ui.notify import notifier
from pokete.base.ui.views.boxes import LabelBoxView
from pokete.data.quests import QuestDict, quests as quest_definitions
from pokete.util import liner


class QuestType(Enum):
    CATCH = "catch"
    TRAINER_BATTLE = "trainer_battle"
    COLLECT_COINS = "collect_coins"
    WIN_BATTLES = "win_battles"


@dataclass
class QuestReward:
    money: int
    items: dict[str, int]

    @classmethod
    def from_dict(cls, data: dict) -> "QuestReward":
        return cls(
            money=data.get("money", 0),
            items=data.get("items", {}),
        )


@dataclass
class Quest:
    identifier: str
    title: str
    description: str
    quest_type: QuestType
    target: int
    reward: QuestReward

    @classmethod
    def from_dict(cls, identifier: str, data: QuestDict) -> "Quest":
        return cls(
            identifier=identifier,
            title=data["title"],
            description=data["description"],
            quest_type=QuestType(data["quest_type"]),
            target=data["target"],
            reward=QuestReward.from_dict(data["reward"]),
        )


@dataclass
class ActiveQuest:
    quest: Quest
    progress: int
    completed: bool
    rewarded: bool
    assigned_date: str

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest.identifier,
            "progress": self.progress,
            "completed": self.completed,
            "rewarded": self.rewarded,
            "assigned_date": self.assigned_date,
        }

    @classmethod
    def from_dict(cls, data: dict, quests: dict[str, Quest]) -> Optional["ActiveQuest"]:
        quest_id = data.get("quest_id")
        if quest_id not in quests:
            return None
        return cls(
            quest=quests[quest_id],
            progress=data.get("progress", 0),
            completed=data.get("completed", False),
            rewarded=data.get("rewarded", False),
            assigned_date=data.get("assigned_date", ""),
        )

    def add_progress(self, amount: int = 1) -> bool:
        """Add progress and return True if quest was just completed"""
        if self.completed:
            return False
        self.progress = min(self.progress + amount, self.quest.target)
        if self.progress >= self.quest.target and not self.completed:
            self.completed = True
            return True
        return False

    def progress_text(self) -> str:
        return f"{self.progress}/{self.quest.target}"


class DailyQuestManager:
    """Manages the daily quest system"""

    def __init__(self):
        self.quests: dict[str, Quest] = {}
        self.active_quest: Optional[ActiveQuest] = None
        self._reward_callback: Optional[Callable[[int, dict[str, int]], None]] = None
        self._load_quests()

    def _load_quests(self):
        """Load quest definitions"""
        for identifier, quest_data in quest_definitions.items():
            self.quests[identifier] = Quest.from_dict(identifier, quest_data)

    def set_reward_callback(self, callback: Callable[[int, dict[str, int]], None]):
        """Set callback for giving rewards (money, items)"""
        self._reward_callback = callback

    def get_today_str(self) -> str:
        """Get today's date as string"""
        return str(datetime.date.today())

    def select_random_quest(self, seed: Optional[str] = None) -> Quest:
        """Select a random quest, optionally with a seed for determinism"""
        quest_list = list(self.quests.values())
        if seed:
            rng = random.Random(seed)
            return rng.choice(quest_list)
        return random.choice(quest_list)

    def check_new_day(self) -> bool:
        """Check if it's a new day and reset quest if needed. Returns True if new quest assigned."""
        today = self.get_today_str()
        if self.active_quest is None or self.active_quest.assigned_date != today:
            self._assign_new_quest(today)
            return True
        return False

    def _assign_new_quest(self, date_str: str):
        """Assign a new quest for the given date"""
        # Use date as seed for deterministic daily quest
        quest = self.select_random_quest(seed=date_str)
        self.active_quest = ActiveQuest(
            quest=quest,
            progress=0,
            completed=False,
            rewarded=False,
            assigned_date=date_str,
        )
        logging.info("[DailyQuest] Assigned new quest: %s", quest.title)

    def record_catch(self):
        """Record a pokete catch"""
        if self.active_quest and self.active_quest.quest.quest_type == QuestType.CATCH:
            if self.active_quest.add_progress():
                self._notify_completion()

    def record_trainer_battle_win(self):
        """Record a trainer battle win"""
        if self.active_quest:
            quest_type = self.active_quest.quest.quest_type
            if quest_type == QuestType.TRAINER_BATTLE:
                if self.active_quest.add_progress():
                    self._notify_completion()
            elif quest_type == QuestType.WIN_BATTLES:
                if self.active_quest.add_progress():
                    self._notify_completion()

    def record_wild_battle_win(self):
        """Record a wild battle win"""
        if self.active_quest and self.active_quest.quest.quest_type == QuestType.WIN_BATTLES:
            if self.active_quest.add_progress():
                self._notify_completion()

    def record_coins_collected(self, amount: int):
        """Record coins collected"""
        if self.active_quest and self.active_quest.quest.quest_type == QuestType.COLLECT_COINS:
            if self.active_quest.add_progress(amount):
                self._notify_completion()

    def _notify_completion(self):
        """Notify player that quest was completed"""
        if self.active_quest:
            notifier.notify(
                "Quest Complete!",
                "Daily Quest",
                f"{self.active_quest.quest.title} - Claim your reward!"
            )
            logging.info("[DailyQuest] Quest completed: %s", self.active_quest.quest.title)

    def claim_reward(self) -> bool:
        """Claim the reward for completed quest. Returns True if reward was claimed."""
        if not self.active_quest or not self.active_quest.completed or self.active_quest.rewarded:
            return False

        reward = self.active_quest.quest.reward
        self.active_quest.rewarded = True

        if self._reward_callback:
            self._reward_callback(reward.money, reward.items)

        logging.info(
            "[DailyQuest] Reward claimed: $%d, items: %s",
            reward.money,
            reward.items
        )
        return True

    def to_dict(self) -> dict:
        """Serialize quest state for saving"""
        if self.active_quest is None:
            return {}
        return {"active_quest": self.active_quest.to_dict()}

    def from_dict(self, data: dict):
        """Load quest state from save data"""
        active_quest_data = data.get("active_quest")
        if active_quest_data:
            self.active_quest = ActiveQuest.from_dict(active_quest_data, self.quests)
        else:
            self.active_quest = None


class QuestInfoBox(LabelBoxView):
    """Box showing quest information"""

    def __init__(self, active_quest: Optional[ActiveQuest]):
        if active_quest is None:
            label = se.Text("No active quest", state="float")
        else:
            quest = active_quest.quest
            status = "COMPLETED!" if active_quest.completed else "In Progress"
            if active_quest.rewarded:
                status = "REWARDED"

            reward_text = f"Reward: ${quest.reward.money}"
            if quest.reward.items:
                items_str = ", ".join(
                    f"{v}x {k}" for k, v in quest.reward.items.items()
                )
                reward_text += f"\n  Items: {items_str}"

            label = (
                se.Text(quest.title + "\n", esccode=Color.thicc, state="float")
                + se.Text(liner(quest.description, 30) + "\n\n", state="float")
                + se.Text(f"Progress: {active_quest.progress_text()}\n", state="float")
                + se.Text(
                    f"Status: {status}\n\n",
                    esccode=Color.green if active_quest.completed else "",
                    state="float",
                )
                + se.Text(liner(reward_text, 30), state="float")
            )

        super().__init__(
            label,
            name="Daily Quest",
            info=[CloseLabel()],
        )


class DailyQuestView:
    """View for displaying and claiming daily quests"""

    def __call__(self, ctx: Context) -> None:
        active_quest = daily_quest_manager.active_quest

        with QuestInfoBox(active_quest).center_add(ctx.map) as box:
            box.set_ctx(ctx)
            view_ctx = change_ctx(ctx, box)

            # If quest is completed but not rewarded, claim it
            if (
                active_quest
                and active_quest.completed
                and not active_quest.rewarded
            ):
                if daily_quest_manager.claim_reward():
                    notifier.notify(
                        "Reward Claimed!",
                        "Daily Quest",
                        f"${active_quest.quest.reward.money} and items added!"
                    )

            loops.easy_exit(view_ctx)


# Global instance
daily_quest_manager = DailyQuestManager()
