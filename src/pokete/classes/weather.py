"""Contains Weather class and WeatherManager for dynamic weather cycling"""

from enum import Enum
from typing import Optional
from pokete.data import weathers


class WeatherType(Enum):
    """Enum for weather types"""
    CLEAR = "clear"
    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"
    FOGGY = "foggy"
    SUNNY = "sunny"


# Weather cycle duration in game minutes
WEATHER_CYCLE_DURATION = 60


class Weather:
    """Behaviour for a certain weather
    ARGS:
        index: The weathers name"""

    def __init__(self, index: str):
        self.index = index
        self.info = weathers[index]["info"]
        self.effected = weathers[index]["effected"]
        self._miss_chance_modifier = weathers[index].get("miss_chance_modifier", {})

    def effect(self, typ) -> float:
        """Gives an additional attack factor based on weather
        ARGS:
            typ: The attacks type
        RETURNS:
            Attack damage multiplier"""
        return self.effected.get(typ.name, 1)

    def get_miss_chance_modifier(self, typ) -> float:
        """Gets additional miss chance modifier for attack type
        ARGS:
            typ: The attacks type
        RETURNS:
            Additional miss chance to add (can be negative for improved accuracy)"""
        return self._miss_chance_modifier.get(typ.name, 0)

    def get_global_miss_modifier(self) -> float:
        """Gets global miss chance modifier that applies to all attacks
        RETURNS:
            Additional miss chance applied to all attacks"""
        return self._miss_chance_modifier.get("all", 0)

    @property
    def display_name(self) -> str:
        """Returns a short display name for HUD"""
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
        """Returns an icon/symbol for the weather"""
        icons = {
            "rain": "~",
            "thunderstorm": "⚡",
            "foggy": "≈",
            "sunny": "☀",
            "clear": "○",
        }
        return icons.get(self.index, "?")


class WeatherManager:
    """Manages weather cycling for maps"""

    def __init__(self, base_weather: Optional[str] = None):
        self._base_weather = base_weather
        self._current_weather: Optional[Weather] = None
        self._last_cycle_time = 0
        if base_weather is not None:
            self._current_weather = Weather(base_weather)

    @property
    def current(self) -> Optional[Weather]:
        """Returns current weather"""
        return self._current_weather

    def update(self, game_time: int) -> bool:
        """Updates weather based on game time
        ARGS:
            game_time: Current game time in minutes
        RETURNS:
            True if weather changed"""
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
        """Determines weather based on cycle position and base weather
        ARGS:
            cycle: Current cycle position (0-3)
        RETURNS:
            Weather index string"""
        weather_progressions = {
            "rain": ["rain", "thunderstorm", "rain", "foggy"],
            "thunderstorm": ["thunderstorm", "rain", "foggy", "thunderstorm"],
            "foggy": ["foggy", "foggy", "rain", "foggy"],
            "sunny": ["sunny", "sunny", "sunny", "sunny"],
        }
        progression = weather_progressions.get(self._base_weather, [self._base_weather] * 4)
        return progression[cycle]

    def set_weather(self, weather_index: str):
        """Manually sets weather (for testing/events)
        ARGS:
            weather_index: The weather type to set"""
        if weather_index in weathers:
            self._current_weather = Weather(weather_index)
        else:
            self._current_weather = None

    def clear_weather(self):
        """Clears current weather"""
        self._current_weather = None
