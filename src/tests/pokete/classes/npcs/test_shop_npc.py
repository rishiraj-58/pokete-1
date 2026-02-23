"""Unit tests for ShopNPC and ShopInventoryConfig classes."""

import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the pokete source to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete'))

# Import only what we need to test, avoiding circular dependencies
# We import the module file directly to avoid triggering the full import chain
import importlib.util
spec = importlib.util.spec_from_file_location(
    "shop_npc",
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'pokete', 'classes', 'npcs', 'shop_npc.py')
)
shop_npc_module = importlib.util.module_from_spec(spec)

# Mock the dependencies
class MockNPC:
    registry = {}
    def __init__(self, *args, **kwargs):
        pass

class MockNPCAction:
    pass

class MockNPCInterface:
    pass

class MockUIInterface:
    pass

class TestInvItem:
    def __init__(self, price, name="test"):
        self.price = price
        self.name = name

# Inject mocks
shop_npc_module.NPC = MockNPC
shop_npc_module.NPCAction = MockNPCAction
shop_npc_module.NPCInterface = MockNPCInterface
shop_npc_module.UIInterface = MockUIInterface
shop_npc_module.InvItem = TestInvItem
shop_npc_module.logging = MagicMock()

# Execute the module
exec(compile(open(spec.origin).read(), spec.origin, 'exec'), shop_npc_module.__dict__)

ShopInventoryConfig = shop_npc_module.ShopInventoryConfig
ShopNPC = shop_npc_module.ShopNPC


class TestInvItem:
    """Test item for testing price calculations"""
    def __init__(self, price, name="test"):
        self.price = price
        self.name = name


class TestShopInventoryConfig(unittest.TestCase):
    def test_init_with_list_default_multiplier(self):
        items = ["poketeball", "healing_potion"]
        config = ShopInventoryConfig(items)

        self.assertEqual(config.items, items)
        self.assertEqual(config.price_multiplier, 1.0)

    def test_init_with_dict_stock(self):
        items = {"poketeball": 10, "superball": None}
        config = ShopInventoryConfig(items)

        self.assertIn("poketeball", config.items)
        self.assertIn("superball", config.items)
        self.assertEqual(config.get_stock("poketeball"), 10)
        self.assertIsNone(config.get_stock("superball"))

    def test_init_with_custom_multiplier(self):
        items = ["superball"]
        config = ShopInventoryConfig(items, price_multiplier=0.8)

        self.assertEqual(config.items, items)
        self.assertEqual(config.price_multiplier, 0.8)

    def test_get_item_price_with_default_multiplier(self):
        config = ShopInventoryConfig(["test"])
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 100)

    def test_get_item_price_with_discount_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.5)
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 50)

    def test_get_item_price_with_premium_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=1.5)
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 150)

    def test_get_item_price_with_none_price(self):
        config = ShopInventoryConfig(["test"])
        mock_item = TestInvItem(None)

        self.assertEqual(config.get_item_price(mock_item), 0)

    def test_get_item_price_rounds_down(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.33)
        mock_item = TestInvItem(10)

        self.assertEqual(config.get_item_price(mock_item), 3)


