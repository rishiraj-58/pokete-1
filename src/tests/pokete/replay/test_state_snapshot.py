"""Tests for state snapshots"""

import unittest

from pokete.classes.replay.state_snapshot import (
    PokeSnapshot,
    ProviderSnapshot,
    StateSnapshot,
)


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
        self.attack_obs = [MockAttack("tackle", 30, 30), MockAttack("stone_crush", 15, 15)]
        self.effects = []

    def lvl(self):
        return int((self.xp + 1) ** 0.5)


class MockAttack:
    """Mock Attack for testing"""

    def __init__(self, index: str, ap: int, max_ap: int):
        self.index = index
        self.name = index.replace("_", " ").title()
        self.ap = ap
        self.max_ap = max_ap


class MockEffect:
    """Mock Effect for testing"""

    c_name = "burning"


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


class TestPokeSnapshot(unittest.TestCase):
    def test_snapshot_from_poke(self):
        poke = MockPoke()
        snapshot = PokeSnapshot.from_poke(poke)

        self.assertEqual(snapshot.identifier, "steini")
        self.assertEqual(snapshot.name, "Steini")
        self.assertEqual(snapshot.hp, 25)
        self.assertEqual(snapshot.max_hp, 25)
        self.assertEqual(snapshot.xp, 100)
        self.assertEqual(snapshot.level, 10)
        self.assertEqual(snapshot.attacks, ("tackle", "stone_crush"))
        self.assertEqual(snapshot.attack_aps, (30, 15))
        self.assertFalse(snapshot.shiny)

    def test_snapshot_with_effects(self):
        poke = MockPoke()
        poke.effects = [MockEffect()]
        snapshot = PokeSnapshot.from_poke(poke)

        self.assertEqual(snapshot.effects, ("burning",))

    def test_snapshot_serialization(self):
        poke = MockPoke()
        snapshot = PokeSnapshot.from_poke(poke)
        data = snapshot.to_dict()

        restored = PokeSnapshot.from_dict(data)

        self.assertEqual(snapshot.identifier, restored.identifier)
        self.assertEqual(snapshot.hp, restored.hp)
        self.assertEqual(snapshot.attacks, restored.attacks)

    def test_snapshot_equality(self):
        poke1 = MockPoke()
        poke2 = MockPoke()
        poke3 = MockPoke(hp=20)

        snap1 = PokeSnapshot.from_poke(poke1)
        snap2 = PokeSnapshot.from_poke(poke2)
        snap3 = PokeSnapshot.from_poke(poke3)

        self.assertTrue(snap1.equals(snap2))
        self.assertFalse(snap1.equals(snap3))

    def test_snapshot_equality_ignore_hp(self):
        poke1 = MockPoke()
        poke2 = MockPoke(hp=15)

        snap1 = PokeSnapshot.from_poke(poke1)
        snap2 = PokeSnapshot.from_poke(poke2)

        self.assertFalse(snap1.equals(snap2, check_hp=True))
        self.assertTrue(snap1.equals(snap2, check_hp=False))


class TestProviderSnapshot(unittest.TestCase):
    def test_snapshot_from_provider(self):
        provider = MockProvider(name="Player")
        snapshot = ProviderSnapshot.from_provider(provider)

        self.assertEqual(snapshot.name, "Player")
        self.assertEqual(snapshot.provider_type, "MockProvider")
        self.assertEqual(len(snapshot.pokes), 1)
        self.assertEqual(snapshot.current_index, 0)
        self.assertTrue(snapshot.escapable)

    def test_snapshot_with_multiple_pokes(self):
        pokes = [MockPoke(identifier="steini"), MockPoke(identifier="mowcow")]
        provider = MockProvider(pokes=pokes)
        provider.play_index = 1

        snapshot = ProviderSnapshot.from_provider(provider)

        self.assertEqual(len(snapshot.pokes), 2)
        self.assertEqual(snapshot.current_index, 1)
        self.assertEqual(snapshot.current_poke.identifier, "mowcow")

    def test_snapshot_serialization(self):
        provider = MockProvider()
        snapshot = ProviderSnapshot.from_provider(provider)
        data = snapshot.to_dict()

        restored = ProviderSnapshot.from_dict(data)

        self.assertEqual(snapshot.name, restored.name)
        self.assertEqual(snapshot.current_index, restored.current_index)
        self.assertEqual(len(snapshot.pokes), len(restored.pokes))


