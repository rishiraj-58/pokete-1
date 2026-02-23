"""Shop NPC definitions and their inventories"""

from typing import Dict, List, Optional, TypedDict, Union


class ShopNPCDict(TypedDict):
    shop_name: str
    texts: List[str]
    farewell_texts: List[str]
    inventory: Dict[str, Optional[int]]
    map: str
    x: int
    y: int


shops: dict[str, ShopNPCDict] = {
    "general_store_clerk": {
        "shop_name": "General Store",
        "texts": [
            "Welcome to the General Store!",
            "We have all the basics a trainer needs.",
            "What would you like to buy?"
        ],
        "farewell_texts": [
            "Thanks for shopping with us!",
            "Good luck on your journey!"
        ],
        "inventory": {
            "poketeball": None,
            "superball": 10,
            "healing_potion": None,
            "super_potion": 5,
        },
        "map": "playmap_1",
        "x": 15,
        "y": 10
    },
    "potion_merchant": {
        "shop_name": "Potion Emporium",
        "texts": [
            "Greetings, weary traveler!",
            "I specialize in potions and remedies.",
            "Take a look at my wares!"
        ],
        "farewell_texts": [
            "May your Poketes stay healthy!",
            "Visit again soon!"
        ],
        "inventory": {
            "healing_potion": None,
            "super_potion": None,
            "ap_potion": 3,
        },
        "map": "playmap_3",
        "x": 40,
        "y": 8
    },
}


if __name__ == "__main__":
    print("\033[31;1mDo not execute this!\033[0m")
