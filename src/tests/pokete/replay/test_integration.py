"""Integration tests for the battle replay system"""

import unittest
import tempfile
import os
from datetime import datetime

from pokete.classes.replay.recorder import BattleRecorder
from pokete.classes.replay.replay_player import BattleReplayPlayer, PlaybackState
from pokete.classes.replay.replay_format import (
    ReplayFormat,
    ReplayVersion,
    ReplayEventType,
)
from pokete.classes.replay.spectator import SpectatorMode, AIProvider, SpectatorBattleRunner
from pokete.classes.replay.state_snapshot import StateSnapshot


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
    def __init__(self, name: str = "potion", func: str = "heal_potion"):
        self.name = name
        self.func = func


class TestRecordAndReplayIntegration(unittest.TestCase):
    """Test the complete flow from recording to replay"""

    def test_record_and_replay_simple_battle(self):
        """Record a simple battle and verify replay produces same outcomes"""
        # Setup
        player_poke = MockPoke(identifier="steini", name="Steini", hp=25)
        enemy_poke = MockPoke(identifier="mowcow", name="Mowcow", hp=20)

        provider1 = MockProvider(pokes=[player_poke], name="Player")
        provider2 = MockProvider(pokes=[enemy_poke], name="Wild")

        attack = MockAttack("tackle", 30)

        # Record battle
        recorder = BattleRecorder(seed=42)
        recorder.start_recording([provider1, provider2], battle_type="wild")

        # Turn 1 - Player attacks
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        recorder.record_attack_executed(
            0, attack, 1,
            damage=7, effectiveness=1.0, random_factor=1.0,
            attacker_hp_before=25, defender_hp_before=20,
            attacker_hp_after=25, defender_hp_after=13
        )
        recorder.record_hp_change(1, 0, 20, 13, "damage")
        recorder.record_ap_change(0, 0, 0, 30, 29)

        # Turn 2 - Enemy attacks
        recorder.record_turn_start(1)
        recorder.record_attack_chosen(1, attack, 0)
        recorder.record_attack_executed(
            1, attack, 0,
            damage=5, effectiveness=1.0, random_factor=0.75,
            attacker_hp_before=13, defender_hp_before=25,
            attacker_hp_after=13, defender_hp_after=20
        )
        recorder.record_hp_change(0, 0, 25, 20, "damage")

        # Turn 3 - Player attacks, enemy faints
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        recorder.record_attack_executed(
            0, attack, 1,
            damage=13, effectiveness=1.3, random_factor=1.0,
            attacker_hp_before=20, defender_hp_before=13,
            attacker_hp_after=20, defender_hp_after=0
        )
        recorder.record_hp_change(1, 0, 13, 0, "damage")
        recorder.record_poke_fainted(1, 0)

        # End battle
        replay = recorder.stop_recording(winner_index=0)

        # Verify replay
        player = BattleReplayPlayer(replay)
        player.start()

        # Advance through all frames
        final_state = None
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame:
                final_state = player.current_state

        # Verify final state
        self.assertIsNotNone(final_state)
        self.assertEqual(final_state.provider_states[0].pokes[0].hp, 20)  # Player HP
        self.assertEqual(final_state.provider_states[1].pokes[0].hp, 0)   # Enemy HP

    def test_record_save_load_replay(self):
        """Test saving and loading replay files"""
        # Create a replay
        player_poke = MockPoke()
        enemy_poke = MockPoke()

        provider1 = MockProvider(pokes=[player_poke], name="Player")
        provider2 = MockProvider(pokes=[enemy_poke], name="Enemy")

        attack = MockAttack("tackle", 30)

        recorder = BattleRecorder()
        recorder.start_recording([provider1, provider2])
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        replay = recorder.stop_recording(winner_index=0)

        # Save and load
        with tempfile.NamedTemporaryFile(suffix=".replay", delete=False) as f:
            temp_path = f.name

        try:
            replay.save_to_file(temp_path)
            loaded = ReplayFormat.load_from_file(temp_path)

            # Verify loaded replay
            self.assertEqual(loaded.version, replay.version)
            self.assertEqual(len(loaded.events), len(replay.events))
            self.assertEqual(loaded.metadata.winner_index, replay.metadata.winner_index)
        finally:
            os.unlink(temp_path)

    def test_record_with_poke_switch(self):
        """Test recording and replaying poke switches"""
        poke1 = MockPoke(identifier="steini")
        poke2 = MockPoke(identifier="mowcow")
        enemy_poke = MockPoke(identifier="bigstone")

        provider1 = MockProvider(pokes=[poke1, poke2], name="Player")
        provider2 = MockProvider(pokes=[enemy_poke], name="Enemy")

        recorder = BattleRecorder()
        recorder.start_recording([provider1, provider2])

        recorder.record_turn_start(0)
        recorder.record_poke_switch(0, 0, 1, "manual")

        replay = recorder.stop_recording()

        # Replay and verify switch
        player = BattleReplayPlayer(replay)
        player.start()

        switch_found = False
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.POKE_SWITCHED:
                switch_found = True
                state = player.current_state
                self.assertEqual(state.provider_states[0].current_index, 1)

        self.assertTrue(switch_found)

    def test_record_with_effects(self):
        """Test recording and replaying effects"""
        player_poke = MockPoke()
        enemy_poke = MockPoke()

        provider1 = MockProvider(pokes=[player_poke], name="Player")
        provider2 = MockProvider(pokes=[enemy_poke], name="Enemy")

        recorder = BattleRecorder()
        recorder.start_recording([provider1, provider2])

        recorder.record_turn_start(0)
        recorder.record_effect_applied(1, 0, "burning")
        recorder.record_turn_start(1)
        recorder.record_effect_removed(1, 0, "burning")

        replay = recorder.stop_recording()

        # Replay and verify effects
        player = BattleReplayPlayer(replay)
        player.start()

        effect_applied = False
        effect_removed = False

        while not player.is_at_end:
            frame = player.advance_frame()
            if frame:
                if frame.event.event_type == ReplayEventType.EFFECT_APPLIED:
                    effect_applied = True
                    state = player.current_state
                    self.assertIn("burning", state.provider_states[1].pokes[0].effects)
                elif frame.event.event_type == ReplayEventType.EFFECT_REMOVED:
                    effect_removed = True
                    state = player.current_state
                    self.assertNotIn("burning", state.provider_states[1].pokes[0].effects)

        self.assertTrue(effect_applied)
        self.assertTrue(effect_removed)


