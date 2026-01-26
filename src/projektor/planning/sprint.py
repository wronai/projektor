"""
Sprint - iteracja rozwoju projektu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class SprintStatus(Enum):
    """Status sprintu."""

    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SprintMetrics:
    """Metryki sprintu."""

    planned_points: int = 0
    completed_points: int = 0
    added_points: int = 0  # Dodane w trakcie sprintu
    removed_points: int = 0  # Usunięte w trakcie sprintu

    # Velocity
    velocity: float = 0.0  # points/day

    # Ticket counts
    total_tickets: int = 0
    completed_tickets: int = 0
    blocked_tickets: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "planned_points": self.planned_points,
            "completed_points": self.completed_points,
            "added_points": self.added_points,
            "removed_points": self.removed_points,
            "velocity": self.velocity,
            "total_tickets": self.total_tickets,
            "completed_tickets": self.completed_tickets,
            "blocked_tickets": self.blocked_tickets,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SprintMetrics:
        return cls(**data)

    @property
    def completion_rate(self) -> float:
        """Procent ukończenia (points)."""
        if self.planned_points == 0:
            return 0.0
        return (self.completed_points / self.planned_points) * 100


@dataclass
class Sprint:
    """
    Sprint - iteracja rozwoju.

    Reprezentuje cykl pracy (zazwyczaj 1-4 tygodnie) z określonym
    celem i zestawem ticketów do realizacji.

    Example:
        >>> sprint = Sprint(
        ...     id="SPRINT-1",
        ...     name="Sprint 1",
        ...     goal="Redukcja złożoności cyklomatycznej",
        ...     start_date=date(2025, 1, 27),
        ...     end_date=date(2025, 2, 7)
        ... )
        >>> sprint.add_ticket("PROJ-42")
        >>> sprint.start()
    """

    id: str
    name: str
    goal: str = ""

    # Dates
    start_date: date | None = None
    end_date: date | None = None

    # Status
    status: SprintStatus = SprintStatus.PLANNING

    # Tickets
    tickets: list[str] = field(default_factory=list)

    ticket_points: dict[str, int] = field(default_factory=dict)

    # Metrics
    metrics: SprintMetrics = field(default_factory=SprintMetrics)

    # Retrospektywa
    retrospective: str | None = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = SprintStatus(self.status)
        if isinstance(self.start_date, str):
            self.start_date = date.fromisoformat(self.start_date)
        if isinstance(self.end_date, str):
            self.end_date = date.fromisoformat(self.end_date)

    # ==================== Ticket Management ====================

    def add_ticket(self, ticket_id: str, points: int = 0) -> None:
        """Dodaj ticket do sprintu."""
        if ticket_id in self.tickets:
            self.ticket_points[ticket_id] = points
            return

        self.tickets.append(ticket_id)
        self.ticket_points[ticket_id] = points
        self.metrics.total_tickets += 1

        if self.status == SprintStatus.ACTIVE:
            self.metrics.added_points += points
        else:
            self.metrics.planned_points += points

    def remove_ticket(self, ticket_id: str, points: int = 0) -> None:
        """Usuń ticket ze sprintu."""
        if ticket_id in self.tickets:
            effective_points = points if points else self.ticket_points.get(ticket_id, 0)
            self.tickets.remove(ticket_id)
            self.ticket_points.pop(ticket_id, None)
            self.metrics.total_tickets -= 1

            if self.status == SprintStatus.ACTIVE:
                self.metrics.removed_points += effective_points
            else:
                self.metrics.planned_points -= effective_points

    def complete_ticket(self, ticket_id: str, points: int = 0) -> None:
        """Oznacz ticket jako ukończony."""
        if ticket_id in self.tickets:
            effective_points = points if points else self.ticket_points.get(ticket_id, 0)
            self.metrics.completed_points += effective_points
            self.metrics.completed_tickets += 1

    # ==================== Status Management ====================

    def start(self) -> bool:
        """Rozpocznij sprint."""
        if self.status != SprintStatus.PLANNING:
            return False

        self.status = SprintStatus.ACTIVE
        self.started_at = datetime.now()

        if self.start_date is None:
            self.start_date = date.today()

        return True

    def complete(self, retrospective: str | None = None) -> bool:
        """Zakończ sprint."""
        if self.status != SprintStatus.ACTIVE:
            return False

        self.status = SprintStatus.COMPLETED
        self.completed_at = datetime.now()
        self.retrospective = retrospective

        # Oblicz velocity
        if self.start_date and self.started_at:
            days = (datetime.now() - self.started_at).days or 1
            self.metrics.velocity = self.metrics.completed_points / days

        return True

    def cancel(self, reason: str | None = None) -> bool:
        """Anuluj sprint."""
        if self.status == SprintStatus.COMPLETED:
            return False

        self.status = SprintStatus.CANCELLED
        self.completed_at = datetime.now()
        self.retrospective = reason

        return True

    # ==================== Properties ====================

    @property
    def total_points(self) -> int:
        return sum(self.ticket_points.get(t, 0) for t in self.tickets)

    @property
    def completed_points(self) -> int:
        return self.metrics.completed_points

    @property
    def is_active(self) -> bool:
        """Czy sprint jest aktywny."""
        return self.status == SprintStatus.ACTIVE

    @property
    def days_remaining(self) -> int | None:
        """Dni do końca sprintu."""
        if self.end_date is None or self.status != SprintStatus.ACTIVE:
            return None
        return (self.end_date - date.today()).days

    @property
    def duration_days(self) -> int | None:
        """Długość sprintu w dniach."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def progress(self) -> float:
        """Postęp sprintu (0-100) bazując na czasie."""
        if not self.start_date or not self.end_date:
            return 0.0

        if self.status != SprintStatus.ACTIVE:
            return 100.0 if self.status == SprintStatus.COMPLETED else 0.0

        total_days = (self.end_date - self.start_date).days
        elapsed_days = (date.today() - self.start_date).days

        if total_days <= 0:
            return 100.0

        return min(100.0, (elapsed_days / total_days) * 100)

    # ==================== Serialization ====================

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status.value,
            "tickets": self.tickets,
            "ticket_points": self.ticket_points,
            "metrics": self.metrics.to_dict(),
            "retrospective": self.retrospective,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sprint:
        """Tworzenie z słownika."""
        return cls(
            id=data["id"],
            name=data["name"],
            goal=data.get("goal", ""),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            status=SprintStatus(data.get("status", "planning")),
            tickets=data.get("tickets", []),
            ticket_points=data.get("ticket_points", {}),
            metrics=SprintMetrics.from_dict(data.get("metrics", {})),
            retrospective=data.get("retrospective"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
        )

    def __repr__(self) -> str:
        return f"Sprint({self.id!r}, {self.name!r}, status={self.status.value})"

    def __str__(self) -> str:
        return f"[{self.id}] {self.name}"


def create_sprint(
    id: str,
    name: str,
    goal: str = "",
    duration_weeks: int = 2,
    start_date: date | None = None,
) -> Sprint:
    """
    Fabryka do tworzenia sprintów.

    Args:
        id: ID sprintu
        name: Nazwa
        goal: Cel sprintu
        duration_weeks: Długość w tygodniach
        start_date: Data rozpoczęcia (domyślnie: dziś)

    Returns:
        Nowy sprint
    """
    start = start_date or date.today()
    end = start + timedelta(weeks=duration_weeks)

    return Sprint(
        id=id,
        name=name,
        goal=goal,
        start_date=start,
        end_date=end,
    )
