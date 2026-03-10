"""Boss provider for cave boss fights."""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pokete.base.context import Context
    from pokete.classes.fight.fightmap import FightMap

from pokete.classes.fight.providers import Provider
from pokete.classes.fight.fight_decision import FightDecision
from pokete.classes.poke import Poke


class BossProvider(Provider):
    """Provider for cave boss fights.

    Implements the full Provider interface for proper fight integration.
    """

    def __init__(self, pokes: list[Poke], boss_name: str = "Cave Guardian"):
        super().__init__(
            pokes=pokes,
            escapable=False,
            xp_multiplier=3,
            inv=None
        )
        self.boss_name = boss_name
        self.trainer = True

    def get_decision(self, ctx: "Context", fightmap: "FightMap", enem) -> FightDecision:
        """Choose an attack weighted by AP and type effectiveness."""
        weights = []
        for attack in self.curr.attack_obs:
            weight = attack.ap
            if hasattr(enem, 'curr') and hasattr(enem.curr, 'type'):
                if enem.curr.type.name in attack.type.effective:
                    weight *= 1.5
                elif enem.curr.type.name in attack.type.ineffective:
                    weight *= 0.5
            weights.append(max(weight, 0.1))

        attack = random.choices(self.curr.attack_obs, weights=weights)[0]
        return FightDecision.attack(attack)

    def greet(self, fightmap: "FightMap"):
        """Display boss greeting message."""
        fightmap.outp.outp(f"The {self.boss_name} {self.curr.name} appeared!")

    def handle_defeat(self, ctx: "Context", fightmap: "FightMap", winner) -> bool:
        """Handle when the boss's current Pokete is defeated.

        Returns False since boss fights don't allow switching.
        """
        fightmap.death_animation(self)
        return False

    def handle_win(self, ctx: "Context", loser):
        """Handle when the boss wins the fight."""
        pass


def create_boss(boss_pokes: list[str], min_level: int, max_level: int,
                boss_name: str = "Cave Guardian") -> BossProvider:
    """Factory function to create a boss provider.

    Args:
        boss_pokes: List of possible boss pokete names
        min_level: Minimum level for the boss
        max_level: Maximum level for the boss
        boss_name: Display name for the boss

    Returns:
        Configured BossProvider instance
    """
    boss_poke_name = random.choice(boss_pokes)
    boss_level = random.randint(min_level, max_level)
    pokes = [Poke.wild(boss_poke_name, boss_level)]
    return BossProvider(pokes, boss_name)
