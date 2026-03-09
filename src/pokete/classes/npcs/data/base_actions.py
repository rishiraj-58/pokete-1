from pokete.classes.npcs import NPCAction
from pokete.classes.npcs.npc_action import NPCInterface, UIInterface


class Heal(NPCAction):
    def act(self, npc: NPCInterface, ui: UIInterface):
        npc.ctx.figure.heal()


class HealAndCuddle(NPCAction):
    """Heal poketes and offer to cuddle them for a mood boost."""
    def act(self, npc: NPCInterface, ui: UIInterface):
        npc.ctx.figure.heal()
        if ui.ask_bool("Would you like to cuddle your Poketes?"):
            npc.ctx.figure.cuddle_all()
            npc.text(["Your Poketes look much happier now!"])


class Chat(NPCAction):
    def act(self, npc: NPCInterface, ui: UIInterface):
        npc.chat()


base_actions: dict[str, NPCAction] = {
    "chat": Chat(),
    "heal": Heal(),
    "heal_and_cuddle": HealAndCuddle(),
}
