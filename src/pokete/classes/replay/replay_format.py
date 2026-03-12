"""Versioned replay format for battle recordings"""

from __future__ import annotations
import json
import gzip
import base64
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
from functools import total_ordering


@total_ordering
class ReplayVersion:
    """Semantic version for replay format compatibility"""

    CURRENT_MAJOR = 1
    CURRENT_MINOR = 0
    CURRENT_PATCH = 0

    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def current(cls) -> ReplayVersion:
        return cls(cls.CURRENT_MAJOR, cls.CURRENT_MINOR, cls.CURRENT_PATCH)

    @classmethod
    def from_dict(cls, data: dict) -> ReplayVersion:
        return cls(data["major"], data["minor"], data["patch"])

    def to_dict(self) -> dict:
        return {"major": self.major, "minor": self.minor, "patch": self.patch}

    def is_compatible(self, other: ReplayVersion) -> bool:
        """Check if replay is compatible (same major version)"""
        return self.major == other.major

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReplayVersion):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __gt__(self, other: ReplayVersion) -> bool:
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class ReplayEventType(Enum):
    """Types of events that can occur during battle"""

    BATTLE_START = auto()
    BATTLE_END = auto()
    TURN_START = auto()
    ATTACK_CHOSEN = auto()
    ATTACK_EXECUTED = auto()
    ITEM_USED = auto()
    POKE_SWITCHED = auto()
    RUN_AWAY_ATTEMPT = auto()
    RUN_AWAY_SUCCESS = auto()
    RUN_AWAY_FAILED = auto()
    EFFECT_APPLIED = auto()
    EFFECT_REMOVED = auto()
    HP_CHANGED = auto()
    AP_CHANGED = auto()
    POKE_FAINTED = auto()
    XP_GAINED = auto()
    LEVEL_UP = auto()
    CATCH_ATTEMPT = auto()
    CATCH_SUCCESS = auto()
    CATCH_FAILED = auto()
    STATE_SNAPSHOT = auto()


