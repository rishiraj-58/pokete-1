#!/usr/bin/env python3
"""
Standalone tests for the battle replay system.
Tests the replay module independently without importing the rest of pokete.
"""

import unittest
import tempfile
import os
import json
import sys
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import TypedDict, Any, Iterator
import gzip
import random


# ============================================================================
# Inline copy of the replay system code for testing with Python 3.9
# This allows us to test the logic without needing Python 3.10+ features
# ============================================================================

class ReplayVersion:
    MAJOR = 1
    MINOR = 0
    PATCH = 0

    @classmethod
    def current(cls) -> str:
        return f"{cls.MAJOR}.{cls.MINOR}.{cls.PATCH}"

    @classmethod
    def parse(cls, version_str: str):
        parts = version_str.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])

    @classmethod
    def is_compatible(cls, version_str: str) -> bool:
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
    identifier: str
    name: str
    hp: int
    full_hp: int
    xp: int
    attacks: list
    attack_aps: list
    effects: list
    shiny: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PokeSnapshot":
        return cls(**data)


@dataclass
class ProviderSnapshot:
    provider_type: str
    name: str
    play_index: int
    pokes: list
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
    def from_dict(cls, data: dict) -> "ProviderSnapshot":
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
    turn: int
    provider_index: int
    decision_type: DecisionType
    attack_index: str = None
    item_name: str = None
    poke_index: int = None
    random_values: list = field(default_factory=list)

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
    def from_dict(cls, data: dict) -> "DecisionFrame":
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
    turn: int
    providers: list

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "providers": [p.to_dict() for p in self.providers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StateFrame":
        return cls(
            turn=data["turn"],
            providers=[ProviderSnapshot.from_dict(p) for p in data["providers"]],
        )


@dataclass
class ReplayFrame:
    frame_type: FrameType
    data: Any  # DecisionFrame | StateFrame | dict

    def to_dict(self) -> dict:
        if hasattr(self.data, 'to_dict'):
            data_dict = self.data.to_dict()
        else:
            data_dict = self.data
        return {
            "frame_type": self.frame_type.value,
            "data": data_dict,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayFrame":
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
    version: str
    timestamp: str
    battle_type: str
    provider_names: list
    winner_index: int = None
    total_turns: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayMetadata":
        return cls(**data)


@dataclass
class ReplayFormat:
    metadata: ReplayMetadata
    initial_state: StateFrame
    frames: list
    final_state: StateFrame = None

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "initial_state": self.initial_state.to_dict(),
            "frames": [f.to_dict() for f in self.frames],
            "final_state": self.final_state.to_dict() if self.final_state else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayFormat":
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
    def from_json(cls, json_str: str) -> "ReplayFormat":
        return cls.from_dict(json.loads(json_str))

    def save(self, filepath: str, compress: bool = True):
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
    def load(cls, filepath: str) -> "ReplayFormat":
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rb') as f:
                json_data = f.read().decode('utf-8')
        else:
            with open(filepath, 'r') as f:
                json_data = f.read()
        return cls.from_json(json_data)

    def validate(self):
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
    @staticmethod
    def migrate(replay_data: dict) -> dict:
        version = replay_data.get("metadata", {}).get("version", "0.0.0")
        major, minor, patch = ReplayVersion.parse(version)
        if major < 1:
            replay_data = ReplayMigrator._migrate_0_to_1(replay_data)
        replay_data["metadata"]["version"] = ReplayVersion.current()
        return replay_data

    @staticmethod
    def _migrate_0_to_1(data: dict) -> dict:
        return data


class BattleRecorder:
    def __init__(self):
        self._recording = False
        self._frames = []
        self._initial_state = None
        self._turn = 0
        self._providers = []
        self._battle_type = "unknown"

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, providers: list, battle_type: str = "standard"):
        self._recording = True
        self._frames = []
        self._turn = 0
        self._providers = providers
        self._battle_type = battle_type
        self._initial_state = self._capture_state()

    def _capture_provider_snapshot(self, provider, index: int) -> ProviderSnapshot:
        provider_type = type(provider).__name__
        name = getattr(provider, 'name', f"Provider_{index}")
        pokes = []
        for poke in provider.pokes[:6]:
            pokes.append(PokeSnapshot(
                identifier=poke.identifier,
                name=poke.name,
                hp=poke.hp,
                full_hp=poke.full_hp,
                xp=poke.xp,
                attacks=poke.attacks,
                attack_aps=[atk.ap for atk in poke.attack_obs],
                effects=[eff.c_name for eff in poke.effects],
                shiny=poke.shiny,
            ))
        return ProviderSnapshot(
            provider_type=provider_type,
            name=name,
            play_index=provider.play_index,
            pokes=pokes,
            escapable=provider.escapable,
            xp_multiplier=provider.xp_multiplier,
        )

    def _capture_state(self) -> StateFrame:
        providers = [
            self._capture_provider_snapshot(p, i)
            for i, p in enumerate(self._providers)
        ]
        return StateFrame(turn=self._turn, providers=providers)

    def record_decision(
        self,
        provider_index: int,
        decision_type: DecisionType,
        attack_index: str = None,
        item_name: str = None,
        poke_index: int = None,
        random_values: list = None,
    ):
        if not self._recording:
            return
        frame = DecisionFrame(
            turn=self._turn,
            provider_index=provider_index,
            decision_type=decision_type,
            attack_index=attack_index,
            item_name=item_name,
            poke_index=poke_index,
            random_values=random_values or [],
        )
        self._frames.append(ReplayFrame(
            frame_type=FrameType.DECISION,
            data=frame,
        ))

    def advance_turn(self):
        self._turn += 1

    def stop_recording(self, winner_index: int = None) -> ReplayFormat:
        if not self._recording:
            raise RuntimeError("Not currently recording")
        self._recording = False
        final_state = self._capture_state()
        metadata = ReplayMetadata(
            version=ReplayVersion.current(),
            timestamp=datetime.now().isoformat(),
            battle_type=self._battle_type,
            provider_names=[
                getattr(p, 'name', f"Provider_{i}")
                for i, p in enumerate(self._providers)
            ],
            winner_index=winner_index,
            total_turns=self._turn,
        )
        replay = ReplayFormat(
            metadata=metadata,
            initial_state=self._initial_state,
            frames=self._frames,
            final_state=final_state,
        )
        self._frames = []
        self._initial_state = None
        self._providers = []
        return replay


class BattleReplay:
    def __init__(self, replay: ReplayFormat):
        self._replay = replay
        self._frame_index = 0
        self._current_state = replay.initial_state
        self._finished = False
        valid, errors = replay.validate()
        if not valid:
            raise ValueError(f"Invalid replay: {errors}")

    @property
    def metadata(self):
        return self._replay.metadata

    @property
    def total_frames(self) -> int:
        return len(self._replay.frames)

    @property
    def current_frame_index(self) -> int:
        return self._frame_index

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def current_state(self) -> StateFrame:
        return self._current_state

    def get_initial_state(self) -> StateFrame:
        return self._replay.initial_state

    def get_final_state(self):
        return self._replay.final_state

    def reset(self):
        self._frame_index = 0
        self._current_state = self._replay.initial_state
        self._finished = False

    def get_frame(self, index: int):
        if 0 <= index < len(self._replay.frames):
            return self._replay.frames[index]
        return None

    def current_frame(self):
        return self.get_frame(self._frame_index)

    def advance(self):
        if self._frame_index >= len(self._replay.frames):
            self._finished = True
            return None
        frame = self._replay.frames[self._frame_index]
        self._frame_index += 1
        if frame.frame_type == FrameType.STATE_SNAPSHOT:
            self._current_state = frame.data
        if self._frame_index >= len(self._replay.frames):
            self._finished = True
            if self._replay.final_state:
                self._current_state = self._replay.final_state
        return frame

    def rewind(self, frames: int = 1) -> bool:
        target_index = max(0, self._frame_index - frames)
        self._frame_index = 0
        self._current_state = self._replay.initial_state
        self._finished = False
        while self._frame_index < target_index:
            frame = self._replay.frames[self._frame_index]
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                self._current_state = frame.data
            self._frame_index += 1
        return True

    def seek(self, frame_index: int) -> bool:
        if frame_index < 0:
            frame_index = 0
        if frame_index > len(self._replay.frames):
            frame_index = len(self._replay.frames)
        if frame_index < self._frame_index:
            self._frame_index = 0
            self._current_state = self._replay.initial_state
            self._finished = False
        while self._frame_index < frame_index:
            frame = self._replay.frames[self._frame_index]
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                self._current_state = frame.data
            self._frame_index += 1
        self._finished = self._frame_index >= len(self._replay.frames)
        return True

    def get_decision_frames(self) -> list:
        return [
            f.data for f in self._replay.frames
            if f.frame_type == FrameType.DECISION
        ]

    def iter_frames(self) -> Iterator:
        while not self._finished:
            frame = self.advance()
            if frame:
                yield frame


class ReplayValidator:
    @staticmethod
    def compare_poke_states(expected: PokeSnapshot, actual: PokeSnapshot) -> list:
        diffs = []
        if expected.hp != actual.hp:
            diffs.append(f"HP mismatch: expected {expected.hp}, got {actual.hp}")
        if expected.attack_aps != actual.attack_aps:
            diffs.append(f"AP mismatch: expected {expected.attack_aps}, got {actual.attack_aps}")
        if expected.effects != actual.effects:
            diffs.append(f"Effects mismatch: expected {expected.effects}, got {actual.effects}")
        return diffs


class PlaybackSpeed(Enum):
    SLOW = 2.0
    NORMAL = 1.0
    FAST = 0.5
    VERY_FAST = 0.25
    INSTANT = 0.0


class SpectatorCommand(Enum):
    ADVANCE = auto()
    REWIND = auto()
    FAST_FORWARD = auto()
    PAUSE = auto()
    RESUME = auto()
    SPEED_UP = auto()
    SPEED_DOWN = auto()
    QUIT = auto()
    SEEK_START = auto()
    SEEK_END = auto()


@dataclass
class SpectatorState:
    frame_index: int
    total_frames: int
    is_playing: bool
    is_finished: bool
    speed: PlaybackSpeed
    current_turn: int


class SpectatorMode:
    def __init__(self, replay: BattleReplay, on_frame=None, on_state_change=None):
        self._replay = replay
        self._on_frame = on_frame
        self._on_state_change = on_state_change
        self._speed = PlaybackSpeed.NORMAL
        self._playing = False
        self._current_turn = 0
        self._command_queue = []

    @property
    def state(self) -> SpectatorState:
        return SpectatorState(
            frame_index=self._replay.current_frame_index,
            total_frames=self._replay.total_frames,
            is_playing=self._playing,
            is_finished=self._replay.is_finished,
            speed=self._speed,
            current_turn=self._current_turn,
        )

    @property
    def replay(self) -> BattleReplay:
        return self._replay

    @property
    def is_playing(self) -> bool:
        return self._playing

    def queue_command(self, command: SpectatorCommand):
        self._command_queue.append(command)

    def _process_commands(self) -> bool:
        while self._command_queue:
            cmd = self._command_queue.pop(0)
            if cmd == SpectatorCommand.QUIT:
                self._playing = False
                return False
            elif cmd == SpectatorCommand.PAUSE:
                self._playing = False
            elif cmd == SpectatorCommand.RESUME:
                self._playing = True
            elif cmd == SpectatorCommand.ADVANCE:
                self._advance_frame()
            elif cmd == SpectatorCommand.REWIND:
                self._rewind_frame()
            elif cmd == SpectatorCommand.SPEED_UP:
                self._increase_speed()
            elif cmd == SpectatorCommand.SPEED_DOWN:
                self._decrease_speed()
        return True

    def _advance_frame(self):
        frame = self._replay.advance()
        if frame:
            if frame.frame_type == FrameType.DECISION:
                self._current_turn = frame.data.turn
            if frame.frame_type == FrameType.STATE_SNAPSHOT:
                if self._on_state_change:
                    self._on_state_change(frame.data)
            if self._on_frame:
                self._on_frame(frame, self.state)
        return frame

    def _rewind_frame(self, count: int = 1) -> bool:
        result = self._replay.rewind(count)
        if result and self._on_state_change:
            self._on_state_change(self._replay.current_state)
        return result

    def _increase_speed(self):
        speeds = list(PlaybackSpeed)
        idx = speeds.index(self._speed)
        if idx < len(speeds) - 1:
            self._speed = speeds[idx + 1]

    def _decrease_speed(self):
        speeds = list(PlaybackSpeed)
        idx = speeds.index(self._speed)
        if idx > 0:
            self._speed = speeds[idx - 1]

    def step(self):
        return self._advance_frame()

    def play(self):
        self._playing = True

    def pause(self):
        self._playing = False

    def reset(self):
        self._replay.reset()
        self._current_turn = 0
        self._playing = False

    def get_frame_summary(self, frame: ReplayFrame) -> str:
        if frame.frame_type == FrameType.DECISION:
            decision = frame.data
            provider_name = self._replay.metadata.provider_names[decision.provider_index]
            action = ""
            if decision.decision_type == DecisionType.ATTACK:
                action = f"used attack '{decision.attack_index}'"
            elif decision.decision_type == DecisionType.ITEM:
                action = f"used item '{decision.item_name}'"
            elif decision.decision_type == DecisionType.RUN_AWAY:
                action = "tried to run away"
            elif decision.decision_type == DecisionType.CHOOSE_POKE:
                action = f"switched to poke #{decision.poke_index}"
            return f"Turn {decision.turn}: {provider_name} {action}"
        return f"Frame type: {frame.frame_type.name}"

    def get_battle_summary(self) -> str:
        meta = self._replay.metadata
        lines = [
            f"Battle: {' vs '.join(meta.provider_names)}",
            f"Type: {meta.battle_type}",
            f"Total turns: {meta.total_turns}",
        ]
        if meta.winner_index is not None:
            lines.append(f"Winner: {meta.provider_names[meta.winner_index]}")
        return "\n".join(lines)


@dataclass
class SimulatedPoke:
    identifier: str
    name: str
    hp: int
    full_hp: int
    xp: int
    atc: int
    defense: int
    initiative: int
    miss_chance: float
    attacks: list
    attack_aps: list
    attack_factors: list
    attack_miss_chances: list
    effects: list = field(default_factory=list)
    shiny: bool = False

    def to_snapshot(self) -> PokeSnapshot:
        return PokeSnapshot(
            identifier=self.identifier,
            name=self.name,
            hp=self.hp,
            full_hp=self.full_hp,
            xp=self.xp,
            attacks=self.attacks,
            attack_aps=self.attack_aps,
            effects=self.effects,
            shiny=self.shiny,
        )


@dataclass
class SimulatedProvider:
    name: str
    provider_type: str
    pokes: list
    play_index: int = 0
    escapable: bool = True
    xp_multiplier: int = 1

    @property
    def curr(self):
        return self.pokes[self.play_index]

    def to_snapshot(self) -> ProviderSnapshot:
        return ProviderSnapshot(
            provider_type=self.provider_type,
            name=self.name,
            play_index=self.play_index,
            pokes=[p.to_snapshot() for p in self.pokes],
            escapable=self.escapable,
            xp_multiplier=self.xp_multiplier,
        )


class BattleSimulator:
    def __init__(self, attack_data=None):
        self._attack_data = attack_data or {}
        self._random_index = 0
        self._random_values = []

    def _get_random(self) -> float:
        if self._random_index < len(self._random_values):
            value = self._random_values[self._random_index]
            self._random_index += 1
            return value
        return random.random()

    def _set_random_values(self, values: list):
        self._random_values = values
        self._random_index = 0

    def simulate_attack(self, attacker, defender, attack_index, random_values=None):
        if random_values:
            self._set_random_values(random_values)
        try:
            atk_idx = attacker.attacks.index(attack_index)
        except ValueError:
            return {"success": False, "error": f"Attack {attack_index} not found"}
        if attacker.attack_aps[atk_idx] <= 0:
            return {"success": False, "error": "No AP remaining"}
        factor = attacker.attack_factors[atk_idx]
        miss_chance = attacker.attack_miss_chances[atk_idx] + attacker.miss_chance
        random_factor = self._calculate_random_factor(miss_chance)
        if random_factor == 0:
            attacker.attack_aps[atk_idx] -= 1
            return {"success": True, "missed": True, "damage": 0, "defender_hp": defender.hp}
        defense = max(defender.defense, 1)
        damage = round((attacker.atc * factor / defense) * random_factor)
        defender.hp = max(defender.hp - damage, 0)
        attacker.attack_aps[atk_idx] -= 1
        return {
            "success": True,
            "missed": False,
            "damage": damage,
            "defender_hp": defender.hp,
            "random_factor": random_factor,
        }

    def _calculate_random_factor(self, miss_chance: float) -> float:
        r = self._get_random()
        if r < miss_chance:
            return 0
        choices = [0.75, 1, 1.26]
        idx = int(self._get_random() * len(choices))
        return choices[min(idx, len(choices) - 1)]


def run_ai_battle(p1_config, p2_config, attack_data, max_turns=100, seed=None):
    if seed is not None:
        random.seed(seed)

    def make_pokes(poke_configs):
        pokes = []
        for cfg in poke_configs:
            poke = SimulatedPoke(
                identifier=cfg["identifier"],
                name=cfg.get("name", cfg["identifier"]),
                hp=cfg.get("hp", 20),
                full_hp=cfg.get("hp", 20),
                xp=cfg.get("xp", 100),
                atc=cfg.get("atc", 10),
                defense=cfg.get("defense", 10),
                initiative=cfg.get("initiative", 10),
                miss_chance=cfg.get("miss_chance", 0.0),
                attacks=cfg.get("attacks", ["tackle"]),
                attack_aps=[15] * len(cfg.get("attacks", ["tackle"])),
                attack_factors=[
                    attack_data.get(a, {}).get("factor", 1.5)
                    for a in cfg.get("attacks", ["tackle"])
                ],
                attack_miss_chances=[
                    attack_data.get(a, {}).get("miss_chance", 0.2)
                    for a in cfg.get("attacks", ["tackle"])
                ],
            )
            pokes.append(poke)
        return pokes

    provider1 = SimulatedProvider(
        name=p1_config.get("name", "Player1"),
        provider_type=p1_config.get("type", "AI"),
        pokes=make_pokes(p1_config.get("pokes", [])),
        escapable=p1_config.get("escapable", False),
        xp_multiplier=p1_config.get("xp_multiplier", 1),
    )
    provider2 = SimulatedProvider(
        name=p2_config.get("name", "Player2"),
        provider_type=p2_config.get("type", "AI"),
        pokes=make_pokes(p2_config.get("pokes", [])),
        escapable=p2_config.get("escapable", False),
        xp_multiplier=p2_config.get("xp_multiplier", 1),
    )

    providers = [provider1, provider2]
    frames = []
    turn = 0

    initial_state = StateFrame(turn=0, providers=[p.to_snapshot() for p in providers])
    current_idx = 0 if provider1.curr.initiative >= provider2.curr.initiative else 1
    winner_index = None

    while turn < max_turns:
        attacker = providers[current_idx]
        defender = providers[(current_idx + 1) % 2]

        if attacker.curr.hp <= 0:
            alive_pokes = [i for i, p in enumerate(attacker.pokes) if p.hp > 0]
            if not alive_pokes:
                winner_index = (current_idx + 1) % 2
                break
            attacker.play_index = alive_pokes[0]
            frames.append(ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=turn,
                    provider_index=current_idx,
                    decision_type=DecisionType.CHOOSE_POKE,
                    poke_index=attacker.play_index,
                ),
            ))

        available_attacks = [
            (i, atk) for i, atk in enumerate(attacker.curr.attacks)
            if attacker.curr.attack_aps[i] > 0
        ]
        if not available_attacks:
            winner_index = (current_idx + 1) % 2
            break

        weights = [attacker.curr.attack_aps[i] for i, _ in available_attacks]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        chosen_idx = 0
        for i, (atk_idx, _) in enumerate(available_attacks):
            cumulative += weights[i]
            if r <= cumulative:
                chosen_idx = atk_idx
                break
        attack_name = attacker.curr.attacks[chosen_idx]
        random_values = [random.random(), random.random()]

        frames.append(ReplayFrame(
            frame_type=FrameType.DECISION,
            data=DecisionFrame(
                turn=turn,
                provider_index=current_idx,
                decision_type=DecisionType.ATTACK,
                attack_index=attack_name,
                random_values=random_values,
            ),
        ))

        factor = attacker.curr.attack_factors[chosen_idx]
        miss_chance = attacker.curr.attack_miss_chances[chosen_idx]

        if random_values[0] >= miss_chance:
            random_factors = [0.75, 1.0, 1.26]
            rf_idx = int(random_values[1] * len(random_factors))
            rf = random_factors[min(rf_idx, len(random_factors) - 1)]
            defense = max(defender.curr.defense, 1)
            damage = round((attacker.curr.atc * factor / defense) * rf)
            defender.curr.hp = max(defender.curr.hp - damage, 0)

        attacker.curr.attack_aps[chosen_idx] -= 1

        if turn % 5 == 0:
            frames.append(ReplayFrame(
                frame_type=FrameType.STATE_SNAPSHOT,
                data=StateFrame(turn=turn, providers=[p.to_snapshot() for p in providers]),
            ))

        if defender.curr.hp <= 0:
            alive_pokes = [i for i, p in enumerate(defender.pokes) if p.hp > 0]
            if not alive_pokes:
                winner_index = current_idx
                break

        turn += 1
        current_idx = (current_idx + 1) % 2

    final_state = StateFrame(turn=turn, providers=[p.to_snapshot() for p in providers])
    metadata = ReplayMetadata(
        version=ReplayVersion.current(),
        timestamp=datetime.now().isoformat(),
        battle_type="ai_vs_ai",
        provider_names=[p.name for p in providers],
        winner_index=winner_index,
        total_turns=turn,
    )

    return ReplayFormat(
        metadata=metadata,
        initial_state=initial_state,
        frames=frames,
        final_state=final_state,
    )


