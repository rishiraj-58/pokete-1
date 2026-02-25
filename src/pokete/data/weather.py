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
