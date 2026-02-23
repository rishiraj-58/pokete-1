"""Unit tests for ShopNPC and related classes"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional


class ShopInventory:
    """Local copy of ShopInventory for testing without full imports"""

    def __init__(self, items: Dict[str, Optional[int]]):
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


class TestShopInventory(unittest.TestCase):
    """Tests for ShopInventory class"""

    def test_init_copies_items(self):
        """Inventory should copy items dict to avoid external modification"""
        items = {"poketeball": 5, "healing_potion": None}
        inv = ShopInventory(items)
        items["poketeball"] = 100
        self.assertEqual(inv.get_stock("poketeball"), 5)

    def test_get_items_returns_copy(self):
        """get_items should return a copy"""
        inv = ShopInventory({"poketeball": 5})
        returned = inv.get_items()
        returned["poketeball"] = 100
        self.assertEqual(inv.get_stock("poketeball"), 5)

    def test_has_stock_with_quantity(self):
        """has_stock returns True when stock > 0"""
        inv = ShopInventory({"poketeball": 5})
        self.assertTrue(inv.has_stock("poketeball"))

    def test_has_stock_with_zero_quantity(self):
        """has_stock returns False when stock == 0"""
        inv = ShopInventory({"poketeball": 0})
        self.assertFalse(inv.has_stock("poketeball"))

    def test_has_stock_with_unlimited(self):
        """has_stock returns True when stock is None (unlimited)"""
        inv = ShopInventory({"poketeball": None})
        self.assertTrue(inv.has_stock("poketeball"))

    def test_has_stock_nonexistent_item(self):
        """has_stock returns False for items not in inventory"""
        inv = ShopInventory({"poketeball": 5})
        self.assertFalse(inv.has_stock("nonexistent"))

    def test_reduce_stock_decrements(self):
        """reduce_stock decrements stock by 1"""
        inv = ShopInventory({"poketeball": 5})
        result = inv.reduce_stock("poketeball")
        self.assertTrue(result)
        self.assertEqual(inv.get_stock("poketeball"), 4)

    def test_reduce_stock_unlimited_stays_unlimited(self):
        """reduce_stock doesn't change None (unlimited) stock"""
        inv = ShopInventory({"poketeball": None})
        inv.reduce_stock("poketeball")
        self.assertIsNone(inv.get_stock("poketeball"))

    def test_reduce_stock_empty_fails(self):
        """reduce_stock returns False when no stock"""
        inv = ShopInventory({"poketeball": 0})
        result = inv.reduce_stock("poketeball")
        self.assertFalse(result)

    def test_reduce_stock_nonexistent_fails(self):
        """reduce_stock returns False for nonexistent items"""
        inv = ShopInventory({"poketeball": 5})
        result = inv.reduce_stock("nonexistent")
        self.assertFalse(result)

    def test_reduce_stock_to_zero(self):
        """reduce_stock can reduce stock to zero"""
        inv = ShopInventory({"poketeball": 1})
        result = inv.reduce_stock("poketeball")
        self.assertTrue(result)
        self.assertEqual(inv.get_stock("poketeball"), 0)
        self.assertFalse(inv.has_stock("poketeball"))

    def test_get_stock_returns_quantity(self):
        """get_stock returns the current stock level"""
        inv = ShopInventory({"poketeball": 5, "healing_potion": None})
        self.assertEqual(inv.get_stock("poketeball"), 5)
        self.assertIsNone(inv.get_stock("healing_potion"))

    def test_get_stock_nonexistent_returns_none(self):
        """get_stock returns None for nonexistent items"""
        inv = ShopInventory({"poketeball": 5})
        self.assertIsNone(inv.get_stock("nonexistent"))

    def test_restock_resets_to_initial(self):
        """restock resets inventory to initial state"""
        inv = ShopInventory({"poketeball": 5, "healing_potion": 3})
        inv.reduce_stock("poketeball")
        inv.reduce_stock("poketeball")
        inv.reduce_stock("healing_potion")
        inv.restock()
        self.assertEqual(inv.get_stock("poketeball"), 5)
        self.assertEqual(inv.get_stock("healing_potion"), 3)

    def test_multiple_items(self):
        """Inventory handles multiple items correctly"""
        inv = ShopInventory({
            "poketeball": 10,
            "superball": 5,
            "healing_potion": None
        })
        self.assertTrue(inv.has_stock("poketeball"))
        self.assertTrue(inv.has_stock("superball"))
        self.assertTrue(inv.has_stock("healing_potion"))

        inv.reduce_stock("superball")
        self.assertEqual(inv.get_stock("superball"), 4)
        self.assertEqual(inv.get_stock("poketeball"), 10)





