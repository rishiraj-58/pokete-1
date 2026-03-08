"""Trade Manager - Core trading system logic"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .models import TradeOffer, TradeRequirements, TradeStatus
from .npc_trader import NPCTrader, NPCInventoryItem


class TradeManager:
    """Manages all trading operations including offers, matching, and persistence"""

    DEFAULT_EXPIRY_SECONDS = 3600
    CHECK_INTERVAL_SECONDS = 60

    def __init__(self, save_path: Optional[Path] = None):
        self.offers: dict[str, TradeOffer] = {}
        self.npc_traders: dict[str, NPCTrader] = {}
        self.save_path = save_path
        self._notification_callback: Optional[Callable[[str, str, str], None]] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def set_notification_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Set callback for trade notifications"""
        self._notification_callback = callback

    def _notify(self, title: str, name: str, desc: str) -> None:
        """Send a notification"""
        if self._notification_callback:
            self._notification_callback(title, name, desc)

    def register_npc_trader(self, trader: NPCTrader) -> None:
        """Register an NPC trader"""
        self.npc_traders[trader.trader_id] = trader

    def create_offer(
        self,
        pokete_identifier: str,
        pokete_name: str,
        pokete_level: int,
        owner_id: str,
        requirements: TradeRequirements,
        expiry_seconds: int = DEFAULT_EXPIRY_SECONDS,
    ) -> TradeOffer:
        """Create a new trade offer"""
        offer = TradeOffer(
            offered_pokete_identifier=pokete_identifier,
            offered_pokete_name=pokete_name,
            offered_pokete_level=pokete_level,
            requirements=requirements,
            owner_id=owner_id,
            expires_at=time.time() + expiry_seconds,
        )
        
        with self._lock:
            self.offers[offer.id] = offer
        
        logging.info("[Trade] Created offer %s for %s", offer.id, pokete_name)
        self._save()
        return offer

    def get_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Get an offer by ID"""
        return self.offers.get(offer_id)

    def get_pending_offers(self, owner_id: Optional[str] = None) -> list[TradeOffer]:
        """Get all pending offers, optionally filtered by owner"""
        offers = []
        for offer in self.offers.values():
            if offer.status == TradeStatus.PENDING:
                if owner_id is None or offer.owner_id == owner_id:
                    offers.append(offer)
        return offers

    def get_matched_offers(self, owner_id: Optional[str] = None) -> list[TradeOffer]:
        """Get all matched offers waiting for acceptance"""
        offers = []
        for offer in self.offers.values():
            if offer.status == TradeStatus.MATCHED:
                if owner_id is None or offer.owner_id == owner_id:
                    offers.append(offer)
        return offers

    def cancel_offer(self, offer_id: str, requester_id: str) -> bool:
        """Cancel a trade offer"""
        offer = self.offers.get(offer_id)
        if offer is None:
            return False
        
        if offer.owner_id != requester_id:
            return False
        
        if offer.status not in (TradeStatus.PENDING, TradeStatus.MATCHED):
            return False
        
        with self._lock:
            offer.status = TradeStatus.CANCELLED
        
        logging.info("[Trade] Offer %s cancelled", offer_id)
        self._save()
        return True

    def process_npc_counter_offers(self) -> list[TradeOffer]:
        """Have NPC traders evaluate pending offers and make counter-offers"""
        matched_offers = []
        
        for offer in list(self.offers.values()):
            if offer.status != TradeStatus.PENDING:
                continue
            
            for trader in self.npc_traders.values():
                counter_pokete = trader.generate_counter_offer(offer)
                if counter_pokete:
                    with self._lock:
                        offer.status = TradeStatus.MATCHED
                        offer.counter_offer_id = trader.trader_id
                        offer.counter_pokete_identifier = counter_pokete.identifier
                        offer.counter_pokete_name = counter_pokete.name
                    
                    matched_offers.append(offer)
                    self._notify(
                        "Trade Match!",
                        "Trading",
                        f"NPC offers {counter_pokete.name} for your {offer.offered_pokete_name}",
                    )
                    logging.info(
                        "[Trade] NPC %s matched offer %s with %s",
                        trader.trader_id,
                        offer.id,
                        counter_pokete.name,
                    )
                    break
        
        if matched_offers:
            self._save()
        
        return matched_offers

    def accept_offer(self, offer_id: str, requester_id: str) -> bool:
        """Accept a matched trade offer"""
        offer = self.offers.get(offer_id)
        if offer is None:
            return False
        
        if offer.owner_id != requester_id:
            return False
        
        if offer.status != TradeStatus.MATCHED:
            return False
        
        with self._lock:
            offer.status = TradeStatus.ACCEPTED
        
        npc_trader = self.npc_traders.get(offer.counter_offer_id or "")
        if npc_trader and offer.counter_pokete_identifier:
            npc_trader.remove_from_inventory(offer.counter_pokete_identifier)
        
        logging.info("[Trade] Offer %s accepted", offer_id)
        self._save()
        return True

    def reject_offer(self, offer_id: str, requester_id: str) -> bool:
        """Reject a matched trade offer"""
        offer = self.offers.get(offer_id)
        if offer is None:
            return False
        
        if offer.owner_id != requester_id:
            return False
        
        if offer.status != TradeStatus.MATCHED:
            return False
        
        with self._lock:
            offer.status = TradeStatus.REJECTED
        
        logging.info("[Trade] Offer %s rejected", offer_id)
        self._save()
        return True

    def complete_trade(self, offer_id: str) -> bool:
        """Mark a trade as completed after pokete exchange"""
        offer = self.offers.get(offer_id)
        if offer is None:
            return False
        
        if offer.status != TradeStatus.ACCEPTED:
            return False
        
        with self._lock:
            offer.status = TradeStatus.COMPLETED
        
        logging.info("[Trade] Offer %s completed", offer_id)
        self._save()
        return True

    def check_expired_offers(self) -> list[TradeOffer]:
        """Check and mark expired offers"""
        expired = []
        
        for offer in list(self.offers.values()):
            if offer.status in (TradeStatus.PENDING, TradeStatus.MATCHED):
                if offer.is_expired():
                    with self._lock:
                        offer.status = TradeStatus.EXPIRED
                    expired.append(offer)
                    self._notify(
                        "Trade Expired",
                        "Trading",
                        f"Your trade offer for {offer.offered_pokete_name} has expired",
                    )
                    logging.info("[Trade] Offer %s expired", offer.id)
        
        if expired:
            self._save()
        
        return expired

    def start_expiry_timer(self) -> None:
        """Start background timer for checking expirations"""
        if self._running:
            return
        
        self._running = True
        self._timer_thread = threading.Thread(target=self._expiry_loop, daemon=True)
        self._timer_thread.start()
        logging.info("[Trade] Expiry timer started")

    def stop_expiry_timer(self) -> None:
        """Stop the background expiry timer"""
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
        logging.info("[Trade] Expiry timer stopped")

    def _expiry_loop(self) -> None:
        """Background loop for checking expirations"""
        while self._running:
            time.sleep(self.CHECK_INTERVAL_SECONDS)
            if self._running:
                self.check_expired_offers()

    def _save(self) -> None:
        """Save offers to disk"""
        if self.save_path is None:
            return
        
        data = {
            "offers": {k: v.to_dict() for k, v in self.offers.items()}
        }
        
        try:
            with open(self.save_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error("[Trade] Failed to save: %s", e)

    def load(self) -> None:
        """Load offers from disk"""
        if self.save_path is None or not self.save_path.exists():
            return
        
        try:
            with open(self.save_path) as f:
                data = json.load(f)
            
            for offer_data in data.get("offers", {}).values():
                offer = TradeOffer.from_dict(offer_data)
                self.offers[offer.id] = offer
            
            logging.info("[Trade] Loaded %d offers", len(self.offers))
        except Exception as e:
            logging.error("[Trade] Failed to load: %s", e)

    def to_dict(self) -> dict:
        """Export all trade data as dictionary"""
        return {
            "offers": {k: v.to_dict() for k, v in self.offers.items()}
        }

    def from_dict(self, data: dict) -> None:
        """Import trade data from dictionary"""
        self.offers.clear()
        for offer_data in data.get("offers", {}).values():
            offer = TradeOffer.from_dict(offer_data)
            self.offers[offer.id] = offer


trade_manager = TradeManager()
