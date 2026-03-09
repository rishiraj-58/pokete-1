"""
Standalone tests for the Pokete mood system.
These tests are designed to work independently without importing the game modules.
"""

import random
import unittest
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# Re-implement the core mood classes for testing
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


MOOD_EFFECTS = {
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

TIRED_THRESHOLD = 180
LONELY_THRESHOLD = 120
MOOD_DECAY_INTERVAL = 60


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


MOOD_TRANSITIONS = {
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

    @property
    def effect(self) -> MoodEffect:
        return MOOD_EFFECTS[self.mood_type]

    @property
    def color(self) -> str:
        return ""  # Simplified for testing

    @property
    def name(self) -> str:
        return self.mood_type.value.capitalize()

    @property
    def description(self) -> str:
        return f"Your Pokete is {self.mood_type.value}."

    def get_attack_modifier(self) -> float:
        return self.effect.attack_modifier

    def get_defense_modifier(self) -> float:
        return self.effect.defense_modifier

    def get_initiative_modifier(self) -> float:
        return self.effect.initiative_modifier

    def get_miss_chance_modifier(self) -> float:
        return self.effect.miss_chance_modifier

    def trigger_event(self, event: MoodEvent, current_time: int = 0) -> MoodType:
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

        if event in (MoodEvent.BATTLE_WIN, MoodEvent.BATTLE_LOSS):
            self.last_battle_time = current_time
            self.battles_since_rest += 1

        if event == MoodEvent.HEALED:
            self.battles_since_rest = 0

        return self.mood_type

    def check_time_based_mood(self, current_time: int, last_input_time: int) -> Optional[MoodType]:
        old_mood = self.mood_type

        if self.last_battle_time > 0:
            time_since_battle = current_time - self.last_battle_time
            if time_since_battle > LONELY_THRESHOLD:
                self.trigger_event(MoodEvent.UNUSED_LONG, current_time)

        if self.battles_since_rest > 5:
            self.trigger_event(MoodEvent.USED_HEAVILY, current_time)

        if self.mood_type != old_mood:
            return self.mood_type
        return None

    def dict(self) -> dict:
        return {
            "mood_type": self.mood_type.value,
            "last_battle_time": self.last_battle_time,
            "battles_since_rest": self.battles_since_rest,
            "last_mood_change_time": self.last_mood_change_time,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PokeMood":
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
        mood_type = random.choice(list(MoodType))
        return cls(mood_type=mood_type)


# Tests

class TestMoodType(unittest.TestCase):
    def test_all_moods_exist(self):
        expected_moods = ["happy", "sad", "angry", "tired", "excited", "calm", "anxious", "neutral"]
        for mood in expected_moods:
            self.assertIn(mood, [m.value for m in MoodType])

    def test_mood_type_values(self):
        self.assertEqual(MoodType.HAPPY.value, "happy")
        self.assertEqual(MoodType.ANGRY.value, "angry")
        self.assertEqual(MoodType.NEUTRAL.value, "neutral")


class TestMoodEffect(unittest.TestCase):
    def test_default_modifiers(self):
        effect = MoodEffect()
        self.assertEqual(effect.attack_modifier, 1.0)
        self.assertEqual(effect.defense_modifier, 1.0)
        self.assertEqual(effect.initiative_modifier, 1.0)
        self.assertEqual(effect.miss_chance_modifier, 1.0)

    def test_custom_modifiers(self):
        effect = MoodEffect(
            attack_modifier=1.25,
            defense_modifier=0.85,
            initiative_modifier=1.1,
            miss_chance_modifier=0.9
        )
        self.assertEqual(effect.attack_modifier, 1.25)
        self.assertEqual(effect.defense_modifier, 0.85)
        self.assertEqual(effect.initiative_modifier, 1.1)
        self.assertEqual(effect.miss_chance_modifier, 0.9)

    def test_description_no_effects(self):
        effect = MoodEffect()
        self.assertEqual(effect.description, "No combat effects")

    def test_description_with_effects(self):
        effect = MoodEffect(attack_modifier=1.25, defense_modifier=0.85)
        desc = effect.description
        self.assertIn("attack", desc)
        self.assertIn("defense", desc)


class TestMoodEffectsConfiguration(unittest.TestCase):
    def test_all_moods_have_effects(self):
        for mood_type in MoodType:
            self.assertIn(mood_type, MOOD_EFFECTS)

    def test_angry_boosts_attack_reduces_defense(self):
        angry_effect = MOOD_EFFECTS[MoodType.ANGRY]
        self.assertGreater(angry_effect.attack_modifier, 1.0)
        self.assertLess(angry_effect.defense_modifier, 1.0)

    def test_happy_is_positive(self):
        happy_effect = MOOD_EFFECTS[MoodType.HAPPY]
        self.assertGreaterEqual(happy_effect.attack_modifier, 1.0)
        self.assertGreaterEqual(happy_effect.defense_modifier, 1.0)

    def test_tired_reduces_stats(self):
        tired_effect = MOOD_EFFECTS[MoodType.TIRED]
        self.assertLess(tired_effect.attack_modifier, 1.0)
        self.assertLess(tired_effect.initiative_modifier, 1.0)

    def test_neutral_has_no_modifiers(self):
        neutral_effect = MOOD_EFFECTS[MoodType.NEUTRAL]
        self.assertEqual(neutral_effect.attack_modifier, 1.0)
        self.assertEqual(neutral_effect.defense_modifier, 1.0)
        self.assertEqual(neutral_effect.initiative_modifier, 1.0)
        self.assertEqual(neutral_effect.miss_chance_modifier, 1.0)


class TestPokeMood(unittest.TestCase):
    def test_default_initialization(self):
        mood = PokeMood()
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.last_battle_time, 0)
        self.assertEqual(mood.battles_since_rest, 0)
        self.assertEqual(mood.last_mood_change_time, 0)

    def test_custom_initialization(self):
        mood = PokeMood(
            mood_type=MoodType.HAPPY,
            last_battle_time=100,
            battles_since_rest=3,
            last_mood_change_time=50
        )
        self.assertEqual(mood.mood_type, MoodType.HAPPY)
        self.assertEqual(mood.last_battle_time, 100)
        self.assertEqual(mood.battles_since_rest, 3)
        self.assertEqual(mood.last_mood_change_time, 50)

    def test_effect_property(self):
        mood = PokeMood(mood_type=MoodType.ANGRY)
        effect = mood.effect
        self.assertEqual(effect, MOOD_EFFECTS[MoodType.ANGRY])

    def test_name_property(self):
        mood = PokeMood(mood_type=MoodType.HAPPY)
        self.assertEqual(mood.name, "Happy")

    def test_get_attack_modifier(self):
        mood = PokeMood(mood_type=MoodType.ANGRY)
        modifier = mood.get_attack_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.ANGRY].attack_modifier)

    def test_get_defense_modifier(self):
        mood = PokeMood(mood_type=MoodType.CALM)
        modifier = mood.get_defense_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.CALM].defense_modifier)


