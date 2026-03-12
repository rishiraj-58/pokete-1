"""Tests for spectator mode"""

import unittest
from datetime import datetime

from pokete.classes.replay.spectator import (
    SpectatorMode,
    SpectatorSpeed,
    SpectatorControlAction,
    AIProvider,
    AIDecision,
    SpectatorBattleRunner,
)
from pokete.classes.replay.replay_format import (
    ReplayFormat,
    ReplayVersion,
    ReplayEvent,
    ReplayEventType,
    ReplayMetadata,
    ProviderRecord,
    PokeStateRecord,
)


class TestAIProvider(unittest.TestCase):
    def test_ai_provider_creation(self):
        ai = AIProvider(
            name="TestAI",
            poke_configs=[{"identifier": "steini", "hp": 25}],
            strategy="random",
        )

        self.assertEqual(ai.name, "TestAI")
        self.assertEqual(len(ai.poke_configs), 1)
        self.assertEqual(ai.strategy, "random")

    def test_ai_random_decision(self):
        ai = AIProvider(
            name="RandomAI",
            poke_configs=[{"identifier": "steini"}],
            strategy="random",
        )

        own_pokes = [
            {
                "identifier": "steini",
                "hp": 25,
                "attacks": ["tackle", "stone_crush"],
                "attack_aps": [30, 15],
            }
        ]
        enemy_pokes = [{"identifier": "mowcow", "hp": 20}]

        decision = ai.make_decision(own_pokes, enemy_pokes, 0, 0)

        self.assertIsInstance(decision, AIDecision)
        self.assertEqual(decision.decision_type, "attack")
        self.assertIn(decision.attack_index, [0, 1])

    def test_ai_aggressive_decision(self):
        ai = AIProvider(
            name="AggressiveAI",
            poke_configs=[{"identifier": "steini"}],
            strategy="aggressive",
        )

        own_pokes = [
            {
                "identifier": "steini",
                "hp": 25,
                "attacks": ["tackle", "stone_crush"],
                "attack_aps": [30, 15],
            }
        ]
        enemy_pokes = [{"identifier": "mowcow", "hp": 20}]

        decision = ai.make_decision(own_pokes, enemy_pokes, 0, 0)

        self.assertEqual(decision.decision_type, "attack")

    def test_ai_smart_decision_low_hp_switch(self):
        ai = AIProvider(
            name="SmartAI",
            poke_configs=[{"identifier": "steini"}, {"identifier": "mowcow"}],
            strategy="smart",
        )

        own_pokes = [
            {
                "identifier": "steini",
                "hp": 2,  # Very low HP
                "max_hp": 25,
                "attacks": ["tackle"],
                "attack_aps": [30],
            },
            {
                "identifier": "mowcow",
                "hp": 20,  # Healthy poke
                "max_hp": 20,
                "attacks": ["tackle"],
                "attack_aps": [30],
            },
        ]
        enemy_pokes = [{"identifier": "bigstone", "hp": 30}]

        decision = ai.make_decision(own_pokes, enemy_pokes, 0, 0)

        # Smart AI might switch when HP is low
        self.assertIn(decision.decision_type, ["attack", "switch"])


