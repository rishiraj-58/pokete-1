"""UI components for the daily quest system."""
from __future__ import annotations
import logging
from typing import Optional

import scrap_engine as se

from pokete.base import loops
from pokete.base.change import change_ctx
from pokete.base.color import Color
from pokete.base.context import Context
from pokete.base.input_loops import ask_ok
from pokete.base.ui.elements.labels import CloseLabel
from pokete.base.ui.notify import notifier
from pokete.base.ui.views.boxes import LabelBoxView
from pokete.util import liner

from .quest import Quest
from .quest_manager import daily_quest_manager


class QuestIndicator(se.Object):
    """Small indicator showing quest status on the movemap."""

    INDICATOR_ACTIVE = "Q"
    INDICATOR_COMPLETE = "!"
    INDICATOR_NONE = " "

    def __init__(self):
        super().__init__(self.INDICATOR_NONE, state="float")
        self._quest: Quest | None = None

    def update(self, quest: Quest | None = None):
        """Update indicator based on current quest state."""
        if quest is None:
            quest = daily_quest_manager.current_quest

        self._quest = quest

        if quest is None:
            self.rechar(self.INDICATOR_NONE)
        elif quest.is_completed and not quest.is_claimed:
            self.rechar(
                self.INDICATOR_COMPLETE,
                esccode=Color.green + Color.thicc
            )
        elif not quest.is_claimed:
            self.rechar(
                self.INDICATOR_ACTIVE,
                esccode=Color.yellow
            )
        else:
            self.rechar(self.INDICATOR_NONE)

    def get_tooltip(self) -> str:
        """Get tooltip text for the indicator."""
        if self._quest is None:
            return "No active quest"
        if self._quest.is_claimed:
            return "Quest completed!"
        if self._quest.is_completed:
            return f"{self._quest.name} - Ready to claim!"
        return f"{self._quest.name}: {self._quest.progress_display}"


class QuestProgressBar:
    """Simple text-based progress bar."""

    def __init__(self, width: int = 20):
        self._width = max(5, width)

    def render(self, progress: int, target: int) -> str:
        """Render progress bar as string."""
        if target <= 0:
            return "[" + "=" * self._width + "]"

        filled = int((progress / target) * self._width)
        filled = min(filled, self._width)
        empty = self._width - filled

        return "[" + "=" * filled + "-" * empty + "]"


class QuestInfoBox(LabelBoxView):
    """Box displaying detailed quest information."""

    def __init__(self, quest: Quest):
        progress_bar = QuestProgressBar(18)
        bar_text = progress_bar.render(quest.progress, quest.target)

        status_text = "In Progress"
        status_color = Color.yellow
        if quest.is_claimed:
            status_text = "Completed"
            status_color = Color.grey
        elif quest.is_completed:
            status_text = "Ready to Claim!"
            status_color = Color.green

        rewards_text = self._format_rewards(quest)

        label = (
            se.Text(quest.desc + "\n\n", state="float")
            + se.Text("Progress: ", state="float")
            + se.Text(
                quest.progress_display,
                esccode=Color.thicc,
                state="float"
            )
            + se.Text("\n" + bar_text + "\n\n", state="float")
            + se.Text("Status: ", state="float")
            + se.Text(
                status_text,
                esccode=status_color + Color.thicc,
                state="float"
            )
            + se.Text("\n\nRewards:\n", state="float")
            + se.Text(rewards_text, state="float")
        )

        super().__init__(
            label,
            name=quest.name,
            info=[CloseLabel()],
        )

    def _format_rewards(self, quest: Quest) -> str:
        """Format reward text."""
        lines = []
        config = quest.config

        if config.reward_money > 0:
            lines.append(f"  ${config.reward_money}")

        for item_name, count in config.reward_items.items():
            pretty_name = item_name.replace("_", " ").title()
            lines.append(f"  {count}x {pretty_name}")

        return "\n".join(lines) if lines else "  None"


