"""ShopNPC class for NPCs that sell items to players"""

from typing import Dict, List, Optional

import scrap_engine as se

from pokete.base.change import change_ctx
from pokete.base.context import Context
from pokete.base.input.hotkeys import Action, ActionList
from pokete.base.input_loops import ask_ok
from pokete.base.ui.elements.labels import CloseLabel
from pokete.base.ui.views.choose_box import ChooseBoxView
from pokete.classes.asset_service.service import asset_service
from pokete.classes.inv.base_inv import BaseInv
from pokete.classes.inv.box import InvBox
from pokete.classes.items.invitem import InvItem

from .npcs import NPC
from .npc_trigger import NPCTrigger


class ShopInventory:
    """Represents a shop's inventory with items and quantities"""

    def __init__(self, items: Dict[str, Optional[int]]):
        """
        Initialize shop inventory.
        
        Args:
            items: Dict mapping item names to stock quantities.
                   None means unlimited stock.
        """
        self._items = items.copy()
        self._initial_stock = items.copy()

    def get_items(self) -> Dict[str, Optional[int]]:
        return self._items.copy()

    def has_stock(self, item_name: str) -> bool:
        if item_name not in self._items:
            return False
        stock = self._items[item_name]
        return stock is None or stock > 0

    def reduce_stock(self, item_name: str) -> bool:
        if not self.has_stock(item_name):
            return False
        if self._items[item_name] is not None:
            self._items[item_name] -= 1
        return True

    def get_stock(self, item_name: str) -> Optional[int]:
        return self._items.get(item_name)

    def restock(self):
        """Reset inventory to initial stock levels"""
        self._items = self._initial_stock.copy()


class ShopMenu(BaseInv):
    """Menu for purchasing items from a ShopNPC"""

    def __init__(self, shop_name: str, inventory: ShopInventory):
        super().__init__(shop_name, [CloseLabel()])
        self.inventory = inventory
        self.shop_items: list[InvItem] = []
        self._purchase_result: Optional[tuple[bool, str]] = None

    def _load_items(self):
        """Load available items from inventory"""
        all_items = asset_service.get_items()
        self.shop_items = []
        self.elems = []

        for item_name, stock in self.inventory.get_items().items():
            if item_name not in all_items:
                continue
            if not self.inventory.has_stock(item_name):
                continue

            item = all_items[item_name]
            if item.price is None:
                continue

            self.shop_items.append(item)
            stock_text = "∞" if stock is None else str(stock)
            self.elems.append(
                se.Text(
                    f"{item.pretty_name} : ${item.price} ({stock_text})",
                    state="float"
                )
            )

    def choose(self, ctx: Context, idx: int) -> Optional[tuple[bool, str]]:
        if idx >= len(self.shop_items):
            return None

        item = self.shop_items[idx]
        do_buy: bool = self.invbox(ctx, item)
        ctx = change_ctx(ctx, self)

        if not do_buy or item.price is None:
            return None

        money = ctx.figure.get_money()
        if money < item.price:
            ask_ok(ctx, f"Not enough money! Need ${item.price}, have ${money}.")
            return None

        if not self.inventory.has_stock(item.name):
            ask_ok(ctx, f"{item.pretty_name} is out of stock!")
            return None

        ctx.figure.add_money(-item.price)
        ctx.figure.give_item(item.name)
        self.inventory.reduce_stock(item.name)
        self.set_money(ctx.figure)

        self._refresh_items()
        return (True, item.name)

    def _refresh_items(self):
        """Refresh the item list after a purchase"""
        self.rem_elems()
        self._load_items()
        self.add_elems()
        if self.shop_items and self.index.index >= len(self.shop_items):
            self.set_index(len(self.shop_items) - 1)

    def handle_extra_actions(self, ctx: Context, action: ActionList) -> bool:
        if action.triggers(Action.CANCEL):
            return True
        return False

    def __call__(self, ctx: Context) -> List[str]:
        """
        Open the shop menu.
        
        Returns:
            List of purchased item names
        """
        self._load_items()
        if not self.shop_items:
            ask_ok(ctx, "This shop has nothing for sale!")
            return []

        self.resize(ctx.map.height - 3, 35)
        self.set_money(ctx.figure)
        self.add_elems()

        purchased = []
        with self.add(ctx.map, ctx.map.width - self.width, 0):
            while True:
                result = super().__call__(ctx)
                if result is None:
                    break
                if result[0]:
                    purchased.append(result[1])
                    if not self.shop_items:
                        break

        self.rem_elems()
        return purchased


class ShopNPC(NPC):
    """An NPC that operates a shop where players can buy items"""

    def __init__(
        self,
        name: str,
        shop_name: str,
        texts: List[str],
        inventory: ShopInventory,
        farewell_texts: Optional[List[str]] = None,
    ):
        """
        Create a ShopNPC.
        
        Args:
            name: Unique identifier for this NPC
            shop_name: Display name for the shop
            texts: Greeting texts shown when interacting
            inventory: ShopInventory with items for sale
            farewell_texts: Optional texts shown after shopping
        """
        super().__init__(name, texts, _fn=None, chat=None, side_trigger=True)
        self.shop_name = shop_name
        self.inventory = inventory
        self.farewell_texts = farewell_texts or ["Thanks for visiting!"]
        self._shop_menu = ShopMenu(shop_name, inventory)

    def action(self):
        """Interaction with the ShopNPC"""
        self.ctx.map.full_show()
        self.exclamate()
        self.text(self.texts)
        self._open_shop()

    def _open_shop(self):
        """Open the shop menu for purchasing"""
        purchased = self._shop_menu(self.ctx)
        if purchased:
            self.text(self.farewell_texts)
        else:
            self.text(["Come back anytime!"])

    def func(self):
        """Override NPC func - shop logic handled in action"""
        pass
