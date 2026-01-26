"""
Error Handler - automatyczne przechwytywanie błędów i tworzenie ticketów.

Obsługuje:
- Dekoratory funkcji
- Context managers
- Globalny exception handler
"""

from __future__ import annotations

import asyncio
import functools
import sys
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar

from projektor.core.ticket import Priority, Ticket, TicketType

F = TypeVar("F", bound=Callable[..., Any])

# Przechowuje oryginalny excepthook
_original_excepthook = None


@dataclass
class ErrorReport:
    """Raport błędu do utworzenia ticketu."""

    exception_type: str
    message: str
    traceback_str: str
    file_path: str | None = None
    line_number: int | None = None
    function_name: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict[str, Any] = field(default_factory=dict)

    def to_ticket_description(self) -> str:
        """Generuj opis ticketu z raportu błędu."""
        lines = [
            f"## Error: {self.exception_type}",
            "",
            f"**Message:** {self.message}",
            "",
        ]

        if self.file_path:
            lines.append(f"**Location:** `{self.file_path}:{self.line_number}`")
            if self.function_name:
                lines.append(f"**Function:** `{self.function_name}`")
            lines.append("")

        lines.extend([
            "## Traceback",
            "```python",
            self.traceback_str,
            "```",
            "",
            f"**Timestamp:** {self.timestamp.isoformat()}",
        ])

        if self.context:
            lines.extend([
                "",
                "## Context",
            ])
            for key, value in self.context.items():
                lines.append(f"- **{key}:** {value}")

        return "\n".join(lines)