# ============================================================================
# TESTS
# ============================================================================

class TestReplayVersion(unittest.TestCase):
    def test_current_version(self):
        version = ReplayVersion.current()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_parse_version(self):
        major, minor, patch = ReplayVersion.parse("1.2.3")
        self.assertEqual(major, 1)
        self.assertEqual(minor, 2)
        self.assertEqual(patch, 3)

    def test_is_compatible_same_version(self):
        current = ReplayVersion.current()
        self.assertTrue(ReplayVersion.is_compatible(current))

    def test_is_compatible_older_minor(self):
        self.assertTrue(ReplayVersion.is_compatible("1.0.0"))

    def test_is_incompatible_different_major(self):
        self.assertFalse(ReplayVersion.is_compatible("0.1.0"))
        self.assertFalse(ReplayVersion.is_compatible("2.0.0"))


class TestPokeSnapshot(unittest.TestCase):
    def test_to_dict_and_from_dict(self):
        snapshot = PokeSnapshot(
            identifier="steini", name="Steini", hp=15, full_hp=20,
            xp=100, attacks=["tackle", "bite"], attack_aps=[10, 15],
            effects=["burning"], shiny=False,
        )
        data = snapshot.to_dict()
        restored = PokeSnapshot.from_dict(data)
        self.assertEqual(restored.identifier, "steini")
        self.assertEqual(restored.hp, 15)
        self.assertEqual(restored.effects, ["burning"])


