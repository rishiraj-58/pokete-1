"""Tests for replay format serialization and versioning"""

import unittest
import tempfile
import os
from datetime import datetime

from pokete.classes.replay.replay_format import (
    ReplayFormat,
    ReplayVersion,
    ReplayEvent,
    ReplayEventType,
    ReplayMetadata,
    ProviderRecord,
    PokeStateRecord,
    ReplayLoadError,
    migrate_replay,
)


class TestReplayVersion(unittest.TestCase):
    def test_current_version(self):
        version = ReplayVersion.current()
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 0)
        self.assertEqual(version.patch, 0)

    def test_version_to_string(self):
        version = ReplayVersion(1, 2, 3)
        self.assertEqual(str(version), "1.2.3")

    def test_version_equality(self):
        v1 = ReplayVersion(1, 0, 0)
        v2 = ReplayVersion(1, 0, 0)
        v3 = ReplayVersion(1, 0, 1)

        self.assertEqual(v1, v2)
        self.assertNotEqual(v1, v3)

    def test_version_comparison(self):
        v1 = ReplayVersion(1, 0, 0)
        v2 = ReplayVersion(1, 1, 0)
        v3 = ReplayVersion(2, 0, 0)

        self.assertTrue(v2 > v1)
        self.assertTrue(v3 > v2)
        self.assertTrue(v1 < v2)
        self.assertFalse(v1 > v1)

    def test_version_compatibility(self):
        v1 = ReplayVersion(1, 0, 0)
        v2 = ReplayVersion(1, 5, 3)
        v3 = ReplayVersion(2, 0, 0)

        self.assertTrue(v1.is_compatible(v2))
        self.assertFalse(v1.is_compatible(v3))

    def test_version_serialization(self):
        version = ReplayVersion(1, 2, 3)
        data = version.to_dict()
        restored = ReplayVersion.from_dict(data)

        self.assertEqual(version, restored)


class TestReplayEvent(unittest.TestCase):
    def test_event_creation(self):
        event = ReplayEvent(
            event_type=ReplayEventType.ATTACK_EXECUTED,
            turn_number=5,
            provider_index=0,
            data={"damage": 10},
            timestamp_ms=1000,
        )

        self.assertEqual(event.event_type, ReplayEventType.ATTACK_EXECUTED)
        self.assertEqual(event.turn_number, 5)
        self.assertEqual(event.provider_index, 0)
        self.assertEqual(event.data["damage"], 10)

    def test_event_serialization(self):
        event = ReplayEvent(
            event_type=ReplayEventType.HP_CHANGED,
            turn_number=3,
            provider_index=1,
            data={"old_hp": 20, "new_hp": 15, "delta": -5},
            timestamp_ms=500,
        )

        data = event.to_dict()
        restored = ReplayEvent.from_dict(data)

        self.assertEqual(event.event_type, restored.event_type)
        self.assertEqual(event.turn_number, restored.turn_number)
        self.assertEqual(event.provider_index, restored.provider_index)
        self.assertEqual(event.data, restored.data)


class TestPokeStateRecord(unittest.TestCase):
    def test_poke_state_creation(self):
        poke = PokeStateRecord(
            identifier="steini",
            name="Steini",
            hp=25,
            max_hp=25,
            xp=100,
            level=10,
            attacks=["tackle", "stone_crush"],
            attack_aps=[30, 15],
            effects=["burning"],
            shiny=False,
        )

        self.assertEqual(poke.identifier, "steini")
        self.assertEqual(poke.hp, 25)
        self.assertEqual(len(poke.attacks), 2)

    def test_poke_state_serialization(self):
        poke = PokeStateRecord(
            identifier="mowcow",
            name="Mowcow",
            hp=18,
            max_hp=20,
            xp=50,
            level=7,
            attacks=["tackle"],
            attack_aps=[28],
            effects=[],
            shiny=True,
        )

        data = poke.to_dict()
        restored = PokeStateRecord.from_dict(data)

        self.assertEqual(poke.identifier, restored.identifier)
        self.assertEqual(poke.hp, restored.hp)
        self.assertEqual(poke.shiny, restored.shiny)


class TestProviderRecord(unittest.TestCase):
    def test_provider_record_creation(self):
        poke = PokeStateRecord(
            identifier="steini",
            name="Steini",
            hp=25,
            max_hp=25,
            xp=100,
            level=10,
            attacks=["tackle"],
            attack_aps=[30],
            effects=[],
            shiny=False,
        )

        provider = ProviderRecord(
            provider_type="NatureProvider",
            name="Wild",
            pokes=[poke],
            current_poke_index=0,
            escapable=True,
        )

        self.assertEqual(provider.provider_type, "NatureProvider")
        self.assertEqual(len(provider.pokes), 1)

    def test_provider_record_serialization(self):
        poke = PokeStateRecord(
            identifier="steini",
            name="Steini",
            hp=25,
            max_hp=25,
            xp=100,
            level=10,
            attacks=["tackle"],
            attack_aps=[30],
            effects=[],
            shiny=False,
        )

        provider = ProviderRecord(
            provider_type="Trainer",
            name="Gary",
            pokes=[poke],
            current_poke_index=0,
            escapable=False,
        )

        data = provider.to_dict()
        restored = ProviderRecord.from_dict(data)

        self.assertEqual(provider.name, restored.name)
        self.assertEqual(provider.escapable, restored.escapable)