class ErrorHandler:
    """
    Handler do przechwytywania błędów i tworzenia ticketów w projektorze.

    Example:
        handler = ErrorHandler(project_path="/path/to/project")

        @handler.catch
        def my_function():
            raise ValueError("Something went wrong")
    """

    def __init__(
        self,
        project_path: str | Path | None = None,
        auto_fix: bool = False,
        priority: Priority = Priority.HIGH,
        labels: list[str] | None = None,
        on_error: Callable[[ErrorReport], None] | None = None,
    ):
        """
        Args:
            project_path: Ścieżka do projektu z projektor.yaml
            auto_fix: Czy automatycznie uruchamiać naprawę
            priority: Priorytet tworzonych ticketów
            labels: Etykiety do dodania do ticketów
            on_error: Callback wywoływany przy błędzie
        """
        self.project_path = Path(project_path) if project_path else self._find_project_root()
        self.auto_fix = auto_fix
        self.priority = priority
        self.labels = labels or ["auto-reported", "runtime-error"]
        self.on_error_callback = on_error
        self._project = None

    def _find_project_root(self) -> Path:
        """Znajdź root projektu szukając projektor.yaml lub pyproject.toml."""
        current = Path.cwd()

        while current != current.parent:
            if (current / "projektor.yaml").exists():
                return current
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent

        return Path.cwd()

    def _get_project(self):
        """Lazy load projektu."""
        if self._project is None:
            from projektor.core.project import Project

            try:
                self._project = Project.load(self.project_path)
            except Exception:
                self._project = Project.init(self.project_path)

        return self._project

    def _extract_error_info(
        self,
        exc: BaseException,
        tb: traceback.TracebackException | None = None,
    ) -> ErrorReport:
        """Ekstrahuj informacje o błędzie."""
        if tb is None:
            tb = traceback.TracebackException.from_exception(exc)

        # Znajdź ostatnią ramkę z user code (nie z bibliotek)
        file_path = None
        line_number = None
        function_name = None

        for frame in tb.stack:
            if "site-packages" not in frame.filename and "lib/python" not in frame.filename:
                file_path = frame.filename
                line_number = frame.lineno
                function_name = frame.name

        return ErrorReport(
            exception_type=type(exc).__name__,
            message=str(exc),
            traceback_str="".join(tb.format()),
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
        )

    def _generate_ticket_id(self) -> str:
        """Generuj ID ticketu."""
        project = self._get_project()
        existing = project.list_tickets()
        prefix = project.metadata.name[:4].upper() if project.metadata.name else "BUG"
        num = len(existing) + 1
        return f"{prefix}-{num}"

    def create_bug_ticket(self, report: ErrorReport) -> Ticket:
        """Utwórz ticket typu bug z raportu błędu."""
        project = self._get_project()

        ticket = Ticket(
            id=self._generate_ticket_id(),
            title=f"[Auto] {report.exception_type}: {report.message[:80]}",
            description=report.to_ticket_description(),
            type=TicketType.BUG,
            priority=self.priority,
            labels=self.labels.copy(),
        )

        if report.file_path:
            ticket.affected_files.append(report.file_path)

        project.add_ticket(ticket)
        project.save()

        return ticket

    async def auto_fix_ticket(self, ticket: Ticket) -> dict[str, Any]:
        """Uruchom automatyczną naprawę ticketu."""
        from projektor.orchestration.orchestrator import Orchestrator

        project = self._get_project()
        orchestrator = Orchestrator(project)

        result = await orchestrator.work_on_ticket(ticket.id)

        return {
            "success": result.status.value == "completed",
            "steps_completed": result.steps_completed,
            "files_modified": result.files_modified,
            "errors": result.errors,
        }

    def handle_exception(
        self,
        exc: BaseException,
        context: dict[str, Any] | None = None,
    ) -> Ticket:
        """
        Obsłuż wyjątek - utwórz ticket i opcjonalnie napraw.

        Args:
            exc: Wyjątek do obsłużenia
            context: Dodatkowy kontekst

        Returns:
            Utworzony ticket
        """
        report = self._extract_error_info(exc)

        if context:
            report.context.update(context)

        # Callback
        if self.on_error_callback:
            self.on_error_callback(report)

        # Utwórz ticket
        ticket = self.create_bug_ticket(report)

        # Auto-fix jeśli włączone
        if self.auto_fix:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.auto_fix_ticket(ticket))
                else:
                    loop.run_until_complete(self.auto_fix_ticket(ticket))
            except RuntimeError:
                asyncio.run(self.auto_fix_ticket(ticket))

        return ticket

    def catch(self, func: F) -> F:
        """Dekorator do przechwytywania błędów."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ticket = self.handle_exception(
                    e,
                    context={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                )
                print(f"[projektor] Bug ticket created: {ticket.id}")
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ticket = self.handle_exception(
                    e,
                    context={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                )
                print(f"[projektor] Bug ticket created: {ticket.id}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore


# ==================== Convenience Functions ====================

# Globalny handler
_global_handler: ErrorHandler | None = None


def get_global_handler() -> ErrorHandler:
    """Pobierz globalny handler."""
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def catch_errors(
    func: F | None = None,
    *,
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    labels: list[str] | None = None,
) -> F | Callable[[F], F]:
    """
    Dekorator do przechwytywania błędów i tworzenia ticketów.

    Użycie:
        @catch_errors
        def my_function():
            ...

        @catch_errors(auto_fix=True, priority=Priority.CRITICAL)
        def critical_function():
            ...
    """
    handler = ErrorHandler(auto_fix=auto_fix, priority=priority, labels=labels)

    def decorator(fn: F) -> F:
        return handler.catch(fn)

    if func is not None:
        return decorator(func)
    return decorator


@contextmanager
def projektor_guard(
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
    context: dict[str, Any] | None = None,
    reraise: bool = True,
):
    """
    Context manager do przechwytywania błędów.

    Użycie:
        with projektor_guard(auto_fix=True):
            risky_operation()
    """
    handler = ErrorHandler(auto_fix=auto_fix, priority=priority)

    try:
        yield handler
    except Exception as e:
        ticket = handler.handle_exception(e, context=context)
        print(f"[projektor] Bug ticket created: {ticket.id}")
        if reraise:
            raise


def install_global_handler(
    auto_fix: bool = False,
    priority: Priority = Priority.HIGH,
) -> None:
    """
    Zainstaluj globalny exception handler.

    Wszystkie nieobsłużone wyjątki będą automatycznie
    rejestrowane jako tickety w projektorze.

    Użycie:
        from projektor.integration import install_global_handler

        install_global_handler(auto_fix=True)

        # Teraz każdy nieobsłużony wyjątek utworzy ticket
    """
    global _original_excepthook, _global_handler

    _original_excepthook = sys.excepthook
    _global_handler = ErrorHandler(auto_fix=auto_fix, priority=priority)

    def projektor_excepthook(exc_type, exc_value, exc_tb):
        # Nie obsługuj KeyboardInterrupt i SystemExit
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            _original_excepthook(exc_type, exc_value, exc_tb)
            return

        try:
            tb = traceback.TracebackException(exc_type, exc_value, exc_tb)
            report = _global_handler._extract_error_info(exc_value, tb)
            ticket = _global_handler.create_bug_ticket(report)
            print(f"\n[projektor] Bug ticket created: {ticket.id}")
            print(f"[projektor] Title: {ticket.title}")

            if _global_handler.auto_fix:
                print("[projektor] Starting auto-fix...")
                asyncio.run(_global_handler.auto_fix_ticket(ticket))

        except Exception as handler_error:
            print(f"[projektor] Error creating ticket: {handler_error}")

        # Wywołaj oryginalny excepthook
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = projektor_excepthook


def uninstall_global_handler() -> None:
    """Przywróć oryginalny exception handler."""
    global _original_excepthook

    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
        _original_excepthook = None