class TestDecisionFrame(unittest.TestCase):
    def test_attack_decision(self):
        frame = DecisionFrame(
            turn=1, provider_index=0, decision_type=DecisionType.ATTACK,
            attack_index="tackle", random_values=[0.5, 0.8],
        )
        data = frame.to_dict()
        restored = DecisionFrame.from_dict(data)
        self.assertEqual(restored.turn, 1)
        self.assertEqual(restored.decision_type, DecisionType.ATTACK)
        self.assertEqual(restored.attack_index, "tackle")

    def test_item_decision(self):
        frame = DecisionFrame(
            turn=2, provider_index=0, decision_type=DecisionType.ITEM,
            item_name="heal_potion",
        )
        data = frame.to_dict()
        restored = DecisionFrame.from_dict(data)
        self.assertEqual(restored.decision_type, DecisionType.ITEM)
        self.assertEqual(restored.item_name, "heal_potion")

    def test_switch_poke_decision(self):
        frame = DecisionFrame(
            turn=3, provider_index=0, decision_type=DecisionType.CHOOSE_POKE,
            poke_index=1,
        )
        data = frame.to_dict()
        restored = DecisionFrame.from_dict(data)
        self.assertEqual(restored.decision_type, DecisionType.CHOOSE_POKE)
        self.assertEqual(restored.poke_index, 1)


