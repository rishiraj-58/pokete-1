"""Shop menu for purchasing items from ShopNPCs"""

import logging
from typing import Never, Optional

import scrap_engine as se

from pokete.base.change import change_ctx
from pokete.base.context import Context
from pokete.base.input_loops import ask_bool, ask_ok
from pokete.classes.asset_service.service import asset_service
from pokete.classes.items.invitem import InvItem
from pokete.classes.npcs.shop_npc import ShopInventoryConfig

from .base_inv import BaseInv
from .box import InvBox


class PurchaseResult:
    """Result of a purchase attempt"""

    SUCCESS = "success"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    ITEM_NOT_FOR_SALE = "item_not_for_sale"
    CANCELLED = "cancelled"

    def __init__(self, status: str, message: str = ""):
        self.status = status
        self.message = message

    @property
    def is_success(self) -> bool:
        return self.status == self.SUCCESS


class ShopMenu(BaseInv):
    """Menu for purchasing items from a shop"""

    def __init__(
        self,
        inventory_config: ShopInventoryConfig,
        shop_name: str = "Shop",
    ):
        super().__init__(shop_name)
        self.inventory_config = inventory_config
        self.shop_name = shop_name
        self.items: list[InvItem] = []
        self._load_items()

    def _load_items(self):
        """Loads items from the inventory configuration"""
        all_items = asset_service.get_items()
        self.items = []
        for item_name in self.inventory_config.items:
            if item_name in all_items:
                item = all_items[item_name]
                if item.price is not None:
                    self.items.append(item)
                else:
                    logging.warning(
                        "[ShopMenu] Item '%s' has no price, skipping",
                        item_name,
                    )
            else:
                logging.warning(
                    "[ShopMenu] Item '%s' not found in items registry",
                    item_name,
                )
        self._update_elems()

    def _update_elems(self):
        """Updates the display elements for items"""
        self.elems = [
            se.Text(
                f"{item.pretty_name} : ${self.inventory_config.get_item_price(item)}"
            )
            for item in self.items
        ]

    def choose(self, ctx: Context, idx: int) -> Optional[Never]:
        """Handles item selection"""
        if idx >= len(self.items):
            return None

        item = self.items[idx]
        do_buy: bool = self.invbox(ctx, item)
        ctx = change_ctx(ctx, self)

        if do_buy:
            result = self._attempt_purchase(ctx, item)
            if result.is_success:
                ask_ok(
                    ctx,
                    f"You purchased {item.pretty_name}!",
                )
            elif result.status == PurchaseResult.INSUFFICIENT_FUNDS:
                ask_ok(
                    ctx,
                    f"You don't have enough money!\nYou need ${self.inventory_config.get_item_price(item)} but have ${ctx.figure.get_money()}.",
                )

    def _attempt_purchase(self, ctx: Context, item: InvItem) -> PurchaseResult:
        """Attempts to purchase an item"""
        price = self.inventory_config.get_item_price(item)

        if price is None or price <= 0:
            logging.warning(
                "[ShopMenu] Item '%s' is not for sale (invalid price)",
                item.name,
            )
            return PurchaseResult(
                PurchaseResult.ITEM_NOT_FOR_SALE,
                f"{item.pretty_name} is not for sale.",
            )

        current_money = ctx.figure.get_money()
        if current_money < price:
            logging.info(
                "[ShopMenu] Purchase failed: insufficient funds. "
                "Needed: %d, Have: %d",
                price,
                current_money,
            )
            return PurchaseResult(
                PurchaseResult.INSUFFICIENT_FUNDS,
                f"Not enough money. Need ${price}, have ${current_money}.",
            )

        ctx.figure.add_money(-price)
        ctx.figure.give_item(item.name)
        self.set_money(ctx.figure)

        logging.info(
            "[ShopMenu] Purchase successful: %s for $%d. "
            "Remaining balance: $%d",
            item.name,
            price,
            ctx.figure.get_money(),
        )

        return PurchaseResult(
            PurchaseResult.SUCCESS,
            f"Purchased {item.pretty_name} for ${price}.",
        )

    def __call__(self, ctx: Context):
        """Opens the shop menu"""
        self.resize(ctx.map.height - 3, 35)
        self.set_money(ctx.figure)
        self.add_elems()
        with self.add(ctx.map, ctx.map.width - self.width, 0):
            super().__call__(ctx)
