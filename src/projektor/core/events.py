"""
Event system for Projektor.

Prosty system zdarzeń do komunikacji między komponentami.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Typy zdarzeń."""

    # Project events
    PROJECT_LOADED = "project.loaded"
    PROJECT_SAVED = "project.saved"

    # Ticket events
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    TICKET_STATUS_CHANGED = "ticket.status_changed"
    TICKET_COMPLETED = "ticket.completed"

    # Sprint events
    SPRINT_STARTED = "sprint.started"
    SPRINT_COMPLETED = "sprint.completed"

    # Milestone events
    MILESTONE_REACHED = "milestone.reached"

    # Orchestration events
    PLAN_GENERATED = "orchestration.plan_generated"
    PLAN_STARTED = "orchestration.plan_started"
    PLAN_COMPLETED = "orchestration.plan_completed"
    PLAN_FAILED = "orchestration.plan_failed"

    # Execution events
    STEP_STARTED = "execution.step_started"
    STEP_COMPLETED = "execution.step_completed"
    STEP_FAILED = "execution.step_failed"

    # Code events
    CODE_MODIFIED = "code.modified"
    CODE_CREATED = "code.created"
    CODE_DELETED = "code.deleted"

    # Test events
    TESTS_STARTED = "tests.started"
    TESTS_COMPLETED = "tests.completed"
    TESTS_FAILED = "tests.failed"

    # Git events
    COMMIT_CREATED = "git.commit_created"
    BRANCH_CREATED = "git.branch_created"
    PUSH_COMPLETED = "git.push_completed"

    # Error events
    ERROR_OCCURRED = "error.occurred"
    WARNING_OCCURRED = "warning.occurred"


@dataclass
class Event:
    """
    Reprezentacja zdarzenia.

    Attributes:
        type: Typ zdarzenia
        data: Dane zdarzenia
        source: Źródło zdarzenia
        timestamp: Czas wystąpienia
    """

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "projektor"
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Event({self.type.value}, source={self.source})"


# Type alias dla handlerów
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]  # Coroutine


class EventBus:
    """
    Szyna zdarzeń.

    Zarządza rejestracją handlerów i emisją zdarzeń.
    Obsługuje zarówno synchroniczne jak i asynchroniczne handlery.

    Example:
        >>> bus = EventBus()
        >>> bus.on(EventType.TICKET_CREATED, lambda e: print(f"Created: {e.data}"))
        >>> bus.emit(EventType.TICKET_CREATED, {"id": "PROJ-1"})
    """

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._async_handlers: dict[EventType, list[AsyncEventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._async_global_handlers: list[AsyncEventHandler] = []
        self._history: list[Event] = []
        self._max_history: int = 1000

    def on(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Zarejestruj handler dla typu zdarzenia.

        Args:
            event_type: Typ zdarzenia
            handler: Funkcja obsługi
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_async(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
    ) -> None:
        """
        Zarejestruj asynchroniczny handler.

        Args:
            event_type: Typ zdarzenia
            handler: Funkcja asynchroniczna
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)

    def on_all(self, handler: EventHandler) -> None:
        """Zarejestruj handler dla wszystkich zdarzeń."""
        self._global_handlers.append(handler)

    def on_all_async(self, handler: AsyncEventHandler) -> None:
        """Zarejestruj asynchroniczny handler dla wszystkich zdarzeń."""
        self._async_global_handlers.append(handler)

    def off(
        self,
        event_type: EventType,
        handler: EventHandler | None = None,
    ) -> None:
        """
        Wyrejestruj handler.

        Args:
            event_type: Typ zdarzenia
            handler: Handler do wyrejestrowania (None = wszystkie)
        """
        if event_type in self._handlers:
            if handler is None:
                self._handlers[event_type] = []
            elif handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    def _dispatch_event(self, event: Event) -> None:
        event_type = event.type

        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")

        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")

    def emit(
        self,
        event_type: EventType | Event,
        data: dict[str, Any] | None = None,
        source: str = "projektor",
    ) -> Event:
        """
        Wyemituj zdarzenie (synchronicznie).

        Args:
            event_type: Typ zdarzenia
            data: Dane zdarzenia
            source: Źródło

        Returns:
            Wyemitowane zdarzenie
        """
        if isinstance(event_type, Event):
            event = event_type
        else:
            event = Event(type=event_type, data=data or {}, source=source)

        # Zapisz w historii
        self._add_to_history(event)

        self._dispatch_event(event)

        return event

    async def emit_async(
        self,
        event_type: EventType | Event,
        data: dict[str, Any] | None = None,
        source: str = "projektor",
    ) -> Event:
        """
        Wyemituj zdarzenie (asynchronicznie).

        Args:
            event_type: Typ zdarzenia
            data: Dane zdarzenia
            source: Źródło

        Returns:
            Wyemitowane zdarzenie
        """
        if isinstance(event_type, Event):
            event = event_type
        else:
            event = Event(type=event_type, data=data or {}, source=source)

        # Zapisz w historii
        self._add_to_history(event)

        self._dispatch_event(event)

        real_event_type = event.type

        # Wywołaj asynchroniczne globalne handlery
        for handler in self._async_global_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Async handler error for {real_event_type}: {e}")

        # Wywołaj asynchroniczne handlery dla typu
        if real_event_type in self._async_handlers:
            for handler in self._async_handlers[real_event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Async handler error for {real_event_type}: {e}")

        return event

    def _add_to_history(self, event: Event) -> None:
        """Dodaj zdarzenie do historii."""
        self._history.append(event)

        # Ogranicz rozmiar historii
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Pobierz historię zdarzeń.

        Args:
            event_type: Filtruj po typie
            limit: Maksymalna liczba zdarzeń

        Returns:
            Lista zdarzeń
        """
        events = self._history

        if event_type:
            events = [e for e in events if e.type == event_type]

        return events[-limit:]

    def clear_history(self) -> None:
        """Wyczyść historię."""
        self._history = []

    def clear_handlers(self) -> None:
        """Wyczyść wszystkie handlery."""
        self._handlers = {}
        self._async_handlers = {}
        self._global_handlers = []
        self._async_global_handlers = []


# Globalna instancja EventBus
_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Pobierz globalną szynę zdarzeń."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def emit(
    event_type: EventType,
    data: dict[str, Any] | None = None,
    source: str = "projektor",
) -> Event:
    """Wyemituj zdarzenie do globalnej szyny."""
    return get_event_bus().emit(event_type, data, source)


async def emit_async(
    event_type: EventType,
    data: dict[str, Any] | None = None,
    source: str = "projektor",
) -> Event:
    """Wyemituj zdarzenie asynchronicznie do globalnej szyny."""
    return await get_event_bus().emit_async(event_type, data, source)


def on(event_type: EventType, handler: EventHandler) -> None:
    """Zarejestruj handler w globalnej szynie."""
    get_event_bus().on(event_type, handler)


def on_async(event_type: EventType, handler: AsyncEventHandler) -> None:
    """Zarejestruj asynchroniczny handler w globalnej szynie."""
    get_event_bus().on_async(event_type, handler)
