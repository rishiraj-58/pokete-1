"""Tests for NPCTrader"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pokete.classes.trading.npc_trader import NPCTrader, NPCTraderManager
from pokete.classes.trading.trade_manager import TradeManager
from pokete.classes.trading.trade_offer import TradeRequirements, TradeStatus


class TestNPCTrader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = Path(self.temp_dir) / "test_trades.json"
        self.manager = TradeManager(save_path=self.save_path)

        self.npc_inventory = [
            {"name": "wolfior", "xp": 100, "types": ["fire", "normal"]},
            {"name": "karpi", "xp": 50, "types": ["water", "normal"]},
            {"name": "steini", "xp": 80, "types": ["stone", "normal"]},
        ]
        self.trader = NPCTrader("npc_1", self.manager, self.npc_inventory.copy())

    def tearDown(self):
        self.trader.stop_periodic_checks()
        self.manager.stop_expiry_timer()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_matching_poke_fire(self):
        """Test finding a matching fire pokete"""
        requirements = TradeRequirements(required_types=["fire"])
        offer = self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )
        match = self.trader.find_matching_poke(offer)
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "wolfior")

    def test_find_matching_poke_water(self):
        """Test finding a matching water pokete"""
        requirements = TradeRequirements(required_types=["water"])
        offer = self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )
        match = self.trader.find_matching_poke(offer)
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "karpi")

    def test_find_matching_poke_no_match(self):
        """Test when no match exists"""
        requirements = TradeRequirements(required_types=["electro"])
        offer = self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )
        match = self.trader.find_matching_poke(offer)
        self.assertIsNone(match)

    def test_find_matching_poke_level_requirement(self):
        """Test level requirement matching"""
        requirements = TradeRequirements(min_level=10)
        offer = self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )
        match = self.trader.find_matching_poke(offer)
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "wolfior")  # xp=100 -> level 10

    def test_check_and_make_offers(self):
        """Test making counter offers"""
        requirements = TradeRequirements(required_types=["fire"])
        offer = self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )

        self.trader.check_and_make_offers()

        self.assertEqual(offer.status, TradeStatus.MATCHED)
        self.assertEqual(offer.counter_offer_owner_id, "npc_1")

    def test_check_and_make_offers_removes_from_inventory(self):
        """Test that matched pokete is removed from inventory"""
        requirements = TradeRequirements(required_types=["fire"])
        self.manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )

        initial_count = len(self.trader.inventory)
        self.trader.check_and_make_offers()

        self.assertEqual(len(self.trader.inventory), initial_count - 1)

    def test_check_and_make_offers_skips_own_offers(self):
        """Test that NPC doesn't respond to its own offers"""
        requirements = TradeRequirements(required_types=["fire"])
        offer = self.manager.create_offer(
            "npc_1",  # Same as NPC id
            {"name": "test", "xp": 100},
            requirements,
        )

        self.trader.check_and_make_offers()

        self.assertEqual(offer.status, TradeStatus.PENDING)

    def test_update_inventory(self):
        """Test updating NPC inventory"""
        new_inventory = [
            {"name": "lindemon", "xp": 200, "types": ["fire", "flying"]},
        ]
        self.trader.update_inventory(new_inventory)
        self.assertEqual(self.trader.inventory, new_inventory)


class TestNPCTraderManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = Path(self.temp_dir) / "test_trades.json"
        self.trade_manager = TradeManager(save_path=self.save_path)
        self.trader_manager = NPCTraderManager(self.trade_manager)

    def tearDown(self):
        self.trader_manager.stop_all()
        self.trade_manager.stop_expiry_timer()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_trader(self):
        """Test registering a new trader"""
        inventory = [{"name": "wolfior", "xp": 100, "types": ["fire"]}]
        trader = self.trader_manager.register_trader("npc_1", inventory)

        self.assertIsNotNone(trader)
        self.assertEqual(trader.npc_id, "npc_1")

    def test_get_trader(self):
        """Test getting a registered trader"""
        inventory = [{"name": "wolfior", "xp": 100, "types": ["fire"]}]
        self.trader_manager.register_trader("npc_1", inventory)

        trader = self.trader_manager.get_trader("npc_1")
        self.assertIsNotNone(trader)
        self.assertEqual(trader.npc_id, "npc_1")

    def test_get_trader_not_found(self):
        """Test getting non-existent trader"""
        trader = self.trader_manager.get_trader("nonexistent")
        self.assertIsNone(trader)

    def test_trigger_check_all(self):
        """Test triggering checks on all traders"""
        inventory1 = [{"name": "wolfior", "xp": 100, "types": ["fire"]}]
        inventory2 = [{"name": "karpi", "xp": 50, "types": ["water"]}]

        self.trader_manager.register_trader("npc_1", inventory1)
        self.trader_manager.register_trader("npc_2", inventory2)

        requirements = TradeRequirements(required_types=["fire"])
        offer = self.trade_manager.create_offer(
            "player1",
            {"name": "test", "xp": 100},
            requirements,
        )

        self.trader_manager.trigger_check_all()

        self.assertEqual(offer.status, TradeStatus.MATCHED)


if __name__ == "__main__":
    unittest.main()
