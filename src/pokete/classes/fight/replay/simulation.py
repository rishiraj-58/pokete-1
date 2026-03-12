"""Battle Simulation - Run battles in headless mode for replay verification"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, List, Dict

from .format import (
    DecisionType,
    DecisionFrame,
    StateFrame,
    PokeSnapshot,
    ProviderSnapshot,
    ReplayFormat,
    ReplayFrame,
    FrameType,
    ReplayMetadata,
    ReplayVersion,
)
from .replay import BattleReplay, ReplayValidator
from datetime import datetime


@dataclass
class SimulatedPoke:
    """Simulated Poke for headless battle execution"""
    identifier: str
    name: str
    hp: int
    full_hp: int
    xp: int
    atc: int
    defense: int
    initiative: int
    miss_chance: float
    attacks: List[str]
    attack_aps: List[int]
    attack_factors: List[float]
    attack_miss_chances: List[float]
    effects: List[str] = field(default_factory=list)
    shiny: bool = False

    @classmethod
    def from_snapshot(
        cls,
        snapshot: PokeSnapshot,
        attack_data: Optional[Dict] = None,
    ) -> SimulatedPoke:
        """Create from snapshot, optionally with attack data"""
        attack_factors = []
        attack_miss_chances = []

        if attack_data:
            for atk in snapshot.attacks:
                if atk in attack_data:
                    attack_factors.append(attack_data[atk].get("factor", 1.5))
                    attack_miss_chances.append(attack_data[atk].get("miss_chance", 0.2))
                else:
                    attack_factors.append(1.5)
                    attack_miss_chances.append(0.2)
        else:
            attack_factors = [1.5] * len(snapshot.attacks)
            attack_miss_chances = [0.2] * len(snapshot.attacks)

        return cls(
            identifier=snapshot.identifier,
            name=snapshot.name,
            hp=snapshot.hp,
            full_hp=snapshot.full_hp,
            xp=snapshot.xp,
            atc=10,
            defense=10,
            initiative=10,
            miss_chance=0.0,
            attacks=snapshot.attacks,
            attack_aps=list(snapshot.attack_aps),
            attack_factors=attack_factors,
            attack_miss_chances=attack_miss_chances,
            effects=list(snapshot.effects),
            shiny=snapshot.shiny,
        )

    def to_snapshot(self) -> PokeSnapshot:
        """Convert to snapshot"""
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
    """Simulated Provider for headless battle execution"""
    name: str
    provider_type: str
    pokes: List[SimulatedPoke]
    play_index: int = 0
    escapable: bool = True
    xp_multiplier: int = 1

    @property
    def curr(self) -> SimulatedPoke:
        return self.pokes[self.play_index]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: ProviderSnapshot,
        attack_data: Optional[Dict] = None,
    ) -> SimulatedProvider:
        """Create from snapshot"""
        pokes = [
            SimulatedPoke.from_snapshot(p, attack_data)
            for p in snapshot.pokes
        ]
        return cls(
            name=snapshot.name,
            provider_type=snapshot.provider_type,
            pokes=pokes,
            play_index=snapshot.play_index,
            escapable=snapshot.escapable,
            xp_multiplier=snapshot.xp_multiplier,
        )

    def to_snapshot(self) -> ProviderSnapshot:
        """Convert to snapshot"""
        return ProviderSnapshot(
            provider_type=self.provider_type,
            name=self.name,
            play_index=self.play_index,
            pokes=[p.to_snapshot() for p in self.pokes],
            escapable=self.escapable,
            xp_multiplier=self.xp_multiplier,
        )


class BattleSimulator:
    """Simulates battles without UI for replay verification"""

    def __init__(self, attack_data: Optional[Dict] = None):
        self._attack_data = attack_data or {}
        self._random_index = 0
        self._random_values: List[float] = []

    def _get_random(self) -> float:
        """Get next random value from replay or generate new"""
        if self._random_index < len(self._random_values):
            value = self._random_values[self._random_index]
            self._random_index += 1
            return value
        return random.random()

    def _set_random_values(self, values: List[float]):
        """Set random values for deterministic replay"""
        self._random_values = values
        self._random_index = 0

    def simulate_attack(
        self,
        attacker: SimulatedPoke,
        defender: SimulatedPoke,
        attack_index: str,
        random_values: Optional[List[float]] = None,
    ) -> Dict:
        """Simulate a single attack"""
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
            return {
                "success": True,
                "missed": True,
                "damage": 0,
                "defender_hp": defender.hp,
            }

        defense = max(defender.defense, 1)
        damage = round(
            (attacker.atc * factor / defense) * random_factor
        )
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
        """Calculate random factor for attack"""
        r = self._get_random()
        if r < miss_chance:
            return 0
        choices = [0.75, 1, 1.26]
        idx = int(self._get_random() * len(choices))
        return choices[min(idx, len(choices) - 1)]

    def run_replay_verification(
        self,
        replay: BattleReplay,
    ) -> tuple:
        """Verify replay produces expected results"""
        errors = []
        replay.reset()

        initial = replay.get_initial_state()
        providers = [
            SimulatedProvider.from_snapshot(p, self._attack_data)
            for p in initial.providers
        ]

        for frame in replay.iter_frames():
            if frame.frame_type == FrameType.DECISION:
                decision: DecisionFrame = frame.data
                self._set_random_values(decision.random_values)

                if decision.decision_type == DecisionType.ATTACK:
                    provider = providers[decision.provider_index]
                    enemy_idx = (decision.provider_index + 1) % 2
                    enemy = providers[enemy_idx]

                    result = self.simulate_attack(
                        provider.curr,
                        enemy.curr,
                        decision.attack_index,
                        decision.random_values,
                    )
                    if not result["success"]:
                        errors.append(
                            f"Turn {decision.turn}: Attack failed - "
                            f"{result.get('error', 'unknown')}"
                        )

                elif decision.decision_type == DecisionType.CHOOSE_POKE:
                    provider = providers[decision.provider_index]
                    if decision.poke_index is not None:
                        provider.play_index = decision.poke_index

            elif frame.frame_type == FrameType.STATE_SNAPSHOT:
                state: StateFrame = frame.data
                for i, (sim_prov, snap_prov) in enumerate(
                    zip(providers, state.providers)
                ):
                    sim_snapshot = sim_prov.to_snapshot()
                    diffs = ReplayValidator.compare_provider_states(
                        snap_prov, sim_snapshot
                    )
                    for diff in diffs:
                        errors.append(f"State mismatch at turn {state.turn}: {diff}")

        if replay.get_final_state():
            final = replay.get_final_state()
            for i, (sim_prov, snap_prov) in enumerate(
                zip(providers, final.providers)
            ):
                sim_snapshot = sim_prov.to_snapshot()
                diffs = ReplayValidator.compare_provider_states(
                    snap_prov, sim_snapshot
                )
                for diff in diffs:
                    errors.append(f"Final state mismatch: {diff}")

        return len(errors) == 0, errors


def run_ai_battle(
    provider1_config: Dict,
    provider2_config: Dict,
    attack_data: Dict,
    max_turns: int = 100,
    seed: Optional[int] = None,
) -> ReplayFormat:
    """Run a simulated AI battle and return the replay"""
    if seed is not None:
        random.seed(seed)

    def make_pokes(poke_configs: List[Dict]) -> List[SimulatedPoke]:
        pokes = []
        for poke_cfg in poke_configs:
            poke = SimulatedPoke(
                identifier=poke_cfg["identifier"],
                name=poke_cfg.get("name", poke_cfg["identifier"]),
                hp=poke_cfg.get("hp", 20),
                full_hp=poke_cfg.get("hp", 20),
                xp=poke_cfg.get("xp", 100),
                atc=poke_cfg.get("atc", 10),
                defense=poke_cfg.get("defense", 10),
                initiative=poke_cfg.get("initiative", 10),
                miss_chance=poke_cfg.get("miss_chance", 0.0),
                attacks=poke_cfg.get("attacks", ["tackle"]),
                attack_aps=[15] * len(poke_cfg.get("attacks", ["tackle"])),
                attack_factors=[
                    attack_data.get(a, {}).get("factor", 1.5)
                    for a in poke_cfg.get("attacks", ["tackle"])
                ],
                attack_miss_chances=[
                    attack_data.get(a, {}).get("miss_chance", 0.2)
                    for a in poke_cfg.get("attacks", ["tackle"])
                ],
            )
            pokes.append(poke)
        return pokes

    provider1 = SimulatedProvider(
        name=provider1_config.get("name", "Player1"),
        provider_type=provider1_config.get("type", "AI"),
        pokes=make_pokes(provider1_config.get("pokes", [])),
        escapable=provider1_config.get("escapable", False),
        xp_multiplier=provider1_config.get("xp_multiplier", 1),
    )

    provider2 = SimulatedProvider(
        name=provider2_config.get("name", "Player2"),
        provider_type=provider2_config.get("type", "AI"),
        pokes=make_pokes(provider2_config.get("pokes", [])),
        escapable=provider2_config.get("escapable", False),
        xp_multiplier=provider2_config.get("xp_multiplier", 1),
    )

    providers = [provider1, provider2]
    frames: List[ReplayFrame] = []
    turn = 0

    initial_state = StateFrame(
        turn=0,
        providers=[p.to_snapshot() for p in providers],
    )

    current_idx = 0 if provider1.curr.initiative >= provider2.curr.initiative else 1
    winner_index: Optional[int] = None

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
                data=StateFrame(
                    turn=turn,
                    providers=[p.to_snapshot() for p in providers],
                ),
            ))

        if defender.curr.hp <= 0:
            alive_pokes = [i for i, p in enumerate(defender.pokes) if p.hp > 0]
            if not alive_pokes:
                winner_index = current_idx
                break

        turn += 1
        current_idx = (current_idx + 1) % 2

    final_state = StateFrame(
        turn=turn,
        providers=[p.to_snapshot() for p in providers],
    )

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
