"""
Project model - reprezentacja projektu programistycznego.

Główna klasa zarządzająca kontekstem projektu, konfiguracją
i integracją z systemem plików.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from projektor.core.ticket import Ticket
    from projektor.planning.roadmap import Roadmap
    from projektor.planning.sprint import Sprint


@dataclass
class ProjectMetadata:
    """Metadane projektu."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    language: str = "python"
    authors: list[str] = field(default_factory=list)
    repository: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "language": self.language,
            "authors": self.authors,
            "repository": self.repository,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectMetadata:
        """Tworzenie z słownika."""
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            language=data.get("language", "python"),
            authors=data.get("authors", []),
            repository=data.get("repository"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now()
            ),
        )


@dataclass
class ProjectState:
    """Stan projektu - aktywne sprinty, tickety, etc."""

    current_sprint: str | None = None
    active_tickets: list[str] = field(default_factory=list)
    completed_tickets: list[str] = field(default_factory=list)
    blocked_tickets: list[str] = field(default_factory=list)

    # Metryki
    total_commits: int = 0
    total_tests_run: int = 0
    last_test_coverage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Konwersja do słownika."""
        return {
            "current_sprint": self.current_sprint,
            "active_tickets": self.active_tickets,
            "completed_tickets": self.completed_tickets,
            "blocked_tickets": self.blocked_tickets,
            "total_commits": self.total_commits,
            "total_tests_run": self.total_tests_run,
            "last_test_coverage": self.last_test_coverage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        """Tworzenie z słownika."""
        return cls(
            current_sprint=data.get("current_sprint"),
            active_tickets=data.get("active_tickets", []),
            completed_tickets=data.get("completed_tickets", []),
            blocked_tickets=data.get("blocked_tickets", []),
            total_commits=data.get("total_commits", 0),
            total_tests_run=data.get("total_tests_run", 0),
            last_test_coverage=data.get("last_test_coverage", 0.0),
        )


class Project:
    """
    Główna klasa projektu.

    Zarządza kontekstem projektu, konfiguracją i integracją
    z systemem plików oraz innymi komponentami.

    Example:
        >>> project = Project.load("/path/to/project")
        >>> print(project.metadata.name)
        >>> project.add_ticket(ticket)
        >>> project.save()
    """

    CONFIG_FILE = "projektor.yaml"
    STATE_FILE = ".projektor/state.json"
    TICKETS_DIR = ".projektor/tickets"

    def __init__(
        self,
        root_path: Path,
        metadata: ProjectMetadata | None = None,
        state: ProjectState | None = None,
    ):
        """
        Inicjalizacja projektu.

        Args:
            root_path: Ścieżka główna projektu
            metadata: Metadane projektu
            state: Stan projektu
        """
        self.root_path = Path(root_path).resolve()
        self.metadata = metadata or ProjectMetadata(name=self.root_path.name)
        self.state = state or ProjectState()

        # Cache
        self._tickets: dict[str, Ticket] = {}
        self._roadmap: Roadmap | None = None
        self._sprints: dict[str, Sprint] = {}

    @classmethod
    def load(cls, path: str | Path) -> Project:
        """
        Załaduj projekt z ścieżki.

        Args:
            path: Ścieżka do projektu

        Returns:
            Załadowany projekt

        Raises:
            FileNotFoundError: Gdy ścieżka nie istnieje
            ValueError: Gdy konfiguracja jest nieprawidłowa
        """
        root_path = Path(path).resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {root_path}")

        # Załaduj metadane z projektor.yaml
        config_file = root_path / cls.CONFIG_FILE
        metadata = None

        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                if config and "project" in config:
                    metadata = ProjectMetadata.from_dict(config["project"])

        if metadata is None:
            # Spróbuj odczytać z pyproject.toml
            pyproject = root_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib

                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                        if "project" in data:
                            metadata = ProjectMetadata(
                                name=data["project"].get("name", root_path.name),
                                version=data["project"].get("version", "0.1.0"),
                                description=data["project"].get("description", ""),
                            )
                except ImportError:
                    pass

        if metadata is None:
            metadata = ProjectMetadata(name=root_path.name)

        # Załaduj stan
        state_file = root_path / cls.STATE_FILE
        state = None

        if state_file.exists():
            with open(state_file) as f:
                state = ProjectState.from_dict(json.load(f))

        return cls(root_path, metadata, state)

    @classmethod
    def init(cls, path: str | Path, name: str | None = None) -> Project:
        """
        Inicjalizuj nowy projekt.

        Args:
            path: Ścieżka do projektu
            name: Nazwa projektu (domyślnie: nazwa katalogu)

        Returns:
            Nowy projekt
        """
        root_path = Path(path).resolve()
        root_path.mkdir(parents=True, exist_ok=True)

        # Utwórz strukturę .projektor
        projektor_dir = root_path / ".projektor"
        projektor_dir.mkdir(exist_ok=True)
        (projektor_dir / "tickets").mkdir(exist_ok=True)
        (projektor_dir / "sprints").mkdir(exist_ok=True)

        # Utwórz metadane
        metadata = ProjectMetadata(name=name or root_path.name)

        # Utwórz projekt
        project = cls(root_path, metadata, ProjectState())

        # Zapisz konfigurację
        project.save()

        return project

    def save(self) -> None:
        """Zapisz konfigurację i stan projektu."""
        # Upewnij się, że katalogi istnieją
        projektor_dir = self.root_path / ".projektor"
        projektor_dir.mkdir(exist_ok=True)

        # Zapisz projektor.yaml
        config_file = self.root_path / self.CONFIG_FILE
        config = {
            "project": self.metadata.to_dict(),
            "orchestration": {
                "auto_commit": True,
                "run_tests": True,
                "max_iterations": 10,
            },
            "targets": {
                "max_complexity": 15,
                "min_coverage": 85,
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        # Zapisz stan
        state_file = self.root_path / self.STATE_FILE
        state_file.parent.mkdir(exist_ok=True)

        with open(state_file, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)

    # ==================== Tickets ====================

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        """Pobierz ticket po ID."""
        if ticket_id in self._tickets:
            return self._tickets[ticket_id]

        # Spróbuj załadować z pliku
        ticket_file = self.root_path / self.TICKETS_DIR / f"{ticket_id}.json"
        if ticket_file.exists():
            from projektor.core.ticket import Ticket

            with open(ticket_file) as f:
                ticket = Ticket.from_dict(json.load(f))
                self._tickets[ticket_id] = ticket
                return ticket

        return None

    def add_ticket(self, ticket: Ticket) -> None:
        """Dodaj ticket do projektu."""
        self._tickets[ticket.id] = ticket
        self._save_ticket(ticket)

        if ticket.id not in self.state.active_tickets:
            self.state.active_tickets.append(ticket.id)

    def _save_ticket(self, ticket: Ticket) -> None:
        """Zapisz ticket do pliku."""
        tickets_dir = self.root_path / self.TICKETS_DIR
        tickets_dir.mkdir(parents=True, exist_ok=True)

        ticket_file = tickets_dir / f"{ticket.id}.json"
        with open(ticket_file, "w") as f:
            json.dump(ticket.to_dict(), f, indent=2)

    def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
    ) -> list[Ticket]:
        """
        Listuj tickety z opcjonalnym filtrowaniem.

        Args:
            status: Filtruj po statusie
            priority: Filtruj po priorytecie
            labels: Filtruj po etykietach

        Returns:
            Lista ticketów
        """
        # Załaduj wszystkie tickety
        tickets_dir = self.root_path / self.TICKETS_DIR
        if tickets_dir.exists():
            from projektor.core.ticket import Ticket

            for ticket_file in tickets_dir.glob("*.json"):
                ticket_id = ticket_file.stem
                if ticket_id not in self._tickets:
                    with open(ticket_file) as f:
                        self._tickets[ticket_id] = Ticket.from_dict(json.load(f))

        # Filtruj
        result = list(self._tickets.values())

        if status:
            result = [t for t in result if t.status.value == status]

        if priority:
            result = [t for t in result if t.priority.value == priority]

        if labels:
            result = [t for t in result if any(label in t.labels for label in labels)]

        return sorted(result, key=lambda t: (t.priority.value, t.created_at))

    # ==================== Paths ====================

    @property
    def src_path(self) -> Path:
        """Ścieżka do kodu źródłowego."""
        # Sprawdź typowe lokalizacje
        for src_dir in ["src", "lib", self.metadata.name]:
            path = self.root_path / src_dir
            if path.exists():
                return path
        return self.root_path

    @property
    def tests_path(self) -> Path:
        """Ścieżka do testów."""
        for test_dir in ["tests", "test"]:
            path = self.root_path / test_dir
            if path.exists():
                return path
        return self.root_path / "tests"

    @property
    def toon_file(self) -> Path | None:
        """Ścieżka do pliku TOON."""
        for pattern in ["*.toon", "project*.toon", "*_functions.toon"]:
            files = list(self.root_path.glob(pattern))
            if files:
                return files[0]
        return None

    # ==================== Git ====================

    @property
    def is_git_repo(self) -> bool:
        """Czy projekt jest repozytorium Git."""
        return (self.root_path / ".git").exists()

    def get_git_remote(self) -> str | None:
        """Pobierz URL zdalnego repozytorium."""
        if not self.is_git_repo:
            return None

        import subprocess

        try:
            result = subprocess.run(
                ["git", "-C", str(self.root_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    # ==================== Representation ====================

    def __repr__(self) -> str:
        return f"Project({self.metadata.name!r}, path={self.root_path})"

    def __str__(self) -> str:
        return f"{self.metadata.name} v{self.metadata.version}"
