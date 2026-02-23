"""Shop NPC implementation for purchasable items"""

import logging

from pokete.classes.items.invitem import InvItem

from .npcs import NPC
from .npc_action import NPCAction, NPCInterface, UIInterface


class ShopInventoryConfig:
    """Configuration for a shop's inventory with stock tracking"""

    def __init__(
        self,
        items: list[str] | dict[str, int | None],
        price_multiplier: float = 1.0,
    ):
        """
        Initialize shop inventory configuration.

        Args:
            items: Either a list of item names (unlimited stock) or a dict
                   mapping item names to stock quantities (None = unlimited)
            price_multiplier: Multiplier for item prices (default 1.0)
        """
        self.price_multiplier = price_multiplier

        if isinstance(items, list):
            self._stock: dict[str, int | None] = {item: None for item in items}
        else:
            self._stock = dict(items)

        self._initial_stock: dict[str, int | None] = dict(self._stock)

    @property
    def items(self) -> list[str]:
        """Returns list of item names in the inventory"""
        return list(self._stock.keys())

    def get_item_price(self, item: InvItem) -> int:
        """Gets the adjusted price for an item"""
        if item.price is None:
            return 0
        return int(item.price * self.price_multiplier)

    def get_stock(self, item_name: str) -> int | None:
        """
        Gets the current stock for an item.

        Returns:
            Stock quantity, or None if unlimited
        """
        return self._stock.get(item_name)

    def has_stock(self, item_name: str) -> bool:
        """
        Checks if an item is in stock.

        Returns:
            True if item has stock available (or unlimited), False if depleted
        """
        if item_name not in self._stock:
            return False
        stock = self._stock[item_name]
        return stock is None or stock > 0

    def consume_stock(self, item_name: str) -> bool:
        """
        Consumes one unit of stock for an item.

        Returns:
            True if stock was consumed, False if out of stock
        """
        if item_name not in self._stock:
            return False

        stock = self._stock[item_name]
        if stock is None:
            return True
        if stock > 0:
            self._stock[item_name] = stock - 1
            logging.info(
                "[ShopInventoryConfig] Stock consumed for '%s': %d -> %d",
                item_name,
                stock,
                stock - 1,
            )
            return True
        return False

    def is_out_of_stock(self, item_name: str) -> bool:
        """
        Checks if an item is completely out of stock.

        Returns:
            True if stock is 0, False if has stock or unlimited
        """
        stock = self._stock.get(item_name)
        return stock is not None and stock == 0

    def reset_stock(self):
        """Resets all stock to initial values"""
        self._stock = dict(self._initial_stock)

    def to_dict(self) -> dict[str, int | None]:
        """Serializes current stock state for saving"""
        return dict(self._stock)

    def load_stock(self, stock_data: dict[str, int | None]):
        """
        Loads stock state from saved data.

        Only updates items that exist in both the config and saved data.
        """
        for item_name, stock in stock_data.items():
            if item_name in self._stock:
                self._stock[item_name] = stock
                logging.info(
                    "[ShopInventoryConfig] Loaded stock for '%s': %s",
                    item_name,
                    stock,
                )


class ShopNPC(NPC):
    """An NPC that operates a shop where players can purchase items"""

    registry: dict[str, "ShopNPC"] = {}

    def __init__(
        self,
        name: str,
        texts: list[str],
        inventory_config: ShopInventoryConfig,
        shop_name: str = "Shop",
    ):
        super().__init__(name, texts, _fn=None, chat=None, side_trigger=True)
        self.inventory_config = inventory_config
        self.shop_name = shop_name
        ShopNPC.registry[name] = self

    def action(self):
        """Interaction with the Shop NPC"""
        from pokete.classes.inv.shop_menu import ShopMenu

        logging.info("[ShopNPC][%s] Interaction started", self.name)
        self.ctx.map.full_show()
        self.exclamate()
        self.text(self.texts)
        shop_menu = ShopMenu(self.inventory_config, self.shop_name)
        shop_menu(self.ctx)

    @classmethod
    def save_all_stock(cls) -> dict[str, dict[str, int | None]]:
        """Saves stock data for all shop NPCs"""
        return {
            name: shop.inventory_config.to_dict()
            for name, shop in cls.registry.items()
        }

    @classmethod
    def load_all_stock(cls, stock_data: dict[str, dict[str, int | None]]):
        """Loads stock data for all shop NPCs"""
        for shop_name, shop_stock in stock_data.items():
            if shop_name in cls.registry:
                cls.registry[shop_name].inventory_config.load_stock(shop_stock)
                logging.info("[ShopNPC] Loaded stock for shop '%s'", shop_name)


class OpenShopAction(NPCAction):
    """NPC Action that opens a shop with a specific inventory"""

    def __init__(self, inventory_config: ShopInventoryConfig, shop_name: str = "Shop"):
        self.inventory_config = inventory_config
        self.shop_name = shop_name

    def act(self, npc: NPCInterface, ui: UIInterface):
        from pokete.classes.inv.shop_menu import ShopMenu

        shop_menu = ShopMenu(self.inventory_config, self.shop_name)
        shop_menu(npc.ctx)
