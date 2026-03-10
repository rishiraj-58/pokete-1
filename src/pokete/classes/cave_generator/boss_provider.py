"""Boss provider for cave dungeon boss fights."""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pokete.base.context import Context
    from pokete.classes.fight.fightmap import FightMap


class BossProvider:
    """Provider for cave boss fights.

    Implements the Provider interface for the fight system.
    """

    def __init__(self, pokes: list, boss_name: str = "Cave Guardian"):
        self.pokes = pokes
        self.boss_name = boss_name
        self.escapable = False
        self.xp_multiplier = 3
        self.play_index = 0
        self.trainer = True
        self._inv: dict[str, int] = {}

    @property
    def curr(self):
        """Returns the currently active Pokete."""
        return self.pokes[self.play_index]

    def index_conf(self):
        """Sets index to first Pokete with HP > 0."""
        self.play_index = next(
            (i for i, p in enumerate(self.pokes) if p.hp > 0), 0
        )

    def get_inv(self) -> dict[str, int]:
        """Returns the boss inventory (empty)."""
        return self._inv

    def remove_item(self, item: str, amount: int = 1):
        """Remove item from inventory (no-op for boss)."""
        pass

    def get_decision(self, ctx: "Context", fightmap: "FightMap", enem):
        """Returns the boss's attack decision.

        The boss chooses attacks weighted by AP, with preference for
        attacks that are effective against the enemy's type.
        """
        from pokete.classes.fight.fight_decision import FightDecision

        attack_weights = []
        for attack in self.curr.attack_obs:
            weight = attack.ap
            if hasattr(enem, 'curr') and hasattr(attack, 'type'):
                if hasattr(enem.curr, 'type') and hasattr(attack.type, 'effective'):
                    if enem.curr.type.name in attack.type.effective:
                        weight *= 1.5
                    elif hasattr(attack.type, 'ineffective'):
                        if enem.curr.type.name in attack.type.ineffective:
                            weight *= 0.5
            attack_weights.append(max(weight, 0.1))

        attack = random.choices(
            self.curr.attack_obs,
            weights=attack_weights
        )[0]
        return FightDecision.attack(attack)

    def greet(self, fightmap: "FightMap"):
        """Outputs greeting text when fight starts."""
        fightmap.outp.outp(
            f"The {self.boss_name} {self.curr.name} blocks your path!"
        )

    def handle_defeat(self, ctx: "Context", fightmap: "FightMap", winner) -> bool:
        """Handle when the boss's current Pokete is defeated.

        Returns False to indicate the fight should end (boss has no more Poketes).
        """
        fightmap.death_animation(self)

        remaining = [p for p in self.pokes if p.hp > 0]
        if remaining:
            self.play_index = self.pokes.index(remaining[0])
            fightmap.add_enemy_after_choosing(winner, self)
            return True

        return False

    def handle_win(self, ctx: "Context", loser):
        """Handle when the boss wins the fight."""
        pass

    def heal(self):
        """Heal all boss Poketes to full HP."""
        for poke in self.pokes:
            poke.hp = poke.full_hp
            poke.effects = []
            if hasattr(poke, 'miss_chance') and hasattr(poke, 'full_miss_chance'):
                poke.miss_chance = poke.full_miss_chance