class TestReplayFormat(unittest.TestCase):
    def _create_test_replay(self):
        poke1 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        poke2 = PokeSnapshot(
            identifier="poundi", name="Poundi", hp=25, full_hp=25,
            xp=150, attacks=["bite"], attack_aps=[20], effects=[], shiny=False,
        )
        provider1 = ProviderSnapshot(
            provider_type="ProtoFigure", name="Player",
            play_index=0, pokes=[poke1], escapable=True, xp_multiplier=1,
        )
        provider2 = ProviderSnapshot(
            provider_type="NatureProvider", name="Wild",
            play_index=0, pokes=[poke2], escapable=True, xp_multiplier=1,
        )
        initial_state = StateFrame(turn=0, providers=[provider1, provider2])
        frames = [
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=0, provider_index=0, decision_type=DecisionType.ATTACK,
                    attack_index="tackle", random_values=[0.5, 0.7],
                ),
            ),
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=1, provider_index=1, decision_type=DecisionType.ATTACK,
                    attack_index="bite", random_values=[0.3, 0.5],
                ),
            ),
        ]
        metadata = ReplayMetadata(
            version=ReplayVersion.current(),
            timestamp=datetime.now().isoformat(),
            battle_type="wild",
            provider_names=["Player", "Wild"],
            winner_index=0,
            total_turns=2,
        )
        return ReplayFormat(
            metadata=metadata,
            initial_state=initial_state,
            frames=frames,
            final_state=None,
        )

    def test_to_json_and_from_json(self):
        replay = self._create_test_replay()
        json_str = replay.to_json()
        restored = ReplayFormat.from_json(json_str)
        self.assertEqual(restored.metadata.battle_type, "wild")
        self.assertEqual(len(restored.frames), 2)

    def test_save_and_load_uncompressed(self):
        replay = self._create_test_replay()
        with tempfile.NamedTemporaryFile(suffix=".pokereplay", delete=False) as f:
            filepath = f.name
        try:
            replay.save(filepath, compress=False)
            loaded = ReplayFormat.load(filepath)
            self.assertEqual(loaded.metadata.battle_type, "wild")
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_and_load_compressed(self):
        replay = self._create_test_replay()
        with tempfile.NamedTemporaryFile(suffix=".pokereplay.gz", delete=False) as f:
            filepath = f.name
        try:
            replay.save(filepath, compress=True)
            loaded = ReplayFormat.load(filepath)
            self.assertEqual(loaded.metadata.battle_type, "wild")
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_validate_valid_replay(self):
        replay = self._create_test_replay()
        valid, errors = replay.validate()
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_incompatible_version(self):
        replay = self._create_test_replay()
        replay.metadata.version = "0.1.0"
        valid, errors = replay.validate()
        self.assertFalse(valid)
        self.assertTrue(any("Incompatible version" in e for e in errors))


