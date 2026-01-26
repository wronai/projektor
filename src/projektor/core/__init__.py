"""
Core module - podstawowe modele i komponenty Projektora.
"""

from projektor.core.project import Project, ProjectMetadata, ProjectState
from projektor.core.ticket import (
    Ticket,
    TicketType,
    TicketStatus,
    Priority,
    Comment,
    WorkLog,
    AcceptanceCriteria,
    create_bug,
    create_feature,
    create_tech_debt,
)
from projektor.core.config import (
    Config,
    ProjectConfig,
    LLMConfig,
    OrchestrationConfig,
    TargetsConfig,
    DevOpsConfig,
    GitConfig,
    CIConfig,
    NotificationsConfig,
    get_config,
    set_config,
    load_config,
)
from projektor.core.events import (
    Event,
    EventType,
    EventBus,
    get_event_bus,
    emit,
    emit_async,
    on,
    on_async,
)

__all__ = [
    # Project
    "Project",
    "ProjectMetadata",
    "ProjectState",
    # Ticket
    "Ticket",
    "TicketType",
    "TicketStatus",
    "Priority",
    "Comment",
    "WorkLog",
    "AcceptanceCriteria",
    "create_bug",
    "create_feature",
    "create_tech_debt",
    # Config
    "Config",
    "ProjectConfig",
    "LLMConfig",
    "OrchestrationConfig",
    "TargetsConfig",
    "DevOpsConfig",
    "GitConfig",
    "CIConfig",
    "NotificationsConfig",
    "get_config",
    "set_config",
    "load_config",
    # Events
    "Event",
    "EventType",
    "EventBus",
    "get_event_bus",
    "emit",
    "emit_async",
    "on",
    "on_async",
]
