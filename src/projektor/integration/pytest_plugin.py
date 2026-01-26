"""
Pytest Plugin - przechwytywanie błędów testów.

Użycie w conftest.py:
    pytest_plugins = ["projektor.pytest_plugin"]

Lub przez CLI:
    pytest -p projektor.pytest_plugin tests/
"""

from __future__ import annotations

from typing import Any

import pytest

from projektor.core.ticket import Priority, Ticket, TicketType


def pytest_configure(config):
    """Konfiguracja pluginu pytest."""
    config.addinivalue_line(
        "markers",
        "projektor_track: mark test to be tracked by projektor",
    )


def pytest_collection_modifyitems(session, config, items):
    """Modyfikuj kolekcję testów."""
    pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook wywoływany po każdym teście.
    
    Tworzy ticket dla nieudanych testów.
    """
    outcome = yield
    report = outcome.get_result()

    # Tylko dla fazy "call" (nie setup/teardown) i tylko dla failures
    if report.when == "call" and report.failed:
        _create_test_failure_ticket(item, call, report)


def _create_test_failure_ticket(item, call, report) -> Ticket | None:
    """Utwórz ticket dla nieudanego testu."""
    try:
        from projektor.integration.installer import get_handler, is_installed
        from projektor.integration.config_loader import load_integration_config

        # Sprawdź czy projektor jest zainstalowany
        if not is_installed():
            # Spróbuj załadować konfigurację
            config = load_integration_config()
            if not config.enabled:
                return None

            # Zainstaluj tymczasowy handler
            from projektor.integration.error_handler import ErrorHandler
            handler = ErrorHandler(auto_fix=False)
        else:
            handler = get_handler()
            if handler is None:
                return None

        # Pobierz informacje o teście
        test_name = item.name
        test_file = str(item.fspath) if item.fspath else "unknown"
        test_nodeid = item.nodeid

        # Pobierz traceback
        if call.excinfo:
            exc_type = call.excinfo.type.__name__
            exc_message = str(call.excinfo.value)
            traceback_str = str(report.longrepr)
        else:
            exc_type = "TestFailure"
            exc_message = "Test failed without exception"
            traceback_str = str(report.longrepr) if report.longrepr else ""

        # Utwórz opis ticketu
        description = f"""## Test Failure

**Test:** `{test_nodeid}`
**File:** `{test_file}`

### Error
**Type:** {exc_type}
**Message:** {exc_message}

### Traceback
```
{traceback_str}
```

### Context
- **Duration:** {call.duration:.3f}s
- **Outcome:** {report.outcome}
"""

        # Generuj ID ticketu
        project = handler._get_project()
        existing = project.list_tickets()
        prefix = project.metadata.name[:4].upper() if project.metadata.name else "TEST"
        ticket_id = f"{prefix}-{len(existing) + 1}"

        # Utwórz ticket
        ticket = Ticket(
            id=ticket_id,
            title=f"[Test] {test_name}: {exc_type}",
            description=description,
            type=TicketType.BUG,
            priority=Priority.HIGH,
            labels=["test-failure", "pytest", "auto-reported"],
        )

        ticket.affected_files.append(test_file)

        project.add_ticket(ticket)
        project.save()

        print(f"\n[projektor] Test failure ticket created: {ticket_id}")

        return ticket

    except Exception as e:
        # Nie przerywaj testów jeśli projektor zawiedzie
        print(f"[projektor] Warning: Could not create ticket: {e}")
        return None


class ProjektorPlugin:
    """Klasa pluginu dla bardziej zaawansowanych przypadków."""

    def __init__(self, config=None):
        self.config = config
        self.failed_tests: list[dict[str, Any]] = []

    def pytest_runtest_logreport(self, report):
        """Loguj wyniki testów."""
        if report.failed:
            self.failed_tests.append({
                "nodeid": report.nodeid,
                "when": report.when,
                "outcome": report.outcome,
            })

    def pytest_sessionfinish(self, session, exitstatus):
        """Hook na koniec sesji testowej."""
        if self.failed_tests:
            print(f"\n[projektor] Session finished with {len(self.failed_tests)} failures")


def pytest_addoption(parser):
    """Dodaj opcje CLI dla pytest."""
    group = parser.getgroup("projektor")
    group.addoption(
        "--projektor",
        action="store_true",
        default=False,
        help="Enable projektor error tracking",
    )
    group.addoption(
        "--projektor-auto-fix",
        action="store_true",
        default=False,
        help="Enable auto-fix for test failures",
    )


def pytest_configure(config):
    """Konfiguracja na podstawie opcji CLI."""
    if config.getoption("--projektor", default=False):
        try:
            from projektor.integration.installer import install
            install(auto_fix=config.getoption("--projektor-auto-fix", default=False))
        except Exception as e:
            print(f"[projektor] Warning: Could not initialize: {e}")
