"""Tests for TradeOffer"""

import unittest
from datetime import datetime, timedelta

from pokete.classes.trading.trade_offer import (
    TradeOffer,
    TradeRequirements,
    TradeStatus,
)


class TestTradeRequirements(unittest.TestCase):

    def test_matches_no_requirements(self):
        """Test that empty requirements match anything"""
        reqs = TradeRequirements()
        self.assertTrue(reqs.matches(["fire"], 10))
        self.assertTrue(reqs.matches(["water", "normal"], 1))

    def test_matches_required_type(self):
        """Test type matching"""
        reqs = TradeRequirements(required_types=["fire"])
        self.assertTrue(reqs.matches(["fire"], 10))
        self.assertTrue(reqs.matches(["fire", "normal"], 10))
        self.assertFalse(reqs.matches(["water"], 10))

    def test_matches_multiple_required_types(self):
        """Test with multiple accepted types"""
        reqs = TradeRequirements(required_types=["fire", "water"])
        self.assertTrue(reqs.matches(["fire"], 10))
        self.assertTrue(reqs.matches(["water"], 10))
        self.assertFalse(reqs.matches(["ground"], 10))

    def test_matches_min_level(self):
        """Test minimum level requirement"""
        reqs = TradeRequirements(min_level=10)
        self.assertTrue(reqs.matches(["fire"], 10))
        self.assertTrue(reqs.matches(["fire"], 15))
        self.assertFalse(reqs.matches(["fire"], 9))

    def test_matches_max_level(self):
        """Test maximum level requirement"""
        reqs = TradeRequirements(max_level=20)
        self.assertTrue(reqs.matches(["fire"], 20))
        self.assertTrue(reqs.matches(["fire"], 15))
        self.assertFalse(reqs.matches(["fire"], 21))

    def test_matches_level_range(self):
        """Test level range requirement"""
        reqs = TradeRequirements(min_level=10, max_level=20)
        self.assertTrue(reqs.matches(["fire"], 10))
        self.assertTrue(reqs.matches(["fire"], 15))
        self.assertTrue(reqs.matches(["fire"], 20))
        self.assertFalse(reqs.matches(["fire"], 9))
        self.assertFalse(reqs.matches(["fire"], 21))

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization"""
        reqs = TradeRequirements(
            required_types=["fire", "water"],
            min_level=5,
            max_level=25,
        )
        data = reqs.to_dict()
        restored = TradeRequirements.from_dict(data)
        self.assertEqual(restored.required_types, ["fire", "water"])
        self.assertEqual(restored.min_level, 5)
        self.assertEqual(restored.max_level, 25)


class TestTradeOffer(unittest.TestCase):

    def setUp(self):
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

    def test_create_offer(self):
        """Test creating a new offer"""
        offer = TradeOffer.create(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        self.assertIsNotNone(offer.offer_id)
        self.assertEqual(offer.owner_id, "player1")
        self.assertEqual(offer.status, TradeStatus.PENDING)
        self.assertIsNotNone(offer.expires_at)

    def test_is_expired(self):
        """Test expiry checking"""
        offer = TradeOffer.create(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
            expiry_minutes=1,
        )
        self.assertFalse(offer.is_expired())

        offer.expires_at = datetime.now() - timedelta(minutes=1)
        self.assertTrue(offer.is_expired())

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization"""
        offer = TradeOffer.create(
            owner_id="player1",
            offered_poke_data=self.poke_data,
            requirements=self.requirements,
        )
        data = offer.to_dict()
        restored = TradeOffer.from_dict(data)
        self.assertEqual(restored.offer_id, offer.offer_id)
        self.assertEqual(restored.owner_id, "player1")
        self.assertEqual(restored.status, TradeStatus.PENDING)


if __name__ == "__main__":
    unittest.main()