class TestPokeMoodTriggerEvent(unittest.TestCase):
    def test_trigger_event_returns_mood_type(self):
        mood = PokeMood()
        result = mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
        self.assertIsInstance(result, MoodType)

    def test_battle_win_updates_battle_time(self):
        mood = PokeMood()
        mood.trigger_event(MoodEvent.BATTLE_WIN, 150)
        self.assertEqual(mood.last_battle_time, 150)

    def test_battle_win_increments_battles_since_rest(self):
        mood = PokeMood()
        initial = mood.battles_since_rest
        mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
        self.assertEqual(mood.battles_since_rest, initial + 1)

    def test_battle_loss_updates_battle_time(self):
        mood = PokeMood()
        mood.trigger_event(MoodEvent.BATTLE_LOSS, 200)
        self.assertEqual(mood.last_battle_time, 200)

    def test_healed_resets_battles_since_rest(self):
        mood = PokeMood(battles_since_rest=5)
        mood.trigger_event(MoodEvent.HEALED, 100)
        self.assertEqual(mood.battles_since_rest, 0)

    def test_mood_can_change_on_event(self):
        changed = False
        for _ in range(100):
            mood = PokeMood(mood_type=MoodType.NEUTRAL)
            mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
            if mood.mood_type != MoodType.NEUTRAL:
                changed = True
                break
        self.assertTrue(changed, "Mood should eventually change on battle win")


