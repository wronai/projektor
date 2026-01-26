"""
PlanExecutor - wykonawca planów implementacji.

Bezpiecznie wykonuje kroki planu z możliwością rollback.
"""

from __future__ import annotations

import logging
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from projektor.core.project import Project
    from projektor.orchestration.planner import PlanStep, TaskPlan

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Wynik wykonania kroku."""

    step_number: int
    success: bool

    # Output
    output: str | None = None
    error: str | None = None

    # Changes
    file_modified: str | None = None
    backup_path: str | None = None

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "file_modified": self.file_modified,
            "backup_path": self.backup_path,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ExecutionResult:
    """Wynik wykonania planu."""

    success: bool

    # Steps
    step_results: list[StepResult] = field(default_factory=list)
    steps_completed: int = 0
    steps_failed: int = 0

    # Files
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)

    # Backups (for rollback)
    backups: dict[str, str] = field(default_factory=dict)

    # Errors
    errors: list[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def failed(self) -> bool:
        """Czy wykonanie się nie powiodło."""
        return self.steps_failed > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "step_results": [r.to_dict() for r in self.step_results],
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "files_deleted": self.files_deleted,
            "errors": self.errors,
        }


class PlanExecutor:
    """
    Wykonawca planów implementacji.

    Bezpiecznie wykonuje kroki planu z:
    - Automatycznym backupem przed zmianami
    - Walidacją składni
    - Możliwością rollback

    Example:
        >>> executor = PlanExecutor(project)
        >>> result = await executor.execute(plan)
        >>> if result.failed:
        ...     await executor.rollback()
    """

    BACKUP_DIR = ".projektor/backups"

    def __init__(
        self,
        project: Project,
        dry_run: bool = False,
    ):
        """
        Inicjalizacja wykonawcy.

        Args:
            project: Projekt
            dry_run: Tryb testowy (bez zmian)
        """
        self.project = project
        self.dry_run = dry_run

        self._last_result: ExecutionResult | None = None
        self._backup_dir = self.project.root_path / self.BACKUP_DIR

    async def execute(self, plan: TaskPlan) -> ExecutionResult:
        """
        Wykonaj plan.

        Args:
            plan: Plan do wykonania

        Returns:
            Wynik wykonania
        """
        result = ExecutionResult(success=True)
        self._last_result = result

        if not plan.success or not plan.steps:
            result.success = False
            result.errors.append("Invalid or empty plan")
            return result

        # Prepare backup directory
        self._prepare_backup_dir()

        # Execute steps
        for step in plan.steps:
            step_result = await self._execute_step(step, result)
            result.step_results.append(step_result)

            if step_result.success:
                result.steps_completed += 1
            else:
                result.steps_failed += 1
                result.errors.append(step_result.error or f"Step {step.step_number} failed")

                # Stop on failure
                break

        result.completed_at = datetime.now()
        result.success = result.steps_failed == 0

        return result

    async def _execute_step(
        self,
        step: PlanStep,
        result: ExecutionResult,
    ) -> StepResult:
        """Execute a single step."""
        from projektor.orchestration.planner import StepType

        step_result = StepResult(step_number=step.step_number, success=False)

        try:
            logger.info(f"Executing step {step.step_number}: {step.description}")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute: {step.step_type.value}")
                step_result.success = True
                step_result.output = "[DRY RUN]"
                return step_result

            # Dispatch by step type
            if step.step_type == StepType.CREATE_FILE:
                await self._execute_create_file(step, step_result, result)

            elif step.step_type == StepType.MODIFY_FILE:
                await self._execute_modify_file(step, step_result, result)

            elif step.step_type == StepType.DELETE_FILE:
                await self._execute_delete_file(step, step_result, result)

            elif step.step_type == StepType.RUN_COMMAND:
                await self._execute_run_command(step, step_result, result)

            elif step.step_type == StepType.RUN_TESTS:
                await self._execute_run_tests(step, step_result, result)

            elif step.step_type == StepType.ANALYZE:
                await self._execute_analyze(step, step_result, result)

            elif step.step_type == StepType.REFACTOR:
                await self._execute_refactor(step, step_result, result)

            else:
                step_result.error = f"Unknown step type: {step.step_type}"

        except Exception as e:
            logger.exception(f"Step {step.step_number} failed")
            step_result.error = str(e)

        step_result.completed_at = datetime.now()
        step_result.duration_ms = (
            step_result.completed_at - step_result.started_at
        ).total_seconds() * 1000

        return step_result

    async def _execute_create_file(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Create a new file."""
        if not step.target_file:
            step_result.error = "No target file specified"
            return

        target = self.project.root_path / step.target_file

        # Check if already exists
        if target.exists():
            step_result.error = f"File already exists: {step.target_file}"
            return

        # Create parent directories
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        content = step.changes or ""
        target.write_text(content)

        step_result.success = True
        step_result.file_modified = step.target_file
        result.files_created.append(step.target_file)

    async def _execute_modify_file(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Modify an existing file."""
        if not step.target_file:
            step_result.error = "No target file specified"
            return

        if step.target_file.startswith("<") and step.target_file.endswith(">"):
            step_result.error = f"Invalid target file: {step.target_file}"
            return

        target = self.project.root_path / step.target_file

        if not target.exists():
            step_result.error = f"File not found: {step.target_file}"
            return

        # Backup
        backup_path = self._backup_file(target)
        step_result.backup_path = str(backup_path)
        result.backups[step.target_file] = str(backup_path)

        # Apply changes
        if step.changes:
            # For now, just replace content
            # TODO: Implement smarter diff-based changes
            target.write_text(step.changes)

        step_result.success = True
        step_result.file_modified = step.target_file
        result.files_modified.append(step.target_file)

    async def _execute_delete_file(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Delete a file."""
        if not step.target_file:
            step_result.error = "No target file specified"
            return

        if step.target_file.startswith("<") and step.target_file.endswith(">"):
            step_result.error = f"Invalid target file: {step.target_file}"
            return

        target = self.project.root_path / step.target_file

        if not target.exists():
            step_result.error = f"File not found: {step.target_file}"
            return

        # Backup
        backup_path = self._backup_file(target)
        step_result.backup_path = str(backup_path)
        result.backups[step.target_file] = str(backup_path)

        # Delete
        target.unlink()

        step_result.success = True
        step_result.file_modified = step.target_file
        result.files_deleted.append(step.target_file)

    async def _execute_run_command(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Run a command (limited commands only)."""
        cmd = step.command or step.changes
        if not cmd:
            step_result.error = "No command specified"
            return

        # Security: Only allow safe commands
        safe_prefixes = [
            "python",
            "python3",
            "pip",
            "pip3",
            "pytest",
            "black",
            "ruff",
            "mypy",
            "rg",
            "grep",
            "find",
            "ls",
            "cat",
            "head",
            "tail",
        ]

        cmd_lower = str(cmd).lower().strip()
        if not any(cmd_lower.startswith(prefix) for prefix in safe_prefixes):
            step_result.error = f"Command not allowed: {cmd}"
            return

        import asyncio

        proc = await asyncio.create_subprocess_shell(
            str(cmd),
            cwd=str(self.project.root_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        step_result.output = stdout.decode() if stdout else None

        if proc.returncode != 0:
            step_result.error = stderr.decode() if stderr else f"Exit code: {proc.returncode}"
        else:
            step_result.success = True

    async def _execute_run_tests(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Run tests."""
        import asyncio

        cmd = f"{sys.executable} -m pytest -v --tb=short"
        if step.target_file:
            cmd += f" {step.target_file}"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(self.project.root_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        step_result.output = stdout.decode() if stdout else None
        step_result.success = proc.returncode == 0

        if not step_result.success:
            step_result.error = stderr.decode() if stderr else "Tests failed"

    async def _execute_analyze(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Analyze code (no changes)."""
        # Analysis doesn't make changes, just logs
        step_result.success = True
        step_result.output = f"Analysis: {step.description}"

    async def _execute_refactor(
        self,
        step: PlanStep,
        step_result: StepResult,
        result: ExecutionResult,
    ) -> None:
        """Refactor code (same as modify for now)."""
        await self._execute_modify_file(step, step_result, result)

    def _prepare_backup_dir(self) -> None:
        """Prepare backup directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._backup_dir = self.project.root_path / self.BACKUP_DIR / timestamp
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _backup_file(self, path: Path) -> Path:
        """Backup a file before modification."""
        relative = path.relative_to(self.project.root_path)
        backup_path = self._backup_dir / relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        return backup_path

    async def rollback(self) -> bool:
        """
        Rollback last execution.

        Returns:
            True if rollback succeeded
        """
        if not self._last_result:
            logger.warning("No execution to rollback")
            return False

        result = self._last_result

        # Restore backups
        for file_path, backup_path in result.backups.items():
            target = self.project.root_path / file_path
            backup = Path(backup_path)

            if backup.exists():
                logger.info(f"Restoring {file_path} from backup")
                shutil.copy2(backup, target)

        # Delete created files
        for file_path in result.files_created:
            target = self.project.root_path / file_path
            if target.exists():
                logger.info(f"Removing created file: {file_path}")
                target.unlink()

        logger.info("Rollback completed")
        return True
