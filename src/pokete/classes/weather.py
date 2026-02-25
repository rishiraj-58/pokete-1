"""Contains Weather class and WeatherManager for dynamic weather cycling"""

import random
import time
import threading
from typing import Optional, Callable

from pokete.data import weathers


class Weather:
    """Behaviour for a certain weather
    ARGS:
        index: The weathers name"""

    def __init__(self, index: str):
        self.index = index
        self.info = weathers[index]["info"]
        self.effected = weathers[index]["effected"]
        self.miss_chance_modifier = weathers[index].get("miss_chance_modifier", {})
        self.global_miss_modifier = weathers[index].get("global_miss_modifier", 0.0)
        self.icon = weathers[index].get("icon", "")
        self.cycle_weathers = weathers[index].get("cycle_weathers", [])
        self.cycle_weights = weathers[index].get("cycle_weights", [])

    def effect(self, typ) -> float:
        """Gives an additional attackfactor
        ARGS:
            typ: The attacks type
        RETURNS:
            attackfactor"""
        return self.effected.get(typ.name, 1)

    def get_miss_modifier(self, attack_type_name: str) -> float:
        """Gets the miss chance modifier for an attack type
        ARGS:
            attack_type_name: The attack type name
        RETURNS:
            miss chance modifier (additive)"""
        type_modifier = self.miss_chance_modifier.get(attack_type_name, 0.0)
        return type_modifier + self.global_miss_modifier

    def get_next_weather(self) -> Optional[str]:
        """Gets the next weather based on cycle weights
        RETURNS:
            Next weather index or None if no cycling configured"""
        if not self.cycle_weathers or not self.cycle_weights:
            return None
        return random.choices(self.cycle_weathers, weights=self.cycle_weights, k=1)[0]


class WeatherManager:
    """Manages weather cycling for maps using a timer-based system"""

    DEFAULT_CYCLE_INTERVAL = 300  # 5 minutes in seconds

    def __init__(self, cycle_interval: float = DEFAULT_CYCLE_INTERVAL):
        self._cycle_interval = cycle_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._maps: dict[str, "PlayMap"] = {}
        self._on_weather_change: Optional[Callable[[str, Weather], None]] = None

    def register_map(self, map_name: str, play_map: "PlayMap"):
        """Register a map for weather management
        ARGS:
            map_name: The map identifier
            play_map: The PlayMap instance"""
        with self._lock:
            self._maps[map_name] = play_map

    def unregister_map(self, map_name: str):
        """Unregister a map from weather management
        ARGS:
            map_name: The map identifier"""
        with self._lock:
            if map_name in self._maps:
                del self._maps[map_name]

    def set_weather_change_callback(self, callback: Callable[[str, Weather], None]):
        """Set callback for weather change events
        ARGS:
            callback: Function(map_name, new_weather) called on weather change"""
        self._on_weather_change = callback

    def start(self):
        """Start the weather cycling thread"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._cycle_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the weather cycling thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _cycle_loop(self):
        """Main loop for cycling weather"""
        while self._running:
            time.sleep(self._cycle_interval)
            if not self._running:
                break
            self._cycle_all_maps()

    def _cycle_all_maps(self):
        """Cycle weather for all registered maps"""
        with self._lock:
            for map_name, play_map in self._maps.items():
                self._cycle_map_weather(map_name, play_map)

    def _cycle_map_weather(self, map_name: str, play_map: "PlayMap"):
        """Cycle weather for a single map
        ARGS:
            map_name: The map identifier
            play_map: The PlayMap instance"""
        if play_map.weather is None:
            return

        next_weather_index = play_map.weather.get_next_weather()
        if next_weather_index is None:
            return

        play_map.weather = Weather(next_weather_index)

        if self._on_weather_change:
            self._on_weather_change(map_name, play_map.weather)

    def force_cycle(self, map_name: str):
        """Force immediate weather cycle for a specific map
        ARGS:
            map_name: The map identifier"""
        with self._lock:
            if map_name in self._maps:
                self._cycle_map_weather(map_name, self._maps[map_name])

    def set_weather(self, map_name: str, weather_index: str):
        """Manually set weather for a specific map
        ARGS:
            map_name: The map identifier
            weather_index: The weather to set"""
        with self._lock:
            if map_name in self._maps:
                self._maps[map_name].weather = Weather(weather_index)
                if self._on_weather_change:
                    self._on_weather_change(map_name, self._maps[map_name].weather)

    def get_weather(self, map_name: str) -> Optional[Weather]:
        """Get current weather for a map
        ARGS:
            map_name: The map identifier
        RETURNS:
            Current Weather or None"""
        with self._lock:
            if map_name in self._maps:
                return self._maps[map_name].weather
            return None


weather_manager = WeatherManager()
