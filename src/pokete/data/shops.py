"""Shop NPC configurations for the game"""

from typing import TypedDict


class ShopNPCDict(TypedDict):
    texts: list[str]
    map: str
    x: int
    y: int
    shop_name: str
    items: dict[str, int | None]  # item_name -> stock (None = unlimited)
    price_multiplier: float


shops: dict[str, ShopNPCDict] = {
    "general_store_clerk": {
        "texts": [
            "Welcome to the General Store!",
            "We have everything a Pokete trainer needs.",
            "Take a look at our wares!",
        ],
        "map": "playmap_1",
        "x": 15,
        "y": 8,
        "shop_name": "General Store",
        "items": {
            "poketeball": None,  # Unlimited stock
            "superball": None,
            "healing_potion": None,
            "super_potion": 10,  # Limited stock
            "ap_potion": 5,
        },
        "price_multiplier": 1.0,
    },
    "premium_shop_owner": {
        "texts": [
            "Greetings, esteemed trainer!",
            "You've found the Premium Pokete Shop.",
            "Our items are of the highest quality!",
        ],
        "map": "playmap_3",
        "x": 25,
        "y": 10,
        "shop_name": "Premium Shop",
        "items": {
            "superball": 20,  # Limited stock
            "super_potion": 15,
            "ap_potion": 3,
        },
        "price_multiplier": 0.8,
    },
}


if __name__ == "__main__":
    print("\033[31;1mDo not execute this!\033[0m")
