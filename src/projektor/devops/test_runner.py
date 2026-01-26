"""
TestRunner - uruchamianie testów projektu.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Wynik uruchomienia testów."""

    success: bool

    # Counts
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors

    # Coverage
    coverage: float | None = None
    coverage_report: str | None = None

    # Output
    stdout: str = ""
    stderr: str = ""

    # Failed tests
    failed_tests: list[str] = field(default_factory=list)

    # Timing
    duration_seconds: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "total": self.total,
            "coverage": self.coverage,
            "failed_tests": self.failed_tests,
            "duration_seconds": self.duration_seconds,
        }


class TestRunner:
    """
    Runner testów projektu.

    Obsługuje pytest z coverage i parsowaniem wyników.

    Example:
        >>> runner = TestRunner("/path/to/project")
        >>> result = await runner.run()
        >>> print(f"Passed: {result.passed}/{result.total}")
        >>> print(f"Coverage: {result.coverage}%")
    """

    def __init__(
        self,
        project_path: Path | str,
        test_path: str | None = None,
        python_path: str = "python",
        coverage: bool = True,
        verbose: bool = True,
    ):
        """
        Inicjalizacja runnera.

        Args:
            project_path: Ścieżka do projektu
            test_path: Ścieżka do testów (domyślnie: tests/)
            python_path: Ścieżka do interpretera Python
            coverage: Czy mierzyć coverage
            verbose: Czy verbose output
        """
        self.project_path = Path(project_path).resolve()
        self.test_path = test_path or "tests/"
        self.python_path = python_path
        self.coverage = coverage
        self.verbose = verbose

    async def run(
        self,
        test_file: str | None = None,
        test_name: str | None = None,
        markers: list[str] | None = None,
        extra_args: list[str] | None = None,
    ) -> TestResult:
        """
        Uruchom testy.

        Args:
            test_file: Konkretny plik testowy
            test_name: Konkretny test (pattern)
            markers: Pytest markers do filtrowania
            extra_args: Dodatkowe argumenty

        Returns:
            Wynik testów
        """
        result = TestResult(success=False)

        # Build command
        cmd = [self.python_path, "-m", "pytest"]

        # Add test path
        if test_file:
            cmd.append(test_file)
        else:
            cmd.append(self.test_path)

        # Verbose
        if self.verbose:
            cmd.append("-v")

        # Test name filter
        if test_name:
            cmd.extend(["-k", test_name])

        # Markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Coverage
        if self.coverage:
            cmd.extend(
                [
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=html",
                ]
            )

        # Extra args
        if extra_args:
            cmd.extend(extra_args)

        # Run
        logger.info(f"Running: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            result.stdout = stdout.decode() if stdout else ""
            result.stderr = stderr.decode() if stderr else ""
            result.success = proc.returncode == 0

            # Parse output
            self._parse_output(result)

        except Exception as e:
            logger.exception("Test run failed")
            result.stderr = str(e)

        result.completed_at = datetime.now()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        return result

    async def run_single(self, test_path: str) -> TestResult:
        """Uruchom pojedynczy test."""
        return await self.run(test_file=test_path)

    async def run_failed(self) -> TestResult:
        """Uruchom tylko nieudane testy z ostatniego runu."""
        return await self.run(extra_args=["--lf"])

    async def run_changed(self) -> TestResult:
        """Uruchom testy dla zmienionych plików."""
        # Get changed files from git
        from projektor.devops.git_ops import GitOps

        try:
            git = GitOps(self.project_path)
            status = git.status()

            changed_files = status["modified"] + status["staged"] + status["untracked"]

            # Filter to Python files
            python_files = [f for f in changed_files if f.endswith(".py")]

            if not python_files:
                return TestResult(success=True)

            # Find corresponding test files
            test_files = self._find_test_files(python_files)

            if not test_files:
                return TestResult(success=True)

            return await self.run(extra_args=test_files)

        except Exception:
            # Fallback to running all tests
            return await self.run()

    def _find_test_files(self, source_files: list[str]) -> list[str]:
        """Find test files for source files."""
        test_files = []

        for source in source_files:
            # Convert src/module.py to tests/test_module.py
            name = Path(source).stem

            possible_tests = [
                f"tests/test_{name}.py",
                f"tests/unit/test_{name}.py",
                f"tests/integration/test_{name}.py",
            ]

            for test_path in possible_tests:
                full_path = self.project_path / test_path
                if full_path.exists():
                    test_files.append(test_path)

        return list(set(test_files))

    def _parse_output(self, result: TestResult) -> None:
        """Parse pytest output."""
        output = result.stdout

        # Parse test counts
        # Format: "X passed, Y failed, Z skipped in N.NNs"
        summary_match = re.search(
            r"(\d+) passed.*?(?:(\d+) failed)?.*?(?:(\d+) skipped)?.*?(?:(\d+) error)?", output
        )

        if summary_match:
            result.passed = int(summary_match.group(1) or 0)
            result.failed = int(summary_match.group(2) or 0)
            result.skipped = int(summary_match.group(3) or 0)
            result.errors = int(summary_match.group(4) or 0)

        # Alternative format: "=== N passed in X.XXs ==="
        alt_match = re.search(r"=+ (\d+) passed", output)
        if alt_match and result.passed == 0:
            result.passed = int(alt_match.group(1))

        # Parse coverage
        # Format: "TOTAL    XXX    XX    XX%"
        coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if coverage_match:
            result.coverage = float(coverage_match.group(1))

        # Parse failed test names
        # Format: "FAILED tests/test_x.py::test_name"
        failed_matches = re.findall(r"FAILED ([\w/._:]+)", output)
        result.failed_tests = failed_matches

        # Update success based on parsed data
        if result.failed > 0 or result.errors > 0:
            result.success = False


class TestWatcher:
    """
    Watcher testów - uruchamia testy przy zmianach plików.

    Example:
        >>> watcher = TestWatcher("/path/to/project")
        >>> await watcher.start()  # Runs until stopped
    """

    def __init__(
        self,
        project_path: Path | str,
        patterns: list[str] | None = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.patterns = patterns or ["*.py"]
        self.runner = TestRunner(project_path)
        self._running = False

    async def start(self) -> None:
        """Start watching for changes."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.error("watchdog not installed, cannot watch files")
            return

        self._running = True

        class Handler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback
                self._last_run = datetime.min

            def on_modified(self, event):
                if event.is_directory:
                    return

                # Debounce
                now = datetime.now()
                if (now - self._last_run).total_seconds() < 2:
                    return

                self._last_run = now

                # Check pattern
                path = Path(event.src_path)
                if path.suffix == ".py":
                    asyncio.create_task(self.callback(path))

        async def on_change(path: Path):
            logger.info(f"File changed: {path}")
            result = await self.runner.run_changed()
            logger.info(f"Tests: {result.passed} passed, {result.failed} failed")

        observer = Observer()
        observer.schedule(
            Handler(on_change),
            str(self.project_path / "src"),
            recursive=True,
        )
        observer.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            observer.stop()
            observer.join()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