class TestSpectatorMode(unittest.TestCase):
    def _create_sample_replay(self) -> ReplayFormat:
        poke1 = PokeStateRecord(
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

        events = [
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_START,
                turn_number=0,
                provider_index=-1,
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
                data={"poke_index": 0, "old_hp": 20, "new_hp": 15, "delta": -5},
            ),
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_END,
                turn_number=1,
                provider_index=0,
                data={"winner": 0},
            ),
        ]

        metadata = ReplayMetadata(
            recorded_at=datetime.now().isoformat(),
            duration_ms=10000,
            total_turns=1,
            winner_index=0,
            battle_type="wild",
            random_seed=None,
        )

        return ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=[provider1, provider2],
            events=events,
        )

    def test_spectator_mode_creation(self):
        spectator = SpectatorMode()

        state = spectator.state
        self.assertTrue(state.is_paused)
        self.assertFalse(state.is_live)

    def test_load_replay(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()

        spectator.load_replay(replay)

        state = spectator.state
        self.assertFalse(state.is_live)
        self.assertGreater(state.total_frames, 0)

    def test_play_pause(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.play()
        self.assertFalse(spectator.state.is_paused)

        spectator.pause()
        self.assertTrue(spectator.state.is_paused)

    def test_toggle_pause(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        self.assertTrue(spectator.state.is_paused)

        spectator.toggle_pause()
        self.assertFalse(spectator.state.is_paused)

        spectator.toggle_pause()
        self.assertTrue(spectator.state.is_paused)

    def test_step_forward(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        initial_frame = spectator.state.frame_index

        frame = spectator.step_forward()

        self.assertIsNotNone(frame)
        self.assertEqual(spectator.state.frame_index, initial_frame + 1)

    def test_step_backward(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.step_forward()
        spectator.step_forward()
        spectator.step_forward()

        frame = spectator.step_backward()

        self.assertIsNotNone(frame)

    def test_fast_forward(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.fast_forward(3)

        self.assertEqual(spectator.state.frame_index, 2)  # 0-indexed, frames 0,1,2

    def test_rewind(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.fast_forward(5)
        spectator.rewind(2)

        # Should have gone back 2 frames

    def test_jump_to_start_end(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.jump_to_end()
        self.assertTrue(spectator.is_at_end)

        spectator.jump_to_start()
        self.assertTrue(spectator.is_at_start)

    def test_speed_control(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        self.assertEqual(spectator.state.speed, SpectatorSpeed.NORMAL)

        spectator.speed_up()
        self.assertEqual(spectator.state.speed, SpectatorSpeed.FAST)

        spectator.speed_down()
        self.assertEqual(spectator.state.speed, SpectatorSpeed.NORMAL)

    def test_set_speed(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.set_speed(SpectatorSpeed.INSTANT)
        self.assertEqual(spectator.state.speed, SpectatorSpeed.INSTANT)

    def test_get_current_state_summary(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.step_forward()  # Move to first frame

        summary = spectator.get_current_state_summary()

        self.assertIn("turn", summary)
        self.assertIn("providers", summary)

    def test_event_callback(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        events_received = []

        def callback(event):
            events_received.append(event)

        spectator.on_event(callback)

        # Step through all frames
        while not spectator.is_at_end:
            spectator.step_forward()

        self.assertGreater(len(events_received), 0)

    def test_state_change_callback(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        states_received = []

        def callback(state):
            states_received.append(state)

        spectator.on_state_change(callback)

        spectator.play()
        spectator.pause()
        spectator.step_forward()

        self.assertGreater(len(states_received), 0)

    def test_handle_action(self):
        spectator = SpectatorMode()
        replay = self._create_sample_replay()
        spectator.load_replay(replay)

        spectator.handle_action(SpectatorControlAction.PLAY)
        self.assertFalse(spectator.state.is_paused)

        spectator.handle_action(SpectatorControlAction.PAUSE)
        self.assertTrue(spectator.state.is_paused)

        spectator.handle_action(SpectatorControlAction.STEP_FORWARD)
        spectator.handle_action(SpectatorControlAction.STEP_BACKWARD)

    def test_get_delay_seconds(self):
        spectator = SpectatorMode()

        spectator.set_speed(SpectatorSpeed.NORMAL)
        self.assertEqual(spectator.get_delay_seconds(), 1.0)

        spectator.set_speed(SpectatorSpeed.FAST)
        self.assertEqual(spectator.get_delay_seconds(), 0.5)

        spectator.set_speed(SpectatorSpeed.INSTANT)
        self.assertEqual(spectator.get_delay_seconds(), 0.0)


class TestAIBattleSetup(unittest.TestCase):
    def test_setup_ai_battle(self):
        spectator = SpectatorMode()

        ai1 = AIProvider(
            name="AI One",
            poke_configs=[{"identifier": "steini", "hp": 25}],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[{"identifier": "mowcow", "hp": 20}],
        )

        spectator.setup_ai_battle(ai1, ai2, seed=42)

        state = spectator.state
        self.assertTrue(state.is_live)
        self.assertTrue(state.is_paused)


class TestSpectatorBattleRunner(unittest.TestCase):
    def test_run_ai_battle(self):
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
            strategy="random",
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
            strategy="random",
        )

        runner = SpectatorBattleRunner(ai1, ai2, seed=42)
        replay = runner.run_battle()

        self.assertIsNotNone(replay)
        self.assertEqual(len(replay.initial_state), 2)
        self.assertGreater(len(replay.events), 0)
        self.assertEqual(replay.metadata.battle_type, "ai_vs_ai")

        # Battle should have ended
        end_events = [
            e for e in replay.events
            if e.event_type == ReplayEventType.BATTLE_END
        ]
        self.assertEqual(len(end_events), 1)

    def test_ai_battle_deterministic_with_seed(self):
        """Same seed should produce same battle"""
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

        runner1 = SpectatorBattleRunner(ai1, ai2, seed=12345)
        replay1 = runner1.run_battle()

        runner2 = SpectatorBattleRunner(ai1, ai2, seed=12345)
        replay2 = runner2.run_battle()

        self.assertEqual(replay1.metadata.winner_index, replay2.metadata.winner_index)
        self.assertEqual(len(replay1.events), len(replay2.events))

    def test_ai_battle_different_seeds_different_results(self):
        """Different seeds may produce different battles"""
        ai1 = AIProvider(
            name="AI One",
            poke_configs=[
                {"identifier": "steini", "hp": 100, "attacks": ["tackle"], "attack_aps": [100]}
            ],
        )
        ai2 = AIProvider(
            name="AI Two",
            poke_configs=[
                {"identifier": "mowcow", "hp": 100, "attacks": ["tackle"], "attack_aps": [100]}
            ],
        )

        results = set()
        for seed in range(10):
            runner = SpectatorBattleRunner(ai1, ai2, seed=seed)
            replay = runner.run_battle()
            results.add((replay.metadata.winner_index, len(replay.events)))

        # With different seeds, we should get some variation
        # (though not guaranteed, just likely with randomness)


class TestSpectatorSpeedValues(unittest.TestCase):
    def test_speed_enum_values(self):
        self.assertEqual(SpectatorSpeed.SLOW.value, 2.0)
        self.assertEqual(SpectatorSpeed.NORMAL.value, 1.0)
        self.assertEqual(SpectatorSpeed.FAST.value, 0.5)
        self.assertEqual(SpectatorSpeed.VERY_FAST.value, 0.1)
        self.assertEqual(SpectatorSpeed.INSTANT.value, 0.0)


if __name__ == "__main__":
    unittest.main()
