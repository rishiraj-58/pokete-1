"""Replay format and versioning for battle replays"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import TypedDict, Any, Optional, Union, List
import json
import gzip
from datetime import datetime


class ReplayVersion:
    """Semantic versioning for replay format"""
    MAJOR = 1
    MINOR = 0
    PATCH = 0

    @classmethod
    def current(cls) -> str:
        return f"{cls.MAJOR}.{cls.MINOR}.{cls.PATCH}"

    @classmethod
    def parse(cls, version_str: str) -> tuple:
        parts = version_str.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])

    @classmethod
    def is_compatible(cls, version_str: str) -> bool:
        """Check if a replay version is compatible with current version"""
        major, minor, _ = cls.parse(version_str)
        return major == cls.MAJOR and minor <= cls.MINOR


class DecisionType(Enum):
    ATTACK = 1
    RUN_AWAY = 2
    ITEM = 3
    CHOOSE_POKE = 4


class FrameType(Enum):
    DECISION = auto()
    STATE_SNAPSHOT = auto()
    RANDOM_SEED = auto()
    BATTLE_END = auto()


@dataclass
class PokeSnapshot:
    """Snapshot of a Poke's state at a point in time"""
    identifier: str
    name: str
    hp: int
    full_hp: int
    xp: int
    attacks: List[str]
    attack_aps: List[int]
    effects: List[str]
    shiny: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PokeSnapshot:
        return cls(**data)

    @classmethod
    def from_poke(cls, poke) -> PokeSnapshot:
        return cls(
            identifier=poke.identifier,
            name=poke.name,
            hp=poke.hp,
            full_hp=poke.full_hp,
            xp=poke.xp,
            attacks=poke.attacks,
            attack_aps=[atk.ap for atk in poke.attack_obs],
            effects=[eff.c_name for eff in poke.effects],
            shiny=poke.shiny,
        )