class TestBattleReplay(unittest.TestCase):
    def _create_test_replay_format(self):
        poke1 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        poke2 = PokeSnapshot(
            identifier="poundi", name="Poundi", hp=25, full_hp=25,
            xp=150, attacks=["bite"], attack_aps=[20], effects=[], shiny=False,
        )
        provider1 = ProviderSnapshot(
            provider_type="ProtoFigure", name="Player",
            play_index=0, pokes=[poke1], escapable=True, xp_multiplier=1,
        )
        provider2 = ProviderSnapshot(
            provider_type="NatureProvider", name="Wild",
            play_index=0, pokes=[poke2], escapable=True, xp_multiplier=1,
        )
        initial_state = StateFrame(turn=0, providers=[provider1, provider2])
        frames = [
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=0, provider_index=0, decision_type=DecisionType.ATTACK,
                    attack_index="tackle", random_values=[0.5, 0.7],
                ),
            ),
            ReplayFrame(
                frame_type=FrameType.STATE_SNAPSHOT,
                data=StateFrame(turn=0, providers=[provider1, provider2]),
            ),
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=1, provider_index=1, decision_type=DecisionType.ATTACK,
                    attack_index="bite", random_values=[0.3, 0.5],
                ),
            ),
        ]
        metadata = ReplayMetadata(
            version=ReplayVersion.current(),
            timestamp=datetime.now().isoformat(),
            battle_type="wild",
            provider_names=["Player", "Wild"],
            winner_index=0,
            total_turns=2,
        )
        return ReplayFormat(
            metadata=metadata,
            initial_state=initial_state,
            frames=frames,
            final_state=None,
        )

    def test_advance_frame(self):
        replay = BattleReplay(self._create_test_replay_format())
        self.assertEqual(replay.current_frame_index, 0)
        frame = replay.advance()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.frame_type, FrameType.DECISION)
        self.assertEqual(replay.current_frame_index, 1)

    def test_rewind(self):
        replay = BattleReplay(self._create_test_replay_format())
        replay.advance()
        replay.advance()
        self.assertEqual(replay.current_frame_index, 2)
        replay.rewind(1)
        self.assertEqual(replay.current_frame_index, 1)

    def test_seek(self):
        replay = BattleReplay(self._create_test_replay_format())
        replay.seek(2)
        self.assertEqual(replay.current_frame_index, 2)
        replay.seek(0)
        self.assertEqual(replay.current_frame_index, 0)

    def test_reset(self):
        replay = BattleReplay(self._create_test_replay_format())
        replay.advance()
        replay.advance()
        replay.reset()
        self.assertEqual(replay.current_frame_index, 0)
        self.assertFalse(replay.is_finished)

    def test_get_decision_frames(self):
        replay = BattleReplay(self._create_test_replay_format())
        decisions = replay.get_decision_frames()
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0].attack_index, "tackle")

    def test_iter_frames(self):
        replay = BattleReplay(self._create_test_replay_format())
        frames = list(replay.iter_frames())
        self.assertEqual(len(frames), 3)
        self.assertTrue(replay.is_finished)


