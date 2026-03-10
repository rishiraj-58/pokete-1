"""Encounter and item pickup classes for dungeons."""

import random

import scrap_engine as se

from pokete.base.change import change_ctx
from pokete.base.color import Color
from pokete.base.input_loops import ask_ok
from pokete.classes import movemap as mvp
from pokete.classes.asset_service.resources import PokeArgs
from pokete.classes.asset_service.service import asset_service
from pokete.classes.fight import Fight, NatureProvider
from pokete.classes.general import check_walk_back
from pokete.classes.landscape import MapInteract
from pokete.classes.poke import Poke
from pokete.classes import timer


class DungeonEncounterArea(se.Object, MapInteract):
    """Floor tile that can trigger random encounters in dungeons."""

    def __init__(
        self,
        poke_args: PokeArgs,
        encounter_rate: float = 0.1,
    ):
        super().__init__(" ", state="float")
        self.poke_args = poke_args
        self.encounter_rate = encounter_rate

    def action(self, ob) -> None:
        """Potentially trigger a random encounter."""
        if random.random() > self.encounter_rate:
            return

        is_night = 360 > timer.time.normalized or timer.time.normalized > 1320
        all_pokes = asset_service.get_base_assets().pokes

        available_pokes = {
            i: all_pokes[i]
            for i in self.poke_args.pokes
            if i in all_pokes and (
                (n_a := all_pokes[i].night_active) is None or
                (not n_a and not is_night) or
                (n_a and is_night)
            )
        }

        if not available_pokes:
            return

        poke_name = random.choices(
            list(available_pokes.keys()),
            weights=[p.rarity for p in available_pokes.values()],
        )[0]

        wild_poke = Poke.wild(
            poke_name,
            random.randint(self.poke_args.minlvl, self.poke_args.maxlvl)
        )

        Fight()(
            self.ctx,
            [self.ctx.figure, NatureProvider(wild_poke)],
        )
        change_ctx(self.ctx, self.ctx.overview)
        check_walk_back(self.ctx)


class DungeonItemPickup(se.Object, MapInteract):
    """Item pickup in dungeons."""

    DUNGEON_ITEMS = [
        ("poketeball", 10),
        ("superball", 5),
        ("hyperball", 2),
        ("healing_potion", 8),
        ("super_potion", 4),
        ("ap_potion", 3),
        ("treat", 1),
    ]

    def __init__(self, pickup_id: str, floor_number: int = 1):
        self.pickup_id = pickup_id
        self.floor_number = floor_number
        super().__init__(
            Color.thicc + Color.yellow + "*" + Color.reset,
            state="float"
        )

    def action(self, ob) -> None:
        """Pick up the item."""
        if self.pickup_id in self.ctx.figure.used_npcs:
            return

        rarity_bonus = self.floor_number * 0.5
        weights = [
            w * (1 + rarity_bonus if i > 2 else 1)
            for i, (_, w) in enumerate(self.DUNGEON_ITEMS)
        ]

        item_name = random.choices(
            [name for name, _ in self.DUNGEON_ITEMS],
            weights=weights,
        )[0]

        amount = random.choices([1, 2, 3], weights=[10, 3, 1])[0]
        if item_name in ["hyperball", "treat"]:
            amount = 1

        self.ctx.figure.give_item(item_name, amount)
        self.remove()
        mvp.movemap.full_show()

        item_info = asset_service.get_base_assets().items[item_name]
        ask_ok(
            self.ctx,
            f"You found {amount if amount > 1 else 'a'} "
            f"{item_info.pretty_name}{'s' if amount > 1 else ''}!",
        )

        self.ctx.figure.used_npcs.append(self.pickup_id)
