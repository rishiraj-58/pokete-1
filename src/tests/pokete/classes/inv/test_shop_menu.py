"""Unit tests for ShopMenu and PurchaseResult classes."""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the pokete source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete'))

# Import only what we need via direct file loading to avoid circular deps
import importlib.util

# Load shop_npc module
shop_npc_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete', 'classes', 'npcs', 'shop_npc.py')
spec = importlib.util.spec_from_file_location("shop_npc", shop_npc_path)
shop_npc_module = importlib.util.module_from_spec(spec)

class TestInvItem:
    def __init__(self, price=None, name="test"):
        self.price = price
        self.name = name

shop_npc_module.NPC = MagicMock
shop_npc_module.NPCAction = MagicMock
shop_npc_module.NPCInterface = MagicMock
shop_npc_module.UIInterface = MagicMock
shop_npc_module.InvItem = TestInvItem
shop_npc_module.logging = MagicMock()
exec(compile(open(shop_npc_path).read(), shop_npc_path, 'exec'), shop_npc_module.__dict__)
ShopInventoryConfig = shop_npc_module.ShopInventoryConfig

# Load shop_menu module
shop_menu_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete', 'classes', 'inv', 'shop_menu.py')
spec2 = importlib.util.spec_from_file_location("shop_menu", shop_menu_path)
shop_menu_module = importlib.util.module_from_spec(spec2)

# Mock dependencies for shop_menu
shop_menu_module.se = MagicMock()
shop_menu_module.change_ctx = MagicMock()
shop_menu_module.Context = MagicMock
shop_menu_module.ask_ok = MagicMock()
shop_menu_module.asset_service = MagicMock()
shop_menu_module.InvItem = TestInvItem
shop_menu_module.ShopInventoryConfig = ShopInventoryConfig
shop_menu_module.BaseInv = MagicMock
shop_menu_module.logging = MagicMock()
exec(compile(open(shop_menu_path).read(), shop_menu_path, 'exec'), shop_menu_module.__dict__)

PurchaseResult = shop_menu_module.PurchaseResult
ShopMenu = shop_menu_module.ShopMenu


class TestInvItem:
    """Mock item for testing"""
    def __init__(self, name: str, price, pretty_name: str = ""):
        self.name = name
        self.price = price
        self.pretty_name = pretty_name or name.capitalize()


class MockFigure:
    """Mock figure/player for testing"""
    def __init__(self, initial_money: int = 100):
        self._money = initial_money
        self._inventory = {}

    def get_money(self) -> int:
        return self._money

    def add_money(self, amount: int):
        self._money += amount

    def give_item(self, item_name: str):
        self._inventory[item_name] = self._inventory.get(item_name, 0) + 1


class MockContext:
    """Mock context for testing"""
    def __init__(self, initial_money: int = 100):
        self.figure = MockFigure(initial_money)


class TestPurchaseResult(unittest.TestCase):
    def test_success_status(self):
        result = PurchaseResult(PurchaseResult.SUCCESS, "Purchased!")

        self.assertEqual(result.status, PurchaseResult.SUCCESS)
        self.assertEqual(result.message, "Purchased!")
        self.assertTrue(result.is_success)

    def test_insufficient_funds_status(self):
        result = PurchaseResult(
            PurchaseResult.INSUFFICIENT_FUNDS,
            "Not enough money!",
        )

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)
        self.assertEqual(result.message, "Not enough money!")
        self.assertFalse(result.is_success)

    def test_item_not_for_sale_status(self):
        result = PurchaseResult(
            PurchaseResult.ITEM_NOT_FOR_SALE,
            "Item unavailable",
        )

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)
        self.assertFalse(result.is_success)

    def test_out_of_stock_status(self):
        result = PurchaseResult(
            PurchaseResult.OUT_OF_STOCK,
            "Item sold out!",
        )

        self.assertEqual(result.status, PurchaseResult.OUT_OF_STOCK)
        self.assertFalse(result.is_success)

    def test_cancelled_status(self):
        result = PurchaseResult(PurchaseResult.CANCELLED)

        self.assertEqual(result.status, PurchaseResult.CANCELLED)
        self.assertEqual(result.message, "")
        self.assertFalse(result.is_success)

    def test_empty_message_default(self):
        result = PurchaseResult(PurchaseResult.SUCCESS)

        self.assertEqual(result.message, "")