class TestReplayValidator(unittest.TestCase):
    def test_compare_identical_poke_states(self):
        poke1 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        poke2 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        diffs = ReplayValidator.compare_poke_states(poke1, poke2)
        self.assertEqual(len(diffs), 0)

    def test_compare_different_hp(self):
        poke1 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        poke2 = PokeSnapshot(
            identifier="steini", name="Steini", hp=15, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        diffs = ReplayValidator.compare_poke_states(poke1, poke2)
        self.assertEqual(len(diffs), 1)
        self.assertIn("HP mismatch", diffs[0])


class TestSpectatorMode(unittest.TestCase):
    def _create_test_replay(self):
        poke1 = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        poke2 = PokeSnapshot(
            identifier="poundi", name="Poundi", hp=25, full_hp=25,
            xp=150, attacks=["bite"], attack_aps=[20], effects=[], shiny=False,
        )
        provider1 = ProviderSnapshot(
            provider_type="ProtoFigure", name="Player",
            play_index=0, pokes=[poke1], escapable=True, xp_multiplier=1,
        )
        provider2 = ProviderSnapshot(
            provider_type="NatureProvider", name="Wild",
            play_index=0, pokes=[poke2], escapable=True, xp_multiplier=1,
        )
        initial_state = StateFrame(turn=0, providers=[provider1, provider2])
        frames = [
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=0, provider_index=0, decision_type=DecisionType.ATTACK,
                    attack_index="tackle", random_values=[0.5, 0.7],
                ),
            ),
            ReplayFrame(
                frame_type=FrameType.DECISION,
                data=DecisionFrame(
                    turn=1, provider_index=1, decision_type=DecisionType.ATTACK,
                    attack_index="bite", random_values=[0.3, 0.5],
                ),
            ),
        ]
        metadata = ReplayMetadata(
            version=ReplayVersion.current(),
            timestamp=datetime.now().isoformat(),
            battle_type="wild",
            provider_names=["Player", "Wild"],
            winner_index=0,
            total_turns=2,
        )
        replay_format = ReplayFormat(
            metadata=metadata,
            initial_state=initial_state,
            frames=frames,
            final_state=None,
        )
        return BattleReplay(replay_format)

    def test_step_through_frames(self):
        replay = self._create_test_replay()
        spectator = SpectatorMode(replay)
        frame = spectator.step()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.frame_type, FrameType.DECISION)

    def test_play_pause(self):
        replay = self._create_test_replay()
        spectator = SpectatorMode(replay)
        self.assertFalse(spectator.is_playing)
        spectator.play()
        self.assertTrue(spectator.is_playing)
        spectator.pause()
        self.assertFalse(spectator.is_playing)

    def test_speed_changes(self):
        replay = self._create_test_replay()
        spectator = SpectatorMode(replay)
        self.assertEqual(spectator.state.speed, PlaybackSpeed.NORMAL)
        spectator.queue_command(SpectatorCommand.SPEED_UP)
        spectator._process_commands()
        self.assertEqual(spectator.state.speed, PlaybackSpeed.FAST)

    def test_get_frame_summary(self):
        replay = self._create_test_replay()
        spectator = SpectatorMode(replay)
        frame = spectator.step()
        summary = spectator.get_frame_summary(frame)
        self.assertIn("Player", summary)
        self.assertIn("tackle", summary)


