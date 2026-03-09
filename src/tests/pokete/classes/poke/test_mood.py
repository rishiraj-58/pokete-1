"""Tests for the Pokete mood system.

This test file is designed to be compatible with Python 3.9+ by being
self-contained with a copy of the mood classes for testing purposes.
"""

import random
import unittest
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Tuple


# ============================================================================
# Copy of mood system classes for testing
# These should be kept in sync with pokete/classes/poke/mood.py
# ============================================================================

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
    miss_chance_modifier: float = 1.0
    xp_modifier: float = 1.0


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

IDLE_TIRED_THRESHOLD = 60 * 24 * 2
IDLE_SAD_THRESHOLD = 60 * 24 * 5
MOOD_DECAY_INTERVAL = 60 * 12
HEAVILY_USED_THRESHOLD = 5

NATURE_MOOD_AFFINITIES: Dict[str, Dict[MoodType, float]] = {
    "brave": {
        MoodType.CONFIDENT: 1.5,
        MoodType.ANXIOUS: 0.3,
        MoodType.ANGRY: 1.2,
    },
    "relaxed": {
        MoodType.CALM: 1.5,
        MoodType.ANGRY: 0.5,
        MoodType.TIRED: 1.3,
    },
    "hasty": {
        MoodType.EXCITED: 1.4,
        MoodType.ANXIOUS: 1.2,
        MoodType.CALM: 0.6,
    },
    "normal": {},
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
    intensity_change: int = 0
    reset_wins: bool = False
    reset_losses: bool = False


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
            MoodTransition(MoodType.TIRED, 20, 1),
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
            MoodTransition(MoodType.CALM, 25, 1),
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
            MoodTransition(MoodType.SAD, 20, 1),
        ],
        intensity_change=-1,
    ),
}

POSITIVE_MOODS = {MoodType.HAPPY, MoodType.EXCITED, MoodType.CONFIDENT}
NEGATIVE_MOODS = {MoodType.SAD, MoodType.ANGRY, MoodType.ANXIOUS, MoodType.TIRED}
STABLE_MOODS = {MoodType.NEUTRAL, MoodType.CALM}


class PokeMood:
    """Manages a Pokete's mood state."""

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
        self.intensity = min(max(intensity, 1), 3)
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
        """Apply a mood transition based on event data."""
        if event_name not in EVENT_TRANSITIONS:
            return

        event = EVENT_TRANSITIONS[event_name]

        if event.reset_wins:
            self.consecutive_wins = 0
        if event.reset_losses:
            self.consecutive_losses = 0

        weighted_transitions: List[Tuple[MoodTransition, float]] = []
        for trans in event.transitions:
            affinity = self._get_nature_affinity(trans.target)
            adjusted_weight = trans.weight * affinity
            weighted_transitions.append((trans, adjusted_weight))

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

        self.mood_type = selected.target
        new_intensity = selected.intensity + event.intensity_change
        self.intensity = min(max(new_intensity, 1), 3)

        if current_time > 0:
            self.last_mood_update_time = current_time

    @property
    def effect(self) -> MoodEffect:
        """Get the current mood's stat effects, scaled by intensity."""
        base_effect = MOOD_EFFECTS[self.mood_type]
        scale = 1 + (self.intensity - 1) * 0.15
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
        """Update mood based on elapsed time."""
        if self.last_battle_time > 0:
            time_since_battle = current_time - self.last_battle_time

            if time_since_battle >= IDLE_SAD_THRESHOLD:
                if self.mood_type not in (MoodType.SAD,):
                    self._apply_transition("idle_sad", current_time)
            elif time_since_battle >= IDLE_TIRED_THRESHOLD:
                if self.mood_type not in (MoodType.SAD, MoodType.TIRED):
                    self._apply_transition("idle_tired", current_time)

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

        if self.consecutive_battles >= HEAVILY_USED_THRESHOLD:
            self._apply_transition("heavily_used", current_time)
            return

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
        self.consecutive_battles = 0
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

    def dict(self) -> dict:
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
    def from_dict(cls, data: Optional[dict], nature_name: str = "normal") -> "PokeMood":
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
        """Create a PokeMood with random initial state."""
        mood_type = random.choice(list(MoodType))
        intensity = random.randint(1, 2)
        return cls(mood_type=mood_type, intensity=intensity, nature_name=nature_name)


