"""
Configuration management for Projektor.

Obsługuje konfigurację projektu, LLM, DevOps i innych komponentów.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    """Konfiguracja modelu LLM."""

    model: str = "openrouter/x-ai/grok-3-fast"
    temperature: float = 0.1
    max_tokens: int = 4000
    api_key: str | None = None
    api_base: str | None = None

    def __post_init__(self):
        # Allow env overrides for default values
        env_model = os.environ.get("OPENROUTER_MODEL")
        if env_model and self.model == "openrouter/x-ai/grok-3-fast":
            if not env_model.startswith("openrouter/"):
                env_model = f"openrouter/{env_model}"
            self.model = env_model

        env_temperature = os.environ.get("OPENROUTER_TEMPERATURE")
        if env_temperature and self.temperature == 0.1:
            try:
                self.temperature = float(env_temperature)
            except ValueError:
                pass

        env_max_tokens = os.environ.get("OPENROUTER_MAX_TOKENS")
        if env_max_tokens and self.max_tokens == 4000:
            try:
                self.max_tokens = int(env_max_tokens)
            except ValueError:
                pass

        # Pobierz klucz z environment jeśli nie podany
        if self.api_key is None:
            self.api_key = (
                os.environ.get("OPENROUTER_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("ANTHROPIC_API_KEY")
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMConfig:
        return cls(
            model=data.get("model", "openrouter/x-ai/grok-3-fast"),
            temperature=data.get("temperature", 0.1),
            max_tokens=data.get("max_tokens", 4000),
            api_key=data.get("api_key"),
            api_base=data.get("api_base"),
        )


@dataclass
class OrchestrationConfig:
    """Konfiguracja orkiestracji."""

    auto_commit: bool = True
    run_tests: bool = True
    require_review: bool = False
    max_iterations: int = 10
    on_error: str = "stop"  # stop, continue, rollback
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_commit": self.auto_commit,
            "run_tests": self.run_tests,
            "require_review": self.require_review,
            "max_iterations": self.max_iterations,
            "on_error": self.on_error,
            "dry_run": self.dry_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrchestrationConfig:
        return cls(
            auto_commit=data.get("auto_commit", True),
            run_tests=data.get("run_tests", True),
            require_review=data.get("require_review", False),
            max_iterations=data.get("max_iterations", 10),
            on_error=data.get("on_error", "stop"),
            dry_run=data.get("dry_run", False),
        )


@dataclass
class TargetsConfig:
    """Konfiguracja celów jakościowych."""

    max_complexity: int = 15
    min_coverage: float = 85.0
    max_function_lines: int = 50
    max_file_lines: int = 500

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_complexity": self.max_complexity,
            "min_coverage": self.min_coverage,
            "max_function_lines": self.max_function_lines,
            "max_file_lines": self.max_file_lines,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetsConfig:
        return cls(
            max_complexity=data.get("max_complexity", 15),
            min_coverage=data.get("min_coverage", 85.0),
            max_function_lines=data.get("max_function_lines", 50),
            max_file_lines=data.get("max_file_lines", 500),
        )


@dataclass
class GitConfig:
    """Konfiguracja Git."""

    branch_prefix: str = "feature/"
    commit_style: str = "conventional"  # conventional, simple
    auto_push: bool = False
    remote: str = "origin"
    default_branch: str = "main"

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_prefix": self.branch_prefix,
            "commit_style": self.commit_style,
            "auto_push": self.auto_push,
            "remote": self.remote,
            "default_branch": self.default_branch,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitConfig:
        return cls(
            branch_prefix=data.get("branch_prefix", "feature/"),
            commit_style=data.get("commit_style", "conventional"),
            auto_push=data.get("auto_push", False),
            remote=data.get("remote", "origin"),
            default_branch=data.get("default_branch", "main"),
        )


@dataclass
class CIConfig:
    """Konfiguracja CI/CD."""

    provider: str = "github-actions"  # github-actions, gitlab-ci, jenkins
    run_on_commit: bool = True
    run_on_pr: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "run_on_commit": self.run_on_commit,
            "run_on_pr": self.run_on_pr,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CIConfig:
        return cls(
            provider=data.get("provider", "github-actions"),
            run_on_commit=data.get("run_on_commit", True),
            run_on_pr=data.get("run_on_pr", True),
        )


@dataclass
class NotificationsConfig:
    """Konfiguracja powiadomień."""

    slack_webhook: str | None = None
    discord_webhook: str | None = None
    email_recipients: list[str] = field(default_factory=list)
    on_success: bool = False
    on_failure: bool = True

    def __post_init__(self):
        # Pobierz z environment jeśli nie podane
        if self.slack_webhook is None:
            self.slack_webhook = os.environ.get("SLACK_WEBHOOK")
        if self.discord_webhook is None:
            self.discord_webhook = os.environ.get("DISCORD_WEBHOOK")

    def to_dict(self) -> dict[str, Any]:
        return {
            "on_success": self.on_success,
            "on_failure": self.on_failure,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationsConfig:
        return cls(
            slack_webhook=data.get("slack_webhook"),
            discord_webhook=data.get("discord_webhook"),
            email_recipients=data.get("email_recipients", []),
            on_success=data.get("on_success", False),
            on_failure=data.get("on_failure", True),
        )


@dataclass
class DevOpsConfig:
    """Konfiguracja DevOps."""

    git: GitConfig = field(default_factory=GitConfig)
    ci: CIConfig = field(default_factory=CIConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "git": self.git.to_dict(),
            "ci": self.ci.to_dict(),
            "notifications": self.notifications.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevOpsConfig:
        return cls(
            git=GitConfig.from_dict(data.get("git", {})),
            ci=CIConfig.from_dict(data.get("ci", {})),
            notifications=NotificationsConfig.from_dict(data.get("notifications", {})),
        )


@dataclass
class ProjectConfig:
    """Główna konfiguracja projektu."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    language: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            language=data.get("language", "python"),
        )