class TestSimulation(unittest.TestCase):
    def test_simulated_poke_to_snapshot(self):
        poke = SimulatedPoke(
            identifier="steini", name="Steini", hp=15, full_hp=20,
            xp=100, atc=10, defense=10, initiative=10, miss_chance=0,
            attacks=["tackle"], attack_aps=[14],
            attack_factors=[1.5], attack_miss_chances=[0.2],
            effects=["burning"], shiny=False,
        )
        snapshot = poke.to_snapshot()
        self.assertEqual(snapshot.identifier, "steini")
        self.assertEqual(snapshot.hp, 15)
        self.assertEqual(snapshot.effects, ["burning"])

    def test_simulate_attack_hit(self):
        attacker = SimulatedPoke(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, atc=10, defense=10, initiative=10, miss_chance=0,
            attacks=["tackle"], attack_aps=[15],
            attack_factors=[1.5], attack_miss_chances=[0.0],
        )
        defender = SimulatedPoke(
            identifier="poundi", name="Poundi", hp=25, full_hp=25,
            xp=100, atc=10, defense=10, initiative=10, miss_chance=0,
            attacks=["bite"], attack_aps=[20],
            attack_factors=[1.75], attack_miss_chances=[0.1],
        )
        simulator = BattleSimulator()
        result = simulator.simulate_attack(attacker, defender, "tackle", [0.5, 0.5])
        self.assertTrue(result["success"])
        self.assertFalse(result["missed"])
        self.assertGreater(result["damage"], 0)
        self.assertEqual(attacker.attack_aps[0], 14)

    def test_simulate_attack_miss(self):
        attacker = SimulatedPoke(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, atc=10, defense=10, initiative=10, miss_chance=0,
            attacks=["tackle"], attack_aps=[15],
            attack_factors=[1.5], attack_miss_chances=[1.0],
        )
        defender = SimulatedPoke(
            identifier="poundi", name="Poundi", hp=25, full_hp=25,
            xp=100, atc=10, defense=10, initiative=10, miss_chance=0,
            attacks=["bite"], attack_aps=[20],
            attack_factors=[1.75], attack_miss_chances=[0.1],
        )
        simulator = BattleSimulator()
        result = simulator.simulate_attack(attacker, defender, "tackle", [0.0])
        self.assertTrue(result["success"])
        self.assertTrue(result["missed"])
        self.assertEqual(result["damage"], 0)

    def test_run_ai_battle(self):
        attack_data = {
            "tackle": {"factor": 1.5, "miss_chance": 0.2},
            "bite": {"factor": 1.75, "miss_chance": 0.1},
        }
        p1_config = {
            "name": "Player1",
            "pokes": [{
                "identifier": "steini", "hp": 30, "atc": 12, "defense": 10,
                "initiative": 15, "attacks": ["tackle"],
            }],
        }
        p2_config = {
            "name": "Player2",
            "pokes": [{
                "identifier": "poundi", "hp": 25, "atc": 10, "defense": 8,
                "initiative": 10, "attacks": ["bite"],
            }],
        }
        replay = run_ai_battle(p1_config, p2_config, attack_data, seed=42)
        self.assertIsInstance(replay, ReplayFormat)
        self.assertIn(replay.metadata.winner_index, [0, 1, None])
        self.assertGreater(len(replay.frames), 0)


