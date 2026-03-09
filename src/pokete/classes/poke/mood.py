"""Contains everything related to Pokete mood system.

Mood affects a Pokete's battle stats and changes based on game events
like winning/losing battles, being healed, evolving, being traded, etc.

The mood system uses a data-driven weighted probability transition model
for mood changes, making it easy to add new events without writing new methods.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple

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
    CALM = "calm"


@dataclass
class MoodEffect:
    """Stat modifiers applied during battle based on mood."""
    attack_modifier: float = 1.0
    defense_modifier: float = 1.0
    initiative_modifier: float = 1.0
    miss_chance_modifier: float = 1.0  # Higher = more misses
    xp_modifier: float = 1.0  # XP gain multiplier


MOOD_EFFECTS: Dict[MoodType, MoodEffect] = {
    MoodType.HAPPY: MoodEffect(
        attack_modifier=1.1,
        defense_modifier=1.05,
        initiative_modifier=1.05,
        miss_chance_modifier=0.9,
        xp_modifier=1.15
    ),
    MoodType.SAD: MoodEffect(
        attack_modifier=0.9,
        defense_modifier=0.9,
        initiative_modifier=0.85,
        miss_chance_modifier=1.1,
        xp_modifier=0.85
    ),
    MoodType.ANGRY: MoodEffect(
        attack_modifier=1.25,
        defense_modifier=0.85,
        initiative_modifier=1.1,
        miss_chance_modifier=1.05,
        xp_modifier=1.0
    ),
    MoodType.TIRED: MoodEffect(
        attack_modifier=0.85,
        defense_modifier=0.95,
        initiative_modifier=0.7,
        miss_chance_modifier=1.15,
        xp_modifier=0.9
    ),
    MoodType.EXCITED: MoodEffect(
        attack_modifier=1.15,
        defense_modifier=0.95,
        initiative_modifier=1.2,
        miss_chance_modifier=1.0,
        xp_modifier=1.2
    ),
    MoodType.NEUTRAL: MoodEffect(
        attack_modifier=1.0,
        defense_modifier=1.0,
        initiative_modifier=1.0,
        miss_chance_modifier=1.0,
        xp_modifier=1.0
    ),
    MoodType.CONFIDENT: MoodEffect(
        attack_modifier=1.1,
        defense_modifier=1.1,
        initiative_modifier=1.1,
        miss_chance_modifier=0.85,
        xp_modifier=1.1
    ),
    MoodType.ANXIOUS: MoodEffect(
        attack_modifier=0.95,
        defense_modifier=0.9,
        initiative_modifier=1.15,
        miss_chance_modifier=1.2,
        xp_modifier=0.95
    ),
    MoodType.CALM: MoodEffect(
        attack_modifier=1.0,
        defense_modifier=1.1,
        initiative_modifier=0.95,
        miss_chance_modifier=0.9,
        xp_modifier=1.05
    ),
}

MOOD_DESCRIPTIONS: Dict[MoodType, str] = {
    MoodType.HAPPY: "feeling joyful and energetic",
    MoodType.SAD: "feeling down and unmotivated",
    MoodType.ANGRY: "feeling furious and aggressive",
    MoodType.TIRED: "feeling exhausted and sluggish",
    MoodType.EXCITED: "feeling thrilled and eager to battle",
    MoodType.NEUTRAL: "feeling calm and balanced",
    MoodType.CONFIDENT: "feeling sure of itself",
    MoodType.ANXIOUS: "feeling nervous and on edge",
    MoodType.CALM: "feeling serene and at peace",
}

MOOD_COLORS: Dict[MoodType, str] = {
    MoodType.HAPPY: Color.yellow,
    MoodType.SAD: Color.blue,
    MoodType.ANGRY: Color.red,
    MoodType.TIRED: Color.gray,
    MoodType.EXCITED: Color.lightgreen,
    MoodType.NEUTRAL: Color.white,
    MoodType.CONFIDENT: Color.cyan,
    MoodType.ANXIOUS: Color.purple,
    MoodType.CALM: Color.green,
}

# Short mood indicators for battle HUD
MOOD_INDICATORS: Dict[MoodType, str] = {
    MoodType.HAPPY: "☺",
    MoodType.SAD: "☹",
    MoodType.ANGRY: "⚔",
    MoodType.TIRED: "◐",
    MoodType.EXCITED: "★",
    MoodType.NEUTRAL: "○",
    MoodType.CONFIDENT: "♦",
    MoodType.ANXIOUS: "◇",
    MoodType.CALM: "~",
}

# Time thresholds (in in-game minutes)
IDLE_TIRED_THRESHOLD = 60 * 24 * 2  # 2 in-game days without battle
IDLE_SAD_THRESHOLD = 60 * 24 * 5    # 5 in-game days without battle
MOOD_DECAY_INTERVAL = 60 * 12       # 12 in-game hours for decay tick
HEAVILY_USED_THRESHOLD = 5          # Consecutive battles without rest


# Nature mood affinities: nature_name -> {mood: weight_modifier}
# Weight modifier > 1 means more likely to transition TO this mood
# Weight modifier < 1 means less likely (resistant)
NATURE_MOOD_AFFINITIES: Dict[str, Dict[MoodType, float]] = {
    "brave": {
        MoodType.CONFIDENT: 1.5,
        MoodType.ANXIOUS: 0.3,  # Brave resists anxious
        MoodType.ANGRY: 1.2,
    },
    "relaxed": {
        MoodType.CALM: 1.5,
        MoodType.ANGRY: 0.5,  # Relaxed resists anger
        MoodType.TIRED: 1.3,
    },
    "hasty": {
        MoodType.EXCITED: 1.4,
        MoodType.ANXIOUS: 1.2,
        MoodType.CALM: 0.6,  # Hasty resists calm
    },
    "normal": {},  # No special affinities
}


@dataclass
class MoodTransition:
    """Defines a weighted transition to a target mood."""
    target: MoodType
    weight: float
    intensity: int = 1


@dataclass
class EventTransitions:
    """Defines all possible mood transitions for an event."""
    transitions: List[MoodTransition]
    intensity_change: int = 0  # Change to apply to current intensity
    reset_wins: bool = False
    reset_losses: bool = False


# Data-driven event transitions
# Each event maps to possible mood outcomes with weights
EVENT_TRANSITIONS: Dict[str, EventTransitions] = {
    "battle_win": EventTransitions(
        transitions=[
            MoodTransition(MoodType.HAPPY, 60, 1),
            MoodTransition(MoodType.CONFIDENT, 25, 1),
            MoodTransition(MoodType.EXCITED, 15, 1),
        ],
        reset_losses=True,
    ),
    "battle_win_streak_3": EventTransitions(
        transitions=[
            MoodTransition(MoodType.HAPPY, 40, 2),
            MoodTransition(MoodType.CONFIDENT, 50, 2),
            MoodTransition(MoodType.EXCITED, 10, 1),
        ],
    ),
    "battle_win_streak_5": EventTransitions(
        transitions=[
            MoodTransition(MoodType.CONFIDENT, 70, 2),
            MoodTransition(MoodType.HAPPY, 20, 2),
            MoodTransition(MoodType.EXCITED, 10, 2),
        ],
    ),
    "battle_loss": EventTransitions(
        transitions=[
            MoodTransition(MoodType.SAD, 40, 1),
            MoodTransition(MoodType.ANGRY, 40, 1),
            MoodTransition(MoodType.ANXIOUS, 20, 1),
        ],
        reset_wins=True,
    ),
    "battle_loss_streak_3": EventTransitions(
        transitions=[
            MoodTransition(MoodType.ANGRY, 50, 2),
            MoodTransition(MoodType.SAD, 35, 2),
            MoodTransition(MoodType.ANXIOUS, 15, 1),
        ],
    ),
    "battle_loss_streak_5": EventTransitions(
        transitions=[
            MoodTransition(MoodType.SAD, 60, 2),
            MoodTransition(MoodType.ANGRY, 25, 2),
            MoodTransition(MoodType.ANXIOUS, 15, 2),
        ],
    ),
    "battle_start_from_sad": EventTransitions(
        transitions=[
            MoodTransition(MoodType.EXCITED, 70, 1),
            MoodTransition(MoodType.NEUTRAL, 30, 1),
        ],
    ),
    "battle_start_from_tired": EventTransitions(
        transitions=[
            MoodTransition(MoodType.EXCITED, 50, 1),
            MoodTransition(MoodType.NEUTRAL, 30, 1),
            MoodTransition(MoodType.TIRED, 20, 1),  # Might stay tired
        ],
    ),
    "heal": EventTransitions(
        transitions=[
            MoodTransition(MoodType.NEUTRAL, 50, 1),
            MoodTransition(MoodType.HAPPY, 30, 1),
            MoodTransition(MoodType.CALM, 20, 1),
        ],
    ),
    "cuddle": EventTransitions(
        transitions=[
            MoodTransition(MoodType.HAPPY, 50, 2),
            MoodTransition(MoodType.CALM, 30, 1),
            MoodTransition(MoodType.CONFIDENT, 20, 1),
        ],
    ),
    "evolution": EventTransitions(
        transitions=[
            MoodTransition(MoodType.EXCITED, 80, 3),
            MoodTransition(MoodType.HAPPY, 15, 2),
            MoodTransition(MoodType.CONFIDENT, 5, 2),
        ],
        reset_wins=True,
        reset_losses=True,
    ),
    "level_up": EventTransitions(
        transitions=[
            MoodTransition(MoodType.HAPPY, 50, 1),
            MoodTransition(MoodType.EXCITED, 30, 1),
            MoodTransition(MoodType.CONFIDENT, 20, 1),
        ],
        intensity_change=1,
    ),
    "trade": EventTransitions(
        transitions=[
            MoodTransition(MoodType.ANXIOUS, 60, 2),
            MoodTransition(MoodType.SAD, 25, 1),
            MoodTransition(MoodType.NEUTRAL, 15, 1),
        ],
        reset_wins=True,
        reset_losses=True,
    ),
    "catch": EventTransitions(
        transitions=[
            MoodTransition(MoodType.ANXIOUS, 50, 1),
            MoodTransition(MoodType.NEUTRAL, 30, 1),
            MoodTransition(MoodType.SAD, 20, 1),
        ],
        reset_wins=True,
        reset_losses=True,
    ),
    "run_away": EventTransitions(
        transitions=[
            MoodTransition(MoodType.ANXIOUS, 60, 1),
            MoodTransition(MoodType.CALM, 25, 1),  # Relief
            MoodTransition(MoodType.SAD, 15, 1),
        ],
    ),
    "heavily_used": EventTransitions(
        transitions=[
            MoodTransition(MoodType.TIRED, 60, 2),
            MoodTransition(MoodType.ANGRY, 25, 1),
            MoodTransition(MoodType.SAD, 15, 1),
        ],
    ),
    "idle_tired": EventTransitions(
        transitions=[
            MoodTransition(MoodType.TIRED, 80, 1),
            MoodTransition(MoodType.SAD, 20, 1),
        ],
    ),
    "idle_sad": EventTransitions(
        transitions=[
            MoodTransition(MoodType.SAD, 80, 2),
            MoodTransition(MoodType.TIRED, 20, 1),
        ],
    ),
    "decay_positive": EventTransitions(
        transitions=[
            MoodTransition(MoodType.NEUTRAL, 70, 1),
            MoodTransition(MoodType.CALM, 30, 1),
        ],
        intensity_change=-1,
    ),
    "decay_negative": EventTransitions(
        transitions=[
            MoodTransition(MoodType.NEUTRAL, 60, 1),
            MoodTransition(MoodType.CALM, 20, 1),
            MoodTransition(MoodType.SAD, 20, 1),  # Might linger
        ],
        intensity_change=-1,
    ),
}

# Positive and negative mood categories for decay
POSITIVE_MOODS = {MoodType.HAPPY, MoodType.EXCITED, MoodType.CONFIDENT}
NEGATIVE_MOODS = {MoodType.SAD, MoodType.ANGRY, MoodType.ANXIOUS, MoodType.TIRED}
STABLE_MOODS = {MoodType.NEUTRAL, MoodType.CALM}


class PokeMood:
    """Manages a Pokete's mood state.

    The mood changes based on various game events and influences
    battle stats through modifiers. Uses a data-driven weighted
    probability system for mood transitions.
    """

    def __init__(
        self,
        mood_type: MoodType = MoodType.NEUTRAL,
        intensity: int = 1,
        last_battle_time: int = 0,
        last_mood_update_time: int = 0,
        consecutive_wins: int = 0,
        consecutive_losses: int = 0,
        consecutive_battles: int = 0,
        nature_name: str = "normal",
    ):
        self.mood_type = mood_type
        self.intensity = min(max(intensity, 1), 3)  # 1-3 scale
        self.last_battle_time = last_battle_time
        self.last_mood_update_time = last_mood_update_time
        self.consecutive_wins = consecutive_wins
        self.consecutive_losses = consecutive_losses
        self.consecutive_battles = consecutive_battles
        self.nature_name = nature_name

    def set_nature(self, nature_name: str) -> None:
        """Set the nature for mood affinity calculations."""
        self.nature_name = nature_name

    def _get_nature_affinity(self, mood: MoodType) -> float:
        """Get the nature's affinity modifier for a specific mood."""
        affinities = NATURE_MOOD_AFFINITIES.get(self.nature_name, {})
        return affinities.get(mood, 1.0)

    def _apply_transition(
        self,
        event_name: str,
        current_time: int = 0,
    ) -> None:
        """Apply a mood transition based on event data.

        Args:
            event_name: Name of the event triggering the transition
            current_time: Current game time (for time-based tracking)
        """
        if event_name not in EVENT_TRANSITIONS:
            return

        event = EVENT_TRANSITIONS[event_name]

        # Apply resets
        if event.reset_wins:
            self.consecutive_wins = 0
        if event.reset_losses:
            self.consecutive_losses = 0

        # Calculate weights with nature affinity
        weighted_transitions: List[Tuple[MoodTransition, float]] = []
        for trans in event.transitions:
            affinity = self._get_nature_affinity(trans.target)
            adjusted_weight = trans.weight * affinity
            weighted_transitions.append((trans, adjusted_weight))

        # Normalize weights and select
        total_weight = sum(w for _, w in weighted_transitions)
        if total_weight <= 0:
            return

        roll = random.random() * total_weight
        cumulative = 0.0
        selected = weighted_transitions[0][0]

        for trans, weight in weighted_transitions:
            cumulative += weight
            if roll <= cumulative:
                selected = trans
                break

        # Apply the transition
        self.mood_type = selected.target
        new_intensity = selected.intensity + event.intensity_change
        self.intensity = min(max(new_intensity, 1), 3)

        if current_time > 0:
            self.last_mood_update_time = current_time

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
            xp_modifier=self._scale_modifier(base_effect.xp_modifier, scale),
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
    def indicator(self) -> str:
        """Get the short mood indicator for battle HUD."""
        return MOOD_INDICATORS[self.mood_type]

    @property
    def display_name(self) -> str:
        """Get the display name with intensity prefix."""
        intensity_prefix = {1: "", 2: "Very ", 3: "Extremely "}
        return f"{intensity_prefix[self.intensity]}{self.mood_type.value.capitalize()}"

    def get_xp_multiplier(self) -> float:
        """Get the XP gain multiplier based on current mood."""
        return self.effect.xp_modifier

    def update_on_time(self, current_time: int) -> None:
        """Update mood based on elapsed time.

        Handles idle detection and mood decay towards neutral.

        Args:
            current_time: Current in-game time in minutes
        """
        # Handle idle detection
        if self.last_battle_time > 0:
            time_since_battle = current_time - self.last_battle_time

            if time_since_battle >= IDLE_SAD_THRESHOLD:
                if self.mood_type not in (MoodType.SAD,):
                    self._apply_transition("idle_sad", current_time)
            elif time_since_battle >= IDLE_TIRED_THRESHOLD:
                if self.mood_type not in (MoodType.SAD, MoodType.TIRED):
                    self._apply_transition("idle_tired", current_time)

        # Handle mood decay
        if self.last_mood_update_time > 0:
            time_since_update = current_time - self.last_mood_update_time

            if time_since_update >= MOOD_DECAY_INTERVAL:
                self._apply_decay(current_time)

    def _apply_decay(self, current_time: int) -> None:
        """Apply mood decay towards neutral."""
        if self.mood_type in STABLE_MOODS:
            self.last_mood_update_time = current_time
            return

        if self.mood_type in POSITIVE_MOODS:
            if self.intensity > 1:
                self.intensity -= 1
                self.last_mood_update_time = current_time
            else:
                self._apply_transition("decay_positive", current_time)
        elif self.mood_type in NEGATIVE_MOODS:
            if self.intensity > 1:
                self.intensity -= 1
                self.last_mood_update_time = current_time
            else:
                self._apply_transition("decay_negative", current_time)

    def on_battle_start(self, current_time: int) -> None:
        """Called when a battle starts."""
        self.last_battle_time = current_time
        self.consecutive_battles += 1

        # Check for heavily used
        if self.consecutive_battles >= HEAVILY_USED_THRESHOLD:
            self._apply_transition("heavily_used", current_time)
            return

        # If was sad/tired from not being used, become excited
        if self.mood_type == MoodType.SAD:
            self._apply_transition("battle_start_from_sad", current_time)
        elif self.mood_type == MoodType.TIRED:
            self._apply_transition("battle_start_from_tired", current_time)

    def on_battle_win(self, current_time: int) -> None:
        """Called when the Pokete wins a battle."""
        self.last_battle_time = current_time
        self.consecutive_wins += 1
        self.consecutive_losses = 0

        if self.consecutive_wins >= 5:
            self._apply_transition("battle_win_streak_5", current_time)
        elif self.consecutive_wins >= 3:
            self._apply_transition("battle_win_streak_3", current_time)
        else:
            self._apply_transition("battle_win", current_time)

    def on_battle_loss(self, current_time: int) -> None:
        """Called when the Pokete loses a battle."""
        self.last_battle_time = current_time
        self.consecutive_losses += 1
        self.consecutive_wins = 0

        if self.consecutive_losses >= 5:
            self._apply_transition("battle_loss_streak_5", current_time)
        elif self.consecutive_losses >= 3:
            self._apply_transition("battle_loss_streak_3", current_time)
        else:
            self._apply_transition("battle_loss", current_time)

    def on_heal(self) -> None:
        """Called when the Pokete is healed at a Pokecenter."""
        self.consecutive_battles = 0  # Reset battle fatigue
        self._apply_transition("heal")

    def on_cuddle(self) -> None:
        """Called when the Pokete is cuddled at the Pokecenter."""
        self.consecutive_battles = 0
        self._apply_transition("cuddle")

    def on_evolution(self) -> None:
        """Called when the Pokete evolves."""
        self._apply_transition("evolution")

    def on_level_up(self) -> None:
        """Called when the Pokete levels up."""
        self._apply_transition("level_up")

    def on_trade(self) -> None:
        """Called when the Pokete is traded to a new owner."""
        self.last_battle_time = 0
        self.consecutive_battles = 0
        self._apply_transition("trade")

    def on_catch(self, current_time: int) -> None:
        """Called when the Pokete is caught."""
        self.last_battle_time = current_time
        self.consecutive_battles = 0
        self._apply_transition("catch", current_time)

    def on_run_away(self, current_time: int) -> None:
        """Called when the player runs away from a battle."""
        self.last_battle_time = current_time
        self._apply_transition("run_away", current_time)

    def dict(self) -> MoodDict:
        """Return a dict for serialization."""
        return {
            "mood_type": self.mood_type.value,
            "intensity": self.intensity,
            "last_battle_time": self.last_battle_time,
            "last_mood_update_time": self.last_mood_update_time,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_battles": self.consecutive_battles,
        }

    @classmethod
    def from_dict(cls, data: Optional[MoodDict], nature_name: str = "normal") -> "PokeMood":
        """Create a PokeMood from a dict."""
        if data is None:
            return cls(nature_name=nature_name)

        mood_type_str = data.get("mood_type", MoodType.NEUTRAL.value)
        try:
            mood_type = MoodType(mood_type_str)
        except ValueError:
            mood_type = MoodType.NEUTRAL

        return cls(
            mood_type=mood_type,
            intensity=data.get("intensity", 1),
            last_battle_time=data.get("last_battle_time", 0),
            last_mood_update_time=data.get("last_mood_update_time", 0),
            consecutive_wins=data.get("consecutive_wins", 0),
            consecutive_losses=data.get("consecutive_losses", 0),
            consecutive_battles=data.get("consecutive_battles", 0),
            nature_name=nature_name,
        )

    @classmethod
    def random(cls, nature_name: str = "normal") -> "PokeMood":
        """Create a PokeMood with random initial state (for wild poketes)."""
        mood_type = random.choice(list(MoodType))
        intensity = random.randint(1, 2)
        return cls(mood_type=mood_type, intensity=intensity, nature_name=nature_name)


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
            format_stat("XP Gain", effect.xp_modifier),
        ])

        text = (
            se.Text(f"\nMood: ", state="float")
            + se.Text(mood.display_name, esccode=Color.thicc + mood.color, state="float")
            + se.Text(f" {mood.indicator}", esccode=mood.color, state="float")
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
        if mood.consecutive_battles > 0:
            text = text + se.Text(
                f"\nBattles without rest: {mood.consecutive_battles}", state="float"
            )

        super().__init__(text, name="Mood", info=[CloseLabel()])

    def __call__(self, ctx: Context):
        """Show the mood info box."""
        self.set_ctx(ctx)
        with self.center_add(self.map):
            loops.easy_exit(ctx.with_overview(self))
