"""Tests for Trade Manager"""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pokete.classes.trading.trade_manager import TradeManager
from pokete.classes.trading.models import TradeOffer, TradeRequirements, TradeStatus
from pokete.classes.trading.npc_trader import NPCTrader, NPCInventoryItem


class TestTradeManagerCreateOffer(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()

    def test_create_offer(self):
        requirements = TradeRequirements(min_level=10)
        offer = self.manager.create_offer(
            pokete_identifier="steini",
            pokete_name="Steini",
            pokete_level=15,
            owner_id="player1",
            requirements=requirements,
        )
        self.assertIsNotNone(offer)
        self.assertEqual(offer.offered_pokete_identifier, "steini")
        self.assertEqual(offer.status, TradeStatus.PENDING)
        self.assertIn(offer.id, self.manager.offers)

    def test_create_offer_with_custom_expiry(self):
        requirements = TradeRequirements()
        offer = self.manager.create_offer(
            pokete_identifier="steini",
            pokete_name="Steini",
            pokete_level=15,
            owner_id="player1",
            requirements=requirements,
            expiry_seconds=7200,
        )
        self.assertGreater(offer.expires_at, time.time() + 7000)


class TestTradeManagerGetOffers(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()
        self.offer1 = self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements(types=["ice"])
        )
        self.offer2 = self.manager.create_offer(
            "wolfior", "Wolfior", 20, "player2", TradeRequirements(types=["ice"])
        )

    def test_get_offer(self):
        offer = self.manager.get_offer(self.offer1.id)
        self.assertEqual(offer, self.offer1)

    def test_get_offer_not_found(self):
        offer = self.manager.get_offer("nonexistent")
        self.assertIsNone(offer)

    def test_get_pending_offers_all(self):
        offers = self.manager.get_pending_offers()
        self.assertEqual(len(offers), 2)

    def test_get_pending_offers_by_owner(self):
        offers = self.manager.get_pending_offers(owner_id="player1")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].owner_id, "player1")

    def test_get_matched_offers(self):
        self.offer1.status = TradeStatus.MATCHED
        offers = self.manager.get_matched_offers()
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].id, self.offer1.id)


class TestTradeManagerCancelOffer(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()
        self.offer = self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )

    def test_cancel_offer_success(self):
        result = self.manager.cancel_offer(self.offer.id, "player1")
        self.assertTrue(result)
        self.assertEqual(self.offer.status, TradeStatus.CANCELLED)

    def test_cancel_offer_wrong_owner(self):
        result = self.manager.cancel_offer(self.offer.id, "player2")
        self.assertFalse(result)
        self.assertEqual(self.offer.status, TradeStatus.PENDING)

    def test_cancel_offer_not_found(self):
        result = self.manager.cancel_offer("nonexistent", "player1")
        self.assertFalse(result)

    def test_cancel_offer_already_completed(self):
        self.offer.status = TradeStatus.COMPLETED
        result = self.manager.cancel_offer(self.offer.id, "player1")
        self.assertFalse(result)


