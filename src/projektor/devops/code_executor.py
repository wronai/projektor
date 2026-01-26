"""
CodeExecutor - bezpieczne wykonywanie zmian w kodzie.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """Reprezentacja zmiany w kodzie."""

    file_path: str
    change_type: str  # create, modify, delete, rename

    # Content
    old_content: str | None = None
    new_content: str | None = None

    # For rename
    new_path: str | None = None

    # Diff info
    lines_added: int = 0
    lines_removed: int = 0

    # Backup
    backup_path: str | None = None

    # Status
    applied: bool = False
    applied_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "new_path": self.new_path,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "applied": self.applied,
        }


class CodeExecutor:
    """
    Bezpieczny executor zmian w kodzie.

    Features:
    - Automatyczny backup przed zmianami
    - Walidacja składni przed zapisem
    - Atomic operations z rollback
    - Dry-run mode

    Example:
        >>> executor = CodeExecutor(project_path)
        >>> change = CodeChange(
        ...     file_path="src/module.py",
        ...     change_type="modify",
        ...     new_content="# New content"
        ... )
        >>> executor.apply(change)
        >>> # If something goes wrong:
        >>> executor.rollback()
    """

    BACKUP_DIR = ".projektor/backups"

    def __init__(
        self,
        project_path: Path | str,
        dry_run: bool = False,
        validators: dict[str, Callable[[str], bool]] | None = None,
    ):
        """
        Inicjalizacja executora.

        Args:
            project_path: Ścieżka do projektu
            dry_run: Tryb testowy
            validators: Walidatory dla rozszerzeń (np. {".py": validate_python})
        """
        self.project_path = Path(project_path).resolve()
        self.dry_run = dry_run
        self.validators = validators or {}

        self._changes: list[CodeChange] = []
        self._backup_dir: Path | None = None

    def apply(self, change: CodeChange) -> bool:
        """
        Zastosuj zmianę.

        Args:
            change: Zmiana do zastosowania

        Returns:
            True jeśli sukces
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would apply: {change.change_type} {change.file_path}")
            return True

        try:
            # Prepare backup dir
            self._ensure_backup_dir()

            # Dispatch by type
            if change.change_type == "create":
                return self._apply_create(change)
            elif change.change_type == "modify":
                return self._apply_modify(change)
            elif change.change_type == "delete":
                return self._apply_delete(change)
            elif change.change_type == "rename":
                return self._apply_rename(change)
            else:
                logger.error(f"Unknown change type: {change.change_type}")
                return False

        except Exception as e:
            logger.exception(f"Failed to apply change: {e}")
            return False

    def apply_all(self, changes: list[CodeChange]) -> bool:
        """
        Zastosuj wszystkie zmiany.

        Args:
            changes: Lista zmian

        Returns:
            True jeśli wszystkie się powiodły
        """
        for change in changes:
            if not self.apply(change):
                # Rollback on failure
                self.rollback()
                return False
        return True

    def rollback(self) -> bool:
        """
        Cofnij wszystkie zastosowane zmiany.

        Returns:
            True jeśli sukces
        """
        logger.info("Rolling back changes...")

        # Reverse order
        for change in reversed(self._changes):
            if not change.applied:
                continue

            try:
                if change.change_type == "create":
                    # Delete created file
                    target = self.project_path / change.file_path
                    if target.exists():
                        target.unlink()

                elif change.change_type == "modify":
                    # Restore from backup
                    if change.backup_path:
                        backup = Path(change.backup_path)
                        target = self.project_path / change.file_path
                        if backup.exists():
                            shutil.copy2(backup, target)

                elif change.change_type == "delete":
                    # Restore from backup
                    if change.backup_path:
                        backup = Path(change.backup_path)
                        target = self.project_path / change.file_path
                        if backup.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup, target)

                elif change.change_type == "rename":
                    # Reverse rename
                    if change.new_path:
                        new_path = self.project_path / change.new_path
                        old_path = self.project_path / change.file_path
                        if new_path.exists():
                            new_path.rename(old_path)

            except Exception as e:
                logger.error(f"Rollback failed for {change.file_path}: {e}")

        self._changes.clear()
        return True

    def _apply_create(self, change: CodeChange) -> bool:
        """Create a new file."""
        target = self.project_path / change.file_path

        if target.exists():
            logger.error(f"File already exists: {change.file_path}")
            return False

        # Validate content
        if change.new_content and not self._validate(change.file_path, change.new_content):
            logger.error(f"Content validation failed for {change.file_path}")
            return False

        # Create parent dirs
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        target.write_text(change.new_content or "")

        change.applied = True
        change.applied_at = datetime.now()
        self._changes.append(change)

        logger.info(f"Created: {change.file_path}")
        return True

    def _apply_modify(self, change: CodeChange) -> bool:
        """Modify existing file."""
        target = self.project_path / change.file_path

        if not target.exists():
            logger.error(f"File not found: {change.file_path}")
            return False

        # Validate new content
        if change.new_content and not self._validate(change.file_path, change.new_content):
            logger.error(f"Content validation failed for {change.file_path}")
            return False

        # Backup
        change.old_content = target.read_text()
        change.backup_path = str(self._backup_file(target))

        # Calculate diff
        old_lines = len(change.old_content.splitlines())
        new_lines = len((change.new_content or "").splitlines())
        change.lines_added = max(0, new_lines - old_lines)
        change.lines_removed = max(0, old_lines - new_lines)

        # Write
        target.write_text(change.new_content or "")

        change.applied = True
        change.applied_at = datetime.now()
        self._changes.append(change)

        logger.info(f"Modified: {change.file_path} (+{change.lines_added}/-{change.lines_removed})")
        return True

    def _apply_delete(self, change: CodeChange) -> bool:
        """Delete a file."""
        target = self.project_path / change.file_path

        if not target.exists():
            logger.warning(f"File not found (already deleted?): {change.file_path}")
            return True

        # Backup
        change.old_content = target.read_text()
        change.backup_path = str(self._backup_file(target))

        # Delete
        target.unlink()

        change.applied = True
        change.applied_at = datetime.now()
        self._changes.append(change)

        logger.info(f"Deleted: {change.file_path}")
        return True

    def _apply_rename(self, change: CodeChange) -> bool:
        """Rename a file."""
        if not change.new_path:
            logger.error("Rename requires new_path")
            return False

        old_target = self.project_path / change.file_path
        new_target = self.project_path / change.new_path

        if not old_target.exists():
            logger.error(f"File not found: {change.file_path}")
            return False

        if new_target.exists():
            logger.error(f"Target already exists: {change.new_path}")
            return False

        # Backup original
        change.backup_path = str(self._backup_file(old_target))

        # Create parent dirs
        new_target.parent.mkdir(parents=True, exist_ok=True)

        # Rename
        old_target.rename(new_target)

        change.applied = True
        change.applied_at = datetime.now()
        self._changes.append(change)

        logger.info(f"Renamed: {change.file_path} -> {change.new_path}")
        return True

    def _validate(self, file_path: str, content: str) -> bool:
        """Validate content based on file extension."""
        ext = Path(file_path).suffix

        if ext in self.validators:
            try:
                return self.validators[ext](content)
            except Exception:
                return False

        # Default Python validation
        if ext == ".py":
            return self._validate_python(content)

        return True

    def _validate_python(self, content: str) -> bool:
        """Validate Python syntax."""
        try:
            compile(content, "<string>", "exec")
            return True
        except SyntaxError:
            return False

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        if self._backup_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._backup_dir = self.project_path / self.BACKUP_DIR / timestamp
            self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _backup_file(self, path: Path) -> Path:
        """Backup a file."""
        self._ensure_backup_dir()

        relative = path.relative_to(self.project_path)
        backup_path = self._backup_dir / relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)

        return backup_path

    def get_changes(self) -> list[CodeChange]:
        """Get list of applied changes."""
        return self._changes.copy()

    def clear_changes(self) -> None:
        """Clear change history."""
        self._changes.clear()
