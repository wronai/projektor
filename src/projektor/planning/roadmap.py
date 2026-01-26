"""
Roadmap - długoterminowe planowanie projektu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from projektor.planning.milestone import Milestone


@dataclass
class Goal:
    """Cel strategiczny projektu."""

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
    def from_dict(cls, data: dict[str, Any]) -> Goal:
        return cls(
            description=data["description"],
            completed=data.get("completed", False),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
        )


@dataclass
class Roadmap:
    """
    Roadmapa projektu.

    Definiuje wizję, cele strategiczne i kamienie milowe projektu.

    Example:
        >>> roadmap = Roadmap(
        ...     vision="Najszybszy system NLP w Polsce",
        ...     goals=["Latencja <30ms", "95% dokładność dla polskiego"]
        ... )
        >>> roadmap.add_milestone(Milestone(name="MVP", deadline="2025-03-01"))
    """

    vision: str
    goals: list[Goal] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Konwertuj stringi na obiekty Goal jeśli potrzeba
        self.goals = [Goal(description=g) if isinstance(g, str) else g for g in self.goals]

    def add_goal(self, description: str) -> Goal:
        """Dodaj cel strategiczny."""
        goal = Goal(description=description)
        self.goals.append(goal)
        self.updated_at = datetime.now()
        return goal

    def add_milestone(self, milestone: Milestone) -> None:
        """Dodaj kamień milowy."""
        self.milestones.append(milestone)
        # Sortuj po deadline
        self.milestones.sort(key=lambda m: m.deadline or date.max)
        self.updated_at = datetime.now()

    def get_next_milestone(self) -> Milestone | None:
        """Pobierz najbliższy nieukończony milestone."""
        for milestone in self.milestones:
            if not milestone.completed:
                return milestone
        return None

    def get_overdue_milestones(self) -> list[Milestone]:
        """Pobierz przeterminowane milestones."""
        today = date.today()
        return [m for m in self.milestones if not m.completed and m.deadline and m.deadline < today]

    @property
    def progress(self) -> float:
        """Postęp realizacji roadmapy (0-100)."""
        if not self.milestones:
            return 0.0
        completed = sum(1 for m in self.milestones if m.completed)
        return (completed / len(self.milestones)) * 100

    @property
    def goals_progress(self) -> tuple[int, int]:
        """Postęp celów (completed, total)."""
        total = len(self.goals)
        completed = sum(1 for g in self.goals if g.completed)
        return completed, total

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "vision": self.vision,
            "goals": [g.to_dict() for g in self.goals],
            "milestones": [m.to_dict() for m in self.milestones],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Roadmap:
        """Tworzenie z słownika."""
        return cls(
            vision=data.get("vision", ""),
            goals=[Goal.from_dict(g) for g in data.get("goals", [])],
            milestones=[Milestone.from_dict(m) for m in data.get("milestones", [])],
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
        )

    def to_markdown(self) -> str:
        """Generuj dokumentację Markdown."""
        lines = [
            "# Project Roadmap",
            "",
            "## Vision",
            "",
            self.vision,
            "",
        ]

        if self.goals:
            lines.append("## Strategic Goals")
            lines.append("")
            for goal in self.goals:
                status = "✅" if goal.completed else "⬜"
                lines.append(f"- {status} {goal.description}")
            lines.append("")

        if self.milestones:
            lines.append("## Milestones")
            lines.append("")
            for milestone in self.milestones:
                status = "✅" if milestone.completed else "🎯"
                deadline = milestone.deadline.isoformat() if milestone.deadline else "TBD"
                lines.append(f"### {status} {milestone.name}")
                lines.append(f"**Deadline:** {deadline}")
                if milestone.description:
                    lines.append(f"\n{milestone.description}")
                lines.append("")

        return "\n".join(lines)