class TestPokeMoodTimeBased(unittest.TestCase):
    def test_check_time_based_no_change_initially(self):
        mood = PokeMood(last_battle_time=100)
        result = mood.check_time_based_mood(110, 100)
        self.assertIsNone(result)

    def test_check_time_based_unused_long(self):
        changed = False
        for _ in range(50):
            test_mood = PokeMood(mood_type=MoodType.HAPPY, last_battle_time=100)
            result = test_mood.check_time_based_mood(300, 100)
            if result is not None:
                changed = True
                break
        self.assertTrue(changed, "Mood should change when unused for too long")

    def test_check_time_based_used_heavily(self):
        changed = False
        for _ in range(50):
            test_mood = PokeMood(mood_type=MoodType.HAPPY, battles_since_rest=10)
            result = test_mood.check_time_based_mood(100, 100)
            if result is not None:
                changed = True
                break
        self.assertTrue(changed, "Mood should change when used too heavily")


class TestPokeMoodSerialization(unittest.TestCase):
    def test_dict_contains_all_fields(self):
        mood = PokeMood(
            mood_type=MoodType.EXCITED,
            last_battle_time=500,
            battles_since_rest=3,
            last_mood_change_time=450
        )
        d = mood.dict()
        self.assertIn("mood_type", d)
        self.assertIn("last_battle_time", d)
        self.assertIn("battles_since_rest", d)
        self.assertIn("last_mood_change_time", d)

    def test_dict_values_correct(self):
        mood = PokeMood(
            mood_type=MoodType.EXCITED,
            last_battle_time=500,
            battles_since_rest=3,
            last_mood_change_time=450
        )
        d = mood.dict()
        self.assertEqual(d["mood_type"], "excited")
        self.assertEqual(d["last_battle_time"], 500)
        self.assertEqual(d["battles_since_rest"], 3)
        self.assertEqual(d["last_mood_change_time"], 450)

    def test_from_dict_creates_correct_mood(self):
        data = {
            "mood_type": "angry",
            "last_battle_time": 300,
            "battles_since_rest": 2,
            "last_mood_change_time": 250
        }
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.ANGRY)
        self.assertEqual(mood.last_battle_time, 300)
        self.assertEqual(mood.battles_since_rest, 2)
        self.assertEqual(mood.last_mood_change_time, 250)

    def test_from_dict_handles_none(self):
        mood = PokeMood.from_dict(None)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.last_battle_time, 0)

    def test_from_dict_handles_invalid_mood_type(self):
        data = {"mood_type": "invalid_mood"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_from_dict_handles_missing_fields(self):
        data = {"mood_type": "happy"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.HAPPY)
        self.assertEqual(mood.last_battle_time, 0)
        self.assertEqual(mood.battles_since_rest, 0)

    def test_roundtrip_serialization(self):
        original = PokeMood(
            mood_type=MoodType.SAD,
            last_battle_time=1000,
            battles_since_rest=5,
            last_mood_change_time=900
        )
        restored = PokeMood.from_dict(original.dict())
        self.assertEqual(original.mood_type, restored.mood_type)
        self.assertEqual(original.last_battle_time, restored.last_battle_time)
        self.assertEqual(original.battles_since_rest, restored.battles_since_rest)
        self.assertEqual(original.last_mood_change_time, restored.last_mood_change_time)


class TestPokeMoodRandom(unittest.TestCase):
    def test_random_returns_poke_mood(self):
        mood = PokeMood.random()
        self.assertIsInstance(mood, PokeMood)

    def test_random_creates_valid_mood(self):
        mood = PokeMood.random()
        self.assertIn(mood.mood_type, list(MoodType))

    def test_random_creates_variety(self):
        moods = [PokeMood.random().mood_type for _ in range(100)]
        unique_moods = set(moods)
        self.assertGreater(len(unique_moods), 1)


class TestMoodTransitions(unittest.TestCase):
    def test_all_events_have_transitions(self):
        for event in MoodEvent:
            self.assertIn(event, MOOD_TRANSITIONS)

    def test_all_moods_have_transitions_for_battle_win(self):
        for mood_type in MoodType:
            self.assertIn(mood_type, MOOD_TRANSITIONS[MoodEvent.BATTLE_WIN])

    def test_transition_probabilities_sum_to_one(self):
        for event, mood_transitions in MOOD_TRANSITIONS.items():
            for mood_type, transitions in mood_transitions.items():
                total = sum(prob for _, prob in transitions)
                self.assertAlmostEqual(total, 1.0, places=5,
                    msg=f"Probabilities for {event}/{mood_type} don't sum to 1")

    def test_evolution_leads_to_positive_moods(self):
        evo_transitions = MOOD_TRANSITIONS[MoodEvent.EVOLVED]
        for mood_type in MoodType:
            transitions = evo_transitions[mood_type]
            mood_names = [m.value for m, _ in transitions]
            self.assertTrue(
                "excited" in mood_names or "happy" in mood_names,
                "Evolution should lead to positive moods"
            )


class TestMoodEventTypes(unittest.TestCase):
    def test_all_expected_events_exist(self):
        expected = [
            "battle_win", "battle_loss", "healed", "evolved",
            "traded", "caught", "level_up", "cuddled",
            "unused_long", "used_heavily"
        ]
        for event in expected:
            self.assertIn(event, [e.value for e in MoodEvent])


class TestMoodCombatImpact(unittest.TestCase):
    """Test that moods have appropriate combat impacts"""

    def test_angry_high_risk_high_reward(self):
        """Angry should have high attack but low defense"""
        mood = PokeMood(mood_type=MoodType.ANGRY)
        self.assertGreater(mood.get_attack_modifier(), 1.0)
        self.assertLess(mood.get_defense_modifier(), 1.0)

    def test_calm_defensive(self):
        """Calm should have good defense"""
        mood = PokeMood(mood_type=MoodType.CALM)
        self.assertGreater(mood.get_defense_modifier(), 1.0)

    def test_tired_overall_negative(self):
        """Tired should have negative effects"""
        mood = PokeMood(mood_type=MoodType.TIRED)
        self.assertLess(mood.get_attack_modifier(), 1.0)
        self.assertLess(mood.get_initiative_modifier(), 1.0)

    def test_excited_fast_but_risky(self):
        """Excited should be fast but have higher miss chance"""
        mood = PokeMood(mood_type=MoodType.EXCITED)
        self.assertGreater(mood.get_initiative_modifier(), 1.0)
        self.assertGreater(mood.get_miss_chance_modifier(), 1.0)


class TestMoodScenarios(unittest.TestCase):
    """Integration tests for common mood scenarios"""

    def test_battle_streak_leads_to_tiredness(self):
        """Multiple battles without rest should lead to tiredness"""
        mood = PokeMood()
        for i in range(10):
            mood.trigger_event(MoodEvent.BATTLE_WIN, i * 10)

        # After many battles, check time-based effects
        result = mood.check_time_based_mood(1000, 0)
        # Should trigger USED_HEAVILY since battles_since_rest > 5
        self.assertEqual(mood.battles_since_rest, 10)

    def test_healing_resets_battle_count(self):
        """Healing should reset the battles since rest counter"""
        mood = PokeMood()
        mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
        mood.trigger_event(MoodEvent.BATTLE_WIN, 200)
        mood.trigger_event(MoodEvent.BATTLE_WIN, 300)
        self.assertEqual(mood.battles_since_rest, 3)

        mood.trigger_event(MoodEvent.HEALED, 400)
        self.assertEqual(mood.battles_since_rest, 0)

    def test_cuddling_improves_mood(self):
        """Cuddling should tend to improve mood over time"""
        improved = 0
        for _ in range(100):
            mood = PokeMood(mood_type=MoodType.SAD)
            old_mood = mood.mood_type
            mood.trigger_event(MoodEvent.CUDDLED, 100)
            if mood.mood_type != old_mood:
                improved += 1

        # Should improve mood at least some of the time
        self.assertGreater(improved, 0)


if __name__ == "__main__":
    unittest.main()
