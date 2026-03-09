"""Tests for the Pokete mood system"""

import unittest
from unittest.mock import patch

from pokete.classes.poke.mood import (
    MOOD_EFFECTS,
    MOOD_TRANSITIONS,
    MoodEffect,
    MoodEvent,
    MoodType,
    PokeMood,
)


class TestMoodType(unittest.TestCase):
    """Tests for the MoodType enum"""

    def test_all_moods_exist(self):
        """Test that all expected mood types exist"""
        expected_moods = [
            "happy", "sad", "angry", "tired",
            "excited", "calm", "anxious", "neutral"
        ]
        for mood in expected_moods:
            self.assertIn(mood, [m.value for m in MoodType])

    def test_mood_type_values(self):
        """Test that mood types have correct string values"""
        self.assertEqual(MoodType.HAPPY.value, "happy")
        self.assertEqual(MoodType.ANGRY.value, "angry")
        self.assertEqual(MoodType.NEUTRAL.value, "neutral")


class TestMoodEffect(unittest.TestCase):
    """Tests for the MoodEffect dataclass"""

    def test_default_modifiers(self):
        """Test that default modifiers are 1.0"""
        effect = MoodEffect()
        self.assertEqual(effect.attack_modifier, 1.0)
        self.assertEqual(effect.defense_modifier, 1.0)
        self.assertEqual(effect.initiative_modifier, 1.0)
        self.assertEqual(effect.miss_chance_modifier, 1.0)

    def test_custom_modifiers(self):
        """Test creating effects with custom modifiers"""
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
        """Test description for neutral effect"""
        effect = MoodEffect()
        self.assertEqual(effect.description, "No combat effects")

    def test_description_with_effects(self):
        """Test description for effect with modifiers"""
        effect = MoodEffect(attack_modifier=1.25, defense_modifier=0.85)
        desc = effect.description
        self.assertIn("attack", desc)
        self.assertIn("defense", desc)


class TestMoodEffectsConfiguration(unittest.TestCase):
    """Tests for the MOOD_EFFECTS configuration"""

    def test_all_moods_have_effects(self):
        """Test that all mood types have defined effects"""
        for mood_type in MoodType:
            self.assertIn(mood_type, MOOD_EFFECTS)

    def test_angry_boosts_attack_reduces_defense(self):
        """Test that angry mood boosts attack and reduces defense"""
        angry_effect = MOOD_EFFECTS[MoodType.ANGRY]
        self.assertGreater(angry_effect.attack_modifier, 1.0)
        self.assertLess(angry_effect.defense_modifier, 1.0)

    def test_happy_is_positive(self):
        """Test that happy mood has positive effects"""
        happy_effect = MOOD_EFFECTS[MoodType.HAPPY]
        self.assertGreaterEqual(happy_effect.attack_modifier, 1.0)
        self.assertGreaterEqual(happy_effect.defense_modifier, 1.0)

    def test_tired_reduces_stats(self):
        """Test that tired mood reduces stats"""
        tired_effect = MOOD_EFFECTS[MoodType.TIRED]
        self.assertLess(tired_effect.attack_modifier, 1.0)
        self.assertLess(tired_effect.initiative_modifier, 1.0)

    def test_neutral_has_no_modifiers(self):
        """Test that neutral mood has no stat changes"""
        neutral_effect = MOOD_EFFECTS[MoodType.NEUTRAL]
        self.assertEqual(neutral_effect.attack_modifier, 1.0)
        self.assertEqual(neutral_effect.defense_modifier, 1.0)
        self.assertEqual(neutral_effect.initiative_modifier, 1.0)
        self.assertEqual(neutral_effect.miss_chance_modifier, 1.0)


