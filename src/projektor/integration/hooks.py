"""
Hooks - system hooków do uruchamiania akcji na zdarzeniach.

Podobny do CI/CD workflows, ale konfigurowany lokalnie.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from projektor.core.events import Event, EventBus


class HookType(Enum):
    """Typy hooków."""

    ON_ERROR = "on_error"
    ON_START = "on_start"
    ON_SUCCESS = "on_success"
    ON_TEST_FAIL = "on_test_fail"
    ON_COMMIT = "on_commit"
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"


@dataclass
class Hook:
    """
    Pojedynczy hook - akcja uruchamiana na zdarzeniu.

    Example:
        hook = Hook(
            name="report-error",
            hook_type=HookType.ON_ERROR,
            action=lambda ctx: print(f"Error: {ctx['error']}")
        )
    """

    name: str
    hook_type: HookType
    action: Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Coroutine]
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)

    async def execute(self, context: dict[str, Any]) -> Any:
        """Wykonaj hook jeśli warunki są spełnione."""
        if not self.enabled:
            return None

        # Sprawdź warunki
        for key, expected in self.conditions.items():
            if context.get(key) != expected:
                return None

        # Wykonaj akcję
        if asyncio.iscoroutinefunction(self.action):
            return await self.action(context)
        else:
            return self.action(context)


class Hooks:
    """
    Manager hooków - rejestruje i uruchamia hooki.

    Example:
        hooks = Hooks()

        @hooks.on_error
        def handle_error(ctx):
            print(f"Error occurred: {ctx['error']}")

        @hooks.on_success
        async def notify_success(ctx):
            await send_notification(ctx['result'])

        # Uruchom hooki
        await hooks.trigger(HookType.ON_ERROR, {"error": error})
    """

    def __init__(self):
        self._hooks: dict[HookType, list[Hook]] = {t: [] for t in HookType}
        self._event_bus: EventBus | None = None

    def register(self, hook: Hook) -> None:
        """Zarejestruj hook."""
        self._hooks[hook.hook_type].append(hook)

    def unregister(self, name: str) -> bool:
        """Wyrejestruj hook po nazwie."""
        for hook_type, hooks in self._hooks.items():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    del self._hooks[hook_type][i]
                    return True
        return False

    async def trigger(
        self,
        hook_type: HookType,
        context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Uruchom wszystkie hooki danego typu."""
        context = context or {}
        results = []

        for hook in self._hooks[hook_type]:
            try:
                result = await hook.execute(context)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "hook": hook.name})

        return results

    def trigger_sync(
        self,
        hook_type: HookType,
        context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Synchroniczna wersja trigger."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.trigger(hook_type, context))
                    return future.result()
            return loop.run_until_complete(self.trigger(hook_type, context))
        except RuntimeError:
            return asyncio.run(self.trigger(hook_type, context))

    # ==================== Decorator shortcuts ====================

    def on_error(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        conditions: dict[str, Any] | None = None,
    ):
        """Dekorator do rejestracji hooka ON_ERROR."""
        return self._make_decorator(HookType.ON_ERROR, func, name, conditions)

    def on_start(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        conditions: dict[str, Any] | None = None,
    ):
        """Dekorator do rejestracji hooka ON_START."""
        return self._make_decorator(HookType.ON_START, func, name, conditions)

    def on_success(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        conditions: dict[str, Any] | None = None,
    ):
        """Dekorator do rejestracji hooka ON_SUCCESS."""
        return self._make_decorator(HookType.ON_SUCCESS, func, name, conditions)

    def on_test_fail(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        conditions: dict[str, Any] | None = None,
    ):
        """Dekorator do rejestracji hooka ON_TEST_FAIL."""
        return self._make_decorator(HookType.ON_TEST_FAIL, func, name, conditions)

    def on_commit(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        conditions: dict[str, Any] | None = None,
    ):
        """Dekorator do rejestracji hooka ON_COMMIT."""
        return self._make_decorator(HookType.ON_COMMIT, func, name, conditions)

    def _make_decorator(
        self,
        hook_type: HookType,
        func: Callable | None,
        name: str | None,
        conditions: dict[str, Any] | None,
    ):
        """Tworzy dekorator dla danego typu hooka."""

        def decorator(fn: Callable) -> Callable:
            hook = Hook(
                name=name or fn.__name__,
                hook_type=hook_type,
                action=fn,
                conditions=conditions or {},
            )
            self.register(hook)
            return fn

        if func is not None:
            return decorator(func)
        return decorator


# ==================== Global Hooks Instance ====================

_global_hooks = Hooks()


def on_error(
    func: Callable | None = None,
    *,
    name: str | None = None,
    conditions: dict[str, Any] | None = None,
):
    """Globalny dekorator dla ON_ERROR."""
    return _global_hooks.on_error(func, name=name, conditions=conditions)


def on_start(
    func: Callable | None = None,
    *,
    name: str | None = None,
    conditions: dict[str, Any] | None = None,
):
    """Globalny dekorator dla ON_START."""
    return _global_hooks.on_start(func, name=name, conditions=conditions)


def on_success(
    func: Callable | None = None,
    *,
    name: str | None = None,
    conditions: dict[str, Any] | None = None,
):
    """Globalny dekorator dla ON_SUCCESS."""
    return _global_hooks.on_success(func, name=name, conditions=conditions)


def get_global_hooks() -> Hooks:
    """Pobierz globalną instancję hooków."""
    return _global_hooks
