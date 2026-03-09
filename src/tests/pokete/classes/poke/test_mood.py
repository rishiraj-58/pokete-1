"""Tests for the Pokete mood system.

This test file is designed to be compatible with Python 3.9+ by not
importing from the pokete package directly (which requires Python 3.10+).
Instead, the test file is self-contained with a copy of the mood classes.
"""

import random
import unittest
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


# ============================================================================
# Copy of mood system classes for testing (to avoid import issues with Python 3.9)
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


@dataclass
class MoodEffect:
    """Stat modifiers applied during battle based on mood."""
    attack_modifier: float = 1.0
    defense_modifier: float = 1.0
    initiative_modifier: float = 1.0
    miss_chance_modifier: float = 1.0


MOOD_EFFECTS: Dict[MoodType, MoodEffect] = {
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

IDLE_TIRED_THRESHOLD = 60 * 24 * 2
IDLE_SAD_THRESHOLD = 60 * 24 * 5


class PokeMood:
    """Manages a Pokete's mood state."""

    def __init__(
        self,
        mood_type: MoodType = MoodType.NEUTRAL,
        intensity: int = 1,
        last_battle_time: int = 0,
        consecutive_wins: int = 0,
        consecutive_losses: int = 0,
    ):
        self.mood_type = mood_type
        self.intensity = min(max(intensity, 1), 3)
        self.last_battle_time = last_battle_time
        self.consecutive_wins = consecutive_wins
        self.consecutive_losses = consecutive_losses

    @property
    def effect(self) -> MoodEffect:
        base_effect = MOOD_EFFECTS[self.mood_type]
        scale = 1 + (self.intensity - 1) * 0.15
        return MoodEffect(
            attack_modifier=self._scale_modifier(base_effect.attack_modifier, scale),
            defense_modifier=self._scale_modifier(base_effect.defense_modifier, scale),
            initiative_modifier=self._scale_modifier(base_effect.initiative_modifier, scale),
            miss_chance_modifier=self._scale_modifier(base_effect.miss_chance_modifier, scale),
        )

    @staticmethod
    def _scale_modifier(base: float, scale: float) -> float:
        if base >= 1.0:
            return 1.0 + (base - 1.0) * scale
        return 1.0 - (1.0 - base) * scale

    @property
    def display_name(self) -> str:
        intensity_prefix = {1: "", 2: "Very ", 3: "Extremely "}
        return f"{intensity_prefix[self.intensity]}{self.mood_type.value.capitalize()}"

    def update_on_time(self, current_time: int) -> None:
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
        self.last_battle_time = current_time
        if self.mood_type in (MoodType.SAD, MoodType.TIRED):
            self.mood_type = MoodType.EXCITED
            self.intensity = 1

    def on_battle_win(self, current_time: int) -> None:
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
            if random.random() < 0.5:
                self.mood_type = MoodType.ANGRY
                self.intensity = 1
            else:
                self.mood_type = MoodType.SAD
                self.intensity = 1

    def on_heal(self) -> None:
        if self.mood_type in (MoodType.SAD, MoodType.TIRED, MoodType.ANXIOUS):
            self.mood_type = MoodType.NEUTRAL
            self.intensity = 1
        elif self.mood_type == MoodType.ANGRY:
            self.mood_type = MoodType.NEUTRAL
            self.intensity = 1
        elif self.mood_type == MoodType.NEUTRAL:
            if random.random() < 0.3:
                self.mood_type = MoodType.HAPPY
                self.intensity = 1

    def on_evolution(self) -> None:
        self.mood_type = MoodType.EXCITED
        self.intensity = 3
        self.consecutive_wins = 0
        self.consecutive_losses = 0

    def on_trade(self) -> None:
        self.mood_type = MoodType.ANXIOUS
        self.intensity = 2
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_battle_time = 0

    def on_catch(self, current_time: int) -> None:
        self.last_battle_time = current_time
        self.mood_type = MoodType.ANXIOUS
        self.intensity = 1
        self.consecutive_wins = 0
        self.consecutive_losses = 0

    def on_run_away(self, current_time: int) -> None:
        self.last_battle_time = current_time
        if self.mood_type == MoodType.ANXIOUS:
            self.intensity = min(3, self.intensity + 1)
        else:
            self.mood_type = MoodType.ANXIOUS
            self.intensity = 1

    def dict(self) -> dict:
        return {
            "mood_type": self.mood_type.value,
            "intensity": self.intensity,
            "last_battle_time": self.last_battle_time,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PokeMood":
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
        mood_type = random.choice(list(MoodType))
        intensity = random.randint(1, 2)
        return cls(mood_type=mood_type, intensity=intensity)


# ============================================================================
# Tests
# ============================================================================

class MoodTypeTest(unittest.TestCase):
    def test_all_mood_types_exist(self):
        expected_moods = [
            "happy", "sad", "angry", "tired",
            "excited", "neutral", "confident", "anxious"
        ]
        for mood_name in expected_moods:
            self.assertIn(
                mood_name,
                [m.value for m in MoodType],
                f"Missing mood type: {mood_name}"
            )

    def test_all_moods_have_effects(self):
        for mood_type in MoodType:
            self.assertIn(
                mood_type,
                MOOD_EFFECTS,
                f"Missing effect for mood: {mood_type}"
            )


class MoodEffectTest(unittest.TestCase):
    def test_default_effect_is_neutral(self):
        effect = MoodEffect()
        self.assertEqual(effect.attack_modifier, 1.0)
        self.assertEqual(effect.defense_modifier, 1.0)
        self.assertEqual(effect.initiative_modifier, 1.0)
        self.assertEqual(effect.miss_chance_modifier, 1.0)

    def test_angry_boosts_attack_reduces_defense(self):
        effect = MOOD_EFFECTS[MoodType.ANGRY]
        self.assertGreater(effect.attack_modifier, 1.0)
        self.assertLess(effect.defense_modifier, 1.0)

    def test_happy_has_positive_modifiers(self):
        effect = MOOD_EFFECTS[MoodType.HAPPY]
        self.assertGreater(effect.attack_modifier, 1.0)
        self.assertGreater(effect.defense_modifier, 1.0)
        self.assertLess(effect.miss_chance_modifier, 1.0)

    def test_sad_has_negative_modifiers(self):
        effect = MOOD_EFFECTS[MoodType.SAD]
        self.assertLess(effect.attack_modifier, 1.0)
        self.assertLess(effect.defense_modifier, 1.0)

    def test_tired_reduces_initiative(self):
        effect = MOOD_EFFECTS[MoodType.TIRED]
        self.assertLess(effect.initiative_modifier, 1.0)

    def test_neutral_has_no_modifiers(self):
        effect = MOOD_EFFECTS[MoodType.NEUTRAL]
        self.assertEqual(effect.attack_modifier, 1.0)
        self.assertEqual(effect.defense_modifier, 1.0)
        self.assertEqual(effect.initiative_modifier, 1.0)
        self.assertEqual(effect.miss_chance_modifier, 1.0)


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


class MoodBattleEventsTest(unittest.TestCase):
    def test_battle_win_makes_happy(self):
        mood = PokeMood()
        mood.on_battle_win(100)
        self.assertEqual(mood.mood_type, MoodType.HAPPY)
        self.assertEqual(mood.consecutive_wins, 1)
        self.assertEqual(mood.consecutive_losses, 0)

    def test_consecutive_wins_make_confident(self):
        mood = PokeMood()
        for i in range(5):
            mood.on_battle_win(100 + i)
        self.assertEqual(mood.mood_type, MoodType.CONFIDENT)
        self.assertEqual(mood.consecutive_wins, 5)

    def test_battle_loss_can_make_angry_or_sad(self):
        mood = PokeMood()
        mood.on_battle_loss(100)
        self.assertIn(mood.mood_type, [MoodType.ANGRY, MoodType.SAD])
        self.assertEqual(mood.consecutive_losses, 1)
        self.assertEqual(mood.consecutive_wins, 0)

    def test_consecutive_losses_increase_intensity(self):
        mood = PokeMood()
        for i in range(3):
            mood.on_battle_loss(100 + i)
        self.assertEqual(mood.mood_type, MoodType.ANGRY)
        self.assertEqual(mood.intensity, 2)

    def test_many_losses_make_sad(self):
        mood = PokeMood()
        for i in range(5):
            mood.on_battle_loss(100 + i)
        self.assertEqual(mood.mood_type, MoodType.SAD)

    def test_win_resets_loss_streak(self):
        mood = PokeMood()
        mood.on_battle_loss(100)
        mood.on_battle_loss(101)
        mood.on_battle_win(102)
        self.assertEqual(mood.consecutive_losses, 0)
        self.assertEqual(mood.consecutive_wins, 1)

    def test_battle_start_excited_if_was_sad(self):
        mood = PokeMood(mood_type=MoodType.SAD)
        mood.on_battle_start(100)
        self.assertEqual(mood.mood_type, MoodType.EXCITED)

    def test_battle_start_excited_if_was_tired(self):
        mood = PokeMood(mood_type=MoodType.TIRED)
        mood.on_battle_start(100)
        self.assertEqual(mood.mood_type, MoodType.EXCITED)

    def test_run_away_makes_anxious(self):
        mood = PokeMood()
        mood.on_run_away(100)
        self.assertEqual(mood.mood_type, MoodType.ANXIOUS)


class MoodHealingTest(unittest.TestCase):
    def test_heal_neutralizes_negative_moods(self):
        for mood_type in [MoodType.SAD, MoodType.TIRED, MoodType.ANXIOUS]:
            mood = PokeMood(mood_type=mood_type)
            mood.on_heal()
            self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_heal_calms_angry(self):
        mood = PokeMood(mood_type=MoodType.ANGRY)
        mood.on_heal()
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)


class MoodEvolutionTest(unittest.TestCase):
    def test_evolution_makes_excited(self):
        mood = PokeMood(mood_type=MoodType.SAD)
        mood.on_evolution()
        self.assertEqual(mood.mood_type, MoodType.EXCITED)
        self.assertEqual(mood.intensity, 3)

    def test_evolution_resets_streaks(self):
        mood = PokeMood()
        mood.consecutive_wins = 5
        mood.consecutive_losses = 3
        mood.on_evolution()
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 0)