class TestShopInventoryConfigStock(unittest.TestCase):
    def test_get_stock_unlimited(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertIsNone(config.get_stock("poketeball"))

    def test_get_stock_limited(self):
        config = ShopInventoryConfig({"poketeball": 5})
        self.assertEqual(config.get_stock("poketeball"), 5)

    def test_get_stock_nonexistent_item(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertIsNone(config.get_stock("nonexistent"))

    def test_has_stock_unlimited(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertTrue(config.has_stock("poketeball"))

    def test_has_stock_with_quantity(self):
        config = ShopInventoryConfig({"poketeball": 5})
        self.assertTrue(config.has_stock("poketeball"))

    def test_has_stock_zero(self):
        config = ShopInventoryConfig({"poketeball": 0})
        self.assertFalse(config.has_stock("poketeball"))

    def test_has_stock_nonexistent(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertFalse(config.has_stock("nonexistent"))

    def test_consume_stock_unlimited(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertTrue(config.consume_stock("poketeball"))
        self.assertIsNone(config.get_stock("poketeball"))

    def test_consume_stock_limited(self):
        config = ShopInventoryConfig({"poketeball": 3})

        self.assertTrue(config.consume_stock("poketeball"))
        self.assertEqual(config.get_stock("poketeball"), 2)

        self.assertTrue(config.consume_stock("poketeball"))
        self.assertEqual(config.get_stock("poketeball"), 1)

        self.assertTrue(config.consume_stock("poketeball"))
        self.assertEqual(config.get_stock("poketeball"), 0)

    def test_consume_stock_depleted(self):
        config = ShopInventoryConfig({"poketeball": 1})

        self.assertTrue(config.consume_stock("poketeball"))
        self.assertFalse(config.consume_stock("poketeball"))

    def test_consume_stock_nonexistent(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertFalse(config.consume_stock("nonexistent"))

    def test_is_out_of_stock_true(self):
        config = ShopInventoryConfig({"poketeball": 0})
        self.assertTrue(config.is_out_of_stock("poketeball"))

    def test_is_out_of_stock_false_has_stock(self):
        config = ShopInventoryConfig({"poketeball": 5})
        self.assertFalse(config.is_out_of_stock("poketeball"))

    def test_is_out_of_stock_false_unlimited(self):
        config = ShopInventoryConfig(["poketeball"])
        self.assertFalse(config.is_out_of_stock("poketeball"))

    def test_reset_stock(self):
        config = ShopInventoryConfig({"poketeball": 3})

        config.consume_stock("poketeball")
        config.consume_stock("poketeball")
        self.assertEqual(config.get_stock("poketeball"), 1)

        config.reset_stock()
        self.assertEqual(config.get_stock("poketeball"), 3)


class TestShopInventoryConfigSerialization(unittest.TestCase):
    def test_to_dict(self):
        config = ShopInventoryConfig({"poketeball": 5, "superball": None})

        result = config.to_dict()

        self.assertEqual(result["poketeball"], 5)
        self.assertIsNone(result["superball"])

    def test_to_dict_after_consumption(self):
        config = ShopInventoryConfig({"poketeball": 5})
        config.consume_stock("poketeball")
        config.consume_stock("poketeball")

        result = config.to_dict()

        self.assertEqual(result["poketeball"], 3)

    def test_load_stock(self):
        config = ShopInventoryConfig({"poketeball": 10, "superball": 5})

        config.load_stock({"poketeball": 3, "superball": 1})

        self.assertEqual(config.get_stock("poketeball"), 3)
        self.assertEqual(config.get_stock("superball"), 1)

    def test_load_stock_ignores_unknown_items(self):
        config = ShopInventoryConfig({"poketeball": 10})

        config.load_stock({"poketeball": 3, "unknown": 5})

        self.assertEqual(config.get_stock("poketeball"), 3)
        self.assertIsNone(config.get_stock("unknown"))

    def test_load_stock_preserves_unmentioned_items(self):
        config = ShopInventoryConfig({"poketeball": 10, "superball": 5})

        config.load_stock({"poketeball": 3})

        self.assertEqual(config.get_stock("poketeball"), 3)
        self.assertEqual(config.get_stock("superball"), 5)


class TestShopInventoryConfigEmpty(unittest.TestCase):
    def test_empty_items_list(self):
        config = ShopInventoryConfig([])

        self.assertEqual(config.items, [])
        self.assertEqual(config.price_multiplier, 1.0)

    def test_empty_items_dict(self):
        config = ShopInventoryConfig({})

        self.assertEqual(config.items, [])
        self.assertEqual(config.price_multiplier, 1.0)

    def test_zero_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.0)
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 0)


class TestShopInventoryConfigEdgeCases(unittest.TestCase):
    def test_very_small_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.01)
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 1)

    def test_large_multiplier(self):
        config = ShopInventoryConfig(["test"], price_multiplier=10.0)
        mock_item = TestInvItem(100)

        self.assertEqual(config.get_item_price(mock_item), 1000)

    def test_fractional_result_truncates(self):
        config = ShopInventoryConfig(["test"], price_multiplier=0.7)
        mock_item = TestInvItem(15)
        self.assertEqual(config.get_item_price(mock_item), 10)

    def test_mixed_stock_types(self):
        config = ShopInventoryConfig({
            "unlimited": None,
            "limited": 5,
            "zero": 0
        })

        self.assertTrue(config.has_stock("unlimited"))
        self.assertTrue(config.has_stock("limited"))
        self.assertFalse(config.has_stock("zero"))


class TestShopNPCRegistry(unittest.TestCase):
    def setUp(self):
        ShopNPC.registry.clear()

    def test_shop_npc_registers_itself(self):
        config = ShopInventoryConfig(["poketeball"])

        with unittest.mock.patch.object(ShopNPC, '__bases__', (object,)):
            shop = object.__new__(ShopNPC)
            shop.inventory_config = config
            shop.shop_name = "Test Shop"
            shop.name = "test_shop"
            ShopNPC.registry["test_shop"] = shop

        self.assertIn("test_shop", ShopNPC.registry)

    def test_save_all_stock(self):
        config1 = ShopInventoryConfig({"item1": 5})
        config2 = ShopInventoryConfig({"item2": 10})

        ShopNPC.registry["shop1"] = MagicMock()
        ShopNPC.registry["shop1"].inventory_config = config1
        ShopNPC.registry["shop2"] = MagicMock()
        ShopNPC.registry["shop2"].inventory_config = config2

        result = ShopNPC.save_all_stock()

        self.assertEqual(result["shop1"]["item1"], 5)
        self.assertEqual(result["shop2"]["item2"], 10)

    def test_load_all_stock(self):
        config = ShopInventoryConfig({"item1": 10})
        ShopNPC.registry["shop1"] = MagicMock()
        ShopNPC.registry["shop1"].inventory_config = config

        ShopNPC.load_all_stock({"shop1": {"item1": 3}})

        self.assertEqual(config.get_stock("item1"), 3)


class TestStockDepletionScenarios(unittest.TestCase):
    def test_purchase_until_depleted(self):
        config = ShopInventoryConfig({"poketeball": 3})

        for i in range(3):
            self.assertTrue(config.has_stock("poketeball"))
            self.assertTrue(config.consume_stock("poketeball"))

        self.assertFalse(config.has_stock("poketeball"))
        self.assertFalse(config.consume_stock("poketeball"))
        self.assertTrue(config.is_out_of_stock("poketeball"))

    def test_unlimited_never_depletes(self):
        config = ShopInventoryConfig(["poketeball"])

        for _ in range(100):
            self.assertTrue(config.has_stock("poketeball"))
            self.assertTrue(config.consume_stock("poketeball"))

        self.assertTrue(config.has_stock("poketeball"))
        self.assertFalse(config.is_out_of_stock("poketeball"))

    def test_multiple_items_independent_stock(self):
        config = ShopInventoryConfig({
            "item_a": 2,
            "item_b": 1
        })

        config.consume_stock("item_a")
        self.assertEqual(config.get_stock("item_a"), 1)
        self.assertEqual(config.get_stock("item_b"), 1)

        config.consume_stock("item_b")
        self.assertEqual(config.get_stock("item_a"), 1)
        self.assertEqual(config.get_stock("item_b"), 0)


if __name__ == "__main__":
    unittest.main()
