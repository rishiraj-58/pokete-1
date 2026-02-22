"""Rematch system for defeated trainers."""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..poke import Poke


REMATCH_LEVEL_THRESHOLD = 3
REMATCH_STAT_MULTIPLIER = 1.2


@dataclass
class TrainerOriginalData:
    """Stores original trainer data for rematch eligibility calculation."""
    name: str
    highest_poke_level: int


def get_highest_poke_level(pokes: list[Any]) -> int:
    """Get the highest level among a list of poketes."""
    if not pokes:
        return 0
    return max(poke.lvl() for poke in pokes)


def is_rematch_eligible(
    player_highest_level: int,
    trainer_original_highest_level: int
) -> bool:
    """
    Check if a rematch is available based on level difference.
    
    A rematch becomes available when the player's highest level pokete
    is at least REMATCH_LEVEL_THRESHOLD levels above the trainer's
    original highest level pokete.
    """
    return player_highest_level >= trainer_original_highest_level + REMATCH_LEVEL_THRESHOLD


def scale_stat(original_value: int, multiplier: float = REMATCH_STAT_MULTIPLIER) -> int:
    """Scale a stat value by the rematch multiplier."""
    return int(original_value * multiplier)


class RematchManager:
    """Manages rematch state and eligibility for trainers."""
    
    def __init__(
        self,
        trainer_data: Optional[dict[str, int]] = None,
        completed_rematches: Optional[list[str]] = None
    ):
        # Maps trainer name to their original highest pokete level
        self._trainer_data: dict[str, int] = trainer_data or {}
        # List of trainer names who have been rematched
        self._completed_rematches: list[str] = completed_rematches or []
    
    def register_defeated_trainer(self, trainer_name: str, highest_poke_level: int) -> None:
        """Register a trainer as defeated, storing their original highest level."""
        if trainer_name not in self._trainer_data:
            self._trainer_data[trainer_name] = highest_poke_level
    
    def is_rematch_available(
        self,
        trainer_name: str,
        player_highest_level: int
    ) -> bool:
        """Check if a rematch is available for a specific trainer."""
        if trainer_name not in self._trainer_data:
            return False
        if trainer_name in self._completed_rematches:
            return False
        
        trainer_level = self._trainer_data[trainer_name]
        return is_rematch_eligible(player_highest_level, trainer_level)
    
    def complete_rematch(self, trainer_name: str) -> None:
        """Mark a rematch as completed."""
        if trainer_name not in self._completed_rematches:
            self._completed_rematches.append(trainer_name)
    
    def get_trainer_original_level(self, trainer_name: str) -> Optional[int]:
        """Get the original highest pokete level for a trainer."""
        return self._trainer_data.get(trainer_name)
    
    def to_dict(self) -> dict:
        """Serialize rematch data for saving."""
        return {
            "trainer_data": self._trainer_data.copy(),
            "completed_rematches": self._completed_rematches.copy()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RematchManager":
        """Create a RematchManager from saved data."""
        return cls(
            trainer_data=data.get("trainer_data", {}),
            completed_rematches=data.get("completed_rematches", [])
        )


# Global rematch manager instance
rematch_manager = RematchManager()