class QuestOverview(LabelBoxView):
    """Overview box for daily quest with claim functionality."""

    def __init__(self):
        label = se.Text("Loading...", state="float")
        super().__init__(
            label,
            name="Daily Quest",
            info=[CloseLabel()],
        )
        self._quest: Quest | None = None

    def __call__(self, ctx: Context) -> Optional[Never]:
        """Display the quest overview."""
        self._quest = daily_quest_manager.current_quest
        self._update_content()

        with self.center_add(ctx.map) as overview:
            overview.set_ctx(ctx)
            new_ctx = change_ctx(ctx, overview)

            if self._quest and self._quest.is_completed and not self._quest.is_claimed:
                self._handle_claim(new_ctx)
            else:
                loops.easy_exit(new_ctx)

        return None

    def _update_content(self):
        """Update the box content based on current quest."""
        if self._quest is None:
            self._set_no_quest_content()
            return

        progress_bar = QuestProgressBar(18)
        bar_text = progress_bar.render(self._quest.progress, self._quest.target)

        status_text, status_color = self._get_status_display()
        rewards_text = self._format_rewards()

        label = (
            se.Text(liner(self._quest.desc, 28) + "\n\n", state="float")
            + se.Text("Progress: ", state="float")
            + se.Text(
                self._quest.progress_display,
                esccode=Color.thicc,
                state="float"
            )
            + se.Text("\n" + bar_text + "\n\n", state="float")
            + se.Text("Status: ", state="float")
            + se.Text(
                status_text,
                esccode=status_color + Color.thicc,
                state="float"
            )
            + se.Text("\n\nRewards:\n", state="float")
            + se.Text(rewards_text, state="float")
        )

        self.label = label
        self.resize()

    def _set_no_quest_content(self):
        """Set content when no quest is active."""
        self.label = se.Text(
            "No active quest today.\nCheck back tomorrow!",
            state="float"
        )
        self.resize()

    def _get_status_display(self) -> tuple[str, str]:
        """Get status text and color."""
        if self._quest is None:
            return "None", Color.grey

        if self._quest.is_claimed:
            return "Completed", Color.grey
        if self._quest.is_completed:
            return "Ready to Claim!", Color.green
        return "In Progress", Color.yellow

    def _format_rewards(self) -> str:
        """Format reward text."""
        if self._quest is None:
            return "  None"

        lines = []
        config = self._quest.config

        if config.reward_money > 0:
            lines.append(f"  ${config.reward_money}")

        for item_name, count in config.reward_items.items():
            pretty_name = item_name.replace("_", " ").title()
            lines.append(f"  {count}x {pretty_name}")

        return "\n".join(lines) if lines else "  None"

    def _handle_claim(self, ctx: Context):
        """Handle claiming rewards."""
        rewards = daily_quest_manager.claim_reward(ctx.figure)

        if rewards:
            reward_lines = []
            if rewards.get("money", 0) > 0:
                reward_lines.append(f"${rewards['money']}")
            for item, count in rewards.get("items", {}).items():
                pretty_name = item.replace("_", " ").title()
                reward_lines.append(f"{count}x {pretty_name}")

            reward_text = ", ".join(reward_lines) if reward_lines else "Nothing"

            notifier.notify(
                "Quest Complete!",
                "Daily Quest",
                f"Received: {reward_text}"
            )
            logging.info("[QuestUI] Rewards claimed: %s", rewards)

            self._update_content()

        loops.easy_exit(ctx)


def notify_quest_complete(quest: Quest):
    """Show notification when quest is completed."""
    if quest is None:
        return
    notifier.notify(
        quest.name,
        "Quest Complete!",
        "Open quest menu to claim your reward!"
    )


def notify_quest_progress(quest: Quest):
    """Show notification for quest progress (optional, can be noisy)."""
    pass


def show_quest_assigned_notification(quest: Quest):
    """Show notification when new quest is assigned."""
    if quest is None:
        return
    notifier.notify(
        quest.name,
        "New Daily Quest!",
        f"{quest.desc}\nTarget: {quest.target}"
    )
