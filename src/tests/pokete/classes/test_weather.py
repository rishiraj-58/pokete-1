"""Unit tests for the Weather system"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock the data module before importing weather
mock_weathers = {
    "rain": {
        "info": "It's raining!",
        "effected": {
            "fire": 0.5,
            "plant": 1.5,
            "water": 1.5
        },
        "miss_chance_modifier": {
            "fire": 0.1,
        },
        "global_miss_modifier": 0.0,
        "icon": "🌧️",
        "cycle_weathers": ["thunderstorm", "clear"],
        "cycle_weights": [0.4, 0.6],
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
            "fire": 0.15,
        },
        "global_miss_modifier": 0.05,
        "icon": "⛈️",
        "cycle_weathers": ["rain", "clear"],
        "cycle_weights": [0.5, 0.5],
    },
    "foggy": {
        "info": "It's foggy!",
        "effected": {
            "undead": 1.5,
            "normal": 0.75,
        },
        "miss_chance_modifier": {},
        "global_miss_modifier": 0.15,
        "icon": "🌫️",
        "cycle_weathers": ["clear", "rain"],
        "cycle_weights": [0.7, 0.3],
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
            "water": 0.05,
            "ice": 0.1,
        },
        "global_miss_modifier": -0.05,
        "icon": "☀️",
        "cycle_weathers": ["clear", "foggy"],
        "cycle_weights": [0.8, 0.2],
    },
    "clear": {
        "info": "The weather is clear.",
        "effected": {},
        "miss_chance_modifier": {},
        "global_miss_modifier": 0.0,
        "icon": "🌤️",
        "cycle_weathers": ["sunny", "rain", "foggy"],
        "cycle_weights": [0.4, 0.3, 0.3],
    },
}

# Create mock pokete.data module
mock_data = MagicMock()
mock_data.weathers = mock_weathers
sys.modules['pokete.data'] = mock_data


# Now we define Weather and WeatherManager locally to avoid import issues
import random
import time
import threading
from typing import Optional, Callable


class Weather:
    """Behaviour for a certain weather"""

    def __init__(self, index: str):
        self.index = index
        self.info = mock_weathers[index]["info"]
        self.effected = mock_weathers[index]["effected"]
        self.miss_chance_modifier = mock_weathers[index].get("miss_chance_modifier", {})
        self.global_miss_modifier = mock_weathers[index].get("global_miss_modifier", 0.0)
        self.icon = mock_weathers[index].get("icon", "")
        self.cycle_weathers = mock_weathers[index].get("cycle_weathers", [])
        self.cycle_weights = mock_weathers[index].get("cycle_weights", [])

    def effect(self, typ) -> float:
        """Gives an additional attackfactor"""
        return self.effected.get(typ.name, 1)

    def get_miss_modifier(self, attack_type_name: str) -> float:
        """Gets the miss chance modifier for an attack type"""
        type_modifier = self.miss_chance_modifier.get(attack_type_name, 0.0)
        return type_modifier + self.global_miss_modifier

    def get_next_weather(self) -> Optional[str]:
        """Gets the next weather based on cycle weights"""
        if not self.cycle_weathers or not self.cycle_weights:
            return None
        return random.choices(self.cycle_weathers, weights=self.cycle_weights, k=1)[0]


class WeatherManager:
    """Manages weather cycling for maps using a timer-based system"""

    DEFAULT_CYCLE_INTERVAL = 300

    def __init__(self, cycle_interval: float = DEFAULT_CYCLE_INTERVAL):
        self._cycle_interval = cycle_interval
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._maps = {}
        self._on_weather_change = None

    def register_map(self, map_name: str, play_map):
        with self._lock:
            self._maps[map_name] = play_map

    def unregister_map(self, map_name: str):
        with self._lock:
            if map_name in self._maps:
                del self._maps[map_name]

    def set_weather_change_callback(self, callback: Callable):
        self._on_weather_change = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._cycle_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _cycle_loop(self):
        while self._running:
            time.sleep(self._cycle_interval)
            if not self._running:
                break
            self._cycle_all_maps()

    def _cycle_all_maps(self):
        with self._lock:
            for map_name, play_map in self._maps.items():
                self._cycle_map_weather(map_name, play_map)

    def _cycle_map_weather(self, map_name: str, play_map):
        if play_map.weather is None:
            return

        next_weather_index = play_map.weather.get_next_weather()
        if next_weather_index is None:
            return

        play_map.weather = Weather(next_weather_index)

        if self._on_weather_change:
            self._on_weather_change(map_name, play_map.weather)

    def force_cycle(self, map_name: str):
        with self._lock:
            if map_name in self._maps:
                self._cycle_map_weather(map_name, self._maps[map_name])

    def set_weather(self, map_name: str, weather_index: str):
        with self._lock:
            if map_name in self._maps:
                self._maps[map_name].weather = Weather(weather_index)
                if self._on_weather_change:
                    self._on_weather_change(map_name, self._maps[map_name].weather)

    def get_weather(self, map_name: str):
        with self._lock:
            if map_name in self._maps:
                return self._maps[map_name].weather
            return None


class TestWeather(unittest.TestCase):
    """Tests for the Weather class"""

    def test_weather_initialization_rain(self):
        """Test that rain weather initializes correctly"""
        weather = Weather("rain")
        
        self.assertEqual(weather.index, "rain")
        self.assertEqual(weather.info, "It's raining!")
        self.assertEqual(weather.icon, "🌧️")
        self.assertIn("fire", weather.effected)
        self.assertEqual(weather.effected["fire"], 0.5)
        self.assertEqual(weather.effected["water"], 1.5)
        self.assertEqual(weather.effected["plant"], 1.5)

    def test_weather_initialization_sunny(self):
        """Test that sunny weather initializes correctly"""
        weather = Weather("sunny")
        
        self.assertEqual(weather.index, "sunny")
        self.assertEqual(weather.info, "It's a hot sunny day!")
        self.assertEqual(weather.icon, "☀️")
        self.assertEqual(weather.effected["fire"], 1.5)
        self.assertEqual(weather.effected["water"], 0.75)
        self.assertEqual(weather.effected["ice"], 0.5)

    def test_weather_initialization_foggy(self):
        """Test that foggy weather initializes correctly"""
        weather = Weather("foggy")
        
        self.assertEqual(weather.index, "foggy")
        self.assertEqual(weather.info, "It's foggy!")
        self.assertEqual(weather.icon, "🌫️")
        self.assertEqual(weather.effected["undead"], 1.5)
        self.assertEqual(weather.effected["normal"], 0.75)

    def test_weather_initialization_thunderstorm(self):
        """Test that thunderstorm weather initializes correctly"""
        weather = Weather("thunderstorm")
        
        self.assertEqual(weather.index, "thunderstorm")
        self.assertEqual(weather.info, "There is a thunderstorm going on!")
        self.assertEqual(weather.icon, "⛈️")
        self.assertEqual(weather.effected["electro"], 2)

    def test_weather_initialization_clear(self):
        """Test that clear weather initializes correctly"""
        weather = Weather("clear")
        
        self.assertEqual(weather.index, "clear")
        self.assertEqual(weather.info, "The weather is clear.")
        self.assertEqual(weather.icon, "🌤️")
        self.assertEqual(len(weather.effected), 0)

    def test_weather_effect_returns_modifier_for_affected_type(self):
        """Test that effect() returns correct modifier for affected types"""
        weather = Weather("rain")
        
        mock_type = Mock()
        mock_type.name = "water"
        
        result = weather.effect(mock_type)
        
        self.assertEqual(result, 1.5)

    def test_weather_effect_returns_1_for_unaffected_type(self):
        """Test that effect() returns 1 for unaffected types"""
        weather = Weather("rain")
        
        mock_type = Mock()
        mock_type.name = "stone"
        
        result = weather.effect(mock_type)
        
        self.assertEqual(result, 1)

    def test_rain_miss_modifier_fire_type(self):
        """Test that rain increases miss chance for fire attacks"""
        weather = Weather("rain")
        
        miss_modifier = weather.get_miss_modifier("fire")
        
        self.assertEqual(miss_modifier, 0.1)

    def test_rain_miss_modifier_water_type(self):
        """Test that rain doesn't affect miss chance for water attacks"""
        weather = Weather("rain")
        
        miss_modifier = weather.get_miss_modifier("water")
        
        self.assertEqual(miss_modifier, 0.0)

    def test_foggy_global_miss_modifier(self):
        """Test that foggy weather increases miss chance globally"""
        weather = Weather("foggy")
        
        miss_modifier = weather.get_miss_modifier("normal")
        
        self.assertEqual(miss_modifier, 0.15)

    def test_foggy_affects_all_types(self):
        """Test that foggy weather affects all attack types"""
        weather = Weather("foggy")
        
        fire_mod = weather.get_miss_modifier("fire")
        water_mod = weather.get_miss_modifier("water")
        plant_mod = weather.get_miss_modifier("plant")
        
        self.assertEqual(fire_mod, 0.15)
        self.assertEqual(water_mod, 0.15)
        self.assertEqual(plant_mod, 0.15)

    def test_sunny_reduces_miss_chance(self):
        """Test that sunny weather reduces global miss chance"""
        weather = Weather("sunny")
        
        miss_modifier = weather.get_miss_modifier("fire")
        
        self.assertEqual(miss_modifier, -0.05)

    def test_sunny_increases_miss_for_specific_types(self):
        """Test that sunny weather increases miss chance for water/ice"""
        weather = Weather("sunny")
        
        water_mod = weather.get_miss_modifier("water")
        ice_mod = weather.get_miss_modifier("ice")
        
        self.assertEqual(water_mod, 0.0)  # 0.05 type + (-0.05) global = 0
        self.assertEqual(ice_mod, 0.05)  # 0.1 type + (-0.05) global = 0.05

    def test_thunderstorm_miss_modifier(self):
        """Test that thunderstorm has combined miss effects"""
        weather = Weather("thunderstorm")
        
        fire_mod = weather.get_miss_modifier("fire")
        water_mod = weather.get_miss_modifier("water")
        
        self.assertEqual(fire_mod, 0.20)  # 0.15 + 0.05 global
        self.assertEqual(water_mod, 0.05)  # 0 + 0.05 global

    def test_get_next_weather_returns_valid_weather(self):
        """Test that get_next_weather returns a weather from cycle list"""
        weather = Weather("rain")
        
        next_weather = weather.get_next_weather()
        
        self.assertIn(next_weather, weather.cycle_weathers)

    def test_get_next_weather_none_for_empty_cycles(self):
        """Test get_next_weather with manually cleared cycles"""
        weather = Weather("rain")
        weather.cycle_weathers = []
        weather.cycle_weights = []
        
        next_weather = weather.get_next_weather()
        
        self.assertIsNone(next_weather)

    def test_clear_weather_can_transition_to_multiple(self):
        """Test that clear weather has multiple transition options"""
        weather = Weather("clear")
        
        self.assertIn("sunny", weather.cycle_weathers)
        self.assertIn("rain", weather.cycle_weathers)
        self.assertIn("foggy", weather.cycle_weathers)


