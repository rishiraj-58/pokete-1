"""Contains everything related to Pokete mood system.

Mood affects a Pokete's battle stats and changes based on game events
like winning/losing battles, being healed, evolving, being traded, etc.
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import scrap_engine as se

from pokete.base import loops
from pokete.base.color import Color
from pokete.base.context import Context
from pokete.base.ui.elements.labels import CloseLabel
from pokete.base.ui.views.boxes import LabelBoxView
from pokete.classes.model.poke import MoodDict


class MoodType(Enum):
    """Enumeration of all possible mood types."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    TIRED = "tired"
    EXCITED = "excited"
    NEUTRAL = "neutral"
    CONFIDENT = "confident"
    ANXIOUS = "anxious"


@dataclass
class MoodEffect:
    """Stat modifiers applied during battle based on mood."""
    attack_modifier: float = 1.0
    defense_modifier: float = 1.0
    initiative_modifier: float = 1.0
    miss_chance_modifier: float = 1.0  # Higher = more misses


MOOD_EFFECTS: dict[MoodType, MoodEffect] = {
    MoodType.HAPPY: MoodEffect(
        attack_modifier=1.1,
        defense_modifier=1.05,
        initiative_modifier=1.05,
        miss_chance_modifier=0.9
    ),
    MoodType.SAD: MoodEffect(
        attack_modifier=0.9,
        defense_modifier=0.9,
        initiative_modifier=0.85,
        miss_chance_modifier=1.1
    ),
    MoodType.ANGRY: MoodEffect(
        attack_modifier=1.25,
        defense_modifier=0.85,
        initiative_modifier=1.1,
        miss_chance_modifier=1.05
    ),
    MoodType.TIRED: MoodEffect(
        attack_modifier=0.85,
        defense_modifier=0.95,
        initiative_modifier=0.7,
        miss_chance_modifier=1.15
    ),
    MoodType.EXCITED: MoodEffect(
        attack_modifier=1.15,
        defense_modifier=0.95,
        initiative_modifier=1.2,
        miss_chance_modifier=1.0
    ),
    MoodType.NEUTRAL: MoodEffect(
        attack_modifier=1.0,
        defense_modifier=1.0,
        initiative_modifier=1.0,
        miss_chance_modifier=1.0
    ),
    MoodType.CONFIDENT: MoodEffect(
        attack_modifier=1.1,
        defense_modifier=1.1,
        initiative_modifier=1.1,
        miss_chance_modifier=0.85
    ),
    MoodType.ANXIOUS: MoodEffect(
        attack_modifier=0.95,
        defense_modifier=0.9,
        initiative_modifier=1.15,
        miss_chance_modifier=1.2
    ),
}

MOOD_DESCRIPTIONS: dict[MoodType, str] = {
    MoodType.HAPPY: "feeling joyful and energetic",
    MoodType.SAD: "feeling down and unmotivated",
    MoodType.ANGRY: "feeling furious and aggressive",
    MoodType.TIRED: "feeling exhausted and sluggish",
    MoodType.EXCITED: "feeling thrilled and eager to battle",
    MoodType.NEUTRAL: "feeling calm and balanced",
    MoodType.CONFIDENT: "feeling sure of itself",
    MoodType.ANXIOUS: "feeling nervous and on edge",
}

MOOD_COLORS: dict[MoodType, str] = {
    MoodType.HAPPY: Color.yellow,
    MoodType.SAD: Color.blue,
    MoodType.ANGRY: Color.red,
    MoodType.TIRED: Color.gray,
    MoodType.EXCITED: Color.lightgreen,
    MoodType.NEUTRAL: Color.white,
    MoodType.CONFIDENT: Color.cyan,
    MoodType.ANXIOUS: Color.purple,
}

# Time thresholds (in in-game minutes)
IDLE_TIRED_THRESHOLD = 60 * 24 * 2  # 2 in-game days without battle
IDLE_SAD_THRESHOLD = 60 * 24 * 5    # 5 in-game days without battle