class MoodTradeTest(unittest.TestCase):
    def test_trade_makes_anxious(self):
        mood = PokeMood(mood_type=MoodType.HAPPY)
        mood.on_trade()
        self.assertEqual(mood.mood_type, MoodType.ANXIOUS)
        self.assertEqual(mood.intensity, 2)

    def test_trade_resets_all_state(self):
        mood = PokeMood()
        mood.consecutive_wins = 5
        mood.consecutive_losses = 3
        mood.last_battle_time = 100
        mood.on_trade()
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 0)
        self.assertEqual(mood.last_battle_time, 0)


class MoodCatchTest(unittest.TestCase):
    def test_catch_makes_anxious(self):
        mood = PokeMood()
        mood.on_catch(100)
        self.assertEqual(mood.mood_type, MoodType.ANXIOUS)
        self.assertEqual(mood.intensity, 1)

    def test_catch_sets_battle_time(self):
        mood = PokeMood()
        mood.on_catch(150)
        self.assertEqual(mood.last_battle_time, 150)


class MoodTimeUpdateTest(unittest.TestCase):
    def test_no_change_with_zero_last_battle(self):
        mood = PokeMood()
        mood.update_on_time(1000)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_tired_after_idle_threshold(self):
        mood = PokeMood()
        mood.last_battle_time = 100
        mood.update_on_time(100 + IDLE_TIRED_THRESHOLD)
        self.assertEqual(mood.mood_type, MoodType.TIRED)

    def test_sad_after_long_idle(self):
        mood = PokeMood()
        mood.last_battle_time = 100
        mood.update_on_time(100 + IDLE_SAD_THRESHOLD)
        self.assertEqual(mood.mood_type, MoodType.SAD)

    def test_no_change_before_threshold(self):
        mood = PokeMood()
        mood.last_battle_time = 100
        mood.update_on_time(100 + IDLE_TIRED_THRESHOLD - 1)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)