# ============================================================================
# Tests
# ============================================================================

class MoodTypeTest(unittest.TestCase):
    def test_all_mood_types_exist(self):
        expected_moods = [
            "happy", "sad", "angry", "tired",
            "excited", "neutral", "confident", "anxious", "calm"
        ]
        for mood_name in expected_moods:
            self.assertIn(
                mood_name,
                [m.value for m in MoodType],
                f"Missing mood type: {mood_name}"
            )

    def test_calm_mood_exists(self):
        """Test that the new CALM mood type exists."""
        self.assertIn(MoodType.CALM, MoodType)
        self.assertEqual(MoodType.CALM.value, "calm")

    def test_all_moods_have_effects(self):
        for mood_type in MoodType:
            self.assertIn(
                mood_type,
                MOOD_EFFECTS,
                f"Missing effect for mood: {mood_type}"
            )

    def test_all_moods_have_indicators(self):
        for mood_type in MoodType:
            self.assertIn(
                mood_type,
                MOOD_INDICATORS,
                f"Missing indicator for mood: {mood_type}"
            )


class MoodEffectTest(unittest.TestCase):
    def test_default_effect_is_neutral(self):
        effect = MoodEffect()
        self.assertEqual(effect.attack_modifier, 1.0)
        self.assertEqual(effect.defense_modifier, 1.0)
        self.assertEqual(effect.initiative_modifier, 1.0)
        self.assertEqual(effect.miss_chance_modifier, 1.0)
        self.assertEqual(effect.xp_modifier, 1.0)

    def test_xp_modifier_exists_for_all_moods(self):
        """Test that all moods have XP modifiers."""
        for mood_type in MoodType:
            effect = MOOD_EFFECTS[mood_type]
            self.assertIsNotNone(effect.xp_modifier)

    def test_positive_moods_have_xp_bonus(self):
        """Positive moods should give XP bonus."""
        for mood_type in POSITIVE_MOODS:
            effect = MOOD_EFFECTS[mood_type]
            self.assertGreater(
                effect.xp_modifier, 1.0,
                f"{mood_type} should have XP bonus"
            )

    def test_negative_moods_have_xp_penalty(self):
        """Negative moods should have XP penalty (or neutral)."""
        for mood_type in NEGATIVE_MOODS:
            effect = MOOD_EFFECTS[mood_type]
            self.assertLessEqual(
                effect.xp_modifier, 1.0,
                f"{mood_type} should have XP penalty or neutral"
            )

    def test_calm_has_defense_bonus(self):
        """Calm mood should have defense bonus."""
        effect = MOOD_EFFECTS[MoodType.CALM]
        self.assertGreater(effect.defense_modifier, 1.0)


class PokeMoodTest(unittest.TestCase):
    def test_default_mood_is_neutral(self):
        mood = PokeMood()
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.intensity, 1)

    def test_intensity_is_clamped(self):
        mood = PokeMood(intensity=0)
        self.assertEqual(mood.intensity, 1)
        mood = PokeMood(intensity=5)
        self.assertEqual(mood.intensity, 3)

    def test_display_name_includes_intensity(self):
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=1)
        self.assertEqual(mood.display_name, "Happy")
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=2)
        self.assertEqual(mood.display_name, "Very Happy")
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=3)
        self.assertEqual(mood.display_name, "Extremely Happy")

    def test_effect_scales_with_intensity(self):
        mood1 = PokeMood(mood_type=MoodType.ANGRY, intensity=1)
        mood2 = PokeMood(mood_type=MoodType.ANGRY, intensity=2)
        mood3 = PokeMood(mood_type=MoodType.ANGRY, intensity=3)

        self.assertLess(mood1.effect.attack_modifier, mood2.effect.attack_modifier)
        self.assertLess(mood2.effect.attack_modifier, mood3.effect.attack_modifier)

    def test_xp_multiplier_property(self):
        """Test get_xp_multiplier returns correct value."""
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=1)
        self.assertGreater(mood.get_xp_multiplier(), 1.0)

        mood = PokeMood(mood_type=MoodType.SAD, intensity=1)
        self.assertLess(mood.get_xp_multiplier(), 1.0)

    def test_indicator_property(self):
        """Test that mood indicator is returned correctly."""
        for mood_type in MoodType:
            mood = PokeMood(mood_type=mood_type)
            self.assertEqual(mood.indicator, MOOD_INDICATORS[mood_type])


