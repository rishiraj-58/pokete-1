import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from pokete.classes.inv.shop_menu import PurchaseResult, ShopMenu
from pokete.classes.npcs.shop_npc import ShopInventoryConfig


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

    def test_cancelled_status(self):
        result = PurchaseResult(PurchaseResult.CANCELLED)

        self.assertEqual(result.status, PurchaseResult.CANCELLED)
        self.assertEqual(result.message, "")
        self.assertFalse(result.is_success)

    def test_empty_message_default(self):
        result = PurchaseResult(PurchaseResult.SUCCESS)

        self.assertEqual(result.message, "")


class TestShopMenuLoadItems(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_load_items_filters_out_items_without_price(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None

        mock_item_with_price = MagicMock()
        mock_item_with_price.price = 10
        mock_item_with_price.name = "poketeball"
        mock_item_with_price.pretty_name = "Poketeball"

        mock_item_without_price = MagicMock()
        mock_item_without_price.price = None
        mock_item_without_price.name = "hyperball"

        mock_asset_service.get_items.return_value = {
            "poketeball": mock_item_with_price,
            "hyperball": mock_item_without_price,
        }

        config = ShopInventoryConfig(["poketeball", "hyperball"])
        menu = ShopMenu(config)

        self.assertEqual(len(menu.items), 1)
        self.assertEqual(menu.items[0].name, "poketeball")

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_load_items_skips_nonexistent_items(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None

        mock_item = MagicMock()
        mock_item.price = 10
        mock_item.name = "poketeball"
        mock_item.pretty_name = "Poketeball"

        mock_asset_service.get_items.return_value = {
            "poketeball": mock_item,
        }

        config = ShopInventoryConfig(["poketeball", "nonexistent_item"])
        menu = ShopMenu(config)

        self.assertEqual(len(menu.items), 1)
        self.assertEqual(menu.items[0].name, "poketeball")


class TestShopMenuPurchase(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_attempt_purchase_success(self, mock_base_init, mock_asset_service):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 10
        mock_item.name = "poketeball"
        mock_item.pretty_name = "Poketeball"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 100

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertTrue(result.is_success)
        mock_ctx.figure.add_money.assert_called_once_with(-10)
        mock_ctx.figure.give_item.assert_called_once_with("poketeball")
        menu.set_money.assert_called_once_with(mock_ctx.figure)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_attempt_purchase_insufficient_funds(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 100
        mock_item.name = "expensive_item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 50

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)
        mock_ctx.figure.add_money.assert_not_called()
        mock_ctx.figure.give_item.assert_not_called()

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_attempt_purchase_exact_amount(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 50
        mock_item.name = "item"
        mock_item.pretty_name = "Item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 50

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertTrue(result.is_success)
        mock_ctx.figure.add_money.assert_called_once_with(-50)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_attempt_purchase_item_with_zero_price(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)

        mock_item = MagicMock()
        mock_item.price = 0
        mock_item.name = "free_item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 100

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_attempt_purchase_item_with_none_price(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)

        mock_item = MagicMock()
        mock_item.price = None
        mock_item.name = "no_price_item"

        mock_ctx = MagicMock()

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)


class TestShopMenuWithPriceMultiplier(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_purchase_with_discount_multiplier(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"], price_multiplier=0.5)
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 100
        mock_item.name = "item"
        mock_item.pretty_name = "Item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 60

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertTrue(result.is_success)
        mock_ctx.figure.add_money.assert_called_once_with(-50)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_purchase_with_premium_multiplier(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"], price_multiplier=1.5)
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 100
        mock_item.name = "item"
        mock_item.pretty_name = "Item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 100

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)


class TestShopMenuChoose(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.ask_ok")
    @patch("pokete.classes.inv.shop_menu.change_ctx")
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_choose_with_invalid_index(
        self,
        mock_base_init,
        mock_asset_service,
        mock_change_ctx,
        mock_ask_ok,
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig([])
        menu = ShopMenu(config)
        menu.invbox = MagicMock(return_value=True)

        mock_ctx = MagicMock()

        result = menu.choose(mock_ctx, 999)

        self.assertIsNone(result)


class TestShopMenuUpdateElems(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_update_elems_formats_correctly(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None

        mock_item = MagicMock()
        mock_item.price = 15
        mock_item.name = "poketeball"
        mock_item.pretty_name = "Poketeball"

        mock_asset_service.get_items.return_value = {
            "poketeball": mock_item,
        }

        config = ShopInventoryConfig(["poketeball"])
        menu = ShopMenu(config)

        self.assertEqual(len(menu.elems), 1)


class TestShopMenuIntegration(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_multiple_purchases_update_balance(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)
        menu.set_money = MagicMock()

        mock_item = MagicMock()
        mock_item.price = 10
        mock_item.name = "item"
        mock_item.pretty_name = "Item"

        mock_ctx = MagicMock()
        balance = [100]

        def get_money():
            return balance[0]

        def add_money(amount):
            balance[0] += amount

        mock_ctx.figure.get_money = get_money
        mock_ctx.figure.add_money = add_money

        result1 = menu._attempt_purchase(mock_ctx, mock_item)
        self.assertTrue(result1.is_success)
        self.assertEqual(balance[0], 90)

        result2 = menu._attempt_purchase(mock_ctx, mock_item)
        self.assertTrue(result2.is_success)
        self.assertEqual(balance[0], 80)


class TestShopMenuEdgeCases(unittest.TestCase):
    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_purchase_with_zero_balance(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"])
        menu = ShopMenu(config)

        mock_item = MagicMock()
        mock_item.price = 10
        mock_item.name = "item"

        mock_ctx = MagicMock()
        mock_ctx.figure.get_money.return_value = 0

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.INSUFFICIENT_FUNDS)

    @patch("pokete.classes.inv.shop_menu.asset_service")
    @patch("pokete.classes.inv.shop_menu.BaseInv.__init__")
    def test_purchase_with_negative_price_multiplier_result(
        self, mock_base_init, mock_asset_service
    ):
        mock_base_init.return_value = None
        mock_asset_service.get_items.return_value = {}

        config = ShopInventoryConfig(["test"], price_multiplier=-1.0)
        menu = ShopMenu(config)

        mock_item = MagicMock()
        mock_item.price = 10
        mock_item.name = "item"

        mock_ctx = MagicMock()

        result = menu._attempt_purchase(mock_ctx, mock_item)

        self.assertEqual(result.status, PurchaseResult.ITEM_NOT_FOR_SALE)


if __name__ == "__main__":
    unittest.main()
