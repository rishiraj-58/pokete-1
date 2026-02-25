from pokete.classes.asset_service.resources.base import WeatherDict

weathers: dict[str, WeatherDict] = {
    "rain": {
        "info": "It's raining!",
        "effected": {
            "fire": 0.5,
            "plant": 1.5,
            "water": 1.5
        },
        "miss_chance_modifier": {
            "fire": 0.15,  # Fire attacks less accurate in rain
            "water": -0.1,  # Water attacks more accurate
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
            "fire": 0.2,  # Fire heavily affected
            "electro": -0.15,  # Electric attacks very accurate
            "all": 0.05,  # Slight miss penalty for all
        }
    },
    "foggy": {
        "info": "It's foggy!",
        "effected": {
            "undead": 1.5,
            "normal": 0.75,
        },
        "miss_chance_modifier": {
            "all": 0.2,  # All attacks have increased miss chance in fog
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
            "fire": -0.1,  # Fire attacks more accurate
            "ice": 0.1,  # Ice attacks less accurate
        }
    }
}
