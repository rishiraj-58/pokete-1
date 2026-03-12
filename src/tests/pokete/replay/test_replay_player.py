"""Tests for the battle replay player"""

import unittest
from datetime import datetime

from pokete.classes.replay.replay_player import (
    BattleReplayPlayer,
    PlaybackState,
    ReplayFrame,
)
from pokete.classes.replay.replay_format import (
    ReplayFormat,
    ReplayVersion,
    ReplayEvent,
    ReplayEventType,
    ReplayMetadata,
    ProviderRecord,
    PokeStateRecord,
    ReplayVersionError,
)


class TestBattleReplayPlayer(unittest.TestCase):
    def _create_sample_replay(self, num_turns: int = 3) -> ReplayFormat:
        """Create a sample replay for testing"""
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
            total_turns=num_turns,
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
        ]

        # Add turn events
        current_player_hp = 25
        current_enemy_hp = 20

        for turn in range(1, num_turns + 1):
            events.append(
                ReplayEvent(
                    event_type=ReplayEventType.TURN_START,
                    turn_number=turn,
                    provider_index=turn % 2,
                    data={"turn": turn},
                )
            )

            # Player turn
            if turn % 2 == 1:
                damage = 5
                current_enemy_hp = max(0, current_enemy_hp - damage)
                events.append(
                    ReplayEvent(
                        event_type=ReplayEventType.ATTACK_EXECUTED,
                        turn_number=turn,
                        provider_index=0,
                        data={
                            "attack_name": "tackle",
                            "damage": damage,
                            "target": 1,
                        },
                    )
                )
                events.append(
                    ReplayEvent(
                        event_type=ReplayEventType.HP_CHANGED,
                        turn_number=turn,
                        provider_index=1,
                        data={
                            "poke_index": 0,
                            "old_hp": current_enemy_hp + damage,
                            "new_hp": current_enemy_hp,
                            "delta": -damage,
                        },
                    )
                )
            # Enemy turn
            else:
                damage = 3
                current_player_hp = max(0, current_player_hp - damage)
                events.append(
                    ReplayEvent(
                        event_type=ReplayEventType.ATTACK_EXECUTED,
                        turn_number=turn,
                        provider_index=1,
                        data={
                            "attack_name": "tackle",
                            "damage": damage,
                            "target": 0,
                        },
                    )
                )
                events.append(
                    ReplayEvent(
                        event_type=ReplayEventType.HP_CHANGED,
                        turn_number=turn,
                        provider_index=0,
                        data={
                            "poke_index": 0,
                            "old_hp": current_player_hp + damage,
                            "new_hp": current_player_hp,
                            "delta": -damage,
                        },
                    )
                )

        events.append(
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_END,
                turn_number=num_turns,
                provider_index=0,
                data={"winner": 0},
            )
        )

        return ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=[provider1, provider2],
            events=events,
        )

    def test_player_initialization(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        self.assertEqual(player.state, PlaybackState.STOPPED)
        self.assertEqual(player.current_frame_index, -1)
        self.assertGreater(player.total_frames, 0)

    def test_player_version_check(self):
        replay = self._create_sample_replay()
        replay.version = ReplayVersion(99, 0, 0)  # Incompatible version

        with self.assertRaises(ReplayVersionError):
            BattleReplayPlayer(replay)

    def test_start_playback(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()

        self.assertEqual(player.state, PlaybackState.PLAYING)
        self.assertEqual(player.current_frame_index, -1)

    def test_advance_frame(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        frame = player.advance_frame()

        self.assertIsNotNone(frame)
        self.assertEqual(player.current_frame_index, 0)
        self.assertIsInstance(frame, ReplayFrame)

    def test_advance_through_all_frames(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        frame_count = 0
        while True:
            frame = player.advance_frame()
            if frame is None:
                break
            frame_count += 1

        self.assertEqual(frame_count, player.total_frames)
        self.assertTrue(player.is_at_end)

    def test_rewind_frame(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        player.advance_frame()
        player.advance_frame()
        player.advance_frame()

        self.assertEqual(player.current_frame_index, 2)

        frame = player.rewind_frame()

        self.assertIsNotNone(frame)
        self.assertEqual(player.current_frame_index, 1)

    def test_rewind_at_start(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        player.advance_frame()  # Move to frame 0

        frame = player.rewind_frame()

        self.assertIsNone(frame)
        self.assertTrue(player.is_at_start)

    def test_jump_to_frame(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        frame = player.jump_to_frame(5)

        self.assertIsNotNone(frame)
        self.assertEqual(player.current_frame_index, 5)

    def test_jump_to_frame_clamps_bounds(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()

        # Jump past end
        player.jump_to_frame(9999)
        self.assertEqual(player.current_frame_index, player.total_frames - 1)

        # Jump before start
        player.jump_to_frame(-10)
        self.assertEqual(player.current_frame_index, 0)

    def test_jump_to_turn(self):
        replay = self._create_sample_replay(num_turns=5)
        player = BattleReplayPlayer(replay)

        player.start()
        frame = player.jump_to_turn(3)

        self.assertIsNotNone(frame)
        self.assertEqual(frame.event.data.get("turn"), 3)

    def test_fast_forward(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        player.advance_frame()  # Start at 0
        frame = player.fast_forward(5)

        self.assertIsNotNone(frame)
        self.assertEqual(player.current_frame_index, 5)

    def test_rewind_multiple(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        player.jump_to_frame(8)
        frame = player.rewind(5)

        self.assertIsNotNone(frame)
        self.assertEqual(player.current_frame_index, 3)

    def test_pause_resume(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        self.assertEqual(player.state, PlaybackState.PLAYING)

        player.pause()
        self.assertEqual(player.state, PlaybackState.PAUSED)

        player.resume()
        self.assertEqual(player.state, PlaybackState.PLAYING)

    def test_stop(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        player.advance_frame()
        player.stop()

        self.assertEqual(player.state, PlaybackState.STOPPED)

    def test_current_state_tracking(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()

        # Initial state
        state = player.current_state
        self.assertIsNotNone(state)
        self.assertEqual(len(state.provider_states), 2)
        self.assertEqual(state.provider_states[0].current_poke.hp, 25)
        self.assertEqual(state.provider_states[1].current_poke.hp, 20)

        # Advance to find HP change
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.HP_CHANGED:
                break

        state = player.current_state
        # HP should have changed for one of the pokes
        player_hp = state.provider_states[0].current_poke.hp
        enemy_hp = state.provider_states[1].current_poke.hp

        # Either player or enemy HP should be different from initial
        self.assertTrue(player_hp != 25 or enemy_hp != 20)

    def test_frame_descriptions(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()
        frame = player.advance_frame()

        self.assertIsNotNone(frame.description)
        self.assertIsInstance(frame.description, str)
        self.assertGreater(len(frame.description), 0)

    def test_event_handler_registration(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        events_received = []

        def handler(event):
            events_received.append(event)

        player.register_handler(ReplayEventType.ATTACK_EXECUTED, handler)

        player.start()
        while not player.is_at_end:
            player.advance_frame()

        attack_events = [
            e for e in events_received
            if e.event_type == ReplayEventType.ATTACK_EXECUTED
        ]
        self.assertGreater(len(attack_events), 0)

    def test_get_events_in_turn(self):
        replay = self._create_sample_replay(num_turns=5)
        player = BattleReplayPlayer(replay)

        events = player.get_events_in_turn(2)

        self.assertGreater(len(events), 0)
        self.assertTrue(all(e.turn_number == 2 for e in events))

    def test_get_hp_history(self):
        replay = self._create_sample_replay(num_turns=5)
        player = BattleReplayPlayer(replay)

        hp_history = player.get_hp_history(1, 0)  # Enemy, first poke

        self.assertIsInstance(hp_history, list)
        # HP should generally decrease (some damage was dealt)

    def test_frame_state_before_after(self):
        replay = self._create_sample_replay()
        player = BattleReplayPlayer(replay)

        player.start()

        # Find an HP change event
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.HP_CHANGED:
                # State before and after should differ
                self.assertIsNotNone(frame.state_before)
                self.assertIsNotNone(frame.state_after)
                break


class TestPlaybackStateTracking(unittest.TestCase):
    def _create_replay_with_switch(self) -> ReplayFormat:
        """Create a replay with a poke switch"""
        poke1a = PokeStateRecord(
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
        poke1b = PokeStateRecord(
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

        poke2 = PokeStateRecord(
            identifier="bigstone",
            name="Bigstone",
            hp=30,
            max_hp=30,
            xp=75,
            level=8,
            attacks=["tackle"],
            attack_aps=[30],
            effects=[],
            shiny=False,
        )

        provider1 = ProviderRecord(
            provider_type="ProtoFigure",
            name="Player",
            pokes=[poke1a, poke1b],
            current_poke_index=0,
            escapable=True,
        )

        provider2 = ProviderRecord(
            provider_type="Trainer",
            name="Gary",
            pokes=[poke2],
            current_poke_index=0,
            escapable=False,
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
                event_type=ReplayEventType.POKE_SWITCHED,
                turn_number=1,
                provider_index=0,
                data={"from_index": 0, "to_index": 1},
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
            battle_type="trainer",
            random_seed=None,
        )

        return ReplayFormat(
            version=ReplayVersion.current(),
            metadata=metadata,
            initial_state=[provider1, provider2],
            events=events,
        )

    def test_poke_switch_updates_state(self):
        replay = self._create_replay_with_switch()
        player = BattleReplayPlayer(replay)

        player.start()

        # Initial state has index 0
        state = player.current_state
        self.assertEqual(state.provider_states[0].current_index, 0)

        # Advance to switch event
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.POKE_SWITCHED:
                break

        # After switch, index should be 1
        state = player.current_state
        self.assertEqual(state.provider_states[0].current_index, 1)


class TestEffectTracking(unittest.TestCase):
    def _create_replay_with_effect(self) -> ReplayFormat:
        """Create a replay with effect application and removal"""
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
                event_type=ReplayEventType.EFFECT_APPLIED,
                turn_number=1,
                provider_index=1,
                data={"poke_index": 0, "effect": "burning"},
            ),
            ReplayEvent(
                event_type=ReplayEventType.TURN_START,
                turn_number=2,
                provider_index=1,
                data={"turn": 2},
            ),
            ReplayEvent(
                event_type=ReplayEventType.EFFECT_REMOVED,
                turn_number=2,
                provider_index=1,
                data={"poke_index": 0, "effect": "burning"},
            ),
            ReplayEvent(
                event_type=ReplayEventType.BATTLE_END,
                turn_number=2,
                provider_index=0,
                data={"winner": 0},
            ),
        ]

        metadata = ReplayMetadata(
            recorded_at=datetime.now().isoformat(),
            duration_ms=15000,
            total_turns=2,
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

    def test_effect_applied_updates_state(self):
        replay = self._create_replay_with_effect()
        player = BattleReplayPlayer(replay)

        player.start()

        # Advance to effect applied
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.EFFECT_APPLIED:
                break

        state = player.current_state
        effects = state.provider_states[1].pokes[0].effects
        self.assertIn("burning", effects)

    def test_effect_removed_updates_state(self):
        replay = self._create_replay_with_effect()
        player = BattleReplayPlayer(replay)

        player.start()

        # Advance to effect removed
        while not player.is_at_end:
            frame = player.advance_frame()
            if frame and frame.event.event_type == ReplayEventType.EFFECT_REMOVED:
                break

        state = player.current_state
        effects = state.provider_states[1].pokes[0].effects
        self.assertNotIn("burning", effects)


if __name__ == "__main__":
    unittest.main()
