"""Tests for the battle recorder"""

import unittest
from unittest.mock import MagicMock, PropertyMock
from datetime import datetime

from pokete.classes.replay.recorder import BattleRecorder, RecordingError
from pokete.classes.replay.replay_format import ReplayEventType


class MockPoke:
    """Mock Poke for testing"""

    def __init__(
        self,
        identifier: str = "steini",
        name: str = "Steini",
        hp: int = 25,
        full_hp: int = 25,
        xp: int = 100,
        shiny: bool = False,
    ):
        self.identifier = identifier
        self.name = name
        self.hp = hp
        self.full_hp = full_hp
        self.xp = xp
        self.shiny = shiny
        self.atc = 5
        self.defense = 5
        self.initiative = 5
        self.miss_chance = 0.1
        self.attacks = ["tackle", "stone_crush"]
        self.attack_obs = [MockAttack("tackle", 30), MockAttack("stone_crush", 15)]
        self.effects = []

    def lvl(self):
        return int((self.xp + 1) ** 0.5)


class MockAttack:
    """Mock Attack for testing"""

    def __init__(self, index: str, ap: int):
        self.index = index
        self.name = index.replace("_", " ").title()
        self.ap = ap
        self.max_ap = ap


class MockProvider:
    """Mock Provider for testing"""

    def __init__(
        self,
        pokes: list[MockPoke] | None = None,
        name: str = "TestProvider",
        escapable: bool = True,
    ):
        self.pokes = pokes or [MockPoke()]
        self.play_index = 0
        self.escapable = escapable
        self.name = name

    @property
    def curr(self):
        return self.pokes[self.play_index]


class MockItem:
    """Mock InvItem for testing"""

    def __init__(self, name: str = "potion", func: str = "heal_potion"):
        self.name = name
        self.func = func


