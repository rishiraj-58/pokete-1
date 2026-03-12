"""State snapshots for battle replay verification"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple, Optional

if TYPE_CHECKING:
    from ..poke import Poke
    from ..fight.providers import Provider


@dataclass
class PokeSnapshot:
    """Immutable snapshot of a Poke's state"""

    identifier: str
    name: str
    hp: int
    max_hp: int
    xp: int
    level: int
    atc: int
    defense: int
    initiative: int
    attacks: Tuple[str, ...]
    attack_aps: Tuple[int, ...]
    attack_max_aps: Tuple[int, ...]
    effects: Tuple[str, ...]
    shiny: bool
    miss_chance: float

    @classmethod
    def from_poke(cls, poke: Poke) -> PokeSnapshot:
        return cls(
            identifier=poke.identifier,
            name=poke.name,
            hp=poke.hp,
            max_hp=poke.full_hp,
            xp=poke.xp,
            level=poke.lvl(),
            atc=poke.atc,
            defense=poke.defense,
            initiative=poke.initiative,
            attacks=tuple(poke.attacks),
            attack_aps=tuple(atk.ap for atk in poke.attack_obs),
            attack_max_aps=tuple(atk.max_ap for atk in poke.attack_obs),
            effects=tuple(eff.c_name for eff in poke.effects),
            shiny=poke.shiny,
            miss_chance=poke.miss_chance,
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.identifier,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "xp": self.xp,
            "lvl": self.level,
            "atc": self.atc,
            "def": self.defense,
            "init": self.initiative,
            "atks": list(self.attacks),
            "aps": list(self.attack_aps),
            "max_aps": list(self.attack_max_aps),
            "effs": list(self.effects),
            "shiny": self.shiny,
            "miss": self.miss_chance,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> PokeSnapshot:
        return cls(
            identifier=data["id"],
            name=data["name"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            xp=data["xp"],
            level=data["lvl"],
            atc=data["atc"],
            defense=data["def"],
            initiative=data["init"],
            attacks=tuple(data["atks"]),
            attack_aps=tuple(data["aps"]),
            attack_max_aps=tuple(data["max_aps"]),
            effects=tuple(data["effs"]),
            shiny=data.get("shiny", False),
            miss_chance=data.get("miss", 0.0),
        )

    def equals(self, other: PokeSnapshot, check_hp: bool = True) -> bool:
        """Check equality, optionally ignoring HP for structural comparison"""
        if check_hp and self.hp != other.hp:
            return False
        return (
            self.identifier == other.identifier
            and self.name == other.name
            and self.max_hp == other.max_hp
            and self.xp == other.xp
            and self.level == other.level
            and self.attacks == other.attacks
            and self.shiny == other.shiny
        )


@dataclass
class ProviderSnapshot:
    """Immutable snapshot of a Provider's state"""

    provider_type: str
    name: str
    pokes: Tuple[PokeSnapshot, ...]
    current_index: int
    escapable: bool

    @classmethod
    def from_provider(cls, provider: Provider) -> ProviderSnapshot:
        provider_type = type(provider).__name__
        name = getattr(provider, "name", provider_type)
        return cls(
            provider_type=provider_type,
            name=name,
            pokes=tuple(PokeSnapshot.from_poke(p) for p in provider.pokes),
            current_index=provider.play_index,
            escapable=provider.escapable,
        )

    @property
    def current_poke(self) -> PokeSnapshot:
        return self.pokes[self.current_index]

    def to_dict(self) -> Dict:
        return {
            "type": self.provider_type,
            "name": self.name,
            "pokes": [p.to_dict() for p in self.pokes],
            "curr_idx": self.current_index,
            "escapable": self.escapable,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> ProviderSnapshot:
        return cls(
            provider_type=data["type"],
            name=data["name"],
            pokes=tuple(PokeSnapshot.from_dict(p) for p in data["pokes"]),
            current_index=data["curr_idx"],
            escapable=data["escapable"],
        )


@dataclass
class StateSnapshot:
    """Complete battle state at a point in time"""

    turn_number: int
    active_provider_index: int
    providers: Tuple[ProviderSnapshot, ...]
    random_state: Optional[bytes] = None

    @classmethod
    def capture(
        cls,
        turn_number: int,
        active_provider_index: int,
        providers: List[Provider],
    ) -> StateSnapshot:
        return cls(
            turn_number=turn_number,
            active_provider_index=active_provider_index,
            providers=tuple(ProviderSnapshot.from_provider(p) for p in providers),
        )

    def to_dict(self) -> Dict:
        return {
            "turn": self.turn_number,
            "active": self.active_provider_index,
            "providers": [p.to_dict() for p in self.providers],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> StateSnapshot:
        return cls(
            turn_number=data["turn"],
            active_provider_index=data["active"],
            providers=tuple(ProviderSnapshot.from_dict(p) for p in data["providers"]),
        )

    def get_provider(self, index: int) -> ProviderSnapshot:
        return self.providers[index]

    def get_current_poke(self, provider_index: int) -> PokeSnapshot:
        return self.providers[provider_index].current_poke

    def compare(self, other: StateSnapshot) -> List[str]:
        """Compare two snapshots and return differences"""
        diffs = []

        if self.turn_number != other.turn_number:
            diffs.append("Turn mismatch: {} vs {}".format(self.turn_number, other.turn_number))

        if self.active_provider_index != other.active_provider_index:
            diffs.append(
                "Active provider mismatch: {} vs {}".format(self.active_provider_index, other.active_provider_index)
            )

        for i, (p1, p2) in enumerate(zip(self.providers, other.providers)):
            if p1.current_index != p2.current_index:
                diffs.append(
                    "Provider {} current index: {} vs {}".format(i, p1.current_index, p2.current_index)
                )

            for j, (poke1, poke2) in enumerate(zip(p1.pokes, p2.pokes)):
                if poke1.hp != poke2.hp:
                    diffs.append(
                        "Provider {} Poke {} ({}) HP: {} vs {}".format(i, j, poke1.name, poke1.hp, poke2.hp)
                    )
                if poke1.attack_aps != poke2.attack_aps:
                    diffs.append(
                        "Provider {} Poke {} ({}) APs: {} vs {}".format(i, j, poke1.name, poke1.attack_aps, poke2.attack_aps)
                    )
                if poke1.effects != poke2.effects:
                    diffs.append(
                        "Provider {} Poke {} ({}) Effects: {} vs {}".format(i, j, poke1.name, poke1.effects, poke2.effects)
                    )

        return diffs