@dataclass
class Config:
    """
    Pełna konfiguracja Projektora.

    Zbiera wszystkie komponenty konfiguracji w jednym miejscu.
    Może być załadowana z pliku projektor.yaml lub utworzona programowo.

    Example:
        >>> config = Config.load("/path/to/project/projektor.yaml")
        >>> print(config.llm.model)
        >>> config.orchestration.auto_commit = False
        >>> config.save("/path/to/project/projektor.yaml")
    """

    project: ProjectConfig = field(default_factory=lambda: ProjectConfig(name="unknown"))
    llm: LLMConfig = field(default_factory=LLMConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    targets: TargetsConfig = field(default_factory=TargetsConfig)
    devops: DevOpsConfig = field(default_factory=DevOpsConfig)

    # Custom extensions
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "project": self.project.to_dict(),
            "llm": self.llm.to_dict(),
            "orchestration": self.orchestration.to_dict(),
            "targets": self.targets.to_dict(),
            "devops": self.devops.to_dict(),
            "extensions": self.extensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Tworzenie z słownika."""
        return cls(
            project=ProjectConfig.from_dict(data.get("project", {})),
            llm=LLMConfig.from_dict(data.get("llm", {})),
            orchestration=OrchestrationConfig.from_dict(data.get("orchestration", {})),
            targets=TargetsConfig.from_dict(data.get("targets", {})),
            devops=DevOpsConfig.from_dict(data.get("devops", {})),
            extensions=data.get("extensions", {}),
        )

    @classmethod
    def load(cls, path: str | Path) -> Config:
        """
        Załaduj konfigurację z pliku YAML.

        Args:
            path: Ścieżka do pliku konfiguracji

        Returns:
            Załadowana konfiguracja
        """
        path = Path(path)

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data or {})

    def save(self, path: str | Path) -> None:
        """
        Zapisz konfigurację do pliku YAML.

        Args:
            path: Ścieżka do pliku konfiguracji
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(
                self.to_dict(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    @classmethod
    def default(cls, project_name: str = "unknown") -> Config:
        """Utwórz domyślną konfigurację."""
        return cls(
            project=ProjectConfig(name=project_name),
            llm=LLMConfig(),
            orchestration=OrchestrationConfig(),
            targets=TargetsConfig(),
            devops=DevOpsConfig(),
        )


# Globalna instancja konfiguracji (opcjonalna)
_global_config: Config | None = None


def get_config() -> Config:
    """Pobierz globalną konfigurację."""
    global _global_config
    if _global_config is None:
        _global_config = Config.default()
    return _global_config


def set_config(config: Config) -> None:
    """Ustaw globalną konfigurację."""
    global _global_config
    _global_config = config


def load_config(path: str | Path) -> Config:
    """Załaduj i ustaw globalną konfigurację."""
    config = Config.load(path)
    set_config(config)
    return config