class NatureMoodAffinityTest(unittest.TestCase):
    def test_brave_resists_anxious(self):
        """Brave nature should resist becoming anxious."""
        affinity = NATURE_MOOD_AFFINITIES["brave"].get(MoodType.ANXIOUS, 1.0)
        self.assertLess(affinity, 1.0)

    def test_brave_attracted_to_confident(self):
        """Brave nature should be more likely to become confident."""
        affinity = NATURE_MOOD_AFFINITIES["brave"].get(MoodType.CONFIDENT, 1.0)
        self.assertGreater(affinity, 1.0)

    def test_relaxed_resists_angry(self):
        """Relaxed nature should resist becoming angry."""
        affinity = NATURE_MOOD_AFFINITIES["relaxed"].get(MoodType.ANGRY, 1.0)
        self.assertLess(affinity, 1.0)

    def test_relaxed_attracted_to_calm(self):
        """Relaxed nature should be more likely to become calm."""
        affinity = NATURE_MOOD_AFFINITIES["relaxed"].get(MoodType.CALM, 1.0)
        self.assertGreater(affinity, 1.0)

    def test_hasty_resists_calm(self):
        """Hasty nature should resist becoming calm."""
        affinity = NATURE_MOOD_AFFINITIES["hasty"].get(MoodType.CALM, 1.0)
        self.assertLess(affinity, 1.0)

    def test_nature_affects_transition(self):
        """Test that nature affects mood transition probabilities."""
        # Set seed for reproducibility
        random.seed(42)
        
        # Run many trials with brave nature
        brave_anxious_count = 0
        for _ in range(100):
            mood = PokeMood(nature_name="brave")
            mood.on_catch(100)
            if mood.mood_type == MoodType.ANXIOUS:
                brave_anxious_count += 1

        # Run many trials with normal nature
        random.seed(42)
        normal_anxious_count = 0
        for _ in range(100):
            mood = PokeMood(nature_name="normal")
            mood.on_catch(100)
            if mood.mood_type == MoodType.ANXIOUS:
                normal_anxious_count += 1

        # Brave should have fewer anxious outcomes
        self.assertLess(brave_anxious_count, normal_anxious_count)


class EventTransitionsTest(unittest.TestCase):
    def test_all_required_events_exist(self):
        """Test that all required event transitions are defined."""
        required_events = [
            "battle_win", "battle_loss", "heal", "cuddle",
            "evolution", "level_up", "trade", "catch",
            "run_away", "heavily_used"
        ]
        for event in required_events:
            self.assertIn(
                event, EVENT_TRANSITIONS,
                f"Missing event transition: {event}"
            )

    def test_cuddle_event_exists(self):
        """Test that cuddle event is defined."""
        self.assertIn("cuddle", EVENT_TRANSITIONS)
        cuddle = EVENT_TRANSITIONS["cuddle"]
        # Cuddle should lead to positive moods
        targets = [t.target for t in cuddle.transitions]
        self.assertIn(MoodType.HAPPY, targets)

    def test_level_up_event_exists(self):
        """Test that level_up event is defined."""
        self.assertIn("level_up", EVENT_TRANSITIONS)
        level_up = EVENT_TRANSITIONS["level_up"]
        # Level up should increase intensity
        self.assertGreater(level_up.intensity_change, 0)

    def test_heavily_used_event_exists(self):
        """Test that heavily_used event is defined."""
        self.assertIn("heavily_used", EVENT_TRANSITIONS)
        heavily_used = EVENT_TRANSITIONS["heavily_used"]
        # Should lead to tired
        targets = [t.target for t in heavily_used.transitions]
        self.assertIn(MoodType.TIRED, targets)