class TestPokeMood(unittest.TestCase):
    """Tests for the PokeMood class"""

    def test_default_initialization(self):
        """Test default PokeMood initialization"""
        mood = PokeMood()
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.last_battle_time, 0)
        self.assertEqual(mood.battles_since_rest, 0)
        self.assertEqual(mood.last_mood_change_time, 0)

    def test_custom_initialization(self):
        """Test PokeMood with custom values"""
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
        """Test that effect property returns correct MoodEffect"""
        mood = PokeMood(mood_type=MoodType.ANGRY)
        effect = mood.effect
        self.assertEqual(effect, MOOD_EFFECTS[MoodType.ANGRY])

    def test_color_property(self):
        """Test that color property returns a string"""
        mood = PokeMood(mood_type=MoodType.HAPPY)
        self.assertIsInstance(mood.color, str)

    def test_name_property(self):
        """Test that name property returns capitalized mood"""
        mood = PokeMood(mood_type=MoodType.HAPPY)
        self.assertEqual(mood.name, "Happy")

    def test_description_property(self):
        """Test that description property returns a string"""
        mood = PokeMood(mood_type=MoodType.ANGRY)
        self.assertIsInstance(mood.description, str)
        self.assertGreater(len(mood.description), 0)

    def test_get_attack_modifier(self):
        """Test attack modifier getter"""
        mood = PokeMood(mood_type=MoodType.ANGRY)
        modifier = mood.get_attack_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.ANGRY].attack_modifier)

    def test_get_defense_modifier(self):
        """Test defense modifier getter"""
        mood = PokeMood(mood_type=MoodType.CALM)
        modifier = mood.get_defense_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.CALM].defense_modifier)

    def test_get_initiative_modifier(self):
        """Test initiative modifier getter"""
        mood = PokeMood(mood_type=MoodType.TIRED)
        modifier = mood.get_initiative_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.TIRED].initiative_modifier)

    def test_get_miss_chance_modifier(self):
        """Test miss chance modifier getter"""
        mood = PokeMood(mood_type=MoodType.ANXIOUS)
        modifier = mood.get_miss_chance_modifier()
        self.assertEqual(modifier, MOOD_EFFECTS[MoodType.ANXIOUS].miss_chance_modifier)


class TestPokeMoodTriggerEvent(unittest.TestCase):
    """Tests for mood event triggering"""

    def test_trigger_event_returns_mood_type(self):
        """Test that trigger_event returns a MoodType"""
        mood = PokeMood()
        result = mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
        self.assertIsInstance(result, MoodType)

    def test_battle_win_updates_battle_time(self):
        """Test that winning a battle updates last_battle_time"""
        mood = PokeMood()
        mood.trigger_event(MoodEvent.BATTLE_WIN, 150)
        self.assertEqual(mood.last_battle_time, 150)

    def test_battle_win_increments_battles_since_rest(self):
        """Test that winning a battle increments battles_since_rest"""
        mood = PokeMood()
        initial = mood.battles_since_rest
        mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
        self.assertEqual(mood.battles_since_rest, initial + 1)

    def test_battle_loss_updates_battle_time(self):
        """Test that losing a battle updates last_battle_time"""
        mood = PokeMood()
        mood.trigger_event(MoodEvent.BATTLE_LOSS, 200)
        self.assertEqual(mood.last_battle_time, 200)

    def test_healed_resets_battles_since_rest(self):
        """Test that healing resets battles_since_rest"""
        mood = PokeMood(battles_since_rest=5)
        mood.trigger_event(MoodEvent.HEALED, 100)
        self.assertEqual(mood.battles_since_rest, 0)

    def test_mood_can_change_on_event(self):
        """Test that mood can change when an event occurs"""
        changed = False
        for _ in range(100):
            mood = PokeMood(mood_type=MoodType.NEUTRAL)
            mood.trigger_event(MoodEvent.BATTLE_WIN, 100)
            if mood.mood_type != MoodType.NEUTRAL:
                changed = True
                break
        self.assertTrue(changed, "Mood should eventually change on battle win")


class TestPokeMoodTimeBased(unittest.TestCase):
    """Tests for time-based mood changes"""

    def test_check_time_based_no_change_initially(self):
        """Test no change when pokete has recent battle"""
        mood = PokeMood(last_battle_time=100)
        result = mood.check_time_based_mood(110, 100)
        self.assertIsNone(result)

    def test_check_time_based_unused_long(self):
        """Test mood change when pokete unused for too long"""
        mood = PokeMood(last_battle_time=100)
        # Simulate enough time passing (LONELY_THRESHOLD is 120)
        changed = False
        for _ in range(50):
            test_mood = PokeMood(mood_type=MoodType.HAPPY, last_battle_time=100)
            result = test_mood.check_time_based_mood(300, 100)
            if result is not None:
                changed = True
                break
        self.assertTrue(changed, "Mood should change when unused for too long")

    def test_check_time_based_used_heavily(self):
        """Test mood change when pokete used too much"""
        changed = False
        for _ in range(50):
            test_mood = PokeMood(mood_type=MoodType.HAPPY, battles_since_rest=10)
            result = test_mood.check_time_based_mood(100, 100)
            if result is not None:
                changed = True
                break
        self.assertTrue(changed, "Mood should change when used too heavily")