class PokeMood:
    """Manages a Pokete's mood state.

    The mood changes based on various game events and influences
    battle stats through modifiers.
    """

    def __init__(
        self,
        mood_type: MoodType = MoodType.NEUTRAL,
        intensity: int = 1,
        last_battle_time: int = 0,
        consecutive_wins: int = 0,
        consecutive_losses: int = 0,
    ):
        self.mood_type = mood_type
        self.intensity = min(max(intensity, 1), 3)  # 1-3 scale
        self.last_battle_time = last_battle_time
        self.consecutive_wins = consecutive_wins
        self.consecutive_losses = consecutive_losses

    @property
    def effect(self) -> MoodEffect:
        """Get the current mood's stat effects, scaled by intensity."""
        base_effect = MOOD_EFFECTS[self.mood_type]
        # Scale the effect based on intensity (1-3)
        scale = 1 + (self.intensity - 1) * 0.15  # 1.0, 1.15, 1.3
        return MoodEffect(
            attack_modifier=self._scale_modifier(base_effect.attack_modifier, scale),
            defense_modifier=self._scale_modifier(base_effect.defense_modifier, scale),
            initiative_modifier=self._scale_modifier(base_effect.initiative_modifier, scale),
            miss_chance_modifier=self._scale_modifier(base_effect.miss_chance_modifier, scale),
        )

    @staticmethod
    def _scale_modifier(base: float, scale: float) -> float:
        """Scale a modifier away from 1.0 based on intensity."""
        if base >= 1.0:
            return 1.0 + (base - 1.0) * scale
        return 1.0 - (1.0 - base) * scale

    @property
    def description(self) -> str:
        """Get a description of the current mood."""
        return MOOD_DESCRIPTIONS[self.mood_type]

    @property
    def color(self) -> str:
        """Get the display color for the current mood."""
        return MOOD_COLORS[self.mood_type]

    @property
    def display_name(self) -> str:
        """Get the display name with intensity prefix."""
        intensity_prefix = {1: "", 2: "Very ", 3: "Extremely "}
        return f"{intensity_prefix[self.intensity]}{self.mood_type.value.capitalize()}"

    def update_on_time(self, current_time: int) -> None:
        """Update mood based on elapsed time since last battle.

        Args:
            current_time: Current in-game time in minutes
        """
        if self.last_battle_time == 0:
            return

        time_since_battle = current_time - self.last_battle_time

        if time_since_battle >= IDLE_SAD_THRESHOLD:
            if self.mood_type != MoodType.SAD:
                self.mood_type = MoodType.SAD
                self.intensity = min(2, 1 + (time_since_battle - IDLE_SAD_THRESHOLD) // (60 * 24))
        elif time_since_battle >= IDLE_TIRED_THRESHOLD:
            if self.mood_type not in (MoodType.SAD, MoodType.TIRED):
                self.mood_type = MoodType.TIRED
                self.intensity = 1

    def on_battle_start(self, current_time: int) -> None:
        """Called when a battle starts.

        Args:
            current_time: Current in-game time in minutes
        """
        self.last_battle_time = current_time

        # If was sad/tired from not being used, become excited to battle
        if self.mood_type in (MoodType.SAD, MoodType.TIRED):
            self.mood_type = MoodType.EXCITED
            self.intensity = 1

    def on_battle_win(self, current_time: int) -> None:
        """Called when the Pokete wins a battle.

        Args:
            current_time: Current in-game time in minutes
        """
        self.last_battle_time = current_time
        self.consecutive_wins += 1
        self.consecutive_losses = 0

        if self.consecutive_wins >= 5:
            self.mood_type = MoodType.CONFIDENT
            self.intensity = min(3, self.consecutive_wins // 3)
        elif self.consecutive_wins >= 3:
            self.mood_type = MoodType.HAPPY
            self.intensity = 2
        else:
            self.mood_type = MoodType.HAPPY
            self.intensity = 1

    def on_battle_loss(self, current_time: int) -> None:
        """Called when the Pokete loses a battle.

        Args:
            current_time: Current in-game time in minutes
        """
        self.last_battle_time = current_time
        self.consecutive_losses += 1
        self.consecutive_wins = 0

        if self.consecutive_losses >= 5:
            self.mood_type = MoodType.SAD
            self.intensity = min(3, self.consecutive_losses // 3)
        elif self.consecutive_losses >= 3:
            self.mood_type = MoodType.ANGRY
            self.intensity = 2
        elif self.consecutive_losses >= 2:
            self.mood_type = MoodType.ANGRY
            self.intensity = 1
        else:
            # Single loss might make them determined
            if random.random() < 0.5:
                self.mood_type = MoodType.ANGRY
                self.intensity = 1
            else:
                self.mood_type = MoodType.SAD
                self.intensity = 1

    def on_heal(self) -> None:
        """Called when the Pokete is healed at a Pokecenter."""
        # Healing improves mood
        if self.mood_type in (MoodType.SAD, MoodType.TIRED, MoodType.ANXIOUS):
            self.mood_type = MoodType.NEUTRAL
            self.intensity = 1
        elif self.mood_type == MoodType.ANGRY:
            # Angry poketes calm down when healed
            self.mood_type = MoodType.NEUTRAL
            self.intensity = 1
        elif self.mood_type == MoodType.NEUTRAL:
            # Already neutral, might become happy
            if random.random() < 0.3:
                self.mood_type = MoodType.HAPPY
                self.intensity = 1

    def on_evolution(self) -> None:
        """Called when the Pokete evolves."""
        # Evolution is exciting!
        self.mood_type = MoodType.EXCITED
        self.intensity = 3
        # Reset streaks
        self.consecutive_wins = 0
        self.consecutive_losses = 0

    def on_trade(self) -> None:
        """Called when the Pokete is traded to a new owner."""
        # Being traded can be anxious at first
        self.mood_type = MoodType.ANXIOUS
        self.intensity = 2
        # Reset all battle-related state
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_battle_time = 0

    def on_catch(self, current_time: int) -> None:
        """Called when the Pokete is caught.

        Args:
            current_time: Current in-game time in minutes
        """
        self.last_battle_time = current_time
        # Newly caught poketes are a bit anxious
        self.mood_type = MoodType.ANXIOUS
        self.intensity = 1
        self.consecutive_wins = 0
        self.consecutive_losses = 0

    def on_run_away(self, current_time: int) -> None:
        """Called when the player runs away from a battle.

        Args:
            current_time: Current in-game time in minutes
        """
        self.last_battle_time = current_time
        # Running away might make the pokete feel anxious or relieved
        if self.mood_type == MoodType.ANXIOUS:
            # Was already anxious, stays anxious
            self.intensity = min(3, self.intensity + 1)
        else:
            self.mood_type = MoodType.ANXIOUS
            self.intensity = 1

    def dict(self) -> MoodDict:
        """Return a dict for serialization."""
        return {
            "mood_type": self.mood_type.value,
            "intensity": self.intensity,
            "last_battle_time": self.last_battle_time,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
        }

    @classmethod
    def from_dict(cls, data: Optional[MoodDict]) -> "PokeMood":
        """Create a PokeMood from a dict."""
        if data is None:
            return cls()

        mood_type_str = data.get("mood_type", MoodType.NEUTRAL.value)
        try:
            mood_type = MoodType(mood_type_str)
        except ValueError:
            mood_type = MoodType.NEUTRAL

        return cls(
            mood_type=mood_type,
            intensity=data.get("intensity", 1),
            last_battle_time=data.get("last_battle_time", 0),
            consecutive_wins=data.get("consecutive_wins", 0),
            consecutive_losses=data.get("consecutive_losses", 0),
        )

    @classmethod
    def random(cls) -> "PokeMood":
        """Create a PokeMood with random initial state (for wild poketes)."""
        mood_type = random.choice(list(MoodType))
        intensity = random.randint(1, 2)
        return cls(mood_type=mood_type, intensity=intensity)


class MoodInfoBox(LabelBoxView):
    """Box to show mood information in the detail view."""

    def __init__(self, mood: PokeMood):
        effect = mood.effect

        # Format stat changes
        def format_stat(name: str, value: float) -> str:
            if value > 1.0:
                return f"+{int((value - 1) * 100)}% {name}"
            elif value < 1.0:
                return f"-{int((1 - value) * 100)}% {name}"
            return f"Normal {name}"

        stats_text = "\n".join([
            format_stat("Attack", effect.attack_modifier),
            format_stat("Defense", effect.defense_modifier),
            format_stat("Initiative", effect.initiative_modifier),
            format_stat("Accuracy", 1.0 / effect.miss_chance_modifier),
        ])

        text = (
            se.Text(f"\nMood: ", state="float")
            + se.Text(mood.display_name, esccode=Color.thicc + mood.color, state="float")
            + se.Text(f"\n\nThis Pokete is {mood.description}.", state="float")
            + se.Text(f"\n\nBattle Effects:\n{stats_text}\n", state="float")
        )

        if mood.consecutive_wins > 0:
            text = text + se.Text(
                f"\nWin streak: {mood.consecutive_wins}", state="float"
            )
        if mood.consecutive_losses > 0:
            text = text + se.Text(
                f"\nLoss streak: {mood.consecutive_losses}", state="float"
            )

        super().__init__(text, name="Mood", info=[CloseLabel()])

    def __call__(self, ctx: Context):
        """Show the mood info box."""
        self.set_ctx(ctx)
        with self.center_add(self.map):
            loops.easy_exit(ctx.with_overview(self))
