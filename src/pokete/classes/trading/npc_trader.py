"""NPC trader that makes counter offers"""

import logging
import random
import threading
import time
from typing import Optional

from .trade_manager import TradeManager
from .trade_offer import TradeOffer, TradeStatus


class NPCTrader:
    """NPC that periodically checks and makes counter offers"""

    def __init__(
        self,
        npc_id: str,
        trade_manager: TradeManager,
        inventory: list[dict],
    ):
        self.npc_id = npc_id
        self.trade_manager = trade_manager
        self.inventory = inventory
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def update_inventory(self, inventory: list[dict]):
        """Update the NPC's inventory"""
        self.inventory = inventory

    def find_matching_poke(self, offer: TradeOffer) -> Optional[dict]:
        """Find a pokete in inventory that matches the offer requirements"""
        for poke_data in self.inventory:
            poke_types = poke_data.get("types", [])
            xp = poke_data.get("xp", 0)
            level = self._calculate_level(xp)

            if offer.requirements.matches(poke_types, level):
                return poke_data
        return None

    def _calculate_level(self, xp: int) -> int:
        """Calculate level from XP"""
        import math
        return int(math.sqrt(xp + 1))

    def check_and_make_offers(self):
        """Check pending offers and make counter offers"""
        pending_offers = self.trade_manager.get_pending_offers()

        for offer in pending_offers:
            if offer.owner_id == self.npc_id:
                continue

            matching_poke = self.find_matching_poke(offer)
            if matching_poke:
                success = self.trade_manager.submit_counter_offer(
                    offer.offer_id,
                    matching_poke,
                    self.npc_id,
                )
                if success:
                    logging.info(
                        "[NPCTrader][%s] Made counter offer for %s",
                        self.npc_id,
                        offer.offer_id,
                    )
                    self.inventory.remove(matching_poke)

    def start_periodic_checks(self, interval: int = 30):
        """Start periodic checking for trade matches"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._check_loop,
            args=(interval,),
            daemon=True,
        )
        self._thread.start()
        logging.info("[NPCTrader][%s] Started periodic checks", self.npc_id)

    def stop_periodic_checks(self):
        """Stop the periodic checking"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logging.info("[NPCTrader][%s] Stopped periodic checks", self.npc_id)

    def _check_loop(self, interval: int):
        """Background loop for checking offers"""
        while self._running:
            time.sleep(interval)
            self.check_and_make_offers()


class NPCTraderManager:
    """Manages multiple NPC traders"""

    def __init__(self, trade_manager: TradeManager):
        self.trade_manager = trade_manager
        self._traders: dict[str, NPCTrader] = {}

    def register_trader(self, npc_id: str, inventory: list[dict]) -> NPCTrader:
        """Register a new NPC trader"""
        trader = NPCTrader(npc_id, self.trade_manager, inventory)
        self._traders[npc_id] = trader
        return trader

    def get_trader(self, npc_id: str) -> Optional[NPCTrader]:
        """Get a trader by ID"""
        return self._traders.get(npc_id)

    def start_all(self, interval: int = 30):
        """Start all traders"""
        for trader in self._traders.values():
            trader.start_periodic_checks(interval)

    def stop_all(self):
        """Stop all traders"""
        for trader in self._traders.values():
            trader.stop_periodic_checks()

    def trigger_check_all(self):
        """Manually trigger a check on all traders"""
        for trader in self._traders.values():
            trader.check_and_make_offers()