class TestSchemaMigration(unittest.TestCase):
    def test_migrate_old_version(self):
        old_data = {
            "metadata": {
                "version": "0.1.0",
                "timestamp": "2024-01-01T00:00:00",
                "battle_type": "wild",
                "provider_names": ["Player", "Wild"],
                "winner_index": 0,
                "total_turns": 5,
            },
            "initial_state": {"turn": 0, "providers": []},
            "frames": [],
            "final_state": None,
        }
        migrated = ReplayMigrator.migrate(old_data)
        self.assertEqual(migrated["metadata"]["version"], ReplayVersion.current())

    def test_load_after_schema_change(self):
        poke = PokeSnapshot(
            identifier="steini", name="Steini", hp=20, full_hp=20,
            xp=100, attacks=["tackle"], attack_aps=[15], effects=[], shiny=False,
        )
        provider = ProviderSnapshot(
            provider_type="NatureProvider", name="Wild",
            play_index=0, pokes=[poke], escapable=True, xp_multiplier=1,
        )
        state = StateFrame(turn=0, providers=[provider])
        replay = ReplayFormat(
            metadata=ReplayMetadata(
                version=ReplayVersion.current(),
                timestamp=datetime.now().isoformat(),
                battle_type="test",
                provider_names=["Wild"],
                winner_index=0,
                total_turns=1,
            ),
            initial_state=state,
            frames=[],
            final_state=state,
        )
        with tempfile.NamedTemporaryFile(suffix=".pokereplay", delete=False) as f:
            filepath = f.name
        try:
            replay.save(filepath, compress=False)
            loaded = ReplayFormat.load(filepath)
            self.assertEqual(loaded.metadata.battle_type, "test")
            self.assertEqual(loaded.initial_state.providers[0].pokes[0].identifier, "steini")
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


class TestDeterministicReplay(unittest.TestCase):
    """Test that replay produces identical outcomes"""

    def test_deterministic_battle_outcome(self):
        """Run same battle twice with same seed, verify identical results"""
        attack_data = {
            "tackle": {"factor": 1.5, "miss_chance": 0.1},
        }
        p1_config = {
            "name": "Player1",
            "pokes": [{
                "identifier": "steini", "hp": 50, "atc": 15, "defense": 10,
                "initiative": 12, "attacks": ["tackle"],
            }],
        }
        p2_config = {
            "name": "Player2",
            "pokes": [{
                "identifier": "poundi", "hp": 45, "atc": 12, "defense": 12,
                "initiative": 10, "attacks": ["tackle"],
            }],
        }

        replay1 = run_ai_battle(p1_config, p2_config, attack_data, seed=12345, max_turns=50)
        replay2 = run_ai_battle(p1_config, p2_config, attack_data, seed=12345, max_turns=50)

        # Same winner
        self.assertEqual(replay1.metadata.winner_index, replay2.metadata.winner_index)

        # Same number of turns
        self.assertEqual(replay1.metadata.total_turns, replay2.metadata.total_turns)

        # Same frames
        self.assertEqual(len(replay1.frames), len(replay2.frames))

        # Same final HP values
        if replay1.final_state and replay2.final_state:
            for i in range(len(replay1.final_state.providers)):
                for j in range(len(replay1.final_state.providers[i].pokes)):
                    self.assertEqual(
                        replay1.final_state.providers[i].pokes[j].hp,
                        replay2.final_state.providers[i].pokes[j].hp,
                    )

    def test_replay_file_roundtrip_preserves_data(self):
        """Save and load replay, verify data integrity"""
        attack_data = {"tackle": {"factor": 1.5, "miss_chance": 0.1}}
        p1_config = {
            "name": "Player1",
            "pokes": [{"identifier": "steini", "hp": 30, "attacks": ["tackle"]}],
        }
        p2_config = {
            "name": "Player2",
            "pokes": [{"identifier": "poundi", "hp": 30, "attacks": ["tackle"]}],
        }

        original = run_ai_battle(p1_config, p2_config, attack_data, seed=999)

        with tempfile.NamedTemporaryFile(suffix=".pokereplay.gz", delete=False) as f:
            filepath = f.name

        try:
            original.save(filepath, compress=True)
            loaded = ReplayFormat.load(filepath)

            # Verify metadata
            self.assertEqual(original.metadata.version, loaded.metadata.version)
            self.assertEqual(original.metadata.winner_index, loaded.metadata.winner_index)
            self.assertEqual(original.metadata.total_turns, loaded.metadata.total_turns)

            # Verify initial state
            self.assertEqual(
                len(original.initial_state.providers),
                len(loaded.initial_state.providers)
            )

            # Verify frames
            self.assertEqual(len(original.frames), len(loaded.frames))

            # Verify all decision frames match
            orig_decisions = [f.data for f in original.frames if f.frame_type == FrameType.DECISION]
            load_decisions = [f.data for f in loaded.frames if f.frame_type == FrameType.DECISION]

            for orig, load in zip(orig_decisions, load_decisions):
                self.assertEqual(orig.turn, load.turn)
                self.assertEqual(orig.provider_index, load.provider_index)
                self.assertEqual(orig.decision_type, load.decision_type)
                self.assertEqual(orig.attack_index, load.attack_index)
                self.assertEqual(orig.random_values, load.random_values)

        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


if __name__ == "__main__":
    unittest.main()