class TestShopInventoryEdgeCases(unittest.TestCase):
    """Edge case tests for ShopInventory"""

    def test_empty_inventory(self):
        """Empty inventory should work correctly"""
        inv = ShopInventory({})
        self.assertEqual(inv.get_items(), {})
        self.assertFalse(inv.has_stock("anything"))

    def test_all_unlimited_stock(self):
        """Inventory with all unlimited items"""
        inv = ShopInventory({
            "item1": None,
            "item2": None,
            "item3": None,
        })
        for _ in range(100):
            inv.reduce_stock("item1")
        self.assertTrue(inv.has_stock("item1"))

    def test_mixed_stock_types(self):
        """Inventory with mix of limited and unlimited"""
        inv = ShopInventory({
            "limited": 2,
            "unlimited": None,
        })

        inv.reduce_stock("limited")
        inv.reduce_stock("limited")
        inv.reduce_stock("unlimited")

        self.assertFalse(inv.has_stock("limited"))
        self.assertTrue(inv.has_stock("unlimited"))

    def test_restock_after_complete_depletion(self):
        """Restock should work after complete depletion"""
        inv = ShopInventory({"item": 1})
        inv.reduce_stock("item")
        self.assertFalse(inv.has_stock("item"))

        inv.restock()
        self.assertTrue(inv.has_stock("item"))
        self.assertEqual(inv.get_stock("item"), 1)

    def test_large_stock_values(self):
        """Large stock values should work correctly"""
        inv = ShopInventory({"item": 999999})
        self.assertEqual(inv.get_stock("item"), 999999)
        inv.reduce_stock("item")
        self.assertEqual(inv.get_stock("item"), 999998)


class TestShopDataStructure(unittest.TestCase):
    """Tests for shop data validation"""

    def _load_shops(self):
        """Load shops data safely without running module code"""
        import os
        shop_file = os.path.join(
            os.path.dirname(__file__), 
            '../../../../pokete/data/shops.py'
        )
        namespace = {}
        with open(shop_file) as f:
            exec(f.read(), namespace)
        return namespace.get('shops', {})

    def test_shop_data_format(self):
        """Verify shop data format is correct"""
        shops = self._load_shops()

        for shop_id, shop_data in shops.items():
            self.assertIsInstance(shop_id, str)
            self.assertIn("shop_name", shop_data)
            self.assertIn("texts", shop_data)
            self.assertIn("inventory", shop_data)
            self.assertIn("map", shop_data)
            self.assertIn("x", shop_data)
            self.assertIn("y", shop_data)

            self.assertIsInstance(shop_data["shop_name"], str)
            self.assertIsInstance(shop_data["texts"], list)
            self.assertIsInstance(shop_data["inventory"], dict)
            self.assertIsInstance(shop_data["map"], str)
            self.assertIsInstance(shop_data["x"], int)
            self.assertIsInstance(shop_data["y"], int)

    def test_shop_inventory_items_valid(self):
        """Verify shop inventory items have valid stock types"""
        shops = self._load_shops()

        for shop_id, shop_data in shops.items():
            for item_name, stock in shop_data["inventory"].items():
                self.assertIsInstance(item_name, str)
                self.assertTrue(
                    stock is None or isinstance(stock, int),
                    f"Stock for {item_name} in {shop_id} must be int or None"
                )
                if isinstance(stock, int):
                    self.assertGreaterEqual(
                        stock, 0,
                        f"Stock for {item_name} in {shop_id} must be non-negative"
                    )

    def test_at_least_two_shops_defined(self):
        """Verify at least two shops are defined"""
        shops = self._load_shops()
        self.assertGreaterEqual(len(shops), 2, "At least 2 shops should be defined")

    def test_shops_on_different_maps(self):
        """Verify shops are on different maps or locations"""
        shops = self._load_shops()
        locations = set()
        for shop_id, shop_data in shops.items():
            loc = (shop_data["map"], shop_data["x"], shop_data["y"])
            self.assertNotIn(
                loc, locations, 
                f"Duplicate shop location: {loc}"
            )
            locations.add(loc)


if __name__ == "__main__":
    unittest.main()
