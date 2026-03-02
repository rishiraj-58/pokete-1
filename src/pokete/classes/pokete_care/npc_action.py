from pokete.base.context import Context
from pokete.base.exception_propagation import exception_propagating_periodic_event
from pokete.base.periodic_event_manager import PeriodicEventManager
from .pokete_care import PoketeCare
from .breeding_manager import BreedingManager
from .. import timer
from ..npcs import NPCAction
from ..npcs.npc_action import NPCInterface, UIInterface
from .dummy import DummyFigure
from ..poke import EvoMap, Poke


class PoketeCareNPCAction(NPCAction):
    def __init__(self, care: PoketeCare, breeding: BreedingManager):
        self.care: PoketeCare = care
        self.breeding: BreedingManager = breeding

    def act(self, npc: NPCInterface, ui: UIInterface):
        self.breeding.check_and_notify()

        choices = ["Training", "Breeding", "Nothing"]
        npc.text(["Welcome to the Pokete Care facility!",
                  "What would you like to do?"])

        if self.care.poke is not None or self.breeding.is_breeding():
            self._handle_status(npc, ui)
        else:
            choice = self._ask_choice(npc, ui, choices)
            if choice == "Training":
                self._handle_training(npc, ui)
            elif choice == "Breeding":
                self._handle_breeding(npc, ui)

        npc.text(["See you!"])

    def _ask_choice(self, npc: NPCInterface, ui: UIInterface,
                    choices: list[str]) -> str:
        """Ask user to make a choice from options"""
        for i, choice in enumerate(choices):
            npc.text([f"{i + 1}. {choice}"])
        if ui.ask_bool("Would you like to use the training service?"):
            return "Training"
        if ui.ask_bool("Would you like to use the breeding service?"):
            return "Breeding"
        return "Nothing"

    def _handle_status(self, npc: NPCInterface, ui: UIInterface):
        """Handle checking status of existing care or breeding"""
        if self.care.poke is not None:
            self._handle_training_pickup(npc, ui)
        if self.breeding.is_breeding():
            self._handle_breeding_status(npc, ui)

    def _handle_training(self, npc: NPCInterface, ui: UIInterface):
        """Handle the training service"""
        if self.care.poke is None:
            npc.text(["Here you can leave one of your Poketes for some time "
                      "and we will train it."])
            if ui.ask_bool(
                "Do you want to put a Pokete into the Pokete-Care?"
            ):
                if (index := ui.choose_poke()) is not None:
                    self.care.poke = npc.ctx.figure.pokes[index]
                    self.care.entry = timer.time.time
                    npc.ctx.figure.add_poke(Poke("__fallback__", 0), index)
                    npc.text(["We will take care of it."])

    def _handle_training_pickup(self, npc: NPCInterface, ui: UIInterface):
        """Handle picking up a pokete from training"""
        add_xp = int((timer.time.time - self.care.entry) / 30)
        self.care.entry = timer.time.time
        self.care.poke.add_xp(add_xp)
        npc.text(["Oh, you're back.", f"Your {self.care.poke.name} "
                  f"gained {add_xp}xp and reached level {self.care.poke.lvl()}!"])
        if ui.ask_bool("Do you want it back?"):
            dummy = DummyFigure(self.care.poke)
            evomap = EvoMap(npc.ctx.map.height, npc.ctx.map.width)
            while evomap(
                Context(PeriodicEventManager([exception_propagating_periodic_event]),
                        npc.ctx.map, npc.ctx.overview, dummy),
                dummy.pokes[0]
            ):
                continue
            npc.ctx.figure.add_poke(dummy.pokes[0])
            npc.ctx.figure.caught_pokes += dummy.caught_pokes
            npc.text(["Here you go!", "Until next time!"])
            self.care.poke = None

    def _handle_breeding(self, npc: NPCInterface, ui: UIInterface):
        """Handle the breeding service"""
        npc.text(["Welcome to the breeding service!",
                  "Here you can breed two compatible Poketes to get an egg.",
                  "Poketes are compatible if they share at least one type."])

        if len(npc.ctx.figure.pokes) < 2:
            npc.text(["You need at least 2 Poketes to breed."])
            return

        if ui.ask_bool("Would you like to start breeding?"):
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

            parent1 = npc.ctx.figure.pokes[index1]
            parent2 = npc.ctx.figure.pokes[index2]

            if not self.breeding.are_compatible(parent1, parent2):
                shared_info = "They don't share any types."
                npc.text([f"Sorry, {parent1.name} and {parent2.name} "
                          "are not compatible for breeding.",
                          shared_info])
                return

            shared_types = self.breeding.get_shared_types(parent1, parent2)
            npc.text([f"Great! {parent1.name} and {parent2.name} share "
                      f"the type(s): {', '.join(shared_types)}"])

            if self.breeding.start_breeding(parent1, parent2):
                npc.ctx.figure.add_poke(Poke("__fallback__", 0), index1)
                remaining_idx = index2 if index2 < index1 else index2 - 1
                npc.ctx.figure.add_poke(Poke("__fallback__", 0), remaining_idx)

                hatch_time = self.breeding.get_hatch_time()
                npc.text([f"Breeding has started! The egg will be ready "
                          f"in about {hatch_time} time units.",
                          "Come back later to collect it!"])
            else:
                npc.text(["Sorry, something went wrong. Please try again."])

    def _handle_breeding_status(self, npc: NPCInterface, ui: UIInterface):
        """Handle checking breeding status and egg collection"""
        self.breeding.check_and_notify()

        if self.breeding.egg_ready:
            npc.text(["Great news! Your egg is ready!"])
            if ui.ask_bool("Would you like to collect your egg?"):
                egg = self.breeding.collect_egg()
                if egg is not None:
                    npc.ctx.figure.add_poke(egg)
                    npc.ctx.figure.caught_pokes.append(egg.identifier)
                    npc.text([f"Congratulations! You received a {egg.name}!"])

                parent1, parent2 = self.breeding.collect_parents()
                if parent1 is not None:
                    npc.ctx.figure.add_poke(parent1)
                    npc.text([f"Your {parent1.name} has been returned."])
                if parent2 is not None:
                    npc.ctx.figure.add_poke(parent2)
                    npc.text([f"Your {parent2.name} has been returned."])
        else:
            remaining = self.breeding.get_time_remaining()
            npc.text([f"Your {self.breeding.parent1.name} and "
                      f"{self.breeding.parent2.name} are still breeding.",
                      f"Time remaining: about {remaining} time units."])

            if ui.ask_bool("Would you like to cancel breeding and "
                           "get your Poketes back?"):
                parent1, parent2 = self.breeding.collect_parents()
                if parent1 is not None:
                    npc.ctx.figure.add_poke(parent1)
                if parent2 is not None:
                    npc.ctx.figure.add_poke(parent2)
                npc.text(["Breeding cancelled. Your Poketes have been returned."])
