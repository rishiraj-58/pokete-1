"""Type definitions for the breeding system."""

from typing import TypedDict


class EggDict(TypedDict):
    """Serialization format for an egg pokete."""
    parent1_identifier: str
    parent2_identifier: str
    child_identifier: str
    child_xp: int
    child_hp: int
    child_attacks: list[str]
    child_shiny: bool
    child_nature: dict
    base_atc: int
    base_defense: int
    base_initiative: int
    created_at: int
    hatch_time: int


class BreedingPairDict(TypedDict):
    """Serialization format for a breeding pair."""
    parent1: dict | None
    parent2: dict | None
    start_time: int
    hatch_time: int
    egg: EggDict | None
    is_ready: bool


class BreedingStateDict(TypedDict):
    """Serialization format for the complete breeding state."""
    active_breeding_pair: BreedingPairDict | None
    pending_eggs: list[EggDict]
    collected_eggs_count: int
