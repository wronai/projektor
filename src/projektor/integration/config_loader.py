"""
Config Loader - ładowanie konfiguracji integracji z pyproject.toml i projektor.yaml.

Obsługuje:
- Sekcję [tool.projektor] w pyproject.toml
- Sekcję 'integration' w projektor.yaml
- Zmienne środowiskowe
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WorkflowConfig:
    """Konfiguracja pojedynczego workflow."""

    name: str
    trigger: str  # on_error, on_test_fail, on_commit, etc.
    enabled: bool = True
    auto_fix: bool = False
    priority: str = "high"
    labels: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> WorkflowConfig:
        return cls(
            name=name,
            trigger=data.get("trigger", "on_error"),
            enabled=data.get("enabled", True),
            auto_fix=data.get("auto_fix", False),
            priority=data.get("priority", "high"),
            labels=data.get("labels", []),
            conditions=data.get("conditions", {}),
        )


@dataclass
class IntegrationConfig:
    """
    Konfiguracja integracji projektora z projektem.

    Może być załadowana z:
    - pyproject.toml: [tool.projektor]
    - projektor.yaml: sekcja 'integration'

    Example pyproject.toml:
        [tool.projektor]
        enabled = true
        auto_fix = false
        priority = "high"

        [tool.projektor.workflows.error-reporter]
        trigger = "on_error"
        auto_fix = true
        labels = ["auto-reported", "runtime-error"]

    Example projektor.yaml:
        integration:
          enabled: true
          auto_fix: false
          global_handler: true

          workflows:
            error-reporter:
              trigger: on_error
              auto_fix: true
              labels:
                - auto-reported
                - runtime-error
    """

    enabled: bool = True
    global_handler: bool = False
    auto_fix: bool = False
    priority: str = "high"
    default_labels: list[str] = field(default_factory=lambda: ["projektor"])
    workflows: list[WorkflowConfig] = field(default_factory=list)

    # Paths
    tickets_dir: str = ".projektor/tickets"
    state_file: str = ".projektor/state.json"

    # Watch paths (dla file watcher)
    watch_paths: list[str] = field(default_factory=lambda: ["src", "tests"])
    ignore_patterns: list[str] = field(default_factory=lambda: [
        "*.pyc", "__pycache__", ".git", ".venv", "venv",
        "*.egg-info", ".projektor", "htmlcov", ".coverage", "*.log"
    ])

    # Reporting
    report_to_console: bool = True
    report_to_file: bool = True
    report_file: str = ".projektor/errors.log"

    # GitHub Issues (opcjonalnie)
    create_github_issues: bool = False
    github_repo: str | None = None

    # Notifications
    notify_on_error: bool = True
    notify_on_fix: bool = True

    # Ignore specific errors
    ignore_errors: list[str] = field(default_factory=lambda: [
        "KeyboardInterrupt", "SystemExit"
    ])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationConfig:
        """Utwórz konfigurację ze słownika."""
        workflows = []
        workflows_data = data.get("workflows", {})

        for name, wf_data in workflows_data.items():
            if isinstance(wf_data, dict):
                workflows.append(WorkflowConfig.from_dict(name, wf_data))

        return cls(
            enabled=data.get("enabled", True),
            global_handler=data.get("global_handler", False),
            auto_fix=data.get("auto_fix", False),
            priority=data.get("priority", "high"),
            default_labels=data.get("default_labels", ["projektor"]),
            workflows=workflows,
            tickets_dir=data.get("tickets_dir", ".projektor/tickets"),
            state_file=data.get("state_file", ".projektor/state.json"),
            watch_paths=data.get("watch_paths", ["src", "tests"]),
            ignore_patterns=data.get("ignore_patterns", [
                "*.pyc", "__pycache__", ".git", ".venv", "venv",
                "*.egg-info", ".projektor", "htmlcov", ".coverage", "*.log"
            ]),
            report_to_console=data.get("report_to_console", True),
            report_to_file=data.get("report_to_file", True),
            report_file=data.get("report_file", ".projektor/errors.log"),
            create_github_issues=data.get("create_github_issues", False),
            github_repo=data.get("github_repo"),
            notify_on_error=data.get("notify_on_error", True),
            notify_on_fix=data.get("notify_on_fix", True),
            ignore_errors=data.get("ignore_errors", ["KeyboardInterrupt", "SystemExit"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "enabled": self.enabled,
            "global_handler": self.global_handler,
            "auto_fix": self.auto_fix,
            "priority": self.priority,
            "default_labels": self.default_labels,
            "workflows": {
                wf.name: {
                    "trigger": wf.trigger,
                    "enabled": wf.enabled,
                    "auto_fix": wf.auto_fix,
                    "priority": wf.priority,
                    "labels": wf.labels,
                    "conditions": wf.conditions,
                }
                for wf in self.workflows
            },
            "tickets_dir": self.tickets_dir,
            "state_file": self.state_file,
            "watch_paths": self.watch_paths,
            "ignore_patterns": self.ignore_patterns,
            "report_to_console": self.report_to_console,
            "report_to_file": self.report_to_file,
            "report_file": self.report_file,
            "create_github_issues": self.create_github_issues,
            "github_repo": self.github_repo,
            "notify_on_error": self.notify_on_error,
            "notify_on_fix": self.notify_on_fix,
            "ignore_errors": self.ignore_errors,
        }


def load_from_pyproject(path: str | Path) -> IntegrationConfig | None:
    """
    Załaduj konfigurację z pyproject.toml.

    Szuka sekcji [tool.projektor].

    Args:
        path: Ścieżka do pyproject.toml

    Returns:
        IntegrationConfig lub None jeśli brak sekcji
    """
    path = Path(path)

    if not path.exists():
        return None

    try:
        # Python 3.11+
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except ImportError:
        # Fallback dla starszych wersji
        try:
            import toml
            with open(path) as f:
                data = toml.load(f)
        except ImportError:
            # Ręczne parsowanie podstawowej konfiguracji
            return _parse_pyproject_manual(path)

    tool_section = data.get("tool", {})
    projektor_config = tool_section.get("projektor", {})

    if not projektor_config:
        return None

    return IntegrationConfig.from_dict(projektor_config)


def _parse_pyproject_manual(path: Path) -> IntegrationConfig | None:
    """Ręczne parsowanie pyproject.toml gdy brak biblioteki toml."""
    content = path.read_text()

    if "[tool.projektor]" not in content:
        return None

    # Podstawowe parsowanie - zwróć domyślną konfigurację
    config = IntegrationConfig()

    # Sprawdź podstawowe ustawienia
    if "enabled = false" in content.lower():
        config.enabled = False
    if "auto_fix = true" in content.lower():
        config.auto_fix = True
    if "global_handler = true" in content.lower():
        config.global_handler = True

    return config


def load_from_projektor_yaml(path: str | Path) -> IntegrationConfig | None:
    """
    Załaduj konfigurację z projektor.yaml.

    Szuka sekcji 'integration'.

    Args:
        path: Ścieżka do projektor.yaml

    Returns:
        IntegrationConfig lub None jeśli brak sekcji
    """
    path = Path(path)

    if not path.exists():
        return None

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    integration_config = data.get("integration", {})

    if not integration_config:
        return None

    return IntegrationConfig.from_dict(integration_config)


def load_integration_config(project_path: str | Path | None = None) -> IntegrationConfig:
    """
    Załaduj konfigurację integracji z projektu.

    Szuka w kolejności:
    1. projektor.yaml (sekcja 'integration')
    2. pyproject.toml (sekcja [tool.projektor])
    3. Zmienne środowiskowe
    4. Domyślna konfiguracja

    Args:
        project_path: Ścieżka do projektu (domyślnie cwd)

    Returns:
        IntegrationConfig
    """
    if project_path is None:
        project_path = Path.cwd()
    else:
        project_path = Path(project_path)

    # 1. Spróbuj projektor.yaml
    projektor_yaml = project_path / "projektor.yaml"
    config = load_from_projektor_yaml(projektor_yaml)
    if config is not None:
        return _apply_env_overrides(config)

    # 2. Spróbuj pyproject.toml
    pyproject = project_path / "pyproject.toml"
    config = load_from_pyproject(pyproject)
    if config is not None:
        return _apply_env_overrides(config)

    # 3. Szukaj w parent directories
    current = project_path.parent
    while current != current.parent:
        projektor_yaml = current / "projektor.yaml"
        if projektor_yaml.exists():
            config = load_from_projektor_yaml(projektor_yaml)
            if config is not None:
                return _apply_env_overrides(config)

        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            config = load_from_pyproject(pyproject)
            if config is not None:
                return _apply_env_overrides(config)

        current = current.parent

    # 4. Domyślna konfiguracja z env
    return _apply_env_overrides(IntegrationConfig())


def _apply_env_overrides(config: IntegrationConfig) -> IntegrationConfig:
    """Zastosuj nadpisania ze zmiennych środowiskowych."""
    if os.environ.get("PROJEKTOR_ENABLED", "").lower() == "false":
        config.enabled = False
    elif os.environ.get("PROJEKTOR_ENABLED", "").lower() == "true":
        config.enabled = True

    if os.environ.get("PROJEKTOR_AUTO_FIX", "").lower() == "true":
        config.auto_fix = True

    if os.environ.get("PROJEKTOR_GLOBAL_HANDLER", "").lower() == "true":
        config.global_handler = True

    priority = os.environ.get("PROJEKTOR_PRIORITY")
    if priority in ("critical", "high", "medium", "low"):
        config.priority = priority

    return config


def save_integration_config(
    config: IntegrationConfig,
    path: str | Path,
    format: str = "yaml",
) -> None:
    """
    Zapisz konfigurację integracji.

    Args:
        config: Konfiguracja do zapisania
        path: Ścieżka do pliku
        format: Format pliku ('yaml' lub 'toml')
    """
    path = Path(path)

    if format == "yaml":
        # Dopisz do istniejącego projektor.yaml
        existing = {}
        if path.exists():
            with open(path) as f:
                existing = yaml.safe_load(f) or {}

        existing["integration"] = config.to_dict()

        with open(path, "w") as f:
            yaml.dump(
                existing,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    elif format == "toml":
        # Generuj sekcję TOML
        toml_content = _generate_toml_section(config)

        # Dopisz do pyproject.toml
        if path.exists():
            existing = path.read_text()
            if "[tool.projektor]" not in existing:
                with open(path, "a") as f:
                    f.write("\n" + toml_content)
        else:
            with open(path, "w") as f:
                f.write(toml_content)


def _generate_toml_section(config: IntegrationConfig) -> str:
    """Generuj sekcję TOML dla pyproject.toml."""
    lines = [
        "[tool.projektor]",
        f"enabled = {str(config.enabled).lower()}",
        f"global_handler = {str(config.global_handler).lower()}",
        f"auto_fix = {str(config.auto_fix).lower()}",
        f'priority = "{config.priority}"',
    ]

    if config.default_labels:
        labels_str = ", ".join(f'"{l}"' for l in config.default_labels)
        lines.append(f"default_labels = [{labels_str}]")

    # Workflows
    for wf in config.workflows:
        lines.extend([
            "",
            f"[tool.projektor.workflows.{wf.name}]",
            f'trigger = "{wf.trigger}"',
            f"enabled = {str(wf.enabled).lower()}",
            f"auto_fix = {str(wf.auto_fix).lower()}",
            f'priority = "{wf.priority}"',
        ])
        if wf.labels:
            labels_str = ", ".join(f'"{l}"' for l in wf.labels)
            lines.append(f"labels = [{labels_str}]")

    return "\n".join(lines)
