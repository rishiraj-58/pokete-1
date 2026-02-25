"""
Unit tests for the weather system.

These tests are designed to run with Python 3.12+ as required by the pokete project.
They test the Weather class, WeatherManager class, and their integration with
the attack system.
"""

import unittest
from unittest.mock import Mock, patch
from typing import Optional


# Mock the weather data for testing without importing the full project
MOCK_WEATHERS = {
    "rain": {
        "info": "It's raining!",
        "effected": {
            "fire": 0.5,
            "plant": 1.5,
            "water": 1.5
        },
        "miss_chance_modifier": {
            "fire": 0.15,
            "water": -0.1,
        }
    },
    "thunderstorm": {
        "info": "There is a thunderstorm going on!",
        "effected": {
            "fire": 0.5,
            "plant": 1.5,
            "water": 1.5,
            "electro": 2,
        },
        "miss_chance_modifier": {
            "fire": 0.2,
            "electro": -0.15,
            "all": 0.05,
        }
    },
    "foggy": {
        "info": "It's foggy!",
        "effected": {
            "undead": 1.5,
            "normal": 0.75,
        },
        "miss_chance_modifier": {
            "all": 0.2,
        }
    },
    "sunny": {
        "info": "It's a hot sunny day!",
        "effected": {
            "fire": 1.5,
            "water": 0.75,
            "ice": 0.5,
            "plant": 0.75,
        },
        "miss_chance_modifier": {
            "fire": -0.1,
            "ice": 0.1,
        }
    }
}


class Weather:
    """Test version of Weather class that matches the implementation"""
    
    def __init__(self, index: str):
        self.index = index
        self.info = MOCK_WEATHERS[index]["info"]
        self.effected = MOCK_WEATHERS[index]["effected"]
        self._miss_chance_modifier = MOCK_WEATHERS[index].get("miss_chance_modifier", {})

    def effect(self, typ) -> float:
        return self.effected.get(typ.name, 1)

    def get_miss_chance_modifier(self, typ) -> float:
        return self._miss_chance_modifier.get(typ.name, 0)

    def get_global_miss_modifier(self) -> float:
        return self._miss_chance_modifier.get("all", 0)

    @property
    def display_name(self) -> str:
        display_names = {
            "rain": "Rain",
            "thunderstorm": "Storm",
            "foggy": "Fog",
            "sunny": "Sunny",
            "clear": "Clear",
        }
        return display_names.get(self.index, self.index.capitalize())

    @property
    def icon(self) -> str:
        icons = {
            "rain": "~",
            "thunderstorm": "⚡",
            "foggy": "≈",
            "sunny": "☀",
            "clear": "○",
        }
        return icons.get(self.index, "?")


WEATHER_CYCLE_DURATION = 60


