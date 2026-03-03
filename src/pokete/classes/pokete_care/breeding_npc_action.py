"""NPC action for the breeding facility in Pokete Care."""

from ..npcs import NPCAction
from ..npcs.npc_action import NPCInterface, UIInterface
from ..poke import Poke
from .. import timer
from .breeding import breeding_manager


class BreedingNPCAction(NPCAction):
    """NPC action that handles the breeding facility interactions."""

    def __init__(self):
        self.manager = breeding_manager

    def act(self, npc: NPCInterface, ui: UIInterface):
        # Update breeding state first
        egg_just_ready = self.manager.update(timer.time.time)

        if egg_just_ready:
            npc.text(["Great news! Your egg is ready to hatch!"])

        if self.manager.is_egg_ready():
            self._handle_egg_ready(npc, ui)
        elif self.manager.has_breeding_pair():
            self._handle_breeding_in_progress(npc, ui)
        else:
            self._handle_no_breeding(npc, ui)

        npc.text(["Come back anytime!"])

    def _handle_egg_ready(self, npc: NPCInterface, ui: UIInterface):
        """Handle the case where an egg is ready to be collected."""
        npc.text([
            "Welcome back to the breeding facility!",
            "Your egg is ready to be collected!"
        ])

        if ui.ask_bool("Would you like to collect your egg?"):
            new_poke = self.manager.collect_egg(timer.time.time)
            if new_poke:
                npc.ctx.figure.add_poke(new_poke)
                npc.ctx.figure.caught_pokes.append(new_poke.identifier)

                # Show inherited moves info
                if self.manager.history:
                    last_entry = self.manager.history[-1]
                    if last_entry.inherited_moves:
                        moves_str = ", ".join(last_entry.inherited_moves)
                        npc.text([
                            f"Congratulations! You received a {new_poke.name}!",
                            f"It inherited these special moves: {moves_str}",
                            "Take good care of it!"
                        ])
                    else:
                        npc.text([
                            f"Congratulations! You received a {new_poke.name}!",
                            "Take good care of it!"
                        ])
                else:
                    npc.text([
                        f"Congratulations! You received a {new_poke.name}!",
                        "Take good care of it!"
                    ])
            else:
                npc.text(["Something went wrong with the egg..."])
        else:
            npc.text(["The egg will be waiting here for you."])

        # Offer to view history
        if self.manager.history and ui.ask_bool("Would you like to see your breeding history?"):
            self._show_history(npc)

    def _handle_breeding_in_progress(self, npc: NPCInterface, ui: UIInterface):
        """Handle the case where breeding is in progress."""
        remaining = self.manager.get_time_remaining(timer.time.time)

        npc.text([
            "Welcome back to the breeding facility!",
            f"Your {self.manager.parent1.name} and {self.manager.parent2.name} "
            "are doing well.",
            f"Time remaining: {remaining} units."
        ])

        if ui.ask_bool("Would you like to cancel the breeding?"):
            p1, p2, idx1, idx2 = self.manager.cancel_breeding()
            # Return poketes to their original slots
            if p1 is not None and idx1 is not None:
                npc.ctx.figure.add_poke(p1, idx1)
            elif p1 is not None:
                npc.ctx.figure.add_poke(p1)

            if p2 is not None and idx2 is not None:
                npc.ctx.figure.add_poke(p2, idx2)
            elif p2 is not None:
                npc.ctx.figure.add_poke(p2)

            npc.text(["Breeding cancelled. Your poketes have been returned."])
        elif self.manager.history and ui.ask_bool("Would you like to see your breeding history?"):
            self._show_history(npc)

    def _handle_no_breeding(self, npc: NPCInterface, ui: UIInterface):
        """Handle the case where no breeding is in progress."""
        npc.text([
            "Welcome to the breeding facility!",
            "Here you can breed two compatible poketes to create an egg.",
            "Poketes are compatible if they share at least one type.",
            "The offspring may inherit special moves from its parents!"
        ])

        # Offer to view history first
        if self.manager.history:
            if ui.ask_bool("Would you like to see your breeding history?"):
                self._show_history(npc)
                if not ui.ask_bool("Would you like to start breeding?"):
                    return
            elif not ui.ask_bool("Would you like to start breeding?"):
                return
        elif not ui.ask_bool("Would you like to start breeding?"):
            return

        pokes = npc.ctx.figure.pokes
        valid_pokes = [
            p for p in pokes
            if p.identifier != "__fallback__"
        ]

        if len(valid_pokes) < 2:
            npc.text(["You need at least two valid poketes to start breeding."])
            return

        npc.text(["Please select the first pokete."])
        index1 = ui.choose_poke()
        if index1 is None:
            npc.text(["Breeding cancelled."])
            return

        poke1 = npc.ctx.figure.pokes[index1]
        if poke1.identifier == "__fallback__":
            npc.text(["That's not a valid pokete!"])
            return

        npc.text(["Please select the second pokete."])
        index2 = ui.choose_poke()
        if index2 is None:
            npc.text(["Breeding cancelled."])
            return

        if index1 == index2:
            npc.text(["You can't breed a pokete with itself!"])
            return

        poke2 = npc.ctx.figure.pokes[index2]
        if poke2.identifier == "__fallback__":
            npc.text(["That's not a valid pokete!"])
            return

        if not self.manager.can_breed(poke1, poke2):
            npc.text([
                f"{poke1.name} and {poke2.name} are not compatible!",
                "They need to share at least one type to breed.",
                f"{poke1.name} types: {', '.join(t.name for t in poke1.types)}",
                f"{poke2.name} types: {', '.join(t.name for t in poke2.types)}"
            ])
            return

        # Store references to the pokes before depositing them
        poke1_ref = poke1
        poke2_ref = poke2

        # Replace poketes with fallbacks (same pattern as PoketeCareNPCAction)
        # This properly removes them from the team while keeping slots
        npc.ctx.figure.add_poke(Poke("__fallback__", 0), index1)
        npc.ctx.figure.add_poke(Poke("__fallback__", 0), index2)

        # Start breeding with the stored references and their indices
        if self.manager.start_breeding(
            poke1_ref, poke2_ref, index1, index2, timer.time.time
        ):
            hatch_time = self.manager.compute_hatch_time()
            shared_types = self.manager.get_shared_types(poke1_ref, poke2_ref)

            # Show multi-type bonus info if applicable
            if len(shared_types) >= 2:
                npc.text([
                    f"Great! {poke1_ref.name} and {poke2_ref.name} will start breeding.",
                    f"They share these types: {', '.join(shared_types)}",
                    "Multi-type bonus: 10% faster hatching!",
                    f"Come back in about {hatch_time} time units to collect your egg!"
                ])
            else:
                npc.text([
                    f"Great! {poke1_ref.name} and {poke2_ref.name} will start breeding.",
                    f"They share these types: {', '.join(shared_types)}",
                    f"Come back in about {hatch_time} time units to collect your egg!"
                ])
        else:
            # Return poketes if breeding failed - restore to exact slots
            npc.ctx.figure.add_poke(poke1_ref, index1)
            npc.ctx.figure.add_poke(poke2_ref, index2)
            npc.text(["Something went wrong. Breeding could not start."])

    def _show_history(self, npc: NPCInterface):
        """Display breeding history to the player."""
        history = self.manager.get_history()
        if not history:
            npc.text(["No breeding history yet."])
            return

        npc.text(["=== Breeding History ==="])
        for i, entry in enumerate(reversed(history), 1):
            shiny_str = " (SHINY!)" if entry.shiny else ""
            moves_str = ""
            if entry.inherited_moves:
                moves_str = f" | Moves: {', '.join(entry.inherited_moves)}"

            npc.text([
                f"{i}. {entry.offspring_name}{shiny_str}",
                f"   Parents: {entry.parent1_name} x {entry.parent2_name}{moves_str}"
            ])
