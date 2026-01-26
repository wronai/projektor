"""
Backlog - zarządzanie kolejką zadań.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class BacklogItem:
    """Element backlogu z priorytetem."""

    ticket_id: str
    priority_order: int  # Niższy = wyższy priorytet
    added_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "priority_order": self.priority_order,
            "added_at": self.added_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BacklogItem:
        return cls(
            ticket_id=data["ticket_id"],
            priority_order=data["priority_order"],
            added_at=(
                datetime.fromisoformat(data["added_at"]) if "added_at" in data else datetime.now()
            ),
        )


@dataclass
class Backlog:
    """
    Backlog projektu.

    Zarządza priorytetyzowaną listą ticketów do realizacji.
    Obsługuje grooming, refinement i planowanie sprintów.

    Example:
        >>> backlog = Backlog()
        >>> backlog.add("PROJ-1", priority=1)
        >>> backlog.add("PROJ-2", priority=2)
        >>> top_items = backlog.get_top(5)
    """

    items: list[BacklogItem] = field(default_factory=list)

    # Metadata
    last_groomed: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def add(self, ticket_id: str, priority: int | None = None) -> BacklogItem:
        """
        Dodaj ticket do backlogu.

        Args:
            ticket_id: ID ticketu
            priority: Priorytet (domyślnie: na końcu)

        Returns:
            Utworzony element backlogu
        """
        # Sprawdź czy już istnieje
        existing = self.find(ticket_id)
        if existing:
            if priority is not None:
                self.reprioritize(ticket_id, priority)
            return existing

        # Ustal priorytet
        if priority is None:
            priority = len(self.items)

        item = BacklogItem(ticket_id=ticket_id, priority_order=priority)
        self.items.append(item)
        self._sort()

        return item

    def remove(self, ticket_id: str) -> bool:
        """
        Usuń ticket z backlogu.

        Args:
            ticket_id: ID ticketu

        Returns:
            True jeśli usunięto
        """
        item = self.find(ticket_id)
        if item:
            self.items.remove(item)
            self._renumber()
            return True
        return False

    def find(self, ticket_id: str) -> BacklogItem | None:
        """Znajdź element po ID ticketu."""
        for item in self.items:
            if item.ticket_id == ticket_id:
                return item
        return None

    def reprioritize(self, ticket_id: str, new_priority: int) -> bool:
        """
        Zmień priorytet ticketu.

        Args:
            ticket_id: ID ticketu
            new_priority: Nowy priorytet (pozycja na liście)

        Returns:
            True jeśli zmieniono
        """
        item = self.find(ticket_id)
        if not item:
            return False

        self.items.remove(item)
        item.priority_order = new_priority
        self.items.insert(min(new_priority, len(self.items)), item)
        self._renumber()

        return True

    def move_to_top(self, ticket_id: str) -> bool:
        """Przenieś ticket na górę backlogu."""
        return self.reprioritize(ticket_id, 0)

    def move_to_bottom(self, ticket_id: str) -> bool:
        """Przenieś ticket na dół backlogu."""
        return self.reprioritize(ticket_id, len(self.items))

    def get_top(self, n: int = 10) -> list[str]:
        """
        Pobierz top N ticketów.

        Args:
            n: Liczba ticketów

        Returns:
            Lista ID ticketów
        """
        return [item.ticket_id for item in self.items[:n]]

    def get_for_sprint(self, points_capacity: int, ticket_points: dict[str, int]) -> list[str]:
        """
        Wybierz tickety do sprintu na podstawie capacity.

        Args:
            points_capacity: Maksymalna liczba story points
            ticket_points: Słownik ticket_id -> points

        Returns:
            Lista ID ticketów mieszczących się w capacity
        """
        selected = []
        total_points = 0

        for item in self.items:
            points = ticket_points.get(item.ticket_id, 0)
            if total_points + points <= points_capacity:
                selected.append(item.ticket_id)
                total_points += points

        return selected

    def groom(self) -> None:
        """Oznacz backlog jako przeglądnięty (grooming)."""
        self.last_groomed = datetime.now()

    def _sort(self) -> None:
        """Sortuj elementy po priorytecie."""
        self.items.sort(key=lambda x: x.priority_order)

    def _renumber(self) -> None:
        """Ponumeruj elementy po zmianach."""
        for i, item in enumerate(self.items):
            item.priority_order = i

    @property
    def size(self) -> int:
        """Rozmiar backlogu."""
        return len(self.items)

    def __len__(self) -> int:
        return self.size

    def __iter__(self):
        return iter(self.items)

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "items": [item.to_dict() for item in self.items],
            "last_groomed": self.last_groomed.isoformat() if self.last_groomed else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Backlog:
        """Tworzenie z słownika."""
        return cls(
            items=[BacklogItem.from_dict(i) for i in data.get("items", [])],
            last_groomed=(
                datetime.fromisoformat(data["last_groomed"]) if data.get("last_groomed") else None
            ),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
        )
