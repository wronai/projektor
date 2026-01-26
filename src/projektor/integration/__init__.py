"""
Projektor Integration Module.

Moduł do integracji projektora z dowolnymi projektami Python.
Przechwytuje błędy, tworzy tickety i uruchamia naprawy automatycznie.

Użycie:
    # Automatyczna instalacja (zalecane)
    from projektor import install
    install()
    
    # Jako dekorator
    from projektor import track_errors, track_async_errors
    
    @track_errors(auto_fix=True)
    def my_function():
        ...
    
    @track_async_errors
    async def my_async_function():
        ...
    
    # Jako context manager
    from projektor import ErrorTracker
    
    with ErrorTracker() as tracker:
        risky_operation()
        if tracker.had_error:
            print(f"Error: {tracker.error}")
    
    # Globalny handler (niskopoziomowe API)
    from projektor.integration import install_global_handler
    install_global_handler()
"""

from projektor.integration.error_handler import (
    ErrorHandler,
    catch_errors,
    install_global_handler,
    projektor_guard,
    uninstall_global_handler,
)
from projektor.integration.hooks import (
    Hook,
    HookType,
    Hooks,
    on_error,
    on_start,
    on_success,
)
from projektor.integration.config_loader import (
    IntegrationConfig,
    load_from_pyproject,
    load_integration_config,
)
from projektor.integration.installer import (
    install,
    uninstall,
    is_installed,
    get_handler,
    load_config,
)
from projektor.integration.decorators import (
    track_errors,
    track_async_errors,
    ErrorTracker,
    catch_async_errors,
)

__all__ = [
    # Install API (główne API)
    "install",
    "uninstall",
    "is_installed",
    "get_handler",
    "load_config",
    # Decorators
    "track_errors",
    "track_async_errors",
    "catch_errors",
    "catch_async_errors",
    # Context managers
    "ErrorTracker",
    "projektor_guard",
    # Error handling (niskopoziomowe)
    "ErrorHandler",
    "install_global_handler",
    "uninstall_global_handler",
    # Hooks
    "Hook",
    "HookType",
    "Hooks",
    "on_error",
    "on_start",
    "on_success",
    # Config
    "IntegrationConfig",
    "load_integration_config",
    "load_from_pyproject",
]
