"""Tests for NPC Trader"""

import unittest
from unittest.mock import MagicMock

from pokete.classes.trading.npc_trader import NPCTrader, NPCInventoryItem
from pokete.classes.trading.models import TradeOffer, TradeRequirements, TradeStatus


class TestNPCInventoryItem(unittest.TestCase):
    def test_create_inventory_item(self):
        item = NPCInventoryItem(
            identifier="steini",
            name="Steini",
            level=15,
            types=["stone", "normal"],
        )
        self.assertEqual(item.identifier, "steini")
        self.assertEqual(item.name, "Steini")
        self.assertEqual(item.level, 15)
        self.assertEqual(item.types, ["stone", "normal"])


class TestNPCTrader(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            NPCInventoryItem("steini", "Steini", 15, ["stone", "normal"]),
            NPCInventoryItem("wolfior", "Wolfior", 20, ["fire", "normal"]),
            NPCInventoryItem("karpi", "Karpi", 5, ["water", "normal"]),
        ]
        self.trader = NPCTrader("npc_trader_1", self.inventory)

    def test_find_matching_pokete_by_type(self):
        requirements = TradeRequirements(types=["fire"])
        match = self.trader.find_matching_pokete(requirements)
        self.assertIsNotNone(match)
        self.assertEqual(match.identifier, "wolfior")

    def test_find_matching_pokete_by_level(self):
        requirements = TradeRequirements(min_level=10, max_level=18)
        match = self.trader.find_matching_pokete(requirements)
        self.assertIsNotNone(match)
        self.assertEqual(match.identifier, "steini")

    def test_find_matching_pokete_no_match(self):
        requirements = TradeRequirements(types=["ice"])
        match = self.trader.find_matching_pokete(requirements)
        self.assertIsNone(match)

    def test_find_matching_pokete_specific(self):
        requirements = TradeRequirements(specific_pokete="karpi")
        match = self.trader.find_matching_pokete(requirements)
        self.assertIsNotNone(match)
        self.assertEqual(match.identifier, "karpi")

    def test_evaluate_offer_pending(self):
        offer = TradeOffer(
            offered_pokete_identifier="mowcow",
            offered_pokete_name="Mowcow",
            offered_pokete_level=10,
            requirements=TradeRequirements(types=["fire"]),
            owner_id="player1",
            status=TradeStatus.PENDING,
        )
        self.assertTrue(self.trader.evaluate_offer(offer))

    def test_evaluate_offer_not_pending(self):
        offer = TradeOffer(
            offered_pokete_identifier="mowcow",
            offered_pokete_name="Mowcow",
            offered_pokete_level=10,
            requirements=TradeRequirements(types=["fire"]),
            owner_id="player1",
            status=TradeStatus.MATCHED,
        )
        self.assertFalse(self.trader.evaluate_offer(offer))

    def test_evaluate_offer_no_matching_pokete(self):
        offer = TradeOffer(
            offered_pokete_identifier="mowcow",
            offered_pokete_name="Mowcow",
            offered_pokete_level=10,
            requirements=TradeRequirements(types=["ice"]),
            owner_id="player1",
            status=TradeStatus.PENDING,
        )
        self.assertFalse(self.trader.evaluate_offer(offer))

    def test_generate_counter_offer_success(self):
        offer = TradeOffer(
            offered_pokete_identifier="mowcow",
            offered_pokete_name="Mowcow",
            offered_pokete_level=10,
            requirements=TradeRequirements(types=["stone"]),
            owner_id="player1",
        )
        counter = self.trader.generate_counter_offer(offer)
        self.assertIsNotNone(counter)
        self.assertEqual(counter.identifier, "steini")

    def test_generate_counter_offer_no_match(self):
        offer = TradeOffer(
            offered_pokete_identifier="mowcow",
            offered_pokete_name="Mowcow",
            offered_pokete_level=10,
            requirements=TradeRequirements(types=["ice"]),
            owner_id="player1",
        )
        counter = self.trader.generate_counter_offer(offer)
        self.assertIsNone(counter)

    def test_remove_from_inventory_success(self):
        self.assertEqual(len(self.trader.inventory), 3)
        result = self.trader.remove_from_inventory("steini")
        self.assertTrue(result)
        self.assertEqual(len(self.trader.inventory), 2)
        self.assertIsNone(
            next((p for p in self.trader.inventory if p.identifier == "steini"), None)
        )

    def test_remove_from_inventory_not_found(self):
        result = self.trader.remove_from_inventory("unknown")
        self.assertFalse(result)
        self.assertEqual(len(self.trader.inventory), 3)


class TestNPCTraderWithEmptyInventory(unittest.TestCase):
    def test_empty_inventory(self):
        trader = NPCTrader("empty_trader", [])
        requirements = TradeRequirements()
        match = trader.find_matching_pokete(requirements)
        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