class TestStateSnapshot(unittest.TestCase):
    def test_capture_state(self):
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy", escapable=False)

        snapshot = StateSnapshot.capture(
            turn_number=5,
            active_provider_index=0,
            providers=[provider1, provider2],
        )

        self.assertEqual(snapshot.turn_number, 5)
        self.assertEqual(snapshot.active_provider_index, 0)
        self.assertEqual(len(snapshot.providers), 2)

    def test_get_provider(self):
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        snapshot = StateSnapshot.capture(1, 0, [provider1, provider2])

        p1 = snapshot.get_provider(0)
        p2 = snapshot.get_provider(1)

        self.assertEqual(p1.name, "Player")
        self.assertEqual(p2.name, "Enemy")

    def test_get_current_poke(self):
        pokes = [MockPoke(identifier="steini"), MockPoke(identifier="mowcow")]
        provider = MockProvider(pokes=pokes)
        provider.play_index = 1

        snapshot = StateSnapshot.capture(1, 0, [provider, MockProvider()])

        poke = snapshot.get_current_poke(0)
        self.assertEqual(poke.identifier, "mowcow")

    def test_snapshot_serialization(self):
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        snapshot = StateSnapshot.capture(3, 1, [provider1, provider2])
        data = snapshot.to_dict()

        restored = StateSnapshot.from_dict(data)

        self.assertEqual(snapshot.turn_number, restored.turn_number)
        self.assertEqual(snapshot.active_provider_index, restored.active_provider_index)
        self.assertEqual(len(snapshot.providers), len(restored.providers))

    def test_compare_identical_snapshots(self):
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        snap1 = StateSnapshot.capture(1, 0, [provider1, provider2])
        snap2 = StateSnapshot.capture(1, 0, [provider1, provider2])

        diffs = snap1.compare(snap2)
        self.assertEqual(len(diffs), 0)

    def test_compare_different_turns(self):
        provider1 = MockProvider(name="Player")
        provider2 = MockProvider(name="Enemy")

        snap1 = StateSnapshot.capture(1, 0, [provider1, provider2])
        snap2 = StateSnapshot.capture(2, 0, [provider1, provider2])

        diffs = snap1.compare(snap2)
        self.assertTrue(any("Turn mismatch" in d for d in diffs))

    def test_compare_different_hp(self):
        poke1 = MockPoke(hp=25)
        poke2 = MockPoke(hp=20)

        provider1a = MockProvider(pokes=[poke1])
        provider2a = MockProvider(name="Enemy")

        provider1b = MockProvider(pokes=[poke2])
        provider2b = MockProvider(name="Enemy")

        snap1 = StateSnapshot.capture(1, 0, [provider1a, provider2a])
        snap2 = StateSnapshot.capture(1, 0, [provider1b, provider2b])

        diffs = snap1.compare(snap2)
        self.assertTrue(any("HP" in d for d in diffs))

    def test_compare_different_effects(self):
        poke1 = MockPoke()
        poke2 = MockPoke()
        poke2.effects = [MockEffect()]

        provider1a = MockProvider(pokes=[poke1])
        provider2 = MockProvider(name="Enemy")

        provider1b = MockProvider(pokes=[poke2])

        snap1 = StateSnapshot.capture(1, 0, [provider1a, provider2])
        snap2 = StateSnapshot.capture(1, 0, [provider1b, provider2])

        diffs = snap1.compare(snap2)
        self.assertTrue(any("Effects" in d for d in diffs))

    def test_compare_different_current_index(self):
        pokes = [MockPoke(identifier="steini"), MockPoke(identifier="mowcow")]

        provider1a = MockProvider(pokes=list(pokes))
        provider1a.play_index = 0

        provider1b = MockProvider(pokes=list(pokes))
        provider1b.play_index = 1

        provider2 = MockProvider(name="Enemy")

        snap1 = StateSnapshot.capture(1, 0, [provider1a, provider2])
        snap2 = StateSnapshot.capture(1, 0, [provider1b, provider2])

        diffs = snap1.compare(snap2)
        self.assertTrue(any("current index" in d for d in diffs))


class TestSnapshotImmutability(unittest.TestCase):
    def test_poke_snapshot_is_immutable(self):
        poke = MockPoke()
        snapshot = PokeSnapshot.from_poke(poke)

        # Change original poke
        poke.hp = 10
        poke.attacks.append("new_attack")

        # Snapshot should be unchanged
        self.assertEqual(snapshot.hp, 25)
        self.assertEqual(len(snapshot.attacks), 2)

    def test_provider_snapshot_is_immutable(self):
        pokes = [MockPoke()]
        provider = MockProvider(pokes=pokes)

        snapshot = ProviderSnapshot.from_provider(provider)

        # Change original provider
        provider.play_index = 5
        pokes[0].hp = 5

        # Snapshot should be unchanged
        self.assertEqual(snapshot.current_index, 0)


if __name__ == "__main__":
    unittest.main()