class TestPokeMoodSerialization(unittest.TestCase):
    """Tests for PokeMood serialization/deserialization"""

    def test_dict_contains_all_fields(self):
        """Test that dict() returns all necessary fields"""
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
        """Test that dict() returns correct values"""
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
        """Test that from_dict creates correct PokeMood"""
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
        """Test that from_dict handles None input"""
        mood = PokeMood.from_dict(None)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)
        self.assertEqual(mood.last_battle_time, 0)

    def test_from_dict_handles_invalid_mood_type(self):
        """Test that from_dict handles invalid mood type"""
        data = {"mood_type": "invalid_mood"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.NEUTRAL)

    def test_from_dict_handles_missing_fields(self):
        """Test that from_dict handles missing fields"""
        data = {"mood_type": "happy"}
        mood = PokeMood.from_dict(data)
        self.assertEqual(mood.mood_type, MoodType.HAPPY)
        self.assertEqual(mood.last_battle_time, 0)
        self.assertEqual(mood.battles_since_rest, 0)

    def test_roundtrip_serialization(self):
        """Test that serialization and deserialization preserve data"""
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
    """Tests for random mood generation"""

    def test_random_returns_poke_mood(self):
        """Test that random() returns a PokeMood"""
        mood = PokeMood.random()
        self.assertIsInstance(mood, PokeMood)

    def test_random_creates_valid_mood(self):
        """Test that random() creates a valid mood type"""
        mood = PokeMood.random()
        self.assertIn(mood.mood_type, list(MoodType))

    def test_random_creates_variety(self):
        """Test that random() creates different moods"""
        moods = [PokeMood.random().mood_type for _ in range(100)]
        unique_moods = set(moods)
        self.assertGreater(len(unique_moods), 1)


class TestMoodTransitions(unittest.TestCase):
    """Tests for mood transition configuration"""

    def test_all_events_have_transitions(self):
        """Test that all events have transition definitions"""
        for event in MoodEvent:
            self.assertIn(event, MOOD_TRANSITIONS)

    def test_all_moods_have_transitions_for_battle_win(self):
        """Test that all moods can transition on battle win"""
        for mood_type in MoodType:
            self.assertIn(mood_type, MOOD_TRANSITIONS[MoodEvent.BATTLE_WIN])

    def test_transition_probabilities_sum_to_one(self):
        """Test that transition probabilities approximately sum to 1"""
        for event, mood_transitions in MOOD_TRANSITIONS.items():
            for mood_type, transitions in mood_transitions.items():
                total = sum(prob for _, prob in transitions)
                self.assertAlmostEqual(total, 1.0, places=5,
                    msg=f"Probabilities for {event}/{mood_type} don't sum to 1")

    def test_evolution_leads_to_positive_moods(self):
        """Test that evolution has positive mood outcomes"""
        evo_transitions = MOOD_TRANSITIONS[MoodEvent.EVOLVED]
        for mood_type in MoodType:
            transitions = evo_transitions[mood_type]
            mood_names = [m.value for m, _ in transitions]
            self.assertTrue(
                "excited" in mood_names or "happy" in mood_names,
                "Evolution should lead to positive moods"
            )


class TestMoodEventTypes(unittest.TestCase):
    """Tests for MoodEvent enum"""

    def test_all_expected_events_exist(self):
        """Test that all expected events exist"""
        expected = [
            "battle_win", "battle_loss", "healed", "evolved",
            "traded", "caught", "level_up", "cuddled",
            "unused_long", "used_heavily"
        ]
        for event in expected:
            self.assertIn(event, [e.value for e in MoodEvent])


if __name__ == "__main__":
    unittest.main()
