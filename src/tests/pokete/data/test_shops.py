import unittest

from pokete.data.shops import shops


class TestShopsData(unittest.TestCase):
    def test_shops_dict_exists(self):
        self.assertIsInstance(shops, dict)

    def test_shops_has_at_least_two_entries(self):
        self.assertGreaterEqual(len(shops), 2)

    def test_general_store_clerk_exists(self):
        self.assertIn("general_store_clerk", shops)

    def test_premium_shop_owner_exists(self):
        self.assertIn("premium_shop_owner", shops)

    def test_shop_has_required_fields(self):
        required_fields = [
            "texts",
            "map",
            "x",
            "y",
            "shop_name",
            "items",
            "price_multiplier",
        ]
        for shop_name, shop_data in shops.items():
            for field in required_fields:
                self.assertIn(
                    field,
                    shop_data,
                    f"Shop '{shop_name}' missing required field '{field}'",
                )

    def test_shop_texts_is_list(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["texts"],
                list,
                f"Shop '{shop_name}' texts should be a list",
            )
            self.assertGreater(
                len(shop_data["texts"]),
                0,
                f"Shop '{shop_name}' should have at least one text",
            )

    def test_shop_items_is_list(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["items"],
                list,
                f"Shop '{shop_name}' items should be a list",
            )
            self.assertGreater(
                len(shop_data["items"]),
                0,
                f"Shop '{shop_name}' should have at least one item",
            )

    def test_shop_coordinates_are_integers(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["x"],
                int,
                f"Shop '{shop_name}' x coordinate should be integer",
            )
            self.assertIsInstance(
                shop_data["y"],
                int,
                f"Shop '{shop_name}' y coordinate should be integer",
            )

    def test_shop_coordinates_are_positive(self):
        for shop_name, shop_data in shops.items():
            self.assertGreaterEqual(
                shop_data["x"],
                0,
                f"Shop '{shop_name}' x coordinate should be non-negative",
            )
            self.assertGreaterEqual(
                shop_data["y"],
                0,
                f"Shop '{shop_name}' y coordinate should be non-negative",
            )

    def test_shop_price_multiplier_is_numeric(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["price_multiplier"],
                (int, float),
                f"Shop '{shop_name}' price_multiplier should be numeric",
            )

    def test_shop_price_multiplier_is_positive(self):
        for shop_name, shop_data in shops.items():
            self.assertGreater(
                shop_data["price_multiplier"],
                0,
                f"Shop '{shop_name}' price_multiplier should be positive",
            )

    def test_shops_on_different_maps(self):
        maps = [shop_data["map"] for shop_data in shops.values()]
        self.assertEqual(
            len(maps),
            len(set(maps)),
            "Each shop should be on a different map",
        )

    def test_general_store_has_basic_items(self):
        general_store = shops["general_store_clerk"]
        basic_items = ["poketeball", "healing_potion"]
        for item in basic_items:
            self.assertIn(
                item,
                general_store["items"],
                f"General store should have {item}",
            )

    def test_premium_shop_has_discount(self):
        premium_shop = shops["premium_shop_owner"]
        self.assertLess(
            premium_shop["price_multiplier"],
            1.0,
            "Premium shop should have a discount (multiplier < 1.0)",
        )


class TestShopsMapReferences(unittest.TestCase):
    def test_shop_maps_are_valid_strings(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["map"],
                str,
                f"Shop '{shop_name}' map should be a string",
            )
            self.assertTrue(
                shop_data["map"].startswith("playmap_"),
                f"Shop '{shop_name}' map should start with 'playmap_'",
            )

    def test_shop_names_are_descriptive(self):
        for shop_name, shop_data in shops.items():
            self.assertIsInstance(
                shop_data["shop_name"],
                str,
                f"Shop '{shop_name}' shop_name should be a string",
            )
            self.assertGreater(
                len(shop_data["shop_name"]),
                0,
                f"Shop '{shop_name}' should have a non-empty shop_name",
            )


if __name__ == "__main__":
    unittest.main()
