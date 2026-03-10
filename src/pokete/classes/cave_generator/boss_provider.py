"""Boss provider for dungeon boss fights."""

import random
import time

from pokete.base.context import Context
from pokete.release import SPEED_OF_TIME

from pokete.classes.fight import FightDecision, Provider
from pokete.classes.poke import Poke


class BossProvider(Provider):
    """Provider for dungeon boss fights."""

    BOSS_POKETES = [
        "bigstone",
        "bator",
        "treenator",
        "diamondos",
        "dia_bigstone",
    ]

    def __init__(
        self,
        boss_name: str,
        floor_number: int,
        base_level: int,
        pokes: list[Poke] = None,
    ):
        self.boss_name = boss_name
        self.floor_number = floor_number

        if pokes is None:
            pokes = self._create_boss_team(base_level)

        super().__init__(
            pokes=pokes,
            escapable=False,
            xp_multiplier=5,
        )

    def _create_boss_team(self, base_level: int) -> list[Poke]:
        """Create the boss's team of Poketes."""
        from pokete.classes.asset_service.service import asset_service
        all_pokes = asset_service.get_base_assets().pokes

        available = [p for p in self.BOSS_POKETES if p in all_pokes]
        if not available:
            available = ["steini"]

        team_size = min(3 + self.floor_number // 2, 6)
        boss_level = base_level + self.floor_number * 50

        team = []

        main_boss = random.choice(available)
        team.append(Poke.wild(main_boss, boss_level + 100))

        for _ in range(team_size - 1):
            poke_name = random.choice(available)
            level = random.randint(boss_level - 20, boss_level + 20)
            team.append(Poke.wild(poke_name, level))

        return team

    def get_decision(
        self, ctx: Context, fightmap, enem
    ) -> FightDecision:
        """Boss AI decision making."""
        valid_attacks = [a for a in self.curr.attack_obs if a.ap > 0]
        if not valid_attacks:
            valid_attacks = self.curr.attack_obs

        weights = []
        for attack in valid_attacks:
            weight = attack.ap
            if enem.curr.type.name in attack.type.effective:
                weight *= 2.0
            elif enem.curr.type.name in attack.type.ineffective:
                weight *= 0.5

            if self.curr.hp < self.curr.full_hp * 0.3:
                if hasattr(attack, "effect") and "heal" in str(attack.effect).lower():
                    weight *= 3.0

            weights.append(max(weight, 0.1))

        chosen = random.choices(valid_attacks, weights=weights)[0]
        return FightDecision.attack(chosen)

    def greet(self, fightmap) -> None:
        """Boss greeting at fight start."""
        fightmap.outp.outp(f"The dungeon boss {self.boss_name} challenges you!")
        time.sleep(SPEED_OF_TIME * 1)
        fightmap.outp.outp(
            f"{fightmap.outp.text}\n"
            f"They send out {self.curr.name}!"
        )

    def handle_defeat(
        self, ctx: Context, fightmap, winner
    ) -> bool:
        """Handle when boss's current Pokete is defeated."""
        remaining = [p for p in self.pokes if p.hp > 0]
        if not remaining:
            return False

        fightmap.death_animation(self)
        self.play_index = self.pokes.index(remaining[0])
        fightmap.add_enemy_after_choosing(winner, self)
        return True

    def handle_win(self, ctx: Context, loser) -> None:
        """Handle boss victory over player."""
        pass