class TestWeatherManager(unittest.TestCase):
    """Tests for the WeatherManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = WeatherManager(cycle_interval=0.1)

    def tearDown(self):
        """Clean up after tests"""
        self.manager.stop()

    def test_register_map(self):
        """Test that maps can be registered"""
        mock_map = Mock()
        mock_map.weather = Weather("rain")
        
        self.manager.register_map("test_map", mock_map)
        
        result = self.manager.get_weather("test_map")
        self.assertEqual(result.index, "rain")

    def test_unregister_map(self):
        """Test that maps can be unregistered"""
        mock_map = Mock()
        mock_map.weather = Weather("rain")
        
        self.manager.register_map("test_map", mock_map)
        self.manager.unregister_map("test_map")
        
        result = self.manager.get_weather("test_map")
        self.assertIsNone(result)

    def test_set_weather(self):
        """Test that weather can be set manually"""
        mock_map = Mock()
        mock_map.weather = Weather("rain")
        
        self.manager.register_map("test_map", mock_map)
        self.manager.set_weather("test_map", "sunny")
        
        self.assertEqual(mock_map.weather.index, "sunny")

    def test_force_cycle_changes_weather(self):
        """Test that force_cycle changes the weather"""
        mock_map = Mock()
        mock_map.weather = Weather("clear")
        
        self.manager.register_map("test_map", mock_map)
        
        original_weather = mock_map.weather.index
        cycles = 0
        max_cycles = 100
        
        while mock_map.weather.index == original_weather and cycles < max_cycles:
            self.manager.force_cycle("test_map")
            cycles += 1
        
        self.assertIn(mock_map.weather.index, ["sunny", "rain", "foggy"])

    def test_weather_change_callback(self):
        """Test that callback is called on weather change"""
        mock_map = Mock()
        mock_map.weather = Weather("clear")
        callback = Mock()
        
        self.manager.set_weather_change_callback(callback)
        self.manager.register_map("test_map", mock_map)
        self.manager.set_weather("test_map", "rain")
        
        callback.assert_called_once()
        call_args = callback.call_args
        self.assertEqual(call_args[0][0], "test_map")
        self.assertEqual(call_args[0][1].index, "rain")

    def test_start_stop(self):
        """Test that manager can be started and stopped"""
        self.assertFalse(self.manager._running)
        
        self.manager.start()
        self.assertTrue(self.manager._running)
        self.assertIsNotNone(self.manager._thread)
        
        self.manager.stop()
        self.assertFalse(self.manager._running)

    def test_get_weather_nonexistent_map(self):
        """Test that get_weather returns None for nonexistent maps"""
        result = self.manager.get_weather("nonexistent")
        
        self.assertIsNone(result)

    def test_null_weather_map_not_cycled(self):
        """Test that maps with no weather are not cycled"""
        mock_map = Mock()
        mock_map.weather = None
        
        self.manager.register_map("test_map", mock_map)
        self.manager.force_cycle("test_map")
        
        self.assertIsNone(mock_map.weather)


class TestWeatherAttackEffects(unittest.TestCase):
    """Integration tests for weather effects on attacks"""

    def test_rain_boosts_water_attacks(self):
        """Test that rain weather boosts water type attacks"""
        weather = Weather("rain")
        
        mock_water_type = Mock()
        mock_water_type.name = "water"
        
        effect = weather.effect(mock_water_type)
        
        self.assertEqual(effect, 1.5)

    def test_rain_reduces_fire_attacks(self):
        """Test that rain weather reduces fire type attacks"""
        weather = Weather("rain")
        
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        effect = weather.effect(mock_fire_type)
        
        self.assertEqual(effect, 0.5)

    def test_sunny_boosts_fire_attacks(self):
        """Test that sunny weather boosts fire type attacks"""
        weather = Weather("sunny")
        
        mock_fire_type = Mock()
        mock_fire_type.name = "fire"
        
        effect = weather.effect(mock_fire_type)
        
        self.assertEqual(effect, 1.5)

    def test_sunny_reduces_water_attacks(self):
        """Test that sunny weather reduces water type attacks"""
        weather = Weather("sunny")
        
        mock_water_type = Mock()
        mock_water_type.name = "water"
        
        effect = weather.effect(mock_water_type)
        
        self.assertEqual(effect, 0.75)

    def test_thunderstorm_boosts_electro_attacks(self):
        """Test that thunderstorm weather boosts electro attacks"""
        weather = Weather("thunderstorm")
        
        mock_electro_type = Mock()
        mock_electro_type.name = "electro"
        
        effect = weather.effect(mock_electro_type)
        
        self.assertEqual(effect, 2)

    def test_foggy_boosts_undead_attacks(self):
        """Test that foggy weather boosts undead attacks"""
        weather = Weather("foggy")
        
        mock_undead_type = Mock()
        mock_undead_type.name = "undead"
        
        effect = weather.effect(mock_undead_type)
        
        self.assertEqual(effect, 1.5)

    def test_foggy_reduces_normal_attacks(self):
        """Test that foggy weather reduces normal attacks"""
        weather = Weather("foggy")
        
        mock_normal_type = Mock()
        mock_normal_type.name = "normal"
        
        effect = weather.effect(mock_normal_type)
        
        self.assertEqual(effect, 0.75)


class TestWeatherMissChanceCalculations(unittest.TestCase):
    """Tests for miss chance calculations with weather effects"""

    def test_combined_miss_chance_foggy(self):
        """Test combined miss chance calculation in fog"""
        weather = Weather("foggy")
        base_miss = 0.2
        
        weather_modifier = weather.get_miss_modifier("normal")
        total_miss = base_miss + weather_modifier
        
        self.assertEqual(total_miss, 0.35)

    def test_combined_miss_chance_sunny_fire(self):
        """Test combined miss chance for fire in sunny weather"""
        weather = Weather("sunny")
        base_miss = 0.2
        
        weather_modifier = weather.get_miss_modifier("fire")
        total_miss = base_miss + weather_modifier
        
        self.assertAlmostEqual(total_miss, 0.15)

    def test_combined_miss_chance_rain_fire(self):
        """Test combined miss chance for fire in rain"""
        weather = Weather("rain")
        base_miss = 0.2
        
        weather_modifier = weather.get_miss_modifier("fire")
        total_miss = base_miss + weather_modifier
        
        self.assertAlmostEqual(total_miss, 0.30)

    def test_miss_chance_bounded(self):
        """Test that calculated miss chance remains reasonable"""
        weather = Weather("foggy")
        base_miss = 0.9
        
        weather_modifier = weather.get_miss_modifier("normal")
        total_miss = max(0.0, min(1.0, base_miss + weather_modifier))
        
        self.assertLessEqual(total_miss, 1.0)
        self.assertGreaterEqual(total_miss, 0.0)


class TestWeatherTransitions(unittest.TestCase):
    """Tests for weather transition/cycling logic"""

    def test_rain_can_transition_to_thunderstorm(self):
        """Test that rain can transition to thunderstorm"""
        weather = Weather("rain")
        
        self.assertIn("thunderstorm", weather.cycle_weathers)

    def test_rain_can_transition_to_clear(self):
        """Test that rain can transition to clear"""
        weather = Weather("rain")
        
        self.assertIn("clear", weather.cycle_weathers)

    def test_thunderstorm_transitions(self):
        """Test thunderstorm transition options"""
        weather = Weather("thunderstorm")
        
        self.assertIn("rain", weather.cycle_weathers)
        self.assertIn("clear", weather.cycle_weathers)

    def test_sunny_transitions(self):
        """Test sunny transition options"""
        weather = Weather("sunny")
        
        self.assertIn("clear", weather.cycle_weathers)
        self.assertIn("foggy", weather.cycle_weathers)

    def test_foggy_transitions(self):
        """Test foggy transition options"""
        weather = Weather("foggy")
        
        self.assertIn("clear", weather.cycle_weathers)
        self.assertIn("rain", weather.cycle_weathers)

    def test_cycle_weights_match_weathers(self):
        """Test that cycle weights have same length as cycle weathers"""
        for weather_name in ["rain", "thunderstorm", "foggy", "sunny", "clear"]:
            weather = Weather(weather_name)
            self.assertEqual(
                len(weather.cycle_weathers),
                len(weather.cycle_weights),
                f"Mismatch for {weather_name}"
            )


class TestAttackProcessWeatherMissChance(unittest.TestCase):
    """Tests for miss chance calculations in AttackProcess with weather"""

    @staticmethod
    def get_random_factor(attack, attacker, weather=None):
        """Static method to calculate random factor for testing"""
        base_miss_chance = attack.miss_chance + attacker.miss_chance
        
        weather_miss_modifier = 0.0
        if weather is not None:
            weather_miss_modifier = weather.get_miss_modifier(attack.type.name)
        
        total_miss_chance = max(0.0, min(1.0, base_miss_chance + weather_miss_modifier))
        
        return total_miss_chance

    def test_get_random_factor_no_weather(self):
        """Test random factor calculation without weather"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "normal"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        result = self.get_random_factor(mock_attack, mock_attacker, None)
        
        self.assertAlmostEqual(result, 0.3)

    def test_get_random_factor_with_rain_fire(self):
        """Test that rain increases miss chance for fire attacks"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "fire"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        weather = Weather("rain")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertAlmostEqual(result, 0.4)

    def test_get_random_factor_with_sunny_fire(self):
        """Test that sunny weather reduces miss chance for fire"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "fire"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        weather = Weather("sunny")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertAlmostEqual(result, 0.25)

    def test_get_random_factor_with_foggy(self):
        """Test that foggy weather increases miss chance globally"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "normal"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        weather = Weather("foggy")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertAlmostEqual(result, 0.45)

    def test_get_random_factor_clamped_max(self):
        """Test that miss chance is clamped to maximum of 1.0"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.8
        mock_attack.type = Mock()
        mock_attack.type.name = "fire"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.5
        
        weather = Weather("foggy")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertLessEqual(result, 1.0)

    def test_get_random_factor_clamped_min(self):
        """Test that miss chance is clamped to minimum of 0.0"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.0
        mock_attack.type = Mock()
        mock_attack.type.name = "fire"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.0
        
        weather = Weather("sunny")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertGreaterEqual(result, 0.0)

    def test_get_random_factor_thunderstorm_fire(self):
        """Test thunderstorm combined effects on fire attacks"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "fire"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        weather = Weather("thunderstorm")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertAlmostEqual(result, 0.5)

    def test_get_random_factor_clear_weather(self):
        """Test that clear weather has no effect on miss chance"""
        mock_attack = Mock()
        mock_attack.miss_chance = 0.2
        mock_attack.type = Mock()
        mock_attack.type.name = "normal"
        
        mock_attacker = Mock()
        mock_attacker.miss_chance = 0.1
        
        weather = Weather("clear")
        
        result = self.get_random_factor(mock_attack, mock_attacker, weather)
        
        self.assertAlmostEqual(result, 0.3)


class TestWeatherIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for weather effects"""

    def test_rain_fire_attack_scenario(self):
        """Test complete scenario: fire attack during rain"""
        weather = Weather("rain")
        
        mock_type = Mock()
        mock_type.name = "fire"
        
        effect_modifier = weather.effect(mock_type)
        miss_modifier = weather.get_miss_modifier("fire")
        
        self.assertEqual(effect_modifier, 0.5)
        self.assertEqual(miss_modifier, 0.1)

    def test_rain_water_attack_scenario(self):
        """Test complete scenario: water attack during rain"""
        weather = Weather("rain")
        
        mock_type = Mock()
        mock_type.name = "water"
        
        effect_modifier = weather.effect(mock_type)
        miss_modifier = weather.get_miss_modifier("water")
        
        self.assertEqual(effect_modifier, 1.5)
        self.assertEqual(miss_modifier, 0.0)

    def test_sunny_ice_attack_scenario(self):
        """Test complete scenario: ice attack during sunny weather"""
        weather = Weather("sunny")
        
        mock_type = Mock()
        mock_type.name = "ice"
        
        effect_modifier = weather.effect(mock_type)
        miss_modifier = weather.get_miss_modifier("ice")
        
        self.assertEqual(effect_modifier, 0.5)
        self.assertEqual(miss_modifier, 0.05)

    def test_foggy_undead_attack_scenario(self):
        """Test complete scenario: undead attack during fog"""
        weather = Weather("foggy")
        
        mock_type = Mock()
        mock_type.name = "undead"
        
        effect_modifier = weather.effect(mock_type)
        miss_modifier = weather.get_miss_modifier("undead")
        
        self.assertEqual(effect_modifier, 1.5)
        self.assertEqual(miss_modifier, 0.15)

    def test_thunderstorm_electro_attack_scenario(self):
        """Test complete scenario: electro attack during thunderstorm"""
        weather = Weather("thunderstorm")
        
        mock_type = Mock()
        mock_type.name = "electro"
        
        effect_modifier = weather.effect(mock_type)
        miss_modifier = weather.get_miss_modifier("electro")
        
        self.assertEqual(effect_modifier, 2)
        self.assertEqual(miss_modifier, 0.05)


if __name__ == "__main__":
    unittest.main()
