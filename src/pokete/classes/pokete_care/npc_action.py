from pokete.base.context import Context
from pokete.base.exception_propagation import exception_propagating_periodic_event
from pokete.base.periodic_event_manager import PeriodicEventManager
from .pokete_care import PoketeCare
from .breeding import BreedingManager, breeding_manager
from .. import timer
from ..npcs import NPCAction
from ..npcs.npc_action import NPCInterface, UIInterface
from .dummy import DummyFigure
from ..poke import EvoMap, Poke


class PoketeCareNPCAction(NPCAction):
    def __init__(self, care: PoketeCare, breeding: BreedingManager | None = None):
        self.care: PoketeCare = care
        self.breeding: BreedingManager = breeding if breeding else breeding_manager

    def act(self, npc: NPCInterface, ui: UIInterface):
        if self.care.poke is None:
            npc.text(["Here you can leave one of your Poketes for some time \
and we will train it."])
            if ui.ask_bool(
                "Do you want to put a Pokete into the Pokete-Care?"
            ):
                if (index := ui.choose_poke()) is not None:
                    self.care.poke = npc.ctx.figure.pokes[index]
                    self.care.entry = timer.time.time
                    npc.ctx.figure.add_poke(Poke("__fallback__", 0), index)
                    npc.text(["We will take care of it."])
        else:
            add_xp = int((timer.time.time - self.care.entry) / 30)
            self.care.entry = timer.time.time
            self.care.poke.add_xp(add_xp)
            npc.text(["Oh, you're back.", f"Your {self.care.poke.name} \
gained {add_xp}xp and reached level {self.care.poke.lvl()}!"])
            if ui.ask_bool("Do you want it back?"):
                dummy = DummyFigure(self.care.poke)
                evomap = EvoMap(npc.ctx.map.height, npc.ctx.map.width)
                while evomap(
                    Context(PeriodicEventManager([exception_propagating_periodic_event]), npc.ctx.map,
                            npc.ctx.overview, dummy),
                    dummy.pokes[0]
                ):
                    continue
                npc.ctx.figure.add_poke(dummy.pokes[0])
                npc.ctx.figure.caught_pokes += dummy.caught_pokes
                npc.text(["Here you go!", "Until next time!"])
                self.care.poke = None
        npc.text(["See you!"])


class BreedingNPCAction(NPCAction):
    """NPC action for the breeding facility."""

    def __init__(self, breeding: BreedingManager | None = None):
        self.breeding: BreedingManager = breeding if breeding else breeding_manager

    def act(self, npc: NPCInterface, ui: UIInterface):
        current_time = timer.time.time

        if self.breeding.has_breeding_pair:
            self._handle_existing_breeding(npc, ui, current_time)
        else:
            self._handle_new_breeding(npc, ui, current_time)

        npc.text(["See you!"])

    def _handle_existing_breeding(
        self, npc: NPCInterface, ui: UIInterface, current_time: int
    ):
        """Handle interaction when breeding is in progress."""
        if self.breeding.is_egg_ready(current_time):
            npc.text(["Great news! Your egg is ready to hatch!"])
            if ui.ask_bool("Would you like to collect your new Pokete?"):
                offspring_data = self.breeding.collect_egg(current_time)
                if offspring_data:
                    new_poke = Poke.from_dict(offspring_data)
                    npc.ctx.figure.add_poke(new_poke)
                    npc.ctx.figure.caught_pokes.append(new_poke.identifier)
                    npc.text([
                        f"Congratulations! A {new_poke.name} has hatched!",
                        "Take good care of it!"
                    ])
        else:
            remaining = self.breeding.get_time_remaining(current_time)
            hours = remaining // 60
            minutes = remaining % 60
            npc.text([
                "Your Poketes are still working on the egg.",
                f"About {hours}h {minutes}m remaining until it hatches."
            ])
            if ui.ask_bool("Do you want to cancel the breeding?"):
                parents = self.breeding.cancel_breeding()
                if parents:
                    parent1 = Poke.from_dict(parents[0])
                    parent2 = Poke.from_dict(parents[1])
                    npc.ctx.figure.add_poke(parent1)
                    npc.ctx.figure.add_poke(parent2)
                    npc.text(["Breeding cancelled. Your Poketes are back."])

    def _handle_new_breeding(
        self, npc: NPCInterface, ui: UIInterface, current_time: int
    ):
        """Handle interaction to start new breeding."""
        npc.text([
            "Welcome to the Breeding Center!",
            "Here, two compatible Poketes can produce an egg.",
            "Poketes are compatible if they share at least one type."
        ])

        if not ui.ask_bool("Would you like to start breeding?"):
            return

        if len(npc.ctx.figure.pokes) < 2:
            npc.text(["You need at least two Poketes to start breeding."])
            return

        npc.text(["Please select the first parent Pokete."])
        index1 = ui.choose_poke()
        if index1 is None:
            return

        npc.text(["Please select the second parent Pokete."])
        index2 = ui.choose_poke()
        if index2 is None:
            return

        if index1 == index2:
            npc.text(["You need to select two different Poketes!"])
            return

        poke1 = npc.ctx.figure.pokes[index1]
        poke2 = npc.ctx.figure.pokes[index2]

        if not self.breeding.are_compatible(poke1, poke2):
            shared_needed = "They need to share at least one type."
            npc.text([
                f"{poke1.name} and {poke2.name} are not compatible.",
                shared_needed
            ])
            return

        # Show compatibility info
        shared_types = self.breeding.get_shared_types(poke1, poke2)
        hatch_time = self.breeding.compute_hatch_time(poke1, poke2)
        hours = hatch_time // 60
        minutes = hatch_time % 60

        npc.text([
            f"{poke1.name} and {poke2.name} are compatible!",
            f"Shared types: {', '.join(shared_types)}",
            f"Estimated hatching time: {hours}h {minutes}m"
        ])

        if ui.ask_bool("Do you want to proceed with breeding?"):
            if self.breeding.start_breeding(poke1, poke2, current_time):
                # Remove poketes from player and replace with fallbacks
                # Sort indices in reverse to avoid index shifting issues
                indices = sorted([index1, index2], reverse=True)
                for idx in indices:
                    npc.ctx.figure.add_poke(Poke("__fallback__", 0), idx)

                npc.text([
                    "Excellent! The breeding has started.",
                    "Come back later to collect your egg!"
                ])
            else:
                npc.text(["Sorry, something went wrong. Please try again."])
