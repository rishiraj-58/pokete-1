"""NPC Trader logic for generating counter-offers"""

import random
from typing import Optional, Protocol
from dataclasses import dataclass

from .models import TradeOffer, TradeRequirements, TradeStatus


class PoketeLike(Protocol):
    """Protocol for Pokete-like objects"""
    identifier: str
    name: str
    
    def lvl(self) -> int: ...


@dataclass
class NPCInventoryItem:
    """Represents a pokete in an NPC's inventory"""
    identifier: str
    name: str
    level: int
    types: list[str]


class NPCTrader:
    """Handles NPC trading behavior"""

    def __init__(self, trader_id: str, inventory: list[NPCInventoryItem]):
        self.trader_id = trader_id
        self.inventory = inventory

    def find_matching_pokete(self, requirements: TradeRequirements) -> Optional[NPCInventoryItem]:
        """Find a pokete in inventory that matches the requirements"""
        matching = []
        for pokete in self.inventory:
            if requirements.matches(pokete.identifier, pokete.level, pokete.types):
                matching.append(pokete)
        
        if not matching:
            return None
        return random.choice(matching)

    def evaluate_offer(self, offer: TradeOffer) -> bool:
        """Decide whether to make a counter-offer"""
        if offer.status != TradeStatus.PENDING:
            return False
        
        match = self.find_matching_pokete(offer.requirements)
        return match is not None

    def generate_counter_offer(self, offer: TradeOffer) -> Optional[NPCInventoryItem]:
        """Generate a counter-offer pokete for the given offer"""
        if not self.evaluate_offer(offer):
            return None
        
        return self.find_matching_pokete(offer.requirements)

    def remove_from_inventory(self, identifier: str) -> bool:
        """Remove a pokete from inventory after trade"""
        for i, item in enumerate(self.inventory):
            if item.identifier == identifier:
                self.inventory.pop(i)
                return True
        return False
