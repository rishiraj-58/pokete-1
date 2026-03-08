"""Data models for the trading system"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TypedDict
import uuid
import time


class TradeStatus(Enum):
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TradeRequirementsDict(TypedDict, total=False):
    min_level: int
    max_level: int
    types: list[str]
    specific_pokete: str


class TradeOfferDict(TypedDict):
    id: str
    offered_pokete_identifier: str
    offered_pokete_name: str
    offered_pokete_level: int
    requirements: TradeRequirementsDict
    owner_id: str
    status: str
    created_at: float
    expires_at: float
    counter_offer_id: Optional[str]
    counter_pokete_identifier: Optional[str]
    counter_pokete_name: Optional[str]


@dataclass
class TradeRequirements:
    min_level: Optional[int] = None
    max_level: Optional[int] = None
    types: list[str] = field(default_factory=list)
    specific_pokete: Optional[str] = None

    def matches(self, pokete_identifier: str, pokete_level: int, pokete_types: list[str]) -> bool:
        """Check if a pokete matches these requirements"""
        if self.min_level is not None and pokete_level < self.min_level:
            return False
        if self.max_level is not None and pokete_level > self.max_level:
            return False
        if self.types:
            if not any(t in pokete_types for t in self.types):
                return False
        if self.specific_pokete is not None:
            if pokete_identifier != self.specific_pokete:
                return False
        return True

    def to_dict(self) -> TradeRequirementsDict:
        result: TradeRequirementsDict = {}
        if self.min_level is not None:
            result["min_level"] = self.min_level
        if self.max_level is not None:
            result["max_level"] = self.max_level
        if self.types:
            result["types"] = self.types
        if self.specific_pokete is not None:
            result["specific_pokete"] = self.specific_pokete
        return result

    @classmethod
    def from_dict(cls, data: TradeRequirementsDict) -> "TradeRequirements":
        return cls(
            min_level=data.get("min_level"),
            max_level=data.get("max_level"),
            types=data.get("types", []),
            specific_pokete=data.get("specific_pokete"),
        )


@dataclass
class TradeOffer:
    offered_pokete_identifier: str
    offered_pokete_name: str
    offered_pokete_level: int
    requirements: TradeRequirements
    owner_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TradeStatus = TradeStatus.PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    counter_offer_id: Optional[str] = None
    counter_pokete_identifier: Optional[str] = None
    counter_pokete_name: Optional[str] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> TradeOfferDict:
        return {
            "id": self.id,
            "offered_pokete_identifier": self.offered_pokete_identifier,
            "offered_pokete_name": self.offered_pokete_name,
            "offered_pokete_level": self.offered_pokete_level,
            "requirements": self.requirements.to_dict(),
            "owner_id": self.owner_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "counter_offer_id": self.counter_offer_id,
            "counter_pokete_identifier": self.counter_pokete_identifier,
            "counter_pokete_name": self.counter_pokete_name,
        }

    @classmethod
    def from_dict(cls, data: TradeOfferDict) -> "TradeOffer":
        return cls(
            id=data["id"],
            offered_pokete_identifier=data["offered_pokete_identifier"],
            offered_pokete_name=data["offered_pokete_name"],
            offered_pokete_level=data["offered_pokete_level"],
            requirements=TradeRequirements.from_dict(data["requirements"]),
            owner_id=data["owner_id"],
            status=TradeStatus(data["status"]),
            created_at=data["created_at"],
            expires_at=data["expires_at"],
            counter_offer_id=data.get("counter_offer_id"),
            counter_pokete_identifier=data.get("counter_pokete_identifier"),
            counter_pokete_name=data.get("counter_pokete_name"),
        )