class TestReplayFormat(unittest.TestCase):
    def _create_sample_replay(self) -> ReplayFormat:
        poke1 = PokeStateRecord(
            identifier="steini",
            name="Steini",
            hp=25,
            max_hp=25,
            xp=100,
            level=10,
            attacks=["tackle", "stone_crush"],
            attack_aps=[30, 15],
            effects=[],
            shiny=False,
        )

        poke2 = PokeStateRecord(
            identifier="mowcow",
            name="Mowcow",
            hp=20,
            max_hp=20,
            xp=50,
            level=7,
            attacks=["tackle"],
            attack_aps=[30],
            effects=[],
            shiny=False,
        )

        provider1 = ProviderRecord(
            provider_type="ProtoFigure",
            name="Player",
            pokes=[poke1],
            current_poke_index=0,
            escapable=True,
        )

        provider2 = ProviderRecord(
            provider_type="NatureProvider",
            name="Wild",
            pokes=[poke2],
            current_poke_index=0,
            escapable=True,
        )

        metadata = ReplayMetadata(
            recorded_at=datetime.now().isoformat(),
            duration_ms=30000,
            total_turns=5,
            winner_index=0,
            battle_type="wild",
            random_seed=12345,
        )

        events = [
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_START,
                turn_number=0,
                provider_index=-1,
                data={"battle_type": "wild"},
            ),
            ReplayEvent(
                event_type=ReplayEventType.TURN_START,
                turn_number=1,
                provider_index=0,
                data={"turn": 1},
            ),
            ReplayEvent(
                event_type=ReplayEventType.ATTACK_EXECUTED,
                turn_number=1,
                provider_index=0,
                data={"attack_name": "tackle", "damage": 5},
            ),
            ReplayEvent(
                event_type=ReplayEventType.HP_CHANGED,
                turn_number=1,
                provider_index=1,
                data={"old_hp": 20, "new_hp": 15, "delta": -5},
            ),
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_END,
                turn_number=5,
                provider_index=0,
                data={"winner": 0},
            ),
        ]

        return ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=[provider1, provider2],
            events=events,
        )

    def test_replay_creation(self):
        replay = self._create_sample_replay()

        self.assertEqual(len(replay.initial_state), 2)
        self.assertEqual(len(replay.events), 5)
        self.assertEqual(replay.metadata.total_turns, 5)

    def test_replay_dict_serialization(self):
        replay = self._create_sample_replay()
        data = replay.to_dict()

        self.assertIn("v", data)
        self.assertIn("meta", data)
        self.assertIn("init", data)
        self.assertIn("events", data)

        restored = ReplayFormat.from_dict(data)
        self.assertEqual(len(restored.events), len(replay.events))
        self.assertEqual(restored.metadata.total_turns, replay.metadata.total_turns)

    def test_replay_file_save_load_compressed(self):
        replay = self._create_sample_replay()

        with tempfile.NamedTemporaryFile(suffix=".replay", delete=False) as f:
            temp_path = f.name

        try:
            replay.save_to_file(temp_path, compress=True)
            loaded = ReplayFormat.load_from_file(temp_path)

            self.assertEqual(len(loaded.events), len(replay.events))
            self.assertEqual(loaded.version, replay.version)
        finally:
            os.unlink(temp_path)

    def test_replay_file_save_load_uncompressed(self):
        replay = self._create_sample_replay()

        with tempfile.NamedTemporaryFile(suffix=".replay", delete=False) as f:
            temp_path = f.name

        try:
            replay.save_to_file(temp_path, compress=False)
            loaded = ReplayFormat.load_from_file(temp_path)

            self.assertEqual(len(loaded.events), len(replay.events))
        finally:
            os.unlink(temp_path)

    def test_replay_base64_serialization(self):
        replay = self._create_sample_replay()
        encoded = replay.to_base64()
        decoded = ReplayFormat.from_base64(encoded)

        self.assertEqual(len(decoded.events), len(replay.events))
        self.assertEqual(decoded.metadata.winner_index, replay.metadata.winner_index)

    def test_replay_validation_success(self):
        replay = self._create_sample_replay()
        issues = replay.validate()

        self.assertEqual(len(issues), 0)

    def test_replay_validation_missing_providers(self):
        replay = self._create_sample_replay()
        replay.initial_state = []

        issues = replay.validate()
        self.assertTrue(any("No initial state" in issue for issue in issues))

    def test_replay_validation_wrong_provider_count(self):
        replay = self._create_sample_replay()
        replay.initial_state = [replay.initial_state[0]]

        issues = replay.validate()
        self.assertTrue(any("Expected 2 providers" in issue for issue in issues))


class TestReplayMigration(unittest.TestCase):
    def test_migrate_same_version(self):
        replay = TestReplayFormat()._create_sample_replay()
        migrated = migrate_replay(replay, ReplayVersion.current())

        self.assertEqual(migrated.version, replay.version)

    def test_migrate_to_newer_version(self):
        replay = TestReplayFormat()._create_sample_replay()
        replay.version = ReplayVersion(1, 0, 0)

        target = ReplayVersion(1, 1, 0)
        migrated = migrate_replay(replay, target)

        self.assertEqual(migrated.version, target)


if __name__ == "__main__":
    unittest.main()