class MoodBattleEventsTest(unittest.TestCase):
    def test_battle_win_transitions(self):
        mood = PokeMood()
        mood.on_battle_win(100)
        self.assertIn(mood.mood_type, [MoodType.HAPPY, MoodType.CONFIDENT, MoodType.EXCITED])
        self.assertEqual(mood.consecutive_wins, 1)
        self.assertEqual(mood.consecutive_losses, 0)

    def test_consecutive_wins_streak(self):
        mood = PokeMood()
        for i in range(5):
            mood.on_battle_win(100 + i)
        self.assertEqual(mood.consecutive_wins, 5)
        # Should use win_streak_5 transition
        self.assertIn(mood.mood_type, [MoodType.CONFIDENT, MoodType.HAPPY, MoodType.EXCITED])

    def test_battle_loss_transitions(self):
        mood = PokeMood()
        mood.on_battle_loss(100)
        self.assertIn(mood.mood_type, [MoodType.SAD, MoodType.ANGRY, MoodType.ANXIOUS])
        self.assertEqual(mood.consecutive_losses, 1)
        self.assertEqual(mood.consecutive_wins, 0)

    def test_win_resets_loss_streak(self):
        mood = PokeMood()
        mood.on_battle_loss(100)
        mood.on_battle_loss(101)
        mood.on_battle_win(102)
        self.assertEqual(mood.consecutive_losses, 0)
        self.assertEqual(mood.consecutive_wins, 1)

    def test_battle_start_from_sad_gets_excited(self):
        mood = PokeMood(mood_type=MoodType.SAD)
        mood.on_battle_start(100)
        self.assertIn(mood.mood_type, [MoodType.EXCITED, MoodType.NEUTRAL])

    def test_heavily_used_triggers_tired(self):
        """Test that many consecutive battles cause tiredness."""
        mood = PokeMood()
        for i in range(HEAVILY_USED_THRESHOLD):
            mood.on_battle_start(100 + i)
        self.assertIn(mood.mood_type, [MoodType.TIRED, MoodType.ANGRY, MoodType.SAD])


class MoodCuddleTest(unittest.TestCase):
    def test_cuddle_improves_mood(self):
        """Test that cuddling leads to positive moods."""
        for _ in range(10):  # Run multiple times due to randomness
            mood = PokeMood(mood_type=MoodType.SAD)
            mood.on_cuddle()
            self.assertIn(mood.mood_type, [MoodType.HAPPY, MoodType.CALM, MoodType.CONFIDENT])

    def test_cuddle_resets_battle_fatigue(self):
        """Test that cuddling resets consecutive battles."""
        mood = PokeMood()
        mood.consecutive_battles = 5
        mood.on_cuddle()
        self.assertEqual(mood.consecutive_battles, 0)

    def test_cuddle_can_increase_intensity(self):
        """Test that cuddling can result in higher intensity mood."""
        found_high_intensity = False
        for _ in range(50):  # Run multiple times
            mood = PokeMood(mood_type=MoodType.NEUTRAL)
            mood.on_cuddle()
            if mood.intensity >= 2:
                found_high_intensity = True
                break
        self.assertTrue(found_high_intensity)


class MoodLevelUpTest(unittest.TestCase):
    def test_level_up_transitions_to_positive(self):
        """Test that level up leads to positive moods."""
        for _ in range(10):
            mood = PokeMood(mood_type=MoodType.NEUTRAL)
            mood.on_level_up()
            self.assertIn(mood.mood_type, [MoodType.HAPPY, MoodType.EXCITED, MoodType.CONFIDENT])

    def test_level_up_increases_intensity(self):
        """Test that level up can boost intensity."""
        # Level up has intensity_change=1
        found_increased = False
        for _ in range(20):
            mood = PokeMood(mood_type=MoodType.NEUTRAL, intensity=1)
            mood.on_level_up()
            if mood.intensity >= 2:
                found_increased = True
                break
        self.assertTrue(found_increased)


