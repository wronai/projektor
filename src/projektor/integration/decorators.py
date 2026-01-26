"""
Dekoratory i Context Managery do śledzenia błędów.

Użycie:
    from projektor import track_errors, track_async_errors, ErrorTracker

    @track_errors
    def my_function():
        ...

    @track_async_errors
    async def my_async_function():
        ...

    with ErrorTracker() as tracker:
        risky_operation()
        if tracker.had_error:
            print(f"Error: {tracker.error}")
"""

from __future__ import annotations

import asyncio
import functools
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from projektor.core.ticket import Priority, Ticket

F = TypeVar("F", bound=Callable[..., Any])


def track_errors(
    func: F | None = None,
    *,
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
    context: dict[str, Any] | None = None,
    reraise: bool = True,
) -> F | Callable[[F], F]:
    """
    Dekorator do śledzenia błędów w funkcjach synchronicznych.

    Args:
        func: Funkcja do dekorowania
        auto_fix: Czy próbować automatycznie naprawiać
        priority: Priorytet tworzonych ticketów
        labels: Dodatkowe etykiety
        context: Dodatkowy kontekst do logowania
        reraise: Czy ponownie rzucić wyjątek (domyślnie True)

    Example:
        @track_errors
        def process_data(data):
            ...

        @track_errors(auto_fix=True, context={"component": "parser"})
        def parse(text):
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                _handle_error(
                    e,
                    func_name=fn.__name__,
                    auto_fix=auto_fix,
                    priority=priority,
                    labels=labels,
                    context=context,
                    args=args,
                    kwargs=kwargs,
                )
                if reraise:
                    raise
                return None

        return wrapper  # type: ignore

    if func is not None:
        return decorator(func)
    return decorator


def track_async_errors(
    func: F | None = None,
    *,
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
    context: dict[str, Any] | None = None,
    reraise: bool = True,
) -> F | Callable[[F], F]:
    """
    Dekorator do śledzenia błędów w funkcjach asynchronicznych.

    Args:
        func: Funkcja do dekorowania
        auto_fix: Czy próbować automatycznie naprawiać
        priority: Priorytet tworzonych ticketów
        labels: Dodatkowe etykiety
        context: Dodatkowy kontekst do logowania
        reraise: Czy ponownie rzucić wyjątek (domyślnie True)

    Example:
        @track_async_errors
        async def fetch_data(url):
            ...

        @track_async_errors(context={"component": "thermodynamic"})
        async def generate(text):
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                _handle_error(
                    e,
                    func_name=fn.__name__,
                    auto_fix=auto_fix,
                    priority=priority,
                    labels=labels,
                    context=context,
                    args=args,
                    kwargs=kwargs,
                )
                if reraise:
                    raise
                return None

        return wrapper  # type: ignore

    if func is not None:
        return decorator(func)
    return decorator


def _handle_error(
    exc: Exception,
    func_name: str,
    auto_fix: bool,
    priority: Priority,
    labels: list[str] | None,
    context: dict[str, Any] | None,
    args: tuple,
    kwargs: dict,
) -> Ticket | None:
    """Obsłuż błąd - utwórz ticket."""
    try:
        from projektor.integration.installer import get_handler, is_installed
        from projektor.integration.error_handler import ErrorHandler

        if is_installed():
            handler = get_handler()
        else:
            handler = ErrorHandler(auto_fix=auto_fix, priority=priority, labels=labels)

        if handler is None:
            return None

        # Zbuduj kontekst
        full_context = {
            "function": func_name,
            "args": str(args)[:200],
            "kwargs": str(kwargs)[:200],
        }
        if context:
            full_context.update(context)

        ticket = handler.handle_exception(exc, context=full_context)
        print(f"[projektor] Bug ticket created: {ticket.id}")
        return ticket

    except Exception as e:
        print(f"[projektor] Warning: Could not create ticket: {e}")
        return None


@dataclass
class ErrorTrackerResult:
    """Wynik śledzenia błędów w ErrorTracker."""

    had_error: bool = False
    error: Exception | None = None
    error_type: str | None = None
    ticket: Ticket | None = None
    context: dict[str, Any] = field(default_factory=dict)


@contextmanager
def ErrorTracker(
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
    context: dict[str, Any] | None = None,
    reraise: bool = False,
    suppress: bool = False,
):
    """
    Context manager do śledzenia błędów w bloku kodu.

    Args:
        auto_fix: Czy próbować automatycznie naprawiać
        priority: Priorytet tworzonych ticketów
        labels: Dodatkowe etykiety
        context: Dodatkowy kontekst
        reraise: Czy ponownie rzucić wyjątek
        suppress: Czy całkowicie pominąć wyjątek (deprecated, użyj reraise=False)

    Yields:
        ErrorTrackerResult z informacjami o błędzie

    Example:
        with ErrorTracker(context={"input": text[:50]}) as tracker:
            result = process(text)

        if tracker.had_error:
            print(f"Error occurred: {tracker.error}")
            print(f"Ticket created: {tracker.ticket.id}")
    """
    result = ErrorTrackerResult(context=context or {})

    try:
        yield result
    except Exception as e:
        result.had_error = True
        result.error = e
        result.error_type = type(e).__name__

        # Utwórz ticket
        try:
            from projektor.integration.installer import get_handler, is_installed
            from projektor.integration.error_handler import ErrorHandler

            if is_installed():
                handler = get_handler()
            else:
                handler = ErrorHandler(auto_fix=auto_fix, priority=priority, labels=labels)

            if handler is not None:
                ticket = handler.handle_exception(e, context=context)
                result.ticket = ticket
                print(f"[projektor] Bug ticket created: {ticket.id}")

        except Exception as handler_error:
            print(f"[projektor] Warning: Could not create ticket: {handler_error}")

        # Reraise jeśli potrzebne
        if reraise and not suppress:
            raise


# ==================== Aliases for backwards compatibility ====================

def catch_errors(
    func: F | None = None,
    *,
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
) -> F | Callable[[F], F]:
    """Alias dla track_errors (kompatybilność wsteczna)."""
    return track_errors(func, auto_fix=auto_fix, priority=priority, labels=labels)


def catch_async_errors(
    func: F | None = None,
    *,
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
) -> F | Callable[[F], F]:
    """Alias dla track_async_errors (kompatybilność wsteczna)."""
    return track_async_errors(func, auto_fix=auto_fix, priority=priority, labels=labels)
