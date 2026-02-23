import unittest
from unittest.mock import MagicMock, patch

from pokete.classes.npcs.shop_npc import ShopInventoryConfig, ShopNPC


class TestShopInventoryConfig(unittest.TestCase):
    def test_init_with_default_multiplier(self):
        items = ["poketeball", "healing_potion"]
        config = ShopInventoryConfig(items)

        self.assertEqual(config.items, items)
        self.assertEqual(config.price_multiplier, 1.0)

    def test_init_with_custom_multiplier(self):
        items = ["superball"]
        config = ShopInventoryConfig(items, price_multiplier=0.8)

        self.assertEqual(config.items, items)
        self.assertEqual(config.price_multiplier, 0.8)

    def test_get_item_price_with_default_multiplier(self):
        config = ShopInventoryConfig(["test"])

        mock_item = MagicMock()
        mock_item.price = 100

        self.assertEqual(config.get_item_price(mock_item), 100)

    def test_get_item_price_with_discount_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.5)

        mock_item = MagicMock()
        mock_item.price = 100

        self.assertEqual(config.get_item_price(mock_item), 50)

    def test_get_item_price_with_premium_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=1.5)

        mock_item = MagicMock()
        mock_item.price = 100

        self.assertEqual(config.get_item_price(mock_item), 150)

    def test_get_item_price_with_none_price(self):
        config = ShopInventoryConfig(["test"])

        mock_item = MagicMock()
        mock_item.price = None

        self.assertEqual(config.get_item_price(mock_item), 0)

    def test_get_item_price_rounds_down(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.33)

        mock_item = MagicMock()
        mock_item.price = 10

        self.assertEqual(config.get_item_price(mock_item), 3)


class TestShopNPC(unittest.TestCase):
    @patch("pokete.classes.npcs.shop_npc.NPC.__init__")
    def test_init_creates_shop_npc(self, mock_npc_init):
        mock_npc_init.return_value = None
        items = ["poketeball", "superball"]
        config = ShopInventoryConfig(items)

        shop_npc = ShopNPC(
            name="test_shop",
            texts=["Welcome!"],
            inventory_config=config,
            shop_name="Test Shop",
        )

        self.assertEqual(shop_npc.inventory_config, config)
        self.assertEqual(shop_npc.shop_name, "Test Shop")
        mock_npc_init.assert_called_once_with(
            "test_shop",
            ["Welcome!"],
            _fn=None,
            chat=None,
            side_trigger=True,
        )

    @patch("pokete.classes.npcs.shop_npc.NPC.__init__")
    def test_init_with_default_shop_name(self, mock_npc_init):
        mock_npc_init.return_value = None
        config = ShopInventoryConfig(["poketeball"])

        shop_npc = ShopNPC(
            name="test_shop",
            texts=["Welcome!"],
            inventory_config=config,
        )

        self.assertEqual(shop_npc.shop_name, "Shop")


class TestShopInventoryConfigEmpty(unittest.TestCase):
    def test_empty_items_list(self):
        config = ShopInventoryConfig([])

        self.assertEqual(config.items, [])
        self.assertEqual(config.price_multiplier, 1.0)

    def test_zero_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.0)

        mock_item = MagicMock()
        mock_item.price = 100

        self.assertEqual(config.get_item_price(mock_item), 0)


if __name__ == "__main__":
    unittest.main()