class TestBattleRecorder(unittest.TestCase):
    def test_recorder_initialization(self):
        recorder = BattleRecorder()
        self.assertFalse(recorder.is_recording)
        self.assertEqual(recorder.turn_number, 0)
        self.assertEqual(len(recorder.events), 0)

    def test_recorder_with_seed(self):
        recorder = BattleRecorder(seed=12345)
        self.assertFalse(recorder.is_recording)

    def test_start_recording(self):
        recorder = BattleRecorder()
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        recorder.start_recording([provider1, provider2])

        self.assertTrue(recorder.is_recording)
        self.assertEqual(len(recorder.events), 1)  # BATTLE_START event
        self.assertEqual(
            recorder.events[0].event_type, ReplayEventType.BATTLE_START
        )

    def test_start_recording_while_recording_raises(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])

        with self.assertRaises(RecordingError):
            recorder.start_recording([provider1, provider2])

    def test_stop_recording(self):
        recorder = BattleRecorder()
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        recorder.start_recording([provider1, provider2])
        replay = recorder.stop_recording(winner_index=0)

        self.assertFalse(recorder.is_recording)
        self.assertIsNotNone(replay)
        self.assertEqual(replay.metadata.winner_index, 0)
        self.assertEqual(len(replay.initial_state), 2)

    def test_stop_recording_not_recording_raises(self):
        recorder = BattleRecorder()

        with self.assertRaises(RecordingError):
            recorder.stop_recording()

    def test_record_turn_start(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_turn_start(0)

        self.assertEqual(recorder.turn_number, 1)
        turn_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.TURN_START
        ]
        self.assertEqual(len(turn_events), 1)
        self.assertEqual(turn_events[0].data["turn"], 1)

    def test_record_attack_chosen(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()
        attack = MockAttack("tackle", 30)

        recorder.start_recording([provider1, provider2])
        recorder.record_attack_chosen(0, attack, 1)

        attack_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.ATTACK_CHOSEN
        ]
        self.assertEqual(len(attack_events), 1)
        self.assertEqual(attack_events[0].data["attack_index"], "tackle")

    def test_record_attack_executed(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()
        attack = MockAttack("tackle", 30)

        recorder.start_recording([provider1, provider2])
        recorder.record_attack_executed(
            provider_index=0,
            attack=attack,
            target_provider_index=1,
            damage=10,
            effectiveness=1.0,
            random_factor=1.0,
            attacker_hp_before=25,
            defender_hp_before=20,
            attacker_hp_after=25,
            defender_hp_after=10,
        )

        attack_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.ATTACK_EXECUTED
        ]
        self.assertEqual(len(attack_events), 1)
        self.assertEqual(attack_events[0].data["damage"], 10)
        self.assertEqual(attack_events[0].data["defender_hp_after"], 10)

    def test_record_item_used(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()
        item = MockItem()

        recorder.start_recording([provider1, provider2])
        recorder.record_item_used(0, item, target_poke_index=0)

        item_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.ITEM_USED
        ]
        self.assertEqual(len(item_events), 1)
        self.assertEqual(item_events[0].data["item_name"], "potion")

    def test_record_poke_switch(self):
        recorder = BattleRecorder()
        provider1 = MockProvider(pokes=[MockPoke(), MockPoke(identifier="mowcow")])
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_poke_switch(0, 0, 1, reason="manual")

        switch_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.POKE_SWITCHED
        ]
        self.assertEqual(len(switch_events), 1)
        self.assertEqual(switch_events[0].data["from_index"], 0)
        self.assertEqual(switch_events[0].data["to_index"], 1)

    def test_record_run_attempt_success(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_run_attempt(0, success=True)

        run_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.RUN_AWAY_SUCCESS
        ]
        self.assertEqual(len(run_events), 1)

    def test_record_run_attempt_failed(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_run_attempt(0, success=False)

        run_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.RUN_AWAY_FAILED
        ]
        self.assertEqual(len(run_events), 1)

    def test_record_effect_applied(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_effect_applied(1, 0, "burning")

        effect_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.EFFECT_APPLIED
        ]
        self.assertEqual(len(effect_events), 1)
        self.assertEqual(effect_events[0].data["effect"], "burning")

    def test_record_effect_removed(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_effect_removed(1, 0, "burning")

        effect_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.EFFECT_REMOVED
        ]
        self.assertEqual(len(effect_events), 1)

    def test_record_hp_change(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_hp_change(1, 0, 20, 15, reason="damage")

        hp_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.HP_CHANGED
        ]
        self.assertEqual(len(hp_events), 1)
        self.assertEqual(hp_events[0].data["old_hp"], 20)
        self.assertEqual(hp_events[0].data["new_hp"], 15)
        self.assertEqual(hp_events[0].data["delta"], -5)

    def test_record_ap_change(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_ap_change(0, 0, 0, 30, 29)

        ap_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.AP_CHANGED
        ]
        self.assertEqual(len(ap_events), 1)
        self.assertEqual(ap_events[0].data["old_ap"], 30)
        self.assertEqual(ap_events[0].data["new_ap"], 29)

    def test_record_poke_fainted(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_poke_fainted(1, 0)

        faint_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.POKE_FAINTED
        ]
        self.assertEqual(len(faint_events), 1)

    def test_record_xp_gained(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_xp_gained(0, 0, xp_gained=50, new_total_xp=150)

        xp_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.XP_GAINED
        ]
        self.assertEqual(len(xp_events), 1)
        self.assertEqual(xp_events[0].data["xp_gained"], 50)

    def test_record_level_up(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_level_up(0, 0, old_level=10, new_level=11)

        level_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.LEVEL_UP
        ]
        self.assertEqual(len(level_events), 1)
        self.assertEqual(level_events[0].data["new_level"], 11)

    def test_record_catch_attempt_success(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_catch_attempt(0, 1, "poketeball", success=True)

        catch_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.CATCH_SUCCESS
        ]
        self.assertEqual(len(catch_events), 1)

    def test_record_catch_attempt_failed(self):
        recorder = BattleRecorder()
        provider1 = MockProvider()
        provider2 = MockProvider()

        recorder.start_recording([provider1, provider2])
        recorder.record_catch_attempt(0, 1, "poketeball", success=False)

        catch_events = [
            e for e in recorder.events
            if e.event_type == ReplayEventType.CATCH_FAILED
        ]
        self.assertEqual(len(catch_events), 1)

    def test_full_battle_recording(self):
        """Test recording a complete battle flow"""
        recorder = BattleRecorder(seed=42)
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Wild")
        attack = MockAttack("tackle", 30)

        # Start battle
        recorder.start_recording([provider1, provider2], battle_type="wild")

        # Turn 1 - Player attacks
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        recorder.record_attack_executed(
            0, attack, 1,
            damage=5, effectiveness=1.0, random_factor=1.0,
            attacker_hp_before=25, defender_hp_before=20,
            attacker_hp_after=25, defender_hp_after=15
        )
        recorder.record_hp_change(1, 0, 20, 15, "damage")
        recorder.record_ap_change(0, 0, 0, 30, 29)

        # Turn 2 - Enemy attacks
        recorder.record_turn_start(1)
        recorder.record_attack_chosen(1, attack, 0)
        recorder.record_attack_executed(
            1, attack, 0,
            damage=4, effectiveness=1.0, random_factor=0.75,
            attacker_hp_before=15, defender_hp_before=25,
            attacker_hp_after=15, defender_hp_after=21
        )
        recorder.record_hp_change(0, 0, 25, 21, "damage")

        # End battle
        replay = recorder.stop_recording(winner_index=0)

        # Verify replay
        self.assertEqual(replay.metadata.total_turns, 2)
        self.assertEqual(replay.metadata.winner_index, 0)
        self.assertEqual(replay.metadata.battle_type, "wild")
        self.assertEqual(len(replay.initial_state), 2)
        self.assertGreater(len(replay.events), 5)

    def test_no_recording_when_not_started(self):
        """Events should not be recorded when not started"""
        recorder = BattleRecorder()
        attack = MockAttack("tackle", 30)

        # These should not raise, just be ignored
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        recorder.record_hp_change(0, 0, 20, 15, "damage")

        self.assertEqual(len(recorder.events), 0)

    def test_state_snapshots(self):
        recorder = BattleRecorder()
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        recorder.start_recording([provider1, provider2])
        recorder.record_turn_start(0)

        snapshots = recorder.get_state_snapshots()
        # Should have initial snapshot and one from turn start
        self.assertGreaterEqual(len(snapshots), 1)


if __name__ == "__main__":
    unittest.main()
