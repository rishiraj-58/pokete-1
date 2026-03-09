"""Contains everything related to the mood system for Poketes"""

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
from pokete.util import liner


class MoodType(Enum):
    """Enumeration of all possible mood types"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    TIRED = "tired"
    EXCITED = "excited"
    CALM = "calm"
    ANXIOUS = "anxious"
    NEUTRAL = "neutral"


@dataclass
class MoodEffect:
    """Defines the combat effects of a mood"""
    attack_modifier: float = 1.0
    defense_modifier: float = 1.0
    initiative_modifier: float = 1.0
    miss_chance_modifier: float = 1.0

    @property
    def description(self) -> str:
        parts = []
        if self.attack_modifier != 1.0:
            change = "+" if self.attack_modifier > 1.0 else ""
            parts.append(f"{change}{int((self.attack_modifier - 1) * 100)}% attack")
        if self.defense_modifier != 1.0:
            change = "+" if self.defense_modifier > 1.0 else ""
            parts.append(f"{change}{int((self.defense_modifier - 1) * 100)}% defense")
        if self.initiative_modifier != 1.0:
            change = "+" if self.initiative_modifier > 1.0 else ""
            parts.append(f"{change}{int((self.initiative_modifier - 1) * 100)}% initiative")
        if self.miss_chance_modifier != 1.0:
            change = "+" if self.miss_chance_modifier > 1.0 else ""
            parts.append(f"{change}{int((self.miss_chance_modifier - 1) * 100)}% miss chance")
        return ", ".join(parts) if parts else "No combat effects"


MOOD_EFFECTS: dict[MoodType, MoodEffect] = {
    MoodType.HAPPY: MoodEffect(
        attack_modifier=1.1,
        defense_modifier=1.1,
        miss_chance_modifier=0.9,
    ),
    MoodType.SAD: MoodEffect(
        attack_modifier=0.9,
        defense_modifier=0.9,
        initiative_modifier=0.85,
    ),
    MoodType.ANGRY: MoodEffect(
        attack_modifier=1.25,
        defense_modifier=0.85,
        miss_chance_modifier=1.1,
    ),
    MoodType.TIRED: MoodEffect(
        attack_modifier=0.85,
        defense_modifier=0.85,
        initiative_modifier=0.7,
    ),
    MoodType.EXCITED: MoodEffect(
        attack_modifier=1.15,
        initiative_modifier=1.2,
        miss_chance_modifier=1.05,
    ),
    MoodType.CALM: MoodEffect(
        defense_modifier=1.15,
        miss_chance_modifier=0.85,
    ),
    MoodType.ANXIOUS: MoodEffect(
        attack_modifier=0.9,
        initiative_modifier=1.1,
        miss_chance_modifier=1.15,
    ),
    MoodType.NEUTRAL: MoodEffect(),
}

MOOD_COLORS: dict[MoodType, str] = {
    MoodType.HAPPY: Color.yellow,
    MoodType.SAD: Color.blue,
    MoodType.ANGRY: Color.red,
    MoodType.TIRED: Color.gray,
    MoodType.EXCITED: Color.lightblue,
    MoodType.CALM: Color.green,
    MoodType.ANXIOUS: Color.purple,
    MoodType.NEUTRAL: Color.white,
}

MOOD_DESCRIPTIONS: dict[MoodType, str] = {
    MoodType.HAPPY: "Your Pokete is in a great mood! It's ready to give its all in battle.",
    MoodType.SAD: "Your Pokete seems down. It might not perform at its best.",
    MoodType.ANGRY: "Your Pokete is furious! It hits harder but is reckless.",
    MoodType.TIRED: "Your Pokete is exhausted and needs rest.",
    MoodType.EXCITED: "Your Pokete is bursting with energy! It's faster but a bit wild.",
    MoodType.CALM: "Your Pokete is composed and focused. Its defense is solid.",
    MoodType.ANXIOUS: "Your Pokete seems nervous. It's jittery and error-prone.",
    MoodType.NEUTRAL: "Your Pokete is feeling balanced and ready.",
}

# Time thresholds (in in-game minutes)
TIRED_THRESHOLD = 180  # 3 hours of play without rest
LONELY_THRESHOLD = 120  # 2 hours without being used in battle
MOOD_DECAY_INTERVAL = 60  # Check mood decay every hour


class MoodEvent(Enum):
    """Events that can trigger mood changes"""
    BATTLE_WIN = "battle_win"
    BATTLE_LOSS = "battle_loss"
    HEALED = "healed"
    EVOLVED = "evolved"
    TRADED = "traded"
    CAUGHT = "caught"
    LEVEL_UP = "level_up"
    CUDDLED = "cuddled"
    UNUSED_LONG = "unused_long"
    USED_HEAVILY = "used_heavily"


# Mood transition probabilities based on events
MOOD_TRANSITIONS: dict[MoodEvent, dict[MoodType, list[tuple[MoodType, float]]]] = {
    MoodEvent.BATTLE_WIN: {
        MoodType.NEUTRAL: [(MoodType.HAPPY, 0.6), (MoodType.EXCITED, 0.3), (MoodType.NEUTRAL, 0.1)],
        MoodType.SAD: [(MoodType.NEUTRAL, 0.5), (MoodType.HAPPY, 0.4), (MoodType.SAD, 0.1)],
        MoodType.ANGRY: [(MoodType.HAPPY, 0.4), (MoodType.CALM, 0.3), (MoodType.ANGRY, 0.3)],
        MoodType.TIRED: [(MoodType.TIRED, 0.5), (MoodType.HAPPY, 0.3), (MoodType.NEUTRAL, 0.2)],
        MoodType.HAPPY: [(MoodType.HAPPY, 0.7), (MoodType.EXCITED, 0.3)],
        MoodType.EXCITED: [(MoodType.EXCITED, 0.6), (MoodType.HAPPY, 0.4)],
        MoodType.CALM: [(MoodType.HAPPY, 0.5), (MoodType.CALM, 0.5)],
        MoodType.ANXIOUS: [(MoodType.NEUTRAL, 0.5), (MoodType.HAPPY, 0.4), (MoodType.ANXIOUS, 0.1)],
    },
    MoodEvent.BATTLE_LOSS: {
        MoodType.NEUTRAL: [(MoodType.SAD, 0.4), (MoodType.ANGRY, 0.3), (MoodType.NEUTRAL, 0.3)],
        MoodType.HAPPY: [(MoodType.NEUTRAL, 0.5), (MoodType.SAD, 0.3), (MoodType.HAPPY, 0.2)],
        MoodType.SAD: [(MoodType.SAD, 0.6), (MoodType.ANGRY, 0.2), (MoodType.ANXIOUS, 0.2)],
        MoodType.ANGRY: [(MoodType.ANGRY, 0.7), (MoodType.SAD, 0.3)],
        MoodType.TIRED: [(MoodType.SAD, 0.5), (MoodType.TIRED, 0.5)],
        MoodType.EXCITED: [(MoodType.SAD, 0.4), (MoodType.NEUTRAL, 0.4), (MoodType.ANXIOUS, 0.2)],
        MoodType.CALM: [(MoodType.NEUTRAL, 0.6), (MoodType.SAD, 0.4)],
        MoodType.ANXIOUS: [(MoodType.ANXIOUS, 0.5), (MoodType.SAD, 0.5)],
    },
    MoodEvent.HEALED: {
        MoodType.TIRED: [(MoodType.NEUTRAL, 0.6), (MoodType.HAPPY, 0.3), (MoodType.CALM, 0.1)],
        MoodType.SAD: [(MoodType.NEUTRAL, 0.5), (MoodType.CALM, 0.3), (MoodType.SAD, 0.2)],
        MoodType.ANGRY: [(MoodType.CALM, 0.5), (MoodType.NEUTRAL, 0.4), (MoodType.ANGRY, 0.1)],
        MoodType.ANXIOUS: [(MoodType.CALM, 0.6), (MoodType.NEUTRAL, 0.4)],
        MoodType.NEUTRAL: [(MoodType.HAPPY, 0.4), (MoodType.CALM, 0.3), (MoodType.NEUTRAL, 0.3)],
        MoodType.HAPPY: [(MoodType.HAPPY, 0.8), (MoodType.EXCITED, 0.2)],
        MoodType.EXCITED: [(MoodType.HAPPY, 0.5), (MoodType.EXCITED, 0.5)],
        MoodType.CALM: [(MoodType.CALM, 0.7), (MoodType.HAPPY, 0.3)],
    },
    MoodEvent.EVOLVED: {
        mood: [(MoodType.EXCITED, 0.6), (MoodType.HAPPY, 0.4)]
        for mood in MoodType
    },
    MoodEvent.TRADED: {
        mood: [(MoodType.ANXIOUS, 0.4), (MoodType.SAD, 0.3), (MoodType.NEUTRAL, 0.3)]
        for mood in MoodType
    },
    MoodEvent.CAUGHT: {
        mood: [(MoodType.ANXIOUS, 0.3), (MoodType.NEUTRAL, 0.4), (MoodType.SAD, 0.3)]
        for mood in MoodType
    },
    MoodEvent.LEVEL_UP: {
        mood: [(MoodType.HAPPY, 0.5), (MoodType.EXCITED, 0.3), (mood, 0.2)]
        for mood in MoodType
    },
    MoodEvent.CUDDLED: {
        MoodType.SAD: [(MoodType.NEUTRAL, 0.5), (MoodType.HAPPY, 0.4), (MoodType.SAD, 0.1)],
        MoodType.ANGRY: [(MoodType.CALM, 0.5), (MoodType.NEUTRAL, 0.4), (MoodType.ANGRY, 0.1)],
        MoodType.ANXIOUS: [(MoodType.CALM, 0.6), (MoodType.HAPPY, 0.3), (MoodType.ANXIOUS, 0.1)],
        MoodType.TIRED: [(MoodType.CALM, 0.4), (MoodType.HAPPY, 0.4), (MoodType.TIRED, 0.2)],
        MoodType.NEUTRAL: [(MoodType.HAPPY, 0.6), (MoodType.CALM, 0.3), (MoodType.NEUTRAL, 0.1)],
        MoodType.HAPPY: [(MoodType.HAPPY, 0.9), (MoodType.EXCITED, 0.1)],
        MoodType.EXCITED: [(MoodType.HAPPY, 0.7), (MoodType.EXCITED, 0.3)],
        MoodType.CALM: [(MoodType.HAPPY, 0.5), (MoodType.CALM, 0.5)],
    },
    MoodEvent.UNUSED_LONG: {
        mood: [(MoodType.SAD, 0.4), (MoodType.TIRED, 0.3), (mood, 0.3)]
        for mood in MoodType
    },
    MoodEvent.USED_HEAVILY: {
        mood: [(MoodType.TIRED, 0.6), (MoodType.ANGRY, 0.2), (mood, 0.2)]
        for mood in MoodType
    },
}


class PokeMood:
    """Manages the mood state for a Pokete"""

    def __init__(
        self,
        mood_type: MoodType = MoodType.NEUTRAL,
        last_battle_time: int = 0,
        battles_since_rest: int = 0,
        last_mood_change_time: int = 0,
    ):
        self.mood_type = mood_type
        self.last_battle_time = last_battle_time
        self.battles_since_rest = battles_since_rest
        self.last_mood_change_time = last_mood_change_time
        self.info: Optional["MoodInfo"] = None

    def _init_info(self):
        """Lazily initialize the info box"""
        if self.info is None:
            self.info = MoodInfo(self)

    @property
    def effect(self) -> MoodEffect:
        """Get the combat effects for the current mood"""
        return MOOD_EFFECTS[self.mood_type]

    @property
    def color(self) -> str:
        """Get the color associated with the current mood"""
        return MOOD_COLORS[self.mood_type]

    @property
    def name(self) -> str:
        """Get the display name of the current mood"""
        return self.mood_type.value.capitalize()

    @property
    def description(self) -> str:
        """Get the description of the current mood"""
        return MOOD_DESCRIPTIONS[self.mood_type]

    def get_attack_modifier(self) -> float:
        """Get the attack modifier based on mood"""
        return self.effect.attack_modifier

    def get_defense_modifier(self) -> float:
        """Get the defense modifier based on mood"""
        return self.effect.defense_modifier

    def get_initiative_modifier(self) -> float:
        """Get the initiative modifier based on mood"""
        return self.effect.initiative_modifier

    def get_miss_chance_modifier(self) -> float:
        """Get the miss chance modifier based on mood"""
        return self.effect.miss_chance_modifier

    def trigger_event(self, event: MoodEvent, current_time: int = 0) -> MoodType:
        """
        Trigger a mood event and potentially change the mood.
        Returns the new mood type.
        """
        old_mood = self.mood_type
        transitions = MOOD_TRANSITIONS.get(event, {})
        possible_transitions = transitions.get(
            self.mood_type,
            [(MoodType.NEUTRAL, 1.0)]
        )

        moods, weights = zip(*possible_transitions)
        self.mood_type = random.choices(moods, weights=weights, k=1)[0]

        if self.mood_type != old_mood:
            self.last_mood_change_time = current_time

        # Track battle statistics
        if event in (MoodEvent.BATTLE_WIN, MoodEvent.BATTLE_LOSS):
            self.last_battle_time = current_time
            self.battles_since_rest += 1

        if event == MoodEvent.HEALED:
            self.battles_since_rest = 0

        # Reinitialize info if mood changed
        if self.mood_type != old_mood:
            self.info = None

        return self.mood_type

    def check_time_based_mood(self, current_time: int, last_input_time: int) -> Optional[MoodType]:
        """
        Check and apply time-based mood changes.
        Returns the new mood if it changed, None otherwise.
        """
        old_mood = self.mood_type

        # Check if pokete hasn't been used in battle for a while
        if self.last_battle_time > 0:
            time_since_battle = current_time - self.last_battle_time
            if time_since_battle > LONELY_THRESHOLD:
                self.trigger_event(MoodEvent.UNUSED_LONG, current_time)

        # Check if pokete has been used too much without rest
        if self.battles_since_rest > 5:
            self.trigger_event(MoodEvent.USED_HEAVILY, current_time)

        if self.mood_type != old_mood:
            self.info = None
            return self.mood_type
        return None

    def dict(self) -> MoodDict:
        """Return a dict representation for saving"""
        return {
            "mood_type": self.mood_type.value,
            "last_battle_time": self.last_battle_time,
            "battles_since_rest": self.battles_since_rest,
            "last_mood_change_time": self.last_mood_change_time,
        }

    @classmethod
    def from_dict(cls, data: Optional[MoodDict]) -> "PokeMood":
        """Create a PokeMood from a dict"""
        if data is None:
            return cls()

        mood_str = data.get("mood_type", "neutral")
        try:
            mood_type = MoodType(mood_str)
        except ValueError:
            mood_type = MoodType.NEUTRAL

        return cls(
            mood_type=mood_type,
            last_battle_time=data.get("last_battle_time", 0),
            battles_since_rest=data.get("battles_since_rest", 0),
            last_mood_change_time=data.get("last_mood_change_time", 0),
        )

    @classmethod
    def random(cls) -> "PokeMood":
        """Create a PokeMood with a random mood type"""
        mood_type = random.choice(list(MoodType))
        return cls(mood_type=mood_type)


class MoodInfo(LabelBoxView):
    """Box to show information about a Pokete's mood"""

    def __init__(self, mood: PokeMood):
        effect_desc = mood.effect.description
        text = (
            se.Text(f"Mood: ", state="float")
            + se.Text(mood.name, esccode=Color.thicc + mood.color, state="float")
            + se.Text(
                liner(
                    f"\n\n{mood.description}\n\nCombat effects: {effect_desc}",
                    40,
                    pre="",
                ),
                state="float",
            )
        )
        super().__init__(text, name="Mood", info=[CloseLabel()])

    def __call__(self, ctx: Context):
        """Shows the box"""
        self.set_ctx(ctx)
        with self.center_add(self.map):
            loops.easy_exit(ctx.with_overview(self))


def get_mood_label(mood: PokeMood) -> se.Text:
    """Create a display label for a mood"""
    return se.Text(
        f"({mood.name[:3]})",
        state="float",
        esccode=mood.color,
    )