@dataclass
class ProviderSnapshot:
    """Snapshot of a Provider's state"""
    provider_type: str
    name: str
    play_index: int
    pokes: List[PokeSnapshot]
    escapable: bool
    xp_multiplier: int

    def to_dict(self) -> dict:
        return {
            "provider_type": self.provider_type,
            "name": self.name,
            "play_index": self.play_index,
            "pokes": [p.to_dict() for p in self.pokes],
            "escapable": self.escapable,
            "xp_multiplier": self.xp_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProviderSnapshot:
        return cls(
            provider_type=data["provider_type"],
            name=data["name"],
            play_index=data["play_index"],
            pokes=[PokeSnapshot.from_dict(p) for p in data["pokes"]],
            escapable=data["escapable"],
            xp_multiplier=data["xp_multiplier"],
        )


@dataclass
class DecisionFrame:
    """A single decision made during battle"""
    turn: int
    provider_index: int
    decision_type: DecisionType
    attack_index: Optional[str] = None
    item_name: Optional[str] = None
    poke_index: Optional[int] = None
    random_values: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "provider_index": self.provider_index,
            "decision_type": self.decision_type.value,
            "attack_index": self.attack_index,
            "item_name": self.item_name,
            "poke_index": self.poke_index,
            "random_values": self.random_values,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DecisionFrame:
        return cls(
            turn=data["turn"],
            provider_index=data["provider_index"],
            decision_type=DecisionType(data["decision_type"]),
            attack_index=data.get("attack_index"),
            item_name=data.get("item_name"),
            poke_index=data.get("poke_index"),
            random_values=data.get("random_values", []),
        )


@dataclass
class StateFrame:
    """Complete state snapshot at a point in the battle"""
    turn: int
    providers: List[ProviderSnapshot]

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "providers": [p.to_dict() for p in self.providers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> StateFrame:
        return cls(
            turn=data["turn"],
            providers=[ProviderSnapshot.from_dict(p) for p in data["providers"]],
        )


@dataclass
class ReplayFrame:
    """A frame in the replay, either a decision or state snapshot"""
    frame_type: FrameType
    data: Union[DecisionFrame, StateFrame, dict]

    def to_dict(self) -> dict:
        if isinstance(self.data, (DecisionFrame, StateFrame)):
            data_dict = self.data.to_dict()
        else:
            data_dict = self.data
        return {
            "frame_type": self.frame_type.value,
            "data": data_dict,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReplayFrame:
        frame_type = FrameType(data["frame_type"])
        if frame_type == FrameType.DECISION:
            frame_data = DecisionFrame.from_dict(data["data"])
        elif frame_type == FrameType.STATE_SNAPSHOT:
            frame_data = StateFrame.from_dict(data["data"])
        else:
            frame_data = data["data"]
        return cls(frame_type=frame_type, data=frame_data)


@dataclass
class ReplayMetadata:
    """Metadata about the battle replay"""
    version: str
    timestamp: str
    battle_type: str
    provider_names: List[str]
    winner_index: Optional[int] = None
    total_turns: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ReplayMetadata:
        return cls(**data)


@dataclass
class ReplayFormat:
    """Complete replay file format"""
    metadata: ReplayMetadata
    initial_state: StateFrame
    frames: List[ReplayFrame]
    final_state: Optional[StateFrame] = None

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "initial_state": self.initial_state.to_dict(),
            "frames": [f.to_dict() for f in self.frames],
            "final_state": self.final_state.to_dict() if self.final_state else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReplayFormat:
        return cls(
            metadata=ReplayMetadata.from_dict(data["metadata"]),
            initial_state=StateFrame.from_dict(data["initial_state"]),
            frames=[ReplayFrame.from_dict(f) for f in data["frames"]],
            final_state=StateFrame.from_dict(data["final_state"]) if data.get("final_state") else None,
        )

    def to_json(self, pretty: bool = False) -> str:
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> ReplayFormat:
        return cls.from_dict(json.loads(json_str))

    def save(self, filepath: str, compress: bool = True):
        """Save replay to file"""
        json_data = self.to_json().encode('utf-8')
        if compress:
            if not filepath.endswith('.pokereplay.gz'):
                filepath += '.pokereplay.gz'
            with gzip.open(filepath, 'wb') as f:
                f.write(json_data)
        else:
            if not filepath.endswith('.pokereplay'):
                filepath += '.pokereplay'
            with open(filepath, 'w') as f:
                f.write(json_data.decode('utf-8'))

    @classmethod
    def load(cls, filepath: str) -> ReplayFormat:
        """Load replay from file"""
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rb') as f:
                json_data = f.read().decode('utf-8')
        else:
            with open(filepath, 'r') as f:
                json_data = f.read()
        return cls.from_json(json_data)

    def validate(self) -> tuple:
        """Validate replay format integrity"""
        errors = []
        if not ReplayVersion.is_compatible(self.metadata.version):
            errors.append(
                f"Incompatible version: {self.metadata.version} "
                f"(current: {ReplayVersion.current()})"
            )
        if not self.initial_state.providers:
            errors.append("No providers in initial state")
        return len(errors) == 0, errors


class ReplayMigrator:
    """Handles migration between replay format versions"""

    @staticmethod
    def migrate(replay_data: dict) -> dict:
        """Migrate replay data to current version if needed"""
        version = replay_data.get("metadata", {}).get("version", "0.0.0")
        major, minor, patch = ReplayVersion.parse(version)

        # Migration from 0.x.x to 1.x.x would go here
        if major < 1:
            replay_data = ReplayMigrator._migrate_0_to_1(replay_data)

        replay_data["metadata"]["version"] = ReplayVersion.current()
        return replay_data

    @staticmethod
    def _migrate_0_to_1(data: dict) -> dict:
        """Migration from version 0.x to 1.x"""
        # This is a placeholder for future migrations
        return data
