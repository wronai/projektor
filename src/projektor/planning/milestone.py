"""
Milestone - kamień milowy projektu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class Milestone:
    """
    Kamień milowy projektu.

    Reprezentuje znaczący punkt w projekcie z określonym terminem
    i kryteriami akceptacji.

    Example:
        >>> milestone = Milestone(
        ...     name="MVP",
        ...     description="Minimalna wersja produktu",
        ...     deadline=date(2025, 3, 1),
        ...     acceptance_criteria=["5 adapterów działa", "Testy 80%"]
        ... )
    """

    name: str
    description: str = ""
    deadline: date | None = None

    # Kryteria akceptacji
    acceptance_criteria: list[str] = field(default_factory=list)

    # Powiązane tickety
    tickets: list[str] = field(default_factory=list)

    # Status
    completed: bool = False
    completed_at: datetime | None = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Konwertuj string deadline na date
        if isinstance(self.deadline, str):
            self.deadline = date.fromisoformat(self.deadline)

    def add_ticket(self, ticket_id: str) -> None:
        """Dodaj ticket do milestone."""
        if ticket_id not in self.tickets:
            self.tickets.append(ticket_id)

    def remove_ticket(self, ticket_id: str) -> None:
        """Usuń ticket z milestone."""
        if ticket_id in self.tickets:
            self.tickets.remove(ticket_id)

    def complete(self) -> None:
        """Oznacz milestone jako ukończony."""
        self.completed = True
        self.completed_at = datetime.now()

    @property
    def is_overdue(self) -> bool:
        """Czy milestone jest przeterminowany."""
        if self.completed or self.deadline is None:
            return False
        return date.today() > self.deadline

    @property
    def days_remaining(self) -> int | None:
        """Dni do deadline (None jeśli brak deadline)."""
        if self.deadline is None:
            return None
        return (self.deadline - date.today()).days

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "name": self.name,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "acceptance_criteria": self.acceptance_criteria,
            "tickets": self.tickets,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Milestone:
        """Tworzenie z słownika."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            deadline=date.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            acceptance_criteria=data.get("acceptance_criteria", []),
            tickets=data.get("tickets", []),
            completed=data.get("completed", False),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
        )

    def __repr__(self) -> str:
        return f"Milestone({self.name!r}, deadline={self.deadline})"

    def __str__(self) -> str:
        status = "✅" if self.completed else "🎯"
        return f"{status} {self.name}"