class TestSpectatorModeIntegration(unittest.TestCase):
    """Test spectator mode with AI battles"""

    def test_spectator_ai_battle_flow(self):
        """Test complete AI battle through spectator mode"""
        ai1 = AIProvider(
            name="AI One",
            poke_configs=[
                {
                    "identifier": "steini",
                    "name": "Steini",
                    "hp": 25,
                    "xp": 100,
                    "level": 10,
                    "attacks": ["tackle"],
                    "attack_aps": [30],
                }
            ],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[
                {
                    "identifier": "mowcow",
                    "name": "Mowcow",
                    "hp": 20,
                    "xp": 50,
                    "level": 7,
                    "attacks": ["tackle"],
                    "attack_aps": [30],
                }
            ],
        )

        # Run AI battle
        runner = SpectatorBattleRunner(ai1, ai2, seed=42)
        replay = runner.run_battle()

        # Load in spectator mode
        spectator = SpectatorMode()
        spectator.load_replay(replay)

        # Verify can step through
        frames_seen = 0
        while not spectator.is_at_end:
            frame = spectator.step_forward()
            if frame:
                frames_seen += 1

        self.assertGreater(frames_seen, 0)

    def test_spectator_rewind_produces_correct_state(self):
        """Test that rewinding restores previous state correctly"""
        ai1 = AIProvider(
            name="AI One",
            poke_configs=[
                {"identifier": "steini", "hp": 25, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[
                {"identifier": "mowcow", "hp": 20, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )

        runner = SpectatorBattleRunner(ai1, ai2, seed=123)
        replay = runner.run_battle()

        spectator = SpectatorMode()
        spectator.load_replay(replay)

        # Move forward 5 frames
        for _ in range(5):
            spectator.step_forward()

        state_at_5 = spectator.get_current_state_summary()

        # Move forward more
        for _ in range(3):
            spectator.step_forward()

        # Rewind 3 frames
        for _ in range(3):
            spectator.step_backward()

        state_after_rewind = spectator.get_current_state_summary()

        # States should match
        self.assertEqual(state_at_5["turn"], state_after_rewind["turn"])


class TestReplayVersionMigration(unittest.TestCase):
    """Test replay version handling and migration"""

    def test_replay_loads_with_same_major_version(self):
        """Replays with same major version should load"""
        ai1 = AIProvider(
            name="AI",
            poke_configs=[{"identifier": "test", "hp": 20, "attacks": ["tackle"], "attack_aps": [10]}],
        )
        ai2 = AIProvider(
            name="AI2",
            poke_configs=[{"identifier": "test2", "hp": 20, "attacks": ["tackle"], "attack_aps": [10]}],
        )

        runner = SpectatorBattleRunner(ai1, ai2, seed=1)
        replay = runner.run_battle()

        # Modify version to older minor
        replay.version = ReplayVersion(1, 0, 0)

        # Should still load
        player = BattleReplayPlayer(replay)
        self.assertIsNotNone(player)

    def test_replay_validation_catches_issues(self):
        """Test replay validation"""
        ai1 = AIProvider(
            name="AI",
            poke_configs=[{"identifier": "test", "hp": 20, "attacks": ["tackle"], "attack_aps": [10]}],
        )
        ai2 = AIProvider(
            name="AI2",
            poke_configs=[{"identifier": "test2", "hp": 20, "attacks": ["tackle"], "attack_aps": [10]}],
        )

        runner = SpectatorBattleRunner(ai1, ai2, seed=1)
        replay = runner.run_battle()

        # Valid replay should have no issues
        issues = replay.validate()
        self.assertEqual(len(issues), 0)

        # Remove initial state
        replay.initial_state = []
        issues = replay.validate()
        self.assertGreater(len(issues), 0)


class TestReplayDeterminism(unittest.TestCase):
    """Test that replays produce deterministic outcomes"""

    def test_same_seed_produces_same_replay(self):
        """Same random seed should produce identical replays"""
        ai1 = AIProvider(
            name="AI One",
            poke_configs=[
                {"identifier": "steini", "hp": 30, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[
                {"identifier": "mowcow", "hp": 30, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )

        # Run twice with same seed
        runner1 = SpectatorBattleRunner(ai1, ai2, seed=99999)
        replay1 = runner1.run_battle()

        runner2 = SpectatorBattleRunner(ai1, ai2, seed=99999)
        replay2 = runner2.run_battle()

        # Should have same number of events
        self.assertEqual(len(replay1.events), len(replay2.events))

        # Should have same winner
        self.assertEqual(replay1.metadata.winner_index, replay2.metadata.winner_index)

        # Event types should match
        for e1, e2 in zip(replay1.events, replay2.events):
            self.assertEqual(e1.event_type, e2.event_type)
            self.assertEqual(e1.turn_number, e2.turn_number)

    def test_replay_playback_produces_same_final_state(self):
        """Playing the same replay twice should produce same final state"""
        ai1 = AIProvider(
            name="AI One",
            poke_configs=[
                {"identifier": "steini", "hp": 25, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[
                {"identifier": "mowcow", "hp": 20, "attacks": ["tackle"], "attack_aps": [30]}
            ],
        )

        runner = SpectatorBattleRunner(ai1, ai2, seed=12345)
        replay = runner.run_battle()

        # Play through once
        player1 = BattleReplayPlayer(replay)
        player1.start()
        while not player1.is_at_end:
            player1.advance_frame()
        state1 = player1.current_state

        # Play through again
        player2 = BattleReplayPlayer(replay)
        player2.start()
        while not player2.is_at_end:
            player2.advance_frame()
        state2 = player2.current_state

        # Final states should match
        self.assertEqual(state1.turn_number, state2.turn_number)
        for p1, p2 in zip(state1.provider_states, state2.provider_states):
            for pk1, pk2 in zip(p1.pokes, p2.pokes):
                self.assertEqual(pk1.hp, pk2.hp)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_empty_replay(self):
        """Test handling of minimal replay"""
        player_poke = MockPoke()
        enemy_poke = MockPoke()

        provider1 = MockProvider(pokes=[player_poke])
        provider2 = MockProvider(pokes=[enemy_poke])

        recorder = BattleRecorder()
        recorder.start_recording([provider1, provider2])
        replay = recorder.stop_recording()

        # Should have at least start and end events
        self.assertGreaterEqual(len(replay.events), 2)

        # Should still be playable
        player = BattleReplayPlayer(replay)
        player.start()

    def test_replay_with_single_turn(self):
        """Test replay with only one turn"""
        player_poke = MockPoke()
        enemy_poke = MockPoke()

        provider1 = MockProvider(pokes=[player_poke])
        provider2 = MockProvider(pokes=[enemy_poke])

        attack = MockAttack("tackle", 30)

        recorder = BattleRecorder()
        recorder.start_recording([provider1, provider2])
        recorder.record_turn_start(0)
        recorder.record_attack_chosen(0, attack, 1)
        replay = recorder.stop_recording()

        player = BattleReplayPlayer(replay)
        player.start()

        frame_count = 0
        while not player.is_at_end:
            player.advance_frame()
            frame_count += 1

        self.assertGreater(frame_count, 0)


if __name__ == "__main__":
    unittest.main()
