"""Tests for TradeManager"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from pokete.classes.trading.trade_manager import TradeManager
from pokete.classes.trading.trade_offer import TradeRequirements, TradeStatus


class TestTradeManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = Path(self.temp_dir) / "test_trades.json"
        self.manager = TradeManager(save_path=self.save_path)
        self.poke_data = {
            "name": "steini",
            "xp": 100,
            "hp": 25,
            "types": ["stone", "normal"],
        }
        self.requirements = TradeRequirements(
            required_types=["fire"],
            min_level=5,
        )

    def tearDown(self):
        self.manager.stop_expiry_timer()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_offer(self):
        """Test creating a trade offer"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        self.assertIsNotNone(offer)
        self.assertEqual(offer.owner_id, "player1")
        self.assertEqual(offer.status, TradeStatus.PENDING)

    def test_get_offer(self):
        """Test retrieving an offer"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        retrieved = self.manager.get_offer(offer.offer_id)
        self.assertEqual(retrieved.offer_id, offer.offer_id)

    def test_get_offer_not_found(self):
        """Test retrieving non-existent offer"""
        retrieved = self.manager.get_offer("nonexistent")
        self.assertIsNone(retrieved)

    def test_get_pending_offers(self):
        """Test getting pending offers"""
        self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        self.manager.create_offer(
            owner_id="player2",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        pending = self.manager.get_pending_offers()
        self.assertEqual(len(pending), 2)

    def test_get_offers_by_owner(self):
        """Test filtering offers by owner"""
        self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        self.manager.create_offer(
            owner_id="player2",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        player1_offers = self.manager.get_offers_by_owner("player1")
        self.assertEqual(len(player1_offers), 1)
        self.assertEqual(player1_offers[0].owner_id, "player1")

    def test_submit_counter_offer(self):
        """Test submitting a counter offer"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {
            "name": "wolfior",
            "xp": 100,
            "hp": 20,
            "types": ["fire", "normal"],
        }
        result = self.manager.submit_counter_offer(
            offer.offer_id,
            counter_poke,
            "player2",
        )
        self.assertTrue(result)
        self.assertEqual(offer.status, TradeStatus.MATCHED)
        self.assertEqual(offer.counter_offer_owner_id, "player2")

    def test_submit_counter_offer_wrong_type(self):
        """Test counter offer with wrong type"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {
            "name": "karpi",
            "xp": 100,
            "hp": 15,
            "types": ["water", "normal"],
        }
        result = self.manager.submit_counter_offer(
            offer.offer_id,
            counter_poke,
            "player2",
        )
        self.assertFalse(result)
        self.assertEqual(offer.status, TradeStatus.PENDING)

    def test_submit_counter_offer_low_level(self):
        """Test counter offer with too low level"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {
            "name": "wolfior",
            "xp": 3,  # level ~2
            "hp": 20,
            "types": ["fire", "normal"],
        }
        result = self.manager.submit_counter_offer(
            offer.offer_id,
            counter_poke,
            "player2",
        )
        self.assertFalse(result)

    def test_submit_counter_offer_nonexistent(self):
        """Test counter offer for non-existent offer"""
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        result = self.manager.submit_counter_offer(
            "nonexistent",
            counter_poke,
            "player2",
        )
        self.assertFalse(result)

    def test_accept_trade(self):
        """Test accepting a trade"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        self.manager.submit_counter_offer(offer.offer_id, counter_poke, "player2")

        result = self.manager.accept_trade(offer.offer_id, "player1")
        self.assertTrue(result)
        self.assertEqual(offer.status, TradeStatus.ACCEPTED)

    def test_accept_trade_wrong_owner(self):
        """Test that only offer owner can accept"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        self.manager.submit_counter_offer(offer.offer_id, counter_poke, "player2")

        result = self.manager.accept_trade(offer.offer_id, "player2")
        self.assertFalse(result)
        self.assertEqual(offer.status, TradeStatus.MATCHED)

    def test_accept_trade_not_matched(self):
        """Test accepting unmatched trade fails"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        result = self.manager.accept_trade(offer.offer_id, "player1")
        self.assertFalse(result)

    def test_reject_trade(self):
        """Test rejecting a trade"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        self.manager.submit_counter_offer(offer.offer_id, counter_poke, "player2")

        result = self.manager.reject_trade(offer.offer_id, "player1")
        self.assertTrue(result)
        self.assertEqual(offer.status, TradeStatus.REJECTED)
        self.assertIsNone(offer.counter_offer_poke_data)

    def test_reject_trade_wrong_owner(self):
        """Test that only offer owner can reject"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        self.manager.submit_counter_offer(offer.offer_id, counter_poke, "player2")

        result = self.manager.reject_trade(offer.offer_id, "player2")
        self.assertFalse(result)

    def test_cancel_offer(self):
        """Test cancelling an offer"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        result = self.manager.cancel_offer(offer.offer_id, "player1")
        self.assertTrue(result)
        self.assertEqual(offer.status, TradeStatus.CANCELLED)

    def test_cancel_offer_wrong_owner(self):
        """Test that only owner can cancel"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        result = self.manager.cancel_offer(offer.offer_id, "player2")
        self.assertFalse(result)

    def test_check_expired_offers(self):
        """Test expiry checking"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        offer.expires_at = datetime.now() - timedelta(minutes=1)

        self.manager.check_expired_offers()
        self.assertEqual(offer.status, TradeStatus.EXPIRED)

    def test_save_and_load(self):
        """Test saving and loading offers"""
        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )

        new_manager = TradeManager(save_path=self.save_path)
        new_manager.load()

        loaded_offer = new_manager.get_offer(offer.offer_id)
        self.assertIsNotNone(loaded_offer)
        self.assertEqual(loaded_offer.owner_id, "player1")

    def test_clear_completed_offers(self):
        """Test clearing completed offers"""
        offer1 = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        offer2 = self.manager.create_offer(
            owner_id="player2",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        offer1.status = TradeStatus.ACCEPTED

        self.manager.clear_completed_offers()

        self.assertIsNone(self.manager.get_offer(offer1.offer_id))
        self.assertIsNotNone(self.manager.get_offer(offer2.offer_id))

    def test_notification_callback(self):
        """Test notification callback is called"""
        callback = MagicMock()
        self.manager.set_notification_callback(callback)

        offer = self.manager.create_offer(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        counter_poke = {"name": "wolfior", "xp": 100, "types": ["fire"]}
        self.manager.submit_counter_offer(offer.offer_id, counter_poke, "player2")

        callback.assert_called_once()
        call_args = callback.call_args[0]
        self.assertEqual(call_args[0], "Trade Match!")


if __name__ == "__main__":
    unittest.main()
