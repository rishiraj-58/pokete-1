"""Contains configurable daily quest definitions"""

from typing import TypedDict


class QuestRewardDict(TypedDict):
    money: int
    items: dict[str, int]  # item_name -> amount


class QuestDict(TypedDict):
    title: str
    description: str
    quest_type: str  # "catch", "trainer_battle", "collect_coins", "win_battles"
    target: int
    reward: QuestRewardDict


quests: dict[str, QuestDict] = {
    "catch_3_poketes": {
        "title": "Pokete Collector",
        "description": "Catch 3 wild Poketes today",
        "quest_type": "catch",
        "target": 3,
        "reward": {
            "money": 50,
            "items": {"poketeball": 5},
        },
    },
    "catch_5_poketes": {
        "title": "Expert Catcher",
        "description": "Catch 5 wild Poketes today",
        "quest_type": "catch",
        "target": 5,
        "reward": {
            "money": 100,
            "items": {"superball": 3},
        },
    },
    "win_2_trainer_battles": {
        "title": "Trainer Challenger",
        "description": "Win 2 trainer battles today",
        "quest_type": "trainer_battle",
        "target": 2,
        "reward": {
            "money": 75,
            "items": {"healing_potion": 2},
        },
    },
    "win_5_trainer_battles": {
        "title": "Battle Master",
        "description": "Win 5 trainer battles today",
        "quest_type": "trainer_battle",
        "target": 5,
        "reward": {
            "money": 150,
            "items": {"super_potion": 2},
        },
    },
    "collect_100_coins": {
        "title": "Money Maker",
        "description": "Collect 100 coins today",
        "quest_type": "collect_coins",
        "target": 100,
        "reward": {
            "money": 50,
            "items": {"healing_potion": 3},
        },
    },
    "collect_200_coins": {
        "title": "Wealthy Trainer",
        "description": "Collect 200 coins today",
        "quest_type": "collect_coins",
        "target": 200,
        "reward": {
            "money": 100,
            "items": {"super_potion": 1, "poketeball": 5},
        },
    },
    "win_3_battles": {
        "title": "Battle Enthusiast",
        "description": "Win 3 battles (wild or trainer)",
        "quest_type": "win_battles",
        "target": 3,
        "reward": {
            "money": 60,
            "items": {"poketeball": 3},
        },
    },
    "win_7_battles": {
        "title": "Unstoppable",
        "description": "Win 7 battles today",
        "quest_type": "win_battles",
        "target": 7,
        "reward": {
            "money": 200,
            "items": {"superball": 2, "super_potion": 2},
        },
    },
}

if __name__ == "__main__":
    print("\033[31;1mDo not execute this!\033[0m")
