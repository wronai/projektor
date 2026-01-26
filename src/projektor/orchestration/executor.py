"""
PlanExecutor - wykonawca planów implementacji.

Bezpiecznie wykonuje kroki planu z możliwością rollback.
"""

from __future__ import annotations

import logging
import re
import shutil
import sys
import textwrap
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

    def _strip_markdown_code_fences(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2:
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                return "\n".join(lines).strip() + "\n"
        return content

    def _python_syntax_error(self, filename: str, content: str) -> str | None:
        try:
            compile(content, filename, "exec")
        except SyntaxError as e:
            line = e.lineno or 0
            col = e.offset or 0
            msg = e.msg or "SyntaxError"
            return f"{filename}:{line}:{col}: {msg}"
        return None

    def _looks_like_unified_diff(self, content: str) -> bool:
        s = content.lstrip()
        return s.startswith("diff --git") or s.startswith("--- ") or s.startswith("@@ ")

    def _apply_unified_diff(self, original: str, diff: str, filename: str) -> str:
        hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

        orig_lines = original.splitlines(True)
        diff_lines = diff.splitlines(True)

        out: list[str] = []
        i = 0
        idx = 0

        while idx < len(diff_lines):
            line = diff_lines[idx]

            if line.startswith(("diff --git", "index ", "--- ", "+++ ")):
                idx += 1
                continue

            m = hunk_re.match(line)
            if not m:
                idx += 1
                continue

            start_old = int(m.group(1))

            while i < start_old - 1 and i < len(orig_lines):
                out.append(orig_lines[i])
                i += 1

            idx += 1
            while idx < len(diff_lines):
                dl = diff_lines[idx]
                if dl.startswith("@@ "):
                    break

                if dl.startswith(" "):
                    expected = dl[1:]
                    if i >= len(orig_lines) or orig_lines[i] != expected:
                        raise ValueError(f"Unified diff context mismatch in {filename}")
                    out.append(orig_lines[i])
                    i += 1

                elif dl.startswith("-"):
                    expected = dl[1:]
                    if i >= len(orig_lines) or orig_lines[i] != expected:
                        raise ValueError(f"Unified diff removal mismatch in {filename}")
                    i += 1

                elif dl.startswith("+"):
                    out.append(dl[1:])

                elif dl.startswith("\\"):
                    pass

                else:
                    raise ValueError(f"Invalid unified diff line in {filename}: {dl!r}")

                idx += 1

        out.extend(orig_lines[i:])
        return "".join(out)

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
        content = self._strip_markdown_code_fences(step.changes or "")
        if target.suffix in {".py", ".pyi"}:
            err = self._python_syntax_error(step.target_file, content)
            if err:
                step_result.error = f"Invalid python syntax in create_file content: {err}"
                return

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
        if not step.changes:
            step_result.error = "No changes specified"
            return

        raw_changes = self._strip_markdown_code_fences(step.changes)
        current = target.read_text()

        try:
            if self._looks_like_unified_diff(raw_changes):
                new_content = self._apply_unified_diff(current, raw_changes, step.target_file)
            else:
                new_content = raw_changes
        except Exception as e:
            try:
                shutil.copy2(Path(backup_path), target)
            except Exception:
                pass
            step_result.error = str(e)
            return

        if target.suffix in {".py", ".pyi"}:
            err = self._python_syntax_error(step.target_file, new_content)
            if err:
                try:
                    shutil.copy2(Path(backup_path), target)
                except Exception:
                    pass
                step_result.error = (
                    "Refusing to write invalid python to file. "
                    f"{err}"
                )
                return

        target.write_text(new_content)

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

        allowed_exact_command = None
        try:
            from projektor.core.config import Config

            cfg = Config.load(self.project.root_path / "projektor.yaml")
            if isinstance(getattr(cfg, "extensions", None), dict):
                allowed_exact_command = cfg.extensions.get("test_command")
        except Exception:
            allowed_exact_command = None

        normalized_allowed = (
            str(allowed_exact_command).lower().strip()
            if allowed_exact_command and str(allowed_exact_command).strip()
            else None
        )

        is_allowed = False
        if normalized_allowed and cmd_lower == normalized_allowed:
            is_allowed = True
        elif any(cmd_lower.startswith(prefix) for prefix in safe_prefixes):
            is_allowed = True

        if not is_allowed:
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

        if stderr:
            step_result.error = stderr.decode(errors="replace")

        if proc.returncode != 0:
            if not step_result.error:
                step_result.error = f"Exit code: {proc.returncode}"
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
            if stderr:
                step_result.error = stderr.decode()
            elif stdout:
                out = stdout.decode(errors="replace")
                tail = "\n".join(out.splitlines()[-80:])
                step_result.error = "Tests failed\n" + textwrap.dedent(tail)
            else:
                step_result.error = "Tests failed"

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
