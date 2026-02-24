from .quest_types import QuestType
from .quest import Quest, QuestConfig
from .quest_manager import QuestManager, daily_quest_manager
from .quest_tracker import QuestTracker
from .quest_events import QuestEventType, QuestEvent

# UI imports are deferred to avoid scrap_engine dependency during testing
def __getattr__(name):
    if name in ('QuestIndicator', 'QuestOverview', 'notify_quest_complete',
                'show_quest_assigned_notification'):
        from . import quest_ui
        return getattr(quest_ui, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