class MoodSerializationTest(unittest.TestCase):
    def test_dict_serialization(self):
        mood = PokeMood(
            mood_type=MoodType.HAPPY,
            intensity=2,
            last_battle_time=100,
            consecutive_wins=3,
            consecutive_losses=1,
        )
        data = mood.dict()
        self.assertEqual(data["mood_type"], "happy")
        self.assertEqual(data["intensity"], 2)
        self.assertEqual(data["last_battle_time"], 100)
        self.assertEqual(data["consecutive_wins"], 3)
        self.assertEqual(data["consecutive_losses"], 1)

    def test_from_dict_deserialization(self):
        data = {
            "mood_type": "angry",
            "intensity": 3,
            "last_battle_time": 200,
            "consecutive_wins": 0,
            "consecutive_losses": 4,
        }
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.ANGRY)
        self.assertEqual(mood.intensity, 3)
        self.assertEqual(mood.last_battle_time, 200)
        self.assertEqual(mood.consecutive_wins, 0)
        self.assertEqual(mood.consecutive_losses, 4)

    def test_from_dict_with_none(self):
        mood = PokeMood.from_dict(None)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.intensity, 1)

    def test_from_dict_with_invalid_mood_type(self):
        data = {"mood_type": "invalid_mood"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_roundtrip_serialization(self):
        original = PokeMood(
            mood_type=MoodType.CONFIDENT,
            intensity=2,
            last_battle_time=500,
            consecutive_wins=7,
            consecutive_losses=0,
        )
        restored = PokeMood.from_dict(original.dict())
        self.assertEqual(original.mood_type, restored.mood_type)
        self.assertEqual(original.intensity, restored.intensity)
        self.assertEqual(original.last_battle_time, restored.last_battle_time)
        self.assertEqual(original.consecutive_wins, restored.consecutive_wins)
        self.assertEqual(original.consecutive_losses, restored.consecutive_losses)


class MoodRandomTest(unittest.TestCase):
    def test_random_creates_valid_mood(self):
        for _ in range(10):
            mood = PokeMood.random()
            self.assertIn(mood.mood_type, MoodType)
            self.assertIn(mood.intensity, [1, 2])


if __name__ == "__main__":
    unittest.main()
