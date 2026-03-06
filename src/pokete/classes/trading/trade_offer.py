"""Trade offer data structures"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeStatus(Enum):
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class TradeRequirements:
    """Requirements for accepting a trade"""
    required_types: list[str] = field(default_factory=list)
    min_level: int = 1
    max_level: Optional[int] = None

    def matches(self, poke_types: list[str], level: int) -> bool:
        """Check if a pokete matches the requirements"""
        if self.required_types:
            type_names = [t if isinstance(t, str) else t.name for t in poke_types]
            if not any(t in type_names for t in self.required_types):
                return False
        if level < self.min_level:
            return False
        if self.max_level and level > self.max_level:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "required_types": self.required_types,
            "min_level": self.min_level,
            "max_level": self.max_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRequirements":
        return cls(
            required_types=data.get("required_types", []),
            min_level=data.get("min_level", 1),
            max_level=data.get("max_level"),
        )


@dataclass
class TradeOffer:
    """Represents a trade offer for a Pokete"""
    offer_id: str
    owner_id: str
    offered_poke_data: dict
    requirements: TradeRequirements
    status: TradeStatus = TradeStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    counter_offer_poke_data: Optional[dict] = None
    counter_offer_owner_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        owner_id: str,
        offered_poke_data: dict,
        requirements: TradeRequirements,
        expiry_minutes: int = 60,
    ) -> "TradeOffer":
        """Create a new trade offer"""
        now = datetime.now()
        from datetime import timedelta
        return cls(
            offer_id=str(uuid.uuid4()),
            owner_id=owner_id,
            offered_poke_data=offered_poke_data,
            requirements=requirements,
            created_at=now,
            expires_at=now + timedelta(minutes=expiry_minutes),
        )

    def is_expired(self) -> bool:
        """Check if the offer has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "offer_id": self.offer_id,
            "owner_id": self.owner_id,
            "offered_poke_data": self.offered_poke_data,
            "requirements": self.requirements.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "counter_offer_poke_data": self.counter_offer_poke_data,
            "counter_offer_owner_id": self.counter_offer_owner_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeOffer":
        return cls(
            offer_id=data["offer_id"],
            owner_id=data["owner_id"],
            offered_poke_data=data["offered_poke_data"],
            requirements=TradeRequirements.from_dict(data["requirements"]),
            status=TradeStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            counter_offer_poke_data=data.get("counter_offer_poke_data"),
            counter_offer_owner_id=data.get("counter_offer_owner_id"),
        )
