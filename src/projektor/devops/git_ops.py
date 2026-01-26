"""
GitOps - operacje na repozytorium Git.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Informacje o commicie."""

    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime

    @classmethod
    def from_git_log(cls, log_line: str) -> CommitInfo:
        """Parse z formatu git log."""
        parts = log_line.split("|")
        return cls(
            hash=parts[0],
            short_hash=parts[0][:7],
            message=parts[1] if len(parts) > 1 else "",
            author=parts[2] if len(parts) > 2 else "",
            date=datetime.fromisoformat(parts[3]) if len(parts) > 3 else datetime.now(),
        )


class GitOps:
    """
    Operacje Git.

    Wrapper na komendy git z obsługą błędów i logowaniem.

    Example:
        >>> git = GitOps("/path/to/repo")
        >>> git.stage("src/module.py")
        >>> git.commit("feat: Add new feature")
        >>> git.push()
    """

    def __init__(self, repo_path: Path | str):
        """
        Inicjalizacja.

        Args:
            repo_path: Ścieżka do repozytorium
        """
        self.repo_path = Path(repo_path).resolve()

        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run git command."""
        cmd = ["git", "-C", str(self.repo_path)] + list(args)
        logger.debug(f"Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )

    # ==================== Status ====================

    @property
    def current_branch(self) -> str:
        """Aktualna gałąź."""
        result = self._run("branch", "--show-current")
        return result.stdout.strip()

    @property
    def is_clean(self) -> bool:
        """Czy working directory jest czyste."""
        result = self._run("status", "--porcelain")
        return not result.stdout.strip()

    def status(self) -> dict[str, list[str]]:
        """Pełny status repozytorium."""
        result = self._run("status", "--porcelain")

        status = {
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": [],
        }

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            index_status = line[0]
            work_status = line[1]
            file_path = line[3:].strip()

            if index_status == "A" or index_status == "M":
                status["staged"].append(file_path)
            if work_status == "M":
                status["modified"].append(file_path)
            if index_status == "?" and work_status == "?":
                status["untracked"].append(file_path)
            if index_status == "D" or work_status == "D":
                status["deleted"].append(file_path)

        return status

    def has_changes(self) -> bool:
        """Czy są jakiekolwiek zmiany."""
        return not self.is_clean

    # ==================== Staging ====================

    def stage(self, *paths: str) -> bool:
        """Stage plików."""
        if not paths:
            return False

        try:
            self._run("add", *paths)
            return True
        except subprocess.CalledProcessError:
            return False

    def stage_all(self) -> bool:
        """Stage wszystkich zmian."""
        try:
            self._run("add", "-A")
            return True
        except subprocess.CalledProcessError:
            return False

    def unstage(self, *paths: str) -> bool:
        """Unstage plików."""
        if not paths:
            return False

        try:
            self._run("reset", "HEAD", "--", *paths)
            return True
        except subprocess.CalledProcessError:
            return False

    def unstage_all(self) -> bool:
        """Unstage wszystkich plików."""
        try:
            self._run("reset", "HEAD")
            return True
        except subprocess.CalledProcessError:
            return False

    def get_staged_files(self) -> list[str]:
        """Lista staged plików."""
        result = self._run("diff", "--cached", "--name-only")
        return [f for f in result.stdout.strip().split("\n") if f]

    # ==================== Commits ====================

    def commit(self, message: str, allow_empty: bool = False) -> str | None:
        """
        Utwórz commit.

        Args:
            message: Wiadomość commitu
            allow_empty: Czy pozwolić na pusty commit

        Returns:
            Hash commitu lub None
        """
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")

        try:
            self._run(*args)
            return self.get_last_commit().hash
        except subprocess.CalledProcessError:
            return None

    def get_last_commit(self) -> CommitInfo:
        """Pobierz ostatni commit."""
        result = self._run("log", "-1", "--format=%H|%s|%an|%aI")
        return CommitInfo.from_git_log(result.stdout.strip())

    def get_recent_commits(self, n: int = 10) -> list[CommitInfo]:
        """Pobierz ostatnie N commitów."""
        result = self._run("log", f"-{n}", "--format=%H|%s|%an|%aI")

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                commits.append(CommitInfo.from_git_log(line))

        return commits

    # ==================== Branches ====================

    def create_branch(self, name: str, checkout: bool = True) -> bool:
        """Utwórz nową gałąź."""
        try:
            self._run("branch", name)
            if checkout:
                self._run("checkout", name)
            return True
        except subprocess.CalledProcessError:
            return False

    def checkout(self, ref: str) -> bool:
        """Checkout gałęzi lub commitu."""
        try:
            self._run("checkout", ref)
            return True
        except subprocess.CalledProcessError:
            return False

    def merge(self, branch: str, no_ff: bool = False) -> bool:
        """Merge gałęzi."""
        args = ["merge", branch]
        if no_ff:
            args.append("--no-ff")

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def delete_branch(self, name: str, force: bool = False) -> bool:
        """Usuń gałąź."""
        flag = "-D" if force else "-d"
        try:
            self._run("branch", flag, name)
            return True
        except subprocess.CalledProcessError:
            return False

    def list_branches(self, remote: bool = False) -> list[str]:
        """Lista gałęzi."""
        args = ["branch"]
        if remote:
            args.append("-r")

        result = self._run(*args)
        branches = []

        for line in result.stdout.strip().split("\n"):
            branch = line.strip().lstrip("* ")
            if branch:
                branches.append(branch)

        return branches

    # ==================== Remote ====================

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
        set_upstream: bool = False,
    ) -> bool:
        """Push do remote."""
        args = ["push", remote]

        if branch:
            args.append(branch)

        if force:
            args.append("--force")

        if set_upstream:
            args.append("--set-upstream")

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def pull(self, remote: str = "origin", branch: str | None = None) -> bool:
        """Pull z remote."""
        args = ["pull", remote]
        if branch:
            args.append(branch)

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def fetch(self, remote: str = "origin", prune: bool = False) -> bool:
        """Fetch z remote."""
        args = ["fetch", remote]
        if prune:
            args.append("--prune")

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_remote_url(self, remote: str = "origin") -> str | None:
        """Pobierz URL remote."""
        try:
            result = self._run("remote", "get-url", remote)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    # ==================== Revert / Reset ====================

    def revert_file(self, path: str) -> bool:
        """Przywróć plik do stanu z HEAD."""
        try:
            self._run("checkout", "HEAD", "--", path)
            return True
        except subprocess.CalledProcessError:
            return False

    def reset_hard(self, ref: str = "HEAD") -> bool:
        """Hard reset do ref."""
        try:
            self._run("reset", "--hard", ref)
            return True
        except subprocess.CalledProcessError:
            return False

    def reset_soft(self, ref: str = "HEAD~1") -> bool:
        """Soft reset do ref."""
        try:
            self._run("reset", "--soft", ref)
            return True
        except subprocess.CalledProcessError:
            return False

    # ==================== Stash ====================

    def stash(self, message: str | None = None) -> bool:
        """Stash zmian."""
        args = ["stash", "push"]
        if message:
            args.extend(["-m", message])

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def stash_pop(self) -> bool:
        """Pop ostatniego stash."""
        try:
            self._run("stash", "pop")
            return True
        except subprocess.CalledProcessError:
            return False

    # ==================== Tags ====================

    def create_tag(
        self,
        name: str,
        message: str | None = None,
        ref: str = "HEAD",
    ) -> bool:
        """Utwórz tag."""
        args = ["tag"]
        if message:
            args.extend(["-a", name, "-m", message])
        else:
            args.append(name)
        args.append(ref)

        try:
            self._run(*args)
            return True
        except subprocess.CalledProcessError:
            return False

    def list_tags(self) -> list[str]:
        """Lista tagów."""
        result = self._run("tag", "-l")
        return [t for t in result.stdout.strip().split("\n") if t]

    # ==================== Diff ====================

    def diff(self, path: str | None = None, staged: bool = False) -> str:
        """Pobierz diff."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        if path:
            args.extend(["--", path])

        result = self._run(*args)
        return result.stdout

    def show_commit(self, ref: str = "HEAD") -> str:
        """Pokaż zawartość commitu."""
        result = self._run("show", ref)
        return result.stdout