class TestShopMenuAttemptPurchase(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_attempt_purchase_success(self, mock_asset_service):
        config = ShopInventoryConfig(["poketeball"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("poketeball", 10, "Poketeball")
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertTrue(result.is_success)
        self.assertEqual(ctx.figure.get_money(), 90)
        self.assertEqual(ctx.figure._inventory.get("poketeball"), 1)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_attempt_purchase_insufficient_funds(self, mock_asset_service):
        config = ShopInventoryConfig(["expensive_item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("expensive_item", 100)
        ctx = MockContext(50)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)
        self.assertEqual(ctx.figure.get_money(), 50)
        self.assertNotIn("expensive_item", ctx.figure._inventory)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_attempt_purchase_exact_amount(self, mock_asset_service):
        config = ShopInventoryConfig(["item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 50, "Item")
        ctx = MockContext(50)

        result = menu._attempt_purchase(ctx, item)

        self.assertTrue(result.is_success)
        self.assertEqual(ctx.figure.get_money(), 0)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_attempt_purchase_item_with_zero_price(self, mock_asset_service):
        config = ShopInventoryConfig(["free_item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("free_item", 0)
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_attempt_purchase_item_with_none_price(self, mock_asset_service):
        config = ShopInventoryConfig(["no_price_item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("no_price_item", None)
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)


class TestShopMenuStock(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_limited_stock(self, mock_asset_service):
        config = ShopInventoryConfig({"poketeball": 3})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("poketeball", 10, "Poketeball")
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertTrue(result.is_success)
        self.assertEqual(config.get_stock("poketeball"), 2)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_until_out_of_stock(self, mock_asset_service):
        config = ShopInventoryConfig({"poketeball": 2})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("poketeball", 10, "Poketeball")
        ctx = MockContext(100)

        result1 = menu._attempt_purchase(ctx, item)
        self.assertTrue(result1.is_success)

        result2 = menu._attempt_purchase(ctx, item)
        self.assertTrue(result2.is_success)

        result3 = menu._attempt_purchase(ctx, item)
        self.assertEqual(result3.status, PurchaseResult.OUT_OF_STOCK)
        self.assertEqual(ctx.figure.get_money(), 80)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_unlimited_stock(self, mock_asset_service):
        config = ShopInventoryConfig(["poketeball"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("poketeball", 1, "Poketeball")
        ctx = MockContext(100)

        for _ in range(50):
            result = menu._attempt_purchase(ctx, item)
            self.assertTrue(result.is_success)

        self.assertEqual(ctx.figure.get_money(), 50)
        self.assertEqual(ctx.figure._inventory.get("poketeball"), 50)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_out_of_stock_from_start(self, mock_asset_service):
        config = ShopInventoryConfig({"poketeball": 0})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("poketeball", 10, "Poketeball")
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.OUT_OF_STOCK)
        self.assertEqual(ctx.figure.get_money(), 100)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_stock_checked_before_funds(self, mock_asset_service):
        config = ShopInventoryConfig({"poketeball": 0})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("poketeball", 10, "Poketeball")
        ctx = MockContext(5)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.OUT_OF_STOCK)


class TestShopMenuWithPriceMultiplier(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_discount_multiplier(self, mock_asset_service):
        config = ShopInventoryConfig(["item"], price_multiplier=0.5)
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 100, "Item")
        ctx = MockContext(60)

        result = menu._attempt_purchase(ctx, item)

        self.assertTrue(result.is_success)
        self.assertEqual(ctx.figure.get_money(), 10)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_premium_multiplier(self, mock_asset_service):
        config = ShopInventoryConfig(["item"], price_multiplier=1.5)
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 100, "Item")
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_premium_multiplier_sufficient_funds(self, mock_asset_service):
        config = ShopInventoryConfig(["item"], price_multiplier=1.5)
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 100, "Item")
        ctx = MockContext(200)

        result = menu._attempt_purchase(ctx, item)

        self.assertTrue(result.is_success)
        self.assertEqual(ctx.figure.get_money(), 50)


class TestShopMenuIntegration(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_multiple_purchases_update_balance(self, mock_asset_service):
        config = ShopInventoryConfig(["item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 10, "Item")
        ctx = MockContext(100)

        result1 = menu._attempt_purchase(ctx, item)
        self.assertTrue(result1.is_success)
        self.assertEqual(ctx.figure.get_money(), 90)

        result2 = menu._attempt_purchase(ctx, item)
        self.assertTrue(result2.is_success)
        self.assertEqual(ctx.figure.get_money(), 80)

        self.assertEqual(ctx.figure._inventory.get("item"), 2)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_until_insufficient_funds(self, mock_asset_service):
        config = ShopInventoryConfig(["item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item = TestInvItem("item", 30, "Item")
        ctx = MockContext(100)

        for i in range(3):
            result = menu._attempt_purchase(ctx, item)
            self.assertTrue(result.is_success)

        self.assertEqual(ctx.figure.get_money(), 10)

        result = menu._attempt_purchase(ctx, item)
        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)
        self.assertEqual(ctx.figure.get_money(), 10)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_mixed_stock_purchases(self, mock_asset_service):
        config = ShopInventoryConfig({
            "unlimited_item": None,
            "limited_item": 2
        })
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        unlimited = TestInvItem("unlimited_item", 5, "Unlimited")
        limited = TestInvItem("limited_item", 5, "Limited")
        ctx = MockContext(100)

        for _ in range(3):
            menu._attempt_purchase(ctx, unlimited)

        for _ in range(2):
            result = menu._attempt_purchase(ctx, limited)
            self.assertTrue(result.is_success)

        result = menu._attempt_purchase(ctx, limited)
        self.assertEqual(result.status, PurchaseResult.OUT_OF_STOCK)


class TestShopMenuEdgeCases(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_zero_balance(self, mock_asset_service):
        config = ShopInventoryConfig(["item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("item", 10)
        ctx = MockContext(0)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_negative_price_multiplier_result(self, mock_asset_service):
        config = ShopInventoryConfig(["item"], price_multiplier=-1.0)
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("item", 10)
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_with_very_large_price(self, mock_asset_service):
        config = ShopInventoryConfig(["expensive"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("expensive", 1000000)
        ctx = MockContext(100)

        result = menu._attempt_purchase(ctx, item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_purchase_different_items(self, mock_asset_service):
        config = ShopInventoryConfig(["poketeball", "healing_potion"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config
        menu.set_money = MagicMock()

        item1 = TestInvItem("poketeball", 2, "Poketeball")
        item2 = TestInvItem("healing_potion", 15, "Healing Potion")
        ctx = MockContext(100)

        menu._attempt_purchase(ctx, item1)
        menu._attempt_purchase(ctx, item2)

        self.assertEqual(ctx.figure.get_money(), 83)
        self.assertEqual(ctx.figure._inventory.get("poketeball"), 1)
        self.assertEqual(ctx.figure._inventory.get("healing_potion"), 1)


class TestShopMenuFormatItemDisplay(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_format_unlimited_stock(self, mock_asset_service):
        config = ShopInventoryConfig(["item"])
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("item", 10, "Item")

        display = menu._format_item_display(item)

        self.assertEqual(display, "Item : $10")

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_format_limited_stock(self, mock_asset_service):
        config = ShopInventoryConfig({"item": 5})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("item", 10, "Item")

        display = menu._format_item_display(item)

        self.assertEqual(display, "Item : $10 [x5]")

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch.object(ShopMenu, "__init__", lambda x, y, z: None)
    def test_format_sold_out(self, mock_asset_service):
        config = ShopInventoryConfig({"item": 0})
        menu = ShopMenu.__new__(ShopMenu)
        menu.inventory_config = config

        item = TestInvItem("item", 10, "Item")

        display = menu._format_item_display(item)

        self.assertEqual(display, "Item : $10 [SOLD OUT]")


if __name__ == "__main__":
    unittest.main()