@dataclass
class ReplayEvent:
    """A single event in the battle replay"""

    event_type: ReplayEventType
    turn_number: int
    provider_index: int
    data: Dict = field(default_factory=dict)
    timestamp_ms: int = 0

    def to_dict(self) -> Dict:
        return {
            "type": self.event_type.value,
            "turn": self.turn_number,
            "provider": self.provider_index,
            "data": self.data,
            "ts": self.timestamp_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> ReplayEvent:
        return cls(
            event_type=ReplayEventType(data["type"]),
            turn_number=data["turn"],
            provider_index=data["provider"],
            data=data.get("data", {}),
            timestamp_ms=data.get("ts", 0),
        )


@dataclass
class PokeStateRecord:
    """Minimal poke state for replay"""

    identifier: str
    name: str
    hp: int
    max_hp: int
    xp: int
    level: int
    attacks: List[str]
    attack_aps: List[int]
    effects: List[str]
    shiny: bool

    def to_dict(self) -> Dict:
        return {
            "id": self.identifier,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "xp": self.xp,
            "lvl": self.level,
            "atks": self.attacks,
            "aps": self.attack_aps,
            "effs": self.effects,
            "shiny": self.shiny,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> PokeStateRecord:
        return cls(
            identifier=data["id"],
            name=data["name"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            xp=data["xp"],
            level=data["lvl"],
            attacks=data["atks"],
            attack_aps=data["aps"],
            effects=data["effs"],
            shiny=data.get("shiny", False),
        )


@dataclass
class ProviderRecord:
    """Provider state for replay"""

    provider_type: str
    name: str
    pokes: List[PokeStateRecord]
    current_poke_index: int
    escapable: bool

    def to_dict(self) -> Dict:
        return {
            "type": self.provider_type,
            "name": self.name,
            "pokes": [p.to_dict() for p in self.pokes],
            "curr_idx": self.current_poke_index,
            "escapable": self.escapable,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> ProviderRecord:
        return cls(
            provider_type=data["type"],
            name=data["name"],
            pokes=[PokeStateRecord.from_dict(p) for p in data["pokes"]],
            current_poke_index=data["curr_idx"],
            escapable=data["escapable"],
        )


@dataclass
class ReplayMetadata:
    """Metadata about the replay"""

    recorded_at: str
    duration_ms: int
    total_turns: int
    winner_index: Optional[int]
    battle_type: str  # "wild", "trainer", "multiplayer"
    random_seed: Optional[int]

    def to_dict(self) -> Dict:
        return {
            "recorded_at": self.recorded_at,
            "duration_ms": self.duration_ms,
            "total_turns": self.total_turns,
            "winner": self.winner_index,
            "battle_type": self.battle_type,
            "seed": self.random_seed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> ReplayMetadata:
        return cls(
            recorded_at=data["recorded_at"],
            duration_ms=data["duration_ms"],
            total_turns=data["total_turns"],
            winner_index=data.get("winner"),
            battle_type=data["battle_type"],
            random_seed=data.get("seed"),
        )


@dataclass
class ReplayFormat:
    """Complete replay data structure"""

    version: ReplayVersion
    metadata: ReplayMetadata
    initial_state: List[ProviderRecord]
    events: List[ReplayEvent]

    def to_dict(self) -> Dict:
        return {
            "v": self.version.to_dict(),
            "meta": self.metadata.to_dict(),
            "init": [p.to_dict() for p in self.initial_state],
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> ReplayFormat:
        return cls(
            version=ReplayVersion.from_dict(data["v"]),
            metadata=ReplayMetadata.from_dict(data["meta"]),
            initial_state=[ProviderRecord.from_dict(p) for p in data["init"]],
            events=[ReplayEvent.from_dict(e) for e in data["events"]],
        )

    def save_to_file(self, path: str, compress: bool = True) -> None:
        """Save replay to file"""
        data = json.dumps(self.to_dict(), separators=(",", ":"))
        if compress:
            compressed = gzip.compress(data.encode("utf-8"))
            with open(path, "wb") as f:
                f.write(compressed)
        else:
            with open(path, "w") as f:
                f.write(data)

    @classmethod
    def load_from_file(cls, path: str) -> ReplayFormat:
        """Load replay from file"""
        try:
            with open(path, "rb") as f:
                content = f.read()
            try:
                decompressed = gzip.decompress(content).decode("utf-8")
            except gzip.BadGzipFile:
                decompressed = content.decode("utf-8")
            data = json.loads(decompressed)
            return cls.from_dict(data)
        except Exception as e:
            raise ReplayLoadError("Failed to load replay: {}".format(e)) from e

    def to_base64(self) -> str:
        """Serialize to base64 for memory storage or transmission"""
        data = json.dumps(self.to_dict(), separators=(",", ":"))
        compressed = gzip.compress(data.encode("utf-8"))
        return base64.b64encode(compressed).decode("ascii")

    @classmethod
    def from_base64(cls, encoded: str) -> ReplayFormat:
        """Deserialize from base64"""
        compressed = base64.b64decode(encoded.encode("ascii"))
        data = json.loads(gzip.decompress(compressed).decode("utf-8"))
        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """Validate replay integrity, returns list of issues"""
        issues = []
        current_version = ReplayVersion.current()

        if not self.version.is_compatible(current_version):
            issues.append(
                "Version mismatch: replay v{}, current v{}".format(self.version, current_version)
            )

        if not self.initial_state:
            issues.append("No initial state recorded")

        if len(self.initial_state) != 2:
            issues.append("Expected 2 providers, got {}".format(len(self.initial_state)))

        for i, provider in enumerate(self.initial_state):
            if not provider.pokes:
                issues.append("Provider {} has no pokes".format(i))

        turn_numbers = [e.turn_number for e in self.events]
        if turn_numbers and turn_numbers != sorted(turn_numbers):
            issues.append("Events are not in chronological order")

        return issues


class ReplayLoadError(Exception):
    """Error loading a replay file"""

    pass


class ReplayVersionError(Exception):
    """Replay version incompatibility"""

    pass


def migrate_replay(replay: ReplayFormat, target_version: ReplayVersion) -> ReplayFormat:
    """Migrate a replay to a newer version format"""
    if replay.version >= target_version:
        return replay

    # Migration logic would go here for future versions
    # For now, we only have v1.0.0

    return ReplayFormat(
        version=target_version,
        metadata=replay.metadata,
        initial_state=replay.initial_state,
        events=replay.events,
    )
