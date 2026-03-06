"""Trade manager for handling Pokete trades"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from pokete import release

from .trade_offer import TradeOffer, TradeRequirements, TradeStatus


class TradeManager:
    """Manages Pokete trading system"""

    def __init__(self, save_path: Optional[Path] = None):
        self._offers: dict[str, TradeOffer] = {}
        self._save_path = save_path or release.SAVEPATH / "trades.json"
        self._notification_callback: Optional[Callable[[str, str, str], None]] = None
        self._expiry_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def set_notification_callback(self, callback: Callable[[str, str, str], None]):
        """Set callback for trade notifications (title, name, desc)"""
        self._notification_callback = callback

    def _notify(self, title: str, name: str, desc: str):
        """Send notification if callback is set"""
        if self._notification_callback:
            self._notification_callback(title, name, desc)

    def create_offer(
        self,
        owner_id: str,
        offered_poke_data: dict,
        requirements: TradeRequirements,
        expiry_minutes: int = 60,
    ) -> TradeOffer:
        """Create a new trade offer"""
        offer = TradeOffer.create(
            owner_id=owner_id,
            offered_poke_data=offered_poke_data,
            requirements=requirements,
            expiry_minutes=expiry_minutes,
        )
        with self._lock:
            self._offers[offer.offer_id] = offer
        self.save()
        logging.info("[Trade] Created offer %s for %s", offer.offer_id, owner_id)
        return offer

    def get_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Get a trade offer by ID"""
        return self._offers.get(offer_id)

    def get_pending_offers(self) -> list[TradeOffer]:
        """Get all pending trade offers"""
        return [
            offer for offer in self._offers.values()
            if offer.status == TradeStatus.PENDING
        ]

    def get_offers_by_owner(self, owner_id: str) -> list[TradeOffer]:
        """Get all offers from a specific owner"""
        return [
            offer for offer in self._offers.values()
            if offer.owner_id == owner_id
        ]

    def submit_counter_offer(
        self,
        offer_id: str,
        counter_poke_data: dict,
        counter_owner_id: str,
    ) -> bool:
        """Submit a counter offer for an existing trade"""
        with self._lock:
            offer = self._offers.get(offer_id)
            if not offer:
                return False
            if offer.status != TradeStatus.PENDING:
                return False
            if offer.is_expired():
                offer.status = TradeStatus.EXPIRED
                return False

            poke_types = counter_poke_data.get("types", [])
            poke_level = self._calculate_level(counter_poke_data.get("xp", 0))

            if not offer.requirements.matches(poke_types, poke_level):
                return False

            offer.counter_offer_poke_data = counter_poke_data
            offer.counter_offer_owner_id = counter_owner_id
            offer.status = TradeStatus.MATCHED

        self._notify(
            "Trade Match!",
            "Trading",
            f"Someone wants to trade for your {offer.offered_poke_data.get('name', 'Pokete')}!",
        )
        self.save()
        logging.info("[Trade] Counter offer submitted for %s", offer_id)
        return True

    def accept_trade(self, offer_id: str, accepting_owner_id: str) -> bool:
        """Accept a matched trade"""
        with self._lock:
            offer = self._offers.get(offer_id)
            if not offer:
                return False
            if offer.status != TradeStatus.MATCHED:
                return False
            if offer.owner_id != accepting_owner_id:
                return False

            offer.status = TradeStatus.ACCEPTED

        self._notify(
            "Trade Accepted!",
            "Trading",
            f"Trade completed for {offer.offered_poke_data.get('name', 'Pokete')}!",
        )
        self.save()
        logging.info("[Trade] Trade accepted: %s", offer_id)
        return True

    def reject_trade(self, offer_id: str, rejecting_owner_id: str) -> bool:
        """Reject a matched trade"""
        with self._lock:
            offer = self._offers.get(offer_id)
            if not offer:
                return False
            if offer.status != TradeStatus.MATCHED:
                return False
            if offer.owner_id != rejecting_owner_id:
                return False

            offer.status = TradeStatus.REJECTED
            offer.counter_offer_poke_data = None
            offer.counter_offer_owner_id = None

        self.save()
        logging.info("[Trade] Trade rejected: %s", offer_id)
        return True

    def cancel_offer(self, offer_id: str, owner_id: str) -> bool:
        """Cancel a pending or matched offer"""
        with self._lock:
            offer = self._offers.get(offer_id)
            if not offer:
                return False
            if offer.owner_id != owner_id:
                return False
            if offer.status not in (TradeStatus.PENDING, TradeStatus.MATCHED):
                return False

            offer.status = TradeStatus.CANCELLED

        self.save()
        logging.info("[Trade] Offer cancelled: %s", offer_id)
        return True

    def check_expired_offers(self):
        """Check and mark expired offers"""
        expired_count = 0
        with self._lock:
            for offer in self._offers.values():
                if offer.status == TradeStatus.PENDING and offer.is_expired():
                    offer.status = TradeStatus.EXPIRED
                    expired_count += 1
        if expired_count > 0:
            self.save()
            logging.info("[Trade] Expired %d offers", expired_count)

    def start_expiry_timer(self, check_interval: int = 60):
        """Start background thread for checking expired offers"""
        if self._running:
            return
        self._running = True
        self._expiry_thread = threading.Thread(
            target=self._expiry_loop,
            args=(check_interval,),
            daemon=True,
        )
        self._expiry_thread.start()
        logging.info("[Trade] Started expiry timer")

    def stop_expiry_timer(self):
        """Stop the expiry timer thread"""
        self._running = False
        if self._expiry_thread:
            self._expiry_thread.join(timeout=5)
            self._expiry_thread = None
        logging.info("[Trade] Stopped expiry timer")

    def _expiry_loop(self, check_interval: int):
        """Background loop for checking expired offers"""
        while self._running:
            time.sleep(check_interval)
            self.check_expired_offers()

    def _calculate_level(self, xp: int) -> int:
        """Calculate level from XP"""
        import math
        return int(math.sqrt(xp + 1))

    def save(self):
        """Save trades to file"""
        data = {
            "offers": {
                offer_id: offer.to_dict()
                for offer_id, offer in self._offers.items()
            }
        }
        self._save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._save_path, "w") as f:
            json.dump(data, f, indent=2)
        logging.info("[Trade] Saved %d offers", len(self._offers))

    def load(self):
        """Load trades from file"""
        if not self._save_path.exists():
            return
        try:
            with open(self._save_path) as f:
                data = json.load(f)
            self._offers = {
                offer_id: TradeOffer.from_dict(offer_data)
                for offer_id, offer_data in data.get("offers", {}).items()
            }
            logging.info("[Trade] Loaded %d offers", len(self._offers))
        except Exception as e:
            logging.error("[Trade] Failed to load: %s", e)

    def clear_completed_offers(self):
        """Remove completed, rejected, expired, and cancelled offers"""
        with self._lock:
            completed_statuses = {
                TradeStatus.ACCEPTED,
                TradeStatus.REJECTED,
                TradeStatus.EXPIRED,
                TradeStatus.CANCELLED,
            }
            self._offers = {
                offer_id: offer
                for offer_id, offer in self._offers.items()
                if offer.status not in completed_statuses
            }
        self.save()


trade_manager = TradeManager()
