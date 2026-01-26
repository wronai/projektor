"""
Ticket model - reprezentacja zadania/ticketu w projekcie.

Obsługuje różne typy ticketów: task, bug, feature, epic, story.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TicketType(Enum):
    """Typ ticketu."""

    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    EPIC = "epic"
    STORY = "story"
    SPIKE = "spike"  # Research/investigation
    TECH_DEBT = "tech_debt"
    IMPROVEMENT = "improvement"


class TicketStatus(Enum):
    """Status ticketu."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Priorytet ticketu."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Comment:
    """Komentarz do ticketu."""

    author: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Comment:
        return cls(
            author=data["author"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class Attachment:
    """Załącznik do ticketu."""

    name: str
    path: str
    mime_type: str = "application/octet-stream"
    size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "mime_type": self.mime_type,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Attachment:
        return cls(
            name=data["name"],
            path=data["path"],
            mime_type=data.get("mime_type", "application/octet-stream"),
            size=data.get("size", 0),
        )


@dataclass
class WorkLog:
    """Log pracy nad ticketem."""

    action: str
    description: str
    author: str = "projektor"
    timestamp: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 0
    commit_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "description": self.description,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "duration_minutes": self.duration_minutes,
            "commit_hash": self.commit_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkLog:
        return cls(
            action=data["action"],
            description=data["description"],
            author=data.get("author", "projektor"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_minutes=data.get("duration_minutes", 0),
            commit_hash=data.get("commit_hash"),
        )


@dataclass
class AcceptanceCriteria:
    """Kryterium akceptacji."""

    description: str
    completed: bool = False
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceCriteria:
        return cls(
            description=data["description"],
            completed=data.get("completed", False),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
        )

    def mark_complete(self) -> None:
        """Oznacz jako ukończone."""
        self.completed = True
        self.completed_at = datetime.now()


@dataclass
class Ticket:
    """
    Reprezentacja ticketu/zadania.

    Główna jednostka pracy w projekcie. Może reprezentować task, bug,
    feature, epic lub story.

    Example:
        >>> ticket = Ticket(
        ...     id="PROJ-42",
        ...     type=TicketType.TASK,
        ...     title="Refaktoryzacja modułu X",
        ...     description="Opis zadania...",
        ...     priority=Priority.HIGH
        ... )
        >>> ticket.add_acceptance_criteria("CC < 15")
        >>> ticket.transition_to(TicketStatus.IN_PROGRESS)
    """

    id: str
    title: str
    type: TicketType = TicketType.TASK
    status: TicketStatus = TicketStatus.BACKLOG
    priority: Priority = Priority.MEDIUM

    # Content
    description: str = ""
    acceptance_criteria: list[AcceptanceCriteria] = field(default_factory=list)

    # Metadata
    labels: list[str] = field(default_factory=list)
    story_points: int | None = None
    sprint_id: str | None = None
    milestone_id: str | None = None
    parent_id: str | None = None  # For subtasks

    # Assignment
    assignee: str | None = None
    reporter: str = "projektor"

    # Relations
    blocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    related_to: list[str] = field(default_factory=list)

    # History
    comments: list[Comment] = field(default_factory=list)
    work_logs: list[WorkLog] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    # Files affected
    affected_files: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # LLM context
    llm_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Walidacja po inicjalizacji."""
        if isinstance(self.type, str):
            self.type = TicketType(self.type)
        if isinstance(self.status, str):
            self.status = TicketStatus(self.status)
        if isinstance(self.priority, str):
            self.priority = Priority(self.priority)

    # ==================== Status Management ====================

    def transition_to(self, new_status: TicketStatus) -> bool:
        """
        Zmień status ticketu.

        Args:
            new_status: Nowy status

        Returns:
            True jeśli zmiana się powiodła
        """
        # Walidacja przejść statusu
        valid_transitions = {
            TicketStatus.BACKLOG: [TicketStatus.TODO, TicketStatus.CANCELLED],
            TicketStatus.TODO: [
                TicketStatus.IN_PROGRESS,
                TicketStatus.BLOCKED,
                TicketStatus.CANCELLED,
            ],
            TicketStatus.IN_PROGRESS: [
                TicketStatus.IN_REVIEW,
                TicketStatus.BLOCKED,
                TicketStatus.TODO,
            ],
            TicketStatus.IN_REVIEW: [TicketStatus.TESTING, TicketStatus.IN_PROGRESS],
            TicketStatus.TESTING: [TicketStatus.DONE, TicketStatus.IN_PROGRESS],
            TicketStatus.BLOCKED: [TicketStatus.TODO, TicketStatus.IN_PROGRESS],
            TicketStatus.DONE: [],  # Terminal state
            TicketStatus.CANCELLED: [],  # Terminal state
        }

        if new_status not in valid_transitions.get(self.status, []):
            return False

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()

        # Update timestamps
        if new_status == TicketStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = datetime.now()
        elif new_status == TicketStatus.DONE:
            self.completed_at = datetime.now()

        # Log transition
        self.add_work_log(
            action="status_change",
            description=f"Status changed from {old_status.value} to {new_status.value}",
        )

        return True

    def start(self) -> bool:
        """Rozpocznij pracę nad ticketem."""
        return self.transition_to(TicketStatus.IN_PROGRESS)

    def complete(self) -> bool:
        """Oznacz ticket jako ukończony."""
        # Sprawdź czy wszystkie kryteria są spełnione
        if not self.all_criteria_met:
            return False
        return self.transition_to(TicketStatus.DONE)

    def block(self, blocked_by: str | None = None) -> bool:
        """Zablokuj ticket."""
        if blocked_by and blocked_by not in self.blocked_by:
            self.blocked_by.append(blocked_by)
        return self.transition_to(TicketStatus.BLOCKED)

    # ==================== Acceptance Criteria ====================

    def add_acceptance_criteria(self, description: str) -> AcceptanceCriteria:
        """Dodaj kryterium akceptacji."""
        criteria = AcceptanceCriteria(description=description)
        self.acceptance_criteria.append(criteria)
        self.updated_at = datetime.now()
        return criteria

    def complete_criteria(self, index: int) -> bool:
        """Oznacz kryterium jako ukończone."""
        if 0 <= index < len(self.acceptance_criteria):
            self.acceptance_criteria[index].mark_complete()
            self.updated_at = datetime.now()
            return True
        return False

    @property
    def all_criteria_met(self) -> bool:
        """Czy wszystkie kryteria są spełnione."""
        if not self.acceptance_criteria:
            return True
        return all(c.completed for c in self.acceptance_criteria)

    @property
    def criteria_progress(self) -> tuple[int, int]:
        """Postęp kryteriów (completed, total)."""
        total = len(self.acceptance_criteria)
        completed = sum(1 for c in self.acceptance_criteria if c.completed)
        return completed, total

    # ==================== Comments & Logs ====================

    def add_comment(self, content: str, author: str = "projektor") -> Comment:
        """Dodaj komentarz."""
        comment = Comment(author=author, content=content)
        self.comments.append(comment)
        self.updated_at = datetime.now()
        return comment

    def add_work_log(
        self,
        action: str,
        description: str,
        duration_minutes: int = 0,
        commit_hash: str | None = None,
    ) -> WorkLog:
        """Dodaj log pracy."""
        log = WorkLog(
            action=action,
            description=description,
            duration_minutes=duration_minutes,
            commit_hash=commit_hash,
        )
        self.work_logs.append(log)
        self.updated_at = datetime.now()
        return log

    # ==================== Serialization ====================

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "description": self.description,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "labels": self.labels,
            "story_points": self.story_points,
            "sprint_id": self.sprint_id,
            "milestone_id": self.milestone_id,
            "parent_id": self.parent_id,
            "assignee": self.assignee,
            "reporter": self.reporter,
            "blocks": self.blocks,
            "blocked_by": self.blocked_by,
            "related_to": self.related_to,
            "comments": [c.to_dict() for c in self.comments],
            "work_logs": [w.to_dict() for w in self.work_logs],
            "attachments": [a.to_dict() for a in self.attachments],
            "affected_files": self.affected_files,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "llm_context": self.llm_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ticket:
        """Tworzenie z słownika."""
        return cls(
            id=data["id"],
            title=data["title"],
            type=TicketType(data.get("type", "task")),
            status=TicketStatus(data.get("status", "backlog")),
            priority=Priority(data.get("priority", "medium")),
            description=data.get("description", ""),
            acceptance_criteria=[
                AcceptanceCriteria.from_dict(c) for c in data.get("acceptance_criteria", [])
            ],
            labels=data.get("labels", []),
            story_points=data.get("story_points"),
            sprint_id=data.get("sprint_id"),
            milestone_id=data.get("milestone_id"),
            parent_id=data.get("parent_id"),
            assignee=data.get("assignee"),
            reporter=data.get("reporter", "projektor"),
            blocks=data.get("blocks", []),
            blocked_by=data.get("blocked_by", []),
            related_to=data.get("related_to", []),
            comments=[Comment.from_dict(c) for c in data.get("comments", [])],
            work_logs=[WorkLog.from_dict(w) for w in data.get("work_logs", [])],
            attachments=[Attachment.from_dict(a) for a in data.get("attachments", [])],
            affected_files=data.get("affected_files", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now()
            ),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            llm_context=data.get("llm_context", {}),
        )

    def to_llm_prompt(self) -> str:
        """Generuj prompt dla LLM opisujący ticket."""
        lines = [
            f"# Ticket: {self.id}",
            f"**Title:** {self.title}",
            f"**Type:** {self.type.value}",
            f"**Priority:** {self.priority.value}",
            "",
            "## Description",
            self.description,
            "",
        ]

        if self.acceptance_criteria:
            lines.append("## Acceptance Criteria")
            for i, c in enumerate(self.acceptance_criteria, 1):
                status = "✅" if c.completed else "⬜"
                lines.append(f"{status} {i}. {c.description}")
            lines.append("")

        if self.affected_files:
            lines.append("## Affected Files")
            for f in self.affected_files:
                lines.append(f"- {f}")
            lines.append("")

        if self.labels:
            lines.append(f"**Labels:** {', '.join(self.labels)}")

        return "\n".join(lines)

    # ==================== Representation ====================

    def __repr__(self) -> str:
        return f"Ticket({self.id!r}, {self.title!r}, status={self.status.value})"

    def __str__(self) -> str:
        return f"[{self.id}] {self.title}"


# ==================== Factory Functions ====================


def create_bug(
    id: str,
    title: str,
    description: str,
    priority: Priority = Priority.HIGH,
    **kwargs,
) -> Ticket:
    """Utwórz ticket typu bug."""
    return Ticket(
        id=id,
        title=title,
        description=description,
        type=TicketType.BUG,
        priority=priority,
        labels=["bug"] + kwargs.pop("labels", []),
        **kwargs,
    )


def create_feature(
    id: str,
    title: str,
    description: str,
    priority: Priority = Priority.MEDIUM,
    **kwargs,
) -> Ticket:
    """Utwórz ticket typu feature."""
    return Ticket(
        id=id,
        title=title,
        description=description,
        type=TicketType.FEATURE,
        priority=priority,
        labels=["feature"] + kwargs.pop("labels", []),
        **kwargs,
    )


def create_tech_debt(
    id: str,
    title: str,
    description: str,
    priority: Priority = Priority.LOW,
    **kwargs,
) -> Ticket:
    """Utwórz ticket typu tech debt."""
    return Ticket(
        id=id,
        title=title,
        description=description,
        type=TicketType.TECH_DEBT,
        priority=priority,
        labels=["tech-debt"] + kwargs.pop("labels", []),
        **kwargs,
    )
