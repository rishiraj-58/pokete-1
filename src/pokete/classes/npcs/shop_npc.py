"""Shop NPC implementation for purchasable items"""

import logging
from typing import Optional

import scrap_engine as se

from pokete.base.context import Context
from pokete.base.input_loops import ask_ok
from pokete.classes.asset_service.service import asset_service
from pokete.classes.items.invitem import InvItem

from .npcs import NPC
from .npc_action import NPCAction, NPCInterface, UIInterface
from .ui import UI


class ShopInventoryConfig:
    """Configuration for a shop's inventory"""

    def __init__(
        self,
        items: list[str],
        price_multiplier: float = 1.0,
    ):
        self.items = items
        self.price_multiplier = price_multiplier

    def get_item_price(self, item: InvItem) -> int:
        """Gets the adjusted price for an item"""
        if item.price is None:
            return 0
        return int(item.price * self.price_multiplier)


class ShopNPC(NPC):
    """An NPC that operates a shop where players can purchase items"""

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

    def action(self):
        """Interaction with the Shop NPC"""
        logging.info("[ShopNPC][%s] Interaction started", self.name)
        self.ctx.map.full_show()
        self.exclamate()
        self.text(self.texts)
        self._open_shop()

    def _open_shop(self):
        """Opens the shop menu for the player"""
        from pokete.classes.inv.shop_menu import ShopMenu

        shop_menu = ShopMenu(
            self.inventory_config,
            self.shop_name,
        )
        shop_menu(self.ctx)


class OpenShopAction(NPCAction):
    """NPC Action that opens a shop with a specific inventory"""

    def __init__(self, inventory_config: ShopInventoryConfig, shop_name: str = "Shop"):
        self.inventory_config = inventory_config
        self.shop_name = shop_name

    def act(self, npc: NPCInterface, ui: UIInterface):
        from pokete.classes.inv.shop_menu import ShopMenu

        shop_menu = ShopMenu(
            self.inventory_config,
            self.shop_name,
        )
        shop_menu(npc.ctx)