class MoodHealingTest(unittest.TestCase):
    def test_heal_can_calm_negative_moods(self):
        """Test that healing can transition from negative moods."""
        for _ in range(10):
            mood = PokeMood(mood_type=MoodType.SAD)
            mood.on_heal()
            self.assertIn(mood.mood_type, [MoodType.NEUTRAL, MoodType.HAPPY, MoodType.CALM])

    def test_heal_resets_battle_fatigue(self):
        """Test that healing resets consecutive battles."""
        mood = PokeMood()
        mood.consecutive_battles = 5
        mood.on_heal()
        self.assertEqual(mood.consecutive_battles, 0)


class MoodEvolutionTest(unittest.TestCase):
    def test_evolution_makes_excited(self):
        for _ in range(10):
            mood = PokeMood(mood_type=MoodType.SAD)
            mood.on_evolution()
            self.assertIn(mood.mood_type, [MoodType.EXCITED, MoodType.HAPPY, MoodType.CONFIDENT])

    def test_evolution_resets_streaks(self):
        mood = PokeMood()
        mood.consecutive_wins = 5
        mood.consecutive_losses = 3
        mood.on_evolution()
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 0)


class MoodTradeTest(unittest.TestCase):
    def test_trade_makes_anxious_or_sad(self):
        for _ in range(10):
            mood = PokeMood(mood_type=MoodType.HAPPY)
            mood.on_trade()
            self.assertIn(mood.mood_type, [MoodType.ANXIOUS, MoodType.SAD, MoodType.NEUTRAL])

    def test_trade_resets_all_state(self):
        mood = PokeMood()
        mood.consecutive_wins = 5
        mood.consecutive_losses = 3
        mood.last_battle_time = 100
        mood.consecutive_battles = 3
        mood.on_trade()
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 0)
        self.assertEqual(mood.last_battle_time, 0)
        self.assertEqual(mood.consecutive_battles, 0)


class MoodTimeUpdateTest(unittest.TestCase):
    def test_no_change_with_zero_last_battle(self):
        mood = PokeMood()
        mood.update_on_time(1000)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_tired_after_idle_threshold(self):
        mood = PokeMood()
        mood.last_battle_time = 100
        mood.update_on_time(100 + IDLE_TIRED_THRESHOLD)
        self.assertIn(mood.mood_type, [MoodType.TIRED, MoodType.SAD])

    def test_sad_after_long_idle(self):
        mood = PokeMood()
        mood.last_battle_time = 100
        mood.update_on_time(100 + IDLE_SAD_THRESHOLD)
        self.assertIn(mood.mood_type, [MoodType.SAD, MoodType.TIRED])


class MoodDecayTest(unittest.TestCase):
    def test_positive_mood_decays(self):
        """Test that positive moods decay over time."""
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=3)
        mood.last_mood_update_time = 100

        # Apply decay
        mood.update_on_time(100 + MOOD_DECAY_INTERVAL)
        
        # Intensity should decrease or mood should change
        self.assertTrue(
            mood.intensity < 3 or mood.mood_type != MoodType.HAPPY
        )

    def test_negative_mood_decays(self):
        """Test that negative moods decay over time."""
        mood = PokeMood(mood_type=MoodType.ANGRY, intensity=3)
        mood.last_mood_update_time = 100

        mood.update_on_time(100 + MOOD_DECAY_INTERVAL)
        
        self.assertTrue(
            mood.intensity < 3 or mood.mood_type != MoodType.ANGRY
        )

    def test_neutral_mood_stable(self):
        """Test that neutral mood doesn't decay."""
        mood = PokeMood(mood_type=MoodType.NEUTRAL, intensity=1)
        mood.last_mood_update_time = 100

        mood.update_on_time(100 + MOOD_DECAY_INTERVAL)
        
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_calm_mood_stable(self):
        """Test that calm mood doesn't decay."""
        mood = PokeMood(mood_type=MoodType.CALM, intensity=1)
        mood.last_mood_update_time = 100

        mood.update_on_time(100 + MOOD_DECAY_INTERVAL)
        
        self.assertEqual(mood.mood_type, MoodType.CALM)

    def test_intensity_decreases_before_mood_change(self):
        """Test that intensity decreases before mood type changes."""
        mood = PokeMood(mood_type=MoodType.HAPPY, intensity=3)
        mood.last_mood_update_time = 100

        # First decay should reduce intensity
        mood._apply_decay(100 + MOOD_DECAY_INTERVAL)
        self.assertEqual(mood.intensity, 2)
        self.assertEqual(mood.mood_type, MoodType.HAPPY)


