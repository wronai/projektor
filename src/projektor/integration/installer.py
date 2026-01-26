"""
Installer - funkcja install() do automatycznej instalacji handlerów.

Użycie:
    from projektor import install
    install()  # Włącza wszystkie handlery zgodnie z konfiguracją
"""

from __future__ import annotations

import atexit
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from projektor.integration.config_loader import IntegrationConfig, load_integration_config
from projektor.integration.error_handler import ErrorHandler

# Flaga czy projektor jest zainstalowany
_installed = False
_handler: ErrorHandler | None = None
_original_excepthook = None
_original_threading_excepthook = None


def install(
    project_path: str | Path | None = None,
    config: IntegrationConfig | None = None,
    auto_fix: bool | None = None,
    global_handler: bool | None = None,
    on_error: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    """
    Zainstaluj projektor w aplikacji.

    Automatycznie konfiguruje:
    - sys.excepthook dla nieobsłużonych wyjątków
    - threading.excepthook dla wyjątków w wątkach
    - faulthandler dla segfaultów
    - atexit handler dla cleanup

    Args:
        project_path: Ścieżka do projektu (domyślnie cwd)
        config: Konfiguracja (domyślnie ładowana z plików)
        auto_fix: Nadpisz ustawienie auto_fix z konfiguracji
        global_handler: Nadpisz ustawienie global_handler
        on_error: Callback wywoływany przy każdym błędzie

    Returns:
        True jeśli instalacja się powiodła

    Example:
        # W __init__.py projektu:
        try:
            from projektor import install
            install()
        except ImportError:
            pass
    """
    global _installed, _handler, _original_excepthook, _original_threading_excepthook

    if _installed:
        return True

    # Załaduj konfigurację
    if config is None:
        config = load_integration_config(project_path)

    if not config.enabled:
        return False

    # Nadpisz ustawienia jeśli podane
    if auto_fix is not None:
        config.auto_fix = auto_fix
    if global_handler is not None:
        config.global_handler = global_handler

    # Utwórz handler
    _handler = ErrorHandler(
        project_path=project_path,
        auto_fix=config.auto_fix,
        on_error=on_error,
    )

    # Zainstaluj handlery
    if config.global_handler:
        _install_excepthook()
        _install_threading_excepthook()
        _install_faulthandler()

    # Zarejestruj cleanup
    atexit.register(_cleanup)

    _installed = True

    # Log instalacji jeśli verbose
    if config.notify_on_error:
        print(f"[projektor] Installed for {_handler.project_path.name}")

    return True


def uninstall() -> None:
    """Odinstaluj projektor i przywróć oryginalne handlery."""
    global _installed, _handler, _original_excepthook, _original_threading_excepthook

    if not _installed:
        return

    # Przywróć oryginalne handlery
    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
        _original_excepthook = None

    if _original_threading_excepthook is not None:
        threading.excepthook = _original_threading_excepthook
        _original_threading_excepthook = None

    _handler = None
    _installed = False


def is_installed() -> bool:
    """Sprawdź czy projektor jest zainstalowany."""
    return _installed


def get_handler() -> ErrorHandler | None:
    """Pobierz aktywny handler."""
    return _handler


def _install_excepthook() -> None:
    """Zainstaluj sys.excepthook."""
    global _original_excepthook

    _original_excepthook = sys.excepthook

    def projektor_excepthook(exc_type, exc_value, exc_tb):
        # Nie obsługuj KeyboardInterrupt i SystemExit
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            _original_excepthook(exc_type, exc_value, exc_tb)
            return

        # Obsłuż błąd
        if _handler is not None:
            try:
                import traceback
                tb = traceback.TracebackException(exc_type, exc_value, exc_tb)
                report = _handler._extract_error_info(exc_value, tb)
                ticket = _handler.create_bug_ticket(report)
                print(f"\n[projektor] Bug ticket created: {ticket.id}")
            except Exception as e:
                print(f"[projektor] Error creating ticket: {e}")

        # Wywołaj oryginalny excepthook
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = projektor_excepthook


def _install_threading_excepthook() -> None:
    """Zainstaluj threading.excepthook dla błędów w wątkach."""
    global _original_threading_excepthook

    _original_threading_excepthook = threading.excepthook

    def projektor_threading_excepthook(args):
        # Obsłuż błąd
        if _handler is not None and args.exc_value is not None:
            try:
                import traceback
                tb = traceback.TracebackException(
                    type(args.exc_value),
                    args.exc_value,
                    args.exc_traceback,
                )
                report = _handler._extract_error_info(args.exc_value, tb)
                report.context["thread"] = args.thread.name if args.thread else "unknown"
                ticket = _handler.create_bug_ticket(report)
                print(f"\n[projektor] Bug ticket created (thread): {ticket.id}")
            except Exception as e:
                print(f"[projektor] Error creating ticket: {e}")

        # Wywołaj oryginalny handler
        if _original_threading_excepthook is not None:
            _original_threading_excepthook(args)

    threading.excepthook = projektor_threading_excepthook


def _install_faulthandler() -> None:
    """Zainstaluj faulthandler dla segfaultów."""
    try:
        import faulthandler
        faulthandler.enable()
    except Exception:
        pass


def _cleanup() -> None:
    """Cleanup przy wyjściu z aplikacji."""
    pass  # Na razie nic do czyszczenia


# ==================== Convenience aliases ====================

def load_config(project_path: str | Path | None = None) -> IntegrationConfig:
    """Załaduj konfigurację projektora."""
    return load_integration_config(project_path)
