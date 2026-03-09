from typing import TypedDict


class StatsDict(TypedDict):
    ownership_date: str | None
    evolved_date: str | None
    total_battles: int
    lost_battles: int
    win_battles: int
    earned_xp: int
    caught_with: str
    run_away: int


class NatureDict(TypedDict):
    nature: str
    grade: int


class MoodDict(TypedDict):
    mood_type: str
    last_battle_time: int
    battles_since_rest: int
    last_mood_change_time: int


class PokeDict(TypedDict):
    name: str
    xp: int
    hp: int
    ap: list[int]
    effects: list[str]
    attacks: list[str]
    shiny: bool
    nature: NatureDict
    stats: StatsDict
    mood: MoodDict