class TestTradeManagerNPCCounterOffers(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()
        inventory = [
            NPCInventoryItem("wolfior", "Wolfior", 20, ["fire", "normal"]),
            NPCInventoryItem("karpi", "Karpi", 5, ["water", "normal"]),
        ]
        self.npc_trader = NPCTrader("npc1", inventory)
        self.manager.register_npc_trader(self.npc_trader)

    def test_process_npc_counter_offers_match(self):
        offer = self.manager.create_offer(
            "steini",
            "Steini",
            15,
            "player1",
            TradeRequirements(types=["fire"]),
        )
        matched = self.manager.process_npc_counter_offers()
        self.assertEqual(len(matched), 1)
        self.assertEqual(offer.status, TradeStatus.MATCHED)
        self.assertEqual(offer.counter_offer_id, "npc1")
        self.assertEqual(offer.counter_pokete_identifier, "wolfior")

    def test_process_npc_counter_offers_no_match(self):
        offer = self.manager.create_offer(
            "steini",
            "Steini",
            15,
            "player1",
            TradeRequirements(types=["ice"]),
        )
        matched = self.manager.process_npc_counter_offers()
        self.assertEqual(len(matched), 0)
        self.assertEqual(offer.status, TradeStatus.PENDING)

    def test_process_npc_counter_offers_with_notification(self):
        callback = MagicMock()
        self.manager.set_notification_callback(callback)
        
        self.manager.create_offer(
            "steini",
            "Steini",
            15,
            "player1",
            TradeRequirements(types=["water"]),
        )
        self.manager.process_npc_counter_offers()
        
        callback.assert_called_once()
        args = callback.call_args[0]
        self.assertEqual(args[0], "Trade Match!")


class TestTradeManagerAcceptReject(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()
        inventory = [NPCInventoryItem("wolfior", "Wolfior", 20, ["fire"])]
        self.npc_trader = NPCTrader("npc1", inventory)
        self.manager.register_npc_trader(self.npc_trader)
        
        self.offer = self.manager.create_offer(
            "steini",
            "Steini",
            15,
            "player1",
            TradeRequirements(types=["fire"]),
        )
        self.manager.process_npc_counter_offers()

    def test_accept_offer_success(self):
        result = self.manager.accept_offer(self.offer.id, "player1")
        self.assertTrue(result)
        self.assertEqual(self.offer.status, TradeStatus.ACCEPTED)
        self.assertEqual(len(self.npc_trader.inventory), 0)

    def test_accept_offer_wrong_owner(self):
        result = self.manager.accept_offer(self.offer.id, "player2")
        self.assertFalse(result)
        self.assertEqual(self.offer.status, TradeStatus.MATCHED)

    def test_accept_offer_not_matched(self):
        self.offer.status = TradeStatus.PENDING
        result = self.manager.accept_offer(self.offer.id, "player1")
        self.assertFalse(result)

    def test_reject_offer_success(self):
        result = self.manager.reject_offer(self.offer.id, "player1")
        self.assertTrue(result)
        self.assertEqual(self.offer.status, TradeStatus.REJECTED)

    def test_reject_offer_wrong_owner(self):
        result = self.manager.reject_offer(self.offer.id, "player2")
        self.assertFalse(result)
        self.assertEqual(self.offer.status, TradeStatus.MATCHED)


class TestTradeManagerCompleteTrade(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()
        self.offer = self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        self.offer.status = TradeStatus.ACCEPTED

    def test_complete_trade_success(self):
        result = self.manager.complete_trade(self.offer.id)
        self.assertTrue(result)
        self.assertEqual(self.offer.status, TradeStatus.COMPLETED)

    def test_complete_trade_not_accepted(self):
        self.offer.status = TradeStatus.PENDING
        result = self.manager.complete_trade(self.offer.id)
        self.assertFalse(result)

    def test_complete_trade_not_found(self):
        result = self.manager.complete_trade("nonexistent")
        self.assertFalse(result)


class TestTradeManagerExpiry(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()

    def test_check_expired_offers(self):
        offer = self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        offer.expires_at = time.time() - 100
        
        expired = self.manager.check_expired_offers()
        self.assertEqual(len(expired), 1)
        self.assertEqual(offer.status, TradeStatus.EXPIRED)

    def test_check_expired_offers_with_notification(self):
        callback = MagicMock()
        self.manager.set_notification_callback(callback)
        
        offer = self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        offer.expires_at = time.time() - 100
        
        self.manager.check_expired_offers()
        callback.assert_called_once()

    def test_check_expired_offers_none_expired(self):
        self.manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        expired = self.manager.check_expired_offers()
        self.assertEqual(len(expired), 0)


class TestTradeManagerPersistence(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            save_path = Path(f.name)
        
        try:
            manager1 = TradeManager(save_path=save_path)
            offer = manager1.create_offer(
                "steini", "Steini", 15, "player1", TradeRequirements(min_level=5)
            )
            
            manager2 = TradeManager(save_path=save_path)
            manager2.load()
            
            loaded_offer = manager2.get_offer(offer.id)
            self.assertIsNotNone(loaded_offer)
            self.assertEqual(loaded_offer.offered_pokete_identifier, "steini")
            self.assertEqual(loaded_offer.requirements.min_level, 5)
        finally:
            save_path.unlink(missing_ok=True)

    def test_to_dict(self):
        manager = TradeManager()
        manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        data = manager.to_dict()
        self.assertIn("offers", data)
        self.assertEqual(len(data["offers"]), 1)

    def test_from_dict(self):
        manager = TradeManager()
        offer = manager.create_offer(
            "steini", "Steini", 15, "player1", TradeRequirements()
        )
        data = manager.to_dict()
        
        manager2 = TradeManager()
        manager2.from_dict(data)
        
        loaded = manager2.get_offer(offer.id)
        self.assertIsNotNone(loaded)


class TestTradeManagerTimer(unittest.TestCase):
    def test_start_stop_timer(self):
        manager = TradeManager()
        manager.start_expiry_timer()
        self.assertTrue(manager._running)
        
        manager.stop_expiry_timer()
        self.assertFalse(manager._running)

    def test_start_timer_twice(self):
        manager = TradeManager()
        manager.start_expiry_timer()
        manager.start_expiry_timer()
        self.assertTrue(manager._running)
        manager.stop_expiry_timer()


if __name__ == "__main__":
    unittest.main()