class MoodSerializationTest(unittest.TestCase):
    def test_dict_serialization(self):
        mood = PokeMood(
            mood_type=MoodType.HAPPY,
            intensity=2,
            last_battle_time=100,
            last_mood_update_time=50,
            consecutive_wins=3,
            consecutive_losses=1,
            consecutive_battles=2,
        )
        data = mood.dict()
        self.assertEqual(data["mood_type"], "happy")
        self.assertEqual(data["intensity"], 2)
        self.assertEqual(data["last_battle_time"], 100)
        self.assertEqual(data["last_mood_update_time"], 50)
        self.assertEqual(data["consecutive_wins"], 3)
        self.assertEqual(data["consecutive_losses"], 1)
        self.assertEqual(data["consecutive_battles"], 2)

    def test_from_dict_deserialization(self):
        data = {
            "mood_type": "angry",
            "intensity": 3,
            "last_battle_time": 200,
            "last_mood_update_time": 150,
            "consecutive_wins": 0,
            "consecutive_losses": 4,
            "consecutive_battles": 3,
        }
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.ANGRY)
        self.assertEqual(mood.intensity, 3)
        self.assertEqual(mood.last_battle_time, 200)
        self.assertEqual(mood.last_mood_update_time, 150)
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 4)
        self.assertEqual(mood.consecutive_battles, 3)

    def test_from_dict_with_none(self):
        mood = PokeMood.from_dict(None)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.intensity, 1)

    def test_from_dict_with_invalid_mood_type(self):
        data = {"mood_type": "invalid_mood"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_from_dict_preserves_nature(self):
        """Test that nature is preserved through serialization."""
        mood = PokeMood.from_dict(None, nature_name="brave")
        self.assertEqual(mood.nature_name, "brave")

    def test_roundtrip_serialization(self):
        original = PokeMood(
            mood_type=MoodType.CONFIDENT,
            intensity=2,
            last_battle_time=500,
            last_mood_update_time=400,
            consecutive_wins=7,
            consecutive_losses=0,
            consecutive_battles=5,
            nature_name="brave",
        )
        restored = PokeMood.from_dict(original.dict(), nature_name="brave")
        self.assertEqual(original.mood_type, restored.mood_type)
        self.assertEqual(original.intensity, restored.intensity)
        self.assertEqual(original.last_battle_time, restored.last_battle_time)
        self.assertEqual(original.last_mood_update_time, restored.last_mood_update_time)
        self.assertEqual(original.consecutive_wins, restored.consecutive_wins)
        self.assertEqual(original.consecutive_losses, restored.consecutive_losses)
        self.assertEqual(original.consecutive_battles, restored.consecutive_battles)


class MoodRandomTest(unittest.TestCase):
    def test_random_creates_valid_mood(self):
        for _ in range(10):
            mood = PokeMood.random()
            self.assertIn(mood.mood_type, MoodType)
            self.assertIn(mood.intensity, [1, 2])

    def test_random_with_nature(self):
        """Test that random respects nature parameter."""
        mood = PokeMood.random(nature_name="brave")
        self.assertEqual(mood.nature_name, "brave")


class MoodIndicatorTest(unittest.TestCase):
    def test_all_moods_have_unique_indicators(self):
        """Test that all moods have unique indicators."""
        indicators = list(MOOD_INDICATORS.values())
        self.assertEqual(len(indicators), len(set(indicators)))

    def test_indicator_is_single_char_or_short(self):
        """Test that indicators are short for HUD display."""
        for indicator in MOOD_INDICATORS.values():
            self.assertLessEqual(len(indicator), 2)


if __name__ == "__main__":
    unittest.main()
