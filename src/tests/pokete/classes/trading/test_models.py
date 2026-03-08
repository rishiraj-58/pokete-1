"""Tests for trading models"""

import unittest
import time
from unittest.mock import patch

from pokete.classes.trading.models import (
    TradeOffer,
    TradeRequirements,
    TradeStatus,
)


class TestTradeRequirements(unittest.TestCase):
    def test_matches_with_no_requirements(self):
        requirements = TradeRequirements()
        self.assertTrue(requirements.matches("steini", 10, ["stone", "normal"]))

    def test_matches_min_level(self):
        requirements = TradeRequirements(min_level=10)
        self.assertTrue(requirements.matches("steini", 15, ["stone"]))
        self.assertTrue(requirements.matches("steini", 10, ["stone"]))
        self.assertFalse(requirements.matches("steini", 5, ["stone"]))

    def test_matches_max_level(self):
        requirements = TradeRequirements(max_level=20)
        self.assertTrue(requirements.matches("steini", 15, ["stone"]))
        self.assertTrue(requirements.matches("steini", 20, ["stone"]))
        self.assertFalse(requirements.matches("steini", 25, ["stone"]))

    def test_matches_level_range(self):
        requirements = TradeRequirements(min_level=10, max_level=20)
        self.assertTrue(requirements.matches("steini", 15, ["stone"]))
        self.assertFalse(requirements.matches("steini", 5, ["stone"]))
        self.assertFalse(requirements.matches("steini", 25, ["stone"]))

    def test_matches_types(self):
        requirements = TradeRequirements(types=["fire", "water"])
        self.assertTrue(requirements.matches("wolfior", 10, ["fire", "normal"]))
        self.assertTrue(requirements.matches("karpi", 10, ["water"]))
        self.assertFalse(requirements.matches("steini", 10, ["stone", "normal"]))

    def test_matches_specific_pokete(self):
        requirements = TradeRequirements(specific_pokete="steini")
        self.assertTrue(requirements.matches("steini", 10, ["stone"]))
        self.assertFalse(requirements.matches("mowcow", 10, ["normal"]))

    def test_matches_combined_requirements(self):
        requirements = TradeRequirements(
            min_level=10,
            max_level=30,
            types=["fire"],
        )
        self.assertTrue(requirements.matches("wolfior", 15, ["fire", "normal"]))
        self.assertFalse(requirements.matches("wolfior", 5, ["fire", "normal"]))
        self.assertFalse(requirements.matches("steini", 15, ["stone"]))

    def test_to_dict(self):
        requirements = TradeRequirements(
            min_level=10,
            max_level=20,
            types=["fire"],
            specific_pokete="wolfior",
        )
        result = requirements.to_dict()
        self.assertEqual(result["min_level"], 10)
        self.assertEqual(result["max_level"], 20)
        self.assertEqual(result["types"], ["fire"])
        self.assertEqual(result["specific_pokete"], "wolfior")

    def test_to_dict_empty_requirements(self):
        requirements = TradeRequirements()
        result = requirements.to_dict()
        self.assertEqual(result, {})

    def test_from_dict(self):
        data = {
            "min_level": 10,
            "max_level": 20,
            "types": ["fire", "water"],
            "specific_pokete": "wolfior",
        }
        requirements = TradeRequirements.from_dict(data)
        self.assertEqual(requirements.min_level, 10)
        self.assertEqual(requirements.max_level, 20)
        self.assertEqual(requirements.types, ["fire", "water"])
        self.assertEqual(requirements.specific_pokete, "wolfior")

    def test_from_dict_partial(self):
        data = {"min_level": 5}
        requirements = TradeRequirements.from_dict(data)
        self.assertEqual(requirements.min_level, 5)
        self.assertIsNone(requirements.max_level)
        self.assertEqual(requirements.types, [])
        self.assertIsNone(requirements.specific_pokete)


class TestTradeOffer(unittest.TestCase):
    def test_create_offer(self):
        requirements = TradeRequirements(min_level=10)
        offer = TradeOffer(
            offered_pokete_identifier="steini",
            offered_pokete_name="Steini",
            offered_pokete_level=15,
            requirements=requirements,
            owner_id="player1",
        )
        self.assertEqual(offer.offered_pokete_identifier, "steini")
        self.assertEqual(offer.offered_pokete_name, "Steini")
        self.assertEqual(offer.offered_pokete_level, 15)
        self.assertEqual(offer.owner_id, "player1")
        self.assertEqual(offer.status, TradeStatus.PENDING)
        self.assertIsNotNone(offer.id)

    def test_is_expired_false(self):
        offer = TradeOffer(
            offered_pokete_identifier="steini",
            offered_pokete_name="Steini",
            offered_pokete_level=15,
            requirements=TradeRequirements(),
            owner_id="player1",
            expires_at=time.time() + 3600,
        )
        self.assertFalse(offer.is_expired())

    def test_is_expired_true(self):
        offer = TradeOffer(
            offered_pokete_identifier="steini",
            offered_pokete_name="Steini",
            offered_pokete_level=15,
            requirements=TradeRequirements(),
            owner_id="player1",
            expires_at=time.time() - 100,
        )
        self.assertTrue(offer.is_expired())

    def test_to_dict(self):
        requirements = TradeRequirements(min_level=10)
        offer = TradeOffer(
            id="test-id",
            offered_pokete_identifier="steini",
            offered_pokete_name="Steini",
            offered_pokete_level=15,
            requirements=requirements,
            owner_id="player1",
            status=TradeStatus.MATCHED,
            created_at=1000.0,
            expires_at=2000.0,
            counter_offer_id="npc1",
            counter_pokete_identifier="wolfior",
            counter_pokete_name="Wolfior",
        )
        result = offer.to_dict()
        self.assertEqual(result["id"], "test-id")
        self.assertEqual(result["offered_pokete_identifier"], "steini")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["counter_pokete_name"], "Wolfior")

    def test_from_dict(self):
        data = {
            "id": "test-id",
            "offered_pokete_identifier": "steini",
            "offered_pokete_name": "Steini",
            "offered_pokete_level": 15,
            "requirements": {"min_level": 10},
            "owner_id": "player1",
            "status": "pending",
            "created_at": 1000.0,
            "expires_at": 2000.0,
            "counter_offer_id": None,
            "counter_pokete_identifier": None,
            "counter_pokete_name": None,
        }
        offer = TradeOffer.from_dict(data)
        self.assertEqual(offer.id, "test-id")
        self.assertEqual(offer.offered_pokete_identifier, "steini")
        self.assertEqual(offer.status, TradeStatus.PENDING)
        self.assertEqual(offer.requirements.min_level, 10)


class TestTradeStatus(unittest.TestCase):
    def test_status_values(self):
        self.assertEqual(TradeStatus.PENDING.value, "pending")
        self.assertEqual(TradeStatus.MATCHED.value, "matched")
        self.assertEqual(TradeStatus.ACCEPTED.value, "accepted")
        self.assertEqual(TradeStatus.REJECTED.value, "rejected")
        self.assertEqual(TradeStatus.EXPIRED.value, "expired")
        self.assertEqual(TradeStatus.COMPLETED.value, "completed")
        self.assertEqual(TradeStatus.CANCELLED.value, "cancelled")


if __name__ == "__main__":
    unittest.main()