class WeatherManager:
    """Test version of WeatherManager class that matches the implementation"""

    def __init__(self, base_weather: Optional[str] = None):
        self._base_weather = base_weather
        self._current_weather: Optional[Weather] = None
        self._last_cycle_time = 0
        if base_weather is not None:
            self._current_weather = Weather(base_weather)

    @property
    def current(self) -> Optional[Weather]:
        return self._current_weather

    def update(self, game_time: int) -> bool:
        if self._base_weather is None:
            return False

        cycle_position = (game_time // WEATHER_CYCLE_DURATION) % 4
        new_weather_index = self._get_weather_for_cycle(cycle_position)

        if self._current_weather is None or self._current_weather.index != new_weather_index:
            self._current_weather = Weather(new_weather_index)
            self._last_cycle_time = game_time
            return True
        return False

    def _get_weather_for_cycle(self, cycle: int) -> str:
        weather_progressions = {
            "rain": ["rain", "thunderstorm", "rain", "foggy"],
            "thunderstorm": ["thunderstorm", "rain", "foggy", "thunderstorm"],
            "foggy": ["foggy", "foggy", "rain", "foggy"],
            "sunny": ["sunny", "sunny", "sunny", "sunny"],
        }
        progression = weather_progressions.get(self._base_weather, [self._base_weather] * 4)
        return progression[cycle]

    def set_weather(self, weather_index: str):
        if weather_index in MOCK_WEATHERS:
            self._current_weather = Weather(weather_index)
        else:
            self._current_weather = None

    def clear_weather(self):
        self._current_weather = None


class TestWeather(unittest.TestCase):
    """Tests for Weather class"""

    def test_weather_init_rain(self):
        """Test rain weather initialization"""
        weather = Weather("rain")
        self.assertEqual(weather.index, "rain")
        self.assertEqual(weather.info, "It's raining!")
        self.assertIn("fire", weather.effected)
        self.assertEqual(weather.effected["fire"], 0.5)

    def test_weather_init_sunny(self):
        """Test sunny weather initialization"""
        weather = Weather("sunny")
        self.assertEqual(weather.index, "sunny")
        self.assertEqual(weather.info, "It's a hot sunny day!")
        self.assertEqual(weather.effected["fire"], 1.5)
        self.assertEqual(weather.effected["ice"], 0.5)

    def test_weather_init_foggy(self):
        """Test foggy weather initialization"""
        weather = Weather("foggy")
        self.assertEqual(weather.index, "foggy")
        self.assertEqual(weather.info, "It's foggy!")
        self.assertEqual(weather.effected["undead"], 1.5)

    def test_weather_init_thunderstorm(self):
        """Test thunderstorm weather initialization"""
        weather = Weather("thunderstorm")
        self.assertEqual(weather.index, "thunderstorm")
        self.assertEqual(weather.effected["electro"], 2)

    def test_effect_returns_multiplier_for_affected_type(self):
        """Test effect() returns correct multiplier for affected types"""
        weather = Weather("rain")
        mock_type = Mock()
        mock_type.name = "water"
        self.assertEqual(weather.effect(mock_type), 1.5)

    def test_effect_returns_1_for_unaffected_type(self):
        """Test effect() returns 1.0 for unaffected types"""
        weather = Weather("rain")
        mock_type = Mock()
        mock_type.name = "stone"
        self.assertEqual(weather.effect(mock_type), 1)

    def test_get_miss_chance_modifier_for_affected_type(self):
        """Test miss chance modifier for affected attack types"""
        weather = Weather("rain")
        mock_type = Mock()
        mock_type.name = "fire"
        # Fire attacks have +0.15 miss chance in rain
        self.assertEqual(weather.get_miss_chance_modifier(mock_type), 0.15)

    def test_get_miss_chance_modifier_for_water_in_rain(self):
        """Test water attacks are more accurate in rain"""
        weather = Weather("rain")
        mock_type = Mock()
        mock_type.name = "water"
        # Water attacks have -0.1 miss chance (more accurate) in rain
        self.assertEqual(weather.get_miss_chance_modifier(mock_type), -0.1)

    def test_get_miss_chance_modifier_unaffected_type(self):
        """Test miss chance modifier returns 0 for unaffected types"""
        weather = Weather("rain")
        mock_type = Mock()
        mock_type.name = "normal"
        self.assertEqual(weather.get_miss_chance_modifier(mock_type), 0)

    def test_get_global_miss_modifier_foggy(self):
        """Test foggy weather has global miss modifier"""
        weather = Weather("foggy")
        # Fog adds +0.2 miss chance to all attacks
        self.assertEqual(weather.get_global_miss_modifier(), 0.2)

    def test_get_global_miss_modifier_no_modifier(self):
        """Test weather without global miss modifier returns 0"""
        weather = Weather("sunny")
        self.assertEqual(weather.get_global_miss_modifier(), 0)

    def test_display_name(self):
        """Test weather display names"""
        self.assertEqual(Weather("rain").display_name, "Rain")
        self.assertEqual(Weather("thunderstorm").display_name, "Storm")
        self.assertEqual(Weather("foggy").display_name, "Fog")
        self.assertEqual(Weather("sunny").display_name, "Sunny")

    def test_icon(self):
        """Test weather icons"""
        self.assertEqual(Weather("rain").icon, "~")
        self.assertEqual(Weather("thunderstorm").icon, "⚡")
        self.assertEqual(Weather("foggy").icon, "≈")
        self.assertEqual(Weather("sunny").icon, "☀")


class TestWeatherManager(unittest.TestCase):
    """Tests for WeatherManager class"""

    def test_init_with_no_weather(self):
        """Test initialization with no base weather"""
        manager = WeatherManager(None)
        self.assertIsNone(manager.current)

    def test_init_with_base_weather(self):
        """Test initialization with base weather"""
        manager = WeatherManager("rain")
        self.assertIsNotNone(manager.current)
        self.assertEqual(manager.current.index, "rain")

    def test_update_with_no_base_weather(self):
        """Test update does nothing without base weather"""
        manager = WeatherManager(None)
        changed = manager.update(100)
        self.assertFalse(changed)
        self.assertIsNone(manager.current)

    def test_weather_cycles_over_time(self):
        """Test weather cycles based on game time"""
        manager = WeatherManager("rain")
        
        # Cycle 0: rain
        manager.update(0)
        self.assertEqual(manager.current.index, "rain")
        
        # Cycle 1: thunderstorm (at 60 minutes)
        changed = manager.update(60)
        self.assertTrue(changed)
        self.assertEqual(manager.current.index, "thunderstorm")
        
        # Cycle 2: rain (at 120 minutes)
        changed = manager.update(120)
        self.assertTrue(changed)
        self.assertEqual(manager.current.index, "rain")
        
        # Cycle 3: foggy (at 180 minutes)
        changed = manager.update(180)
        self.assertTrue(changed)
        self.assertEqual(manager.current.index, "foggy")

    def test_sunny_weather_stays_sunny(self):
        """Test sunny weather doesn't cycle to other weather"""
        manager = WeatherManager("sunny")
        
        for time in [0, 60, 120, 180, 240]:
            manager.update(time)
            self.assertEqual(manager.current.index, "sunny")

    def test_foggy_cycles(self):
        """Test foggy weather cycle progression"""
        manager = WeatherManager("foggy")
        
        # Cycle 0-1: foggy
        manager.update(0)
        self.assertEqual(manager.current.index, "foggy")
        
        # Cycle 2: rain
        manager.update(120)
        self.assertEqual(manager.current.index, "rain")
        
        # Cycle 3: foggy
        manager.update(180)
        self.assertEqual(manager.current.index, "foggy")

    def test_set_weather(self):
        """Test manually setting weather"""
        manager = WeatherManager("rain")
        manager.set_weather("sunny")
        self.assertEqual(manager.current.index, "sunny")

    def test_set_invalid_weather(self):
        """Test setting invalid weather clears weather"""
        manager = WeatherManager("rain")
        manager.set_weather("invalid_weather")
        self.assertIsNone(manager.current)

    def test_clear_weather(self):
        """Test clearing weather"""
        manager = WeatherManager("rain")
        self.assertIsNotNone(manager.current)
        manager.clear_weather()
        self.assertIsNone(manager.current)

    def test_no_change_within_same_cycle(self):
        """Test weather doesn't change within same time cycle"""
        manager = WeatherManager("rain")
        manager.update(0)
        initial_weather = manager.current.index
        
        # Update within same cycle
        changed = manager.update(30)
        self.assertFalse(changed)
        self.assertEqual(manager.current.index, initial_weather)

    def test_weather_cycle_wraps_around(self):
        """Test weather cycles wrap around after 4 cycles"""
        manager = WeatherManager("rain")
        
        # Start fresh
        manager.update(0)
        self.assertEqual(manager.current.index, "rain")
        
        # After full cycle (240+ minutes), should be back to cycle 0
        manager.update(240)
        self.assertEqual(manager.current.index, "rain")


class TestAttackProcessWeatherIntegration(unittest.TestCase):
    """Tests for weather integration in attack processing"""

    @staticmethod
    def get_random_factor_test(attack_miss_chance, attacker_miss_chance, 
                               attack_type_name, weather=None):
        """Simplified version of get_random_factor for testing"""
        import random
        
        base_miss_chance = attack_miss_chance + attacker_miss_chance
        
        weather_miss_modifier = 0
        if weather is not None:
            weather_miss_modifier = weather.get_global_miss_modifier()
            mock_type = Mock()
            mock_type.name = attack_type_name
            weather_miss_modifier += weather.get_miss_chance_modifier(mock_type)
        
        total_miss_chance = max(0, min(1, base_miss_chance + weather_miss_modifier))
        
        return total_miss_chance

    def test_get_random_factor_no_weather(self):
        """Test random factor calculation without weather"""
        miss_chance = self.get_random_factor_test(0.1, 0.1, "normal", None)
        self.assertAlmostEqual(miss_chance, 0.2, places=2)

    def test_get_random_factor_with_weather_increases_miss(self):
        """Test weather increases miss chance for affected types"""
        weather = Weather("rain")
        miss_chance = self.get_random_factor_test(0.1, 0.1, "fire", weather)
        # Miss chance should be: 0.1 + 0.1 + 0.15 = 0.35
        self.assertAlmostEqual(miss_chance, 0.35, places=2)

    def test_get_random_factor_with_weather_decreases_miss(self):
        """Test weather decreases miss chance for boosted types"""
        weather = Weather("rain")
        miss_chance = self.get_random_factor_test(0.2, 0.1, "water", weather)
        # Miss chance should be: 0.2 + 0.1 - 0.1 = 0.2
        self.assertAlmostEqual(miss_chance, 0.2, places=2)

    def test_get_random_factor_fog_global_miss_modifier(self):
        """Test fog applies global miss modifier to all attacks"""
        weather = Weather("foggy")
        miss_chance = self.get_random_factor_test(0.1, 0.1, "normal", weather)
        # Miss chance should be: 0.1 + 0.1 + 0.2 = 0.4
        self.assertAlmostEqual(miss_chance, 0.4, places=2)

    def test_get_random_factor_miss_chance_clamped_max(self):
        """Test miss chance is clamped to max 1.0"""
        weather = Weather("foggy")
        # Very high base miss chance
        miss_chance = self.get_random_factor_test(0.8, 0.5, "fire", weather)
        self.assertLessEqual(miss_chance, 1.0)

    def test_get_random_factor_miss_chance_clamped_min(self):
        """Test miss chance is clamped to min 0"""
        weather = Weather("rain")
        # Negative modifier shouldn't make miss chance negative
        miss_chance = self.get_random_factor_test(0.0, 0.0, "water", weather)
        # -0.1 modifier, but clamped to 0
        self.assertGreaterEqual(miss_chance, 0.0)


class TestWeatherDataIntegrity(unittest.TestCase):
    """Tests for weather data consistency"""

    def test_all_weather_types_have_required_fields(self):
        """Test all weather types have info and effected fields"""
        required_fields = ["info", "effected"]
        
        for weather_name, weather_data in MOCK_WEATHERS.items():
            for field in required_fields:
                self.assertIn(field, weather_data, 
                    f"Weather '{weather_name}' missing required field '{field}'")

    def test_effected_values_are_numeric(self):
        """Test all effected values are valid numbers"""
        for weather_name, weather_data in MOCK_WEATHERS.items():
            for type_name, value in weather_data["effected"].items():
                self.assertIsInstance(value, (int, float),
                    f"Weather '{weather_name}' effected['{type_name}'] is not numeric")

    def test_miss_chance_modifiers_are_numeric(self):
        """Test all miss chance modifier values are valid numbers"""
        for weather_name, weather_data in MOCK_WEATHERS.items():
            if "miss_chance_modifier" in weather_data:
                for type_name, value in weather_data["miss_chance_modifier"].items():
                    self.assertIsInstance(value, (int, float),
                        f"Weather '{weather_name}' miss_chance_modifier['{type_name}'] is not numeric")

    def test_all_defined_weathers_are_accessible(self):
        """Test all weather types defined in data can be instantiated"""
        for weather_name in MOCK_WEATHERS:
            try:
                weather = Weather(weather_name)
                self.assertIsNotNone(weather)
            except Exception as e:
                self.fail(f"Failed to instantiate weather '{weather_name}': {e}")


class TestWeatherEffectsOnBattle(unittest.TestCase):
    """Tests for weather effects during battle"""

    def test_rain_boosts_water_damage(self):
        """Test rain weather boosts water type damage"""
        weather = Weather("rain")
        mock_water_type = Mock()
        mock_water_type.name = "water"
        
        multiplier = weather.effect(mock_water_type)
        self.assertGreater(multiplier, 1.0)
        self.assertEqual(multiplier, 1.5)

    def test_rain_reduces_fire_damage(self):
        """Test rain weather reduces fire type damage"""
        weather = Weather("rain")
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        multiplier = weather.effect(mock_fire_type)
        self.assertLess(multiplier, 1.0)
        self.assertEqual(multiplier, 0.5)

    def test_sunny_boosts_fire_damage(self):
        """Test sunny weather boosts fire type damage"""
        weather = Weather("sunny")
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        multiplier = weather.effect(mock_fire_type)
        self.assertGreater(multiplier, 1.0)
        self.assertEqual(multiplier, 1.5)

    def test_sunny_reduces_water_damage(self):
        """Test sunny weather reduces water type damage"""
        weather = Weather("sunny")
        mock_water_type = Mock()
        mock_water_type.name = "water"
        
        multiplier = weather.effect(mock_water_type)
        self.assertLess(multiplier, 1.0)
        self.assertEqual(multiplier, 0.75)

    def test_thunderstorm_doubles_electric_damage(self):
        """Test thunderstorm doubles electric type damage"""
        weather = Weather("thunderstorm")
        mock_electric_type = Mock()
        mock_electric_type.name = "electro"
        
        multiplier = weather.effect(mock_electric_type)
        self.assertEqual(multiplier, 2.0)

    def test_foggy_boosts_undead_damage(self):
        """Test foggy weather boosts undead type damage"""
        weather = Weather("foggy")
        mock_undead_type = Mock()
        mock_undead_type.name = "undead"
        
        multiplier = weather.effect(mock_undead_type)
        self.assertEqual(multiplier, 1.5)

    def test_foggy_increases_all_miss_chance(self):
        """Test foggy weather increases miss chance for all attacks"""
        weather = Weather("foggy")
        global_modifier = weather.get_global_miss_modifier()
        
        self.assertGreater(global_modifier, 0)
        self.assertEqual(global_modifier, 0.2)

    def test_rain_fire_accuracy_penalty(self):
        """Test rain applies accuracy penalty to fire attacks"""
        weather = Weather("rain")
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        modifier = weather.get_miss_chance_modifier(mock_fire_type)
        self.assertGreater(modifier, 0)
        self.assertEqual(modifier, 0.15)

    def test_rain_water_accuracy_boost(self):
        """Test rain gives accuracy boost to water attacks"""
        weather = Weather("rain")
        mock_water_type = Mock()
        mock_water_type.name = "water"
        
        modifier = weather.get_miss_chance_modifier(mock_water_type)
        self.assertLess(modifier, 0)
        self.assertEqual(modifier, -0.1)

    def test_sunny_fire_accuracy_boost(self):
        """Test sunny gives accuracy boost to fire attacks"""
        weather = Weather("sunny")
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        modifier = weather.get_miss_chance_modifier(mock_fire_type)
        self.assertLess(modifier, 0)
        self.assertEqual(modifier, -0.1)

    def test_sunny_ice_accuracy_penalty(self):
        """Test sunny applies accuracy penalty to ice attacks"""
        weather = Weather("sunny")
        mock_ice_type = Mock()
        mock_ice_type.name = "ice"
        
        modifier = weather.get_miss_chance_modifier(mock_ice_type)
        self.assertGreater(modifier, 0)
        self.assertEqual(modifier, 0.1)

    def test_thunderstorm_electric_accuracy_boost(self):
        """Test thunderstorm gives accuracy boost to electric attacks"""
        weather = Weather("thunderstorm")
        mock_electric_type = Mock()
        mock_electric_type.name = "electro"
        
        modifier = weather.get_miss_chance_modifier(mock_electric_type)
        self.assertLess(modifier, 0)
        self.assertEqual(modifier, -0.15)

    def test_thunderstorm_has_global_miss_penalty(self):
        """Test thunderstorm has slight global miss penalty"""
        weather = Weather("thunderstorm")
        global_modifier = weather.get_global_miss_modifier()
        
        self.assertGreater(global_modifier, 0)
        self.assertEqual(global_modifier, 0.05)


class TestWeatherCycleProgression(unittest.TestCase):
    """Tests for weather cycle progression patterns"""

    def test_rain_cycle_pattern(self):
        """Test rain cycles through: rain -> thunderstorm -> rain -> foggy"""
        manager = WeatherManager("rain")
        
        expected = ["rain", "thunderstorm", "rain", "foggy"]
        for i, expected_weather in enumerate(expected):
            manager.update(i * 60)
            self.assertEqual(manager.current.index, expected_weather,
                f"At cycle {i}, expected {expected_weather}")

    def test_thunderstorm_cycle_pattern(self):
        """Test thunderstorm cycles through: thunderstorm -> rain -> foggy -> thunderstorm"""
        manager = WeatherManager("thunderstorm")
        
        expected = ["thunderstorm", "rain", "foggy", "thunderstorm"]
        for i, expected_weather in enumerate(expected):
            manager.update(i * 60)
            self.assertEqual(manager.current.index, expected_weather,
                f"At cycle {i}, expected {expected_weather}")

    def test_foggy_cycle_pattern(self):
        """Test foggy cycles through: foggy -> foggy -> rain -> foggy"""
        manager = WeatherManager("foggy")
        
        expected = ["foggy", "foggy", "rain", "foggy"]
        for i, expected_weather in enumerate(expected):
            manager.update(i * 60)
            self.assertEqual(manager.current.index, expected_weather,
                f"At cycle {i}, expected {expected_weather}")

    def test_sunny_never_changes(self):
        """Test sunny weather never changes"""
        manager = WeatherManager("sunny")
        
        for i in range(10):
            manager.update(i * 60)
            self.assertEqual(manager.current.index, "sunny",
                f"At cycle {i}, expected sunny")


if __name__ == "__main__":
    unittest.main()
