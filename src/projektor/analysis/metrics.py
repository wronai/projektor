"""
MetricsCollector - zbieranie metryk projektu.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """Metryki kodu."""

    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0

    # By language
    by_language: dict[str, int] = field(default_factory=dict)


@dataclass
class ComplexityMetrics:
    """Metryki złożoności."""

    total_functions: int = 0
    avg_cyclomatic: float = 0.0
    max_cyclomatic: int = 0

    # Distribution
    cc_1_5: int = 0  # Low complexity
    cc_6_10: int = 0  # Moderate
    cc_11_15: int = 0  # High
    cc_16_plus: int = 0  # Very high


@dataclass
class TestMetrics:
    """Metryki testów."""

    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    # Coverage
    coverage_percent: float | None = None
    covered_lines: int = 0
    uncovered_lines: int = 0


@dataclass
class GitMetrics:
    """Metryki Git."""

    total_commits: int = 0
    recent_commits: int = 0  # Last 30 days
    contributors: int = 0
    branches: int = 0

    # Activity
    commits_per_day_avg: float = 0.0
    last_commit: datetime | None = None


@dataclass
class ProjectMetrics:
    """Kompletne metryki projektu."""

    project_name: str
    collected_at: datetime = field(default_factory=datetime.now)

    # Component metrics
    code: CodeMetrics = field(default_factory=CodeMetrics)
    complexity: ComplexityMetrics = field(default_factory=ComplexityMetrics)
    tests: TestMetrics = field(default_factory=TestMetrics)
    git: GitMetrics = field(default_factory=GitMetrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "collected_at": self.collected_at.isoformat(),
            "code": {
                "total_files": self.code.total_files,
                "total_lines": self.code.total_lines,
                "code_lines": self.code.code_lines,
                "comment_lines": self.code.comment_lines,
                "by_language": self.code.by_language,
            },
            "complexity": {
                "total_functions": self.complexity.total_functions,
                "avg_cyclomatic": self.complexity.avg_cyclomatic,
                "max_cyclomatic": self.complexity.max_cyclomatic,
            },
            "tests": {
                "total_tests": self.tests.total_tests,
                "passed": self.tests.passed,
                "failed": self.tests.failed,
                "coverage_percent": self.tests.coverage_percent,
            },
            "git": {
                "total_commits": self.git.total_commits,
                "contributors": self.git.contributors,
                "branches": self.git.branches,
            },
        }


class MetricsCollector:
    """
    Collector metryk projektu.

    Zbiera metryki z różnych źródeł:
    - Analiza kodu (LOC, complexity)
    - TOON file
    - Git
    - Test coverage

    Example:
        >>> collector = MetricsCollector("/path/to/project")
        >>> metrics = collector.collect()
        >>> print(f"Lines: {metrics.code.total_lines}")
        >>> print(f"Avg CC: {metrics.complexity.avg_cyclomatic}")
    """

    PYTHON_EXTENSIONS = {".py"}
    JAVASCRIPT_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}

    def __init__(self, project_path: Path | str):
        """
        Inicjalizacja collectora.

        Args:
            project_path: Ścieżka do projektu
        """
        self.project_path = Path(project_path).resolve()

    def collect(self, include_git: bool = True, include_tests: bool = True) -> ProjectMetrics:
        """
        Zbierz wszystkie metryki.

        Args:
            include_git: Czy zbierać metryki Git
            include_tests: Czy zbierać metryki testów

        Returns:
            Kompletne metryki
        """
        metrics = ProjectMetrics(project_name=self.project_path.name)

        # Code metrics
        metrics.code = self._collect_code_metrics()

        # Complexity from TOON if available
        toon_file = self.project_path / "project_functions.toon"
        if toon_file.exists():
            metrics.complexity = self._collect_complexity_from_toon(toon_file)

        # Git metrics
        if include_git:
            metrics.git = self._collect_git_metrics()

        # Test metrics
        if include_tests:
            metrics.tests = self._collect_test_metrics()

        return metrics

    def _collect_code_metrics(self) -> CodeMetrics:
        """Collect code metrics."""
        metrics = CodeMetrics()

        # Find all source files
        src_path = self.project_path / "src"
        if not src_path.exists():
            src_path = self.project_path

        for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
            for file_path in src_path.rglob(f"*{ext}"):
                if self._should_skip(file_path):
                    continue

                metrics.total_files += 1

                try:
                    content = file_path.read_text()
                    lines = content.splitlines()

                    for line in lines:
                        stripped = line.strip()
                        metrics.total_lines += 1

                        if not stripped:
                            metrics.blank_lines += 1
                        elif stripped.startswith(("#", "//", "/*", "*", "'''", '"""')):
                            metrics.comment_lines += 1
                        else:
                            metrics.code_lines += 1

                    # Track by language
                    lang = self._ext_to_language(ext)
                    metrics.by_language[lang] = metrics.by_language.get(lang, 0) + len(lines)

                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")

        return metrics

    def _collect_complexity_from_toon(self, toon_path: Path) -> ComplexityMetrics:
        """Collect complexity metrics from TOON file."""
        from projektor.analysis.toon_parser import ToonParser

        metrics = ComplexityMetrics()

        try:
            parser = ToonParser()
            structure = parser.parse_file(toon_path)

            all_funcs = [f for m in structure.modules for f in m.functions]

            metrics.total_functions = len(all_funcs)

            if all_funcs:
                complexities = [f.cyclomatic_complexity for f in all_funcs]
                metrics.avg_cyclomatic = sum(complexities) / len(complexities)
                metrics.max_cyclomatic = max(complexities)

                # Distribution
                for cc in complexities:
                    if cc <= 5:
                        metrics.cc_1_5 += 1
                    elif cc <= 10:
                        metrics.cc_6_10 += 1
                    elif cc <= 15:
                        metrics.cc_11_15 += 1
                    else:
                        metrics.cc_16_plus += 1

        except Exception as e:
            logger.warning(f"Error parsing TOON: {e}")

        return metrics

    def _collect_git_metrics(self) -> GitMetrics:
        """Collect Git metrics."""
        metrics = GitMetrics()

        git_dir = self.project_path / ".git"
        if not git_dir.exists():
            return metrics

        try:
            # Total commits
            result = subprocess.run(
                ["git", "-C", str(self.project_path), "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            metrics.total_commits = int(result.stdout.strip())

            # Contributors
            result = subprocess.run(
                ["git", "-C", str(self.project_path), "shortlog", "-sn", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            metrics.contributors = len(result.stdout.strip().splitlines())

            # Branches
            result = subprocess.run(
                ["git", "-C", str(self.project_path), "branch", "-a"],
                capture_output=True,
                text=True,
                check=True,
            )
            metrics.branches = len(result.stdout.strip().splitlines())

            # Last commit date
            result = subprocess.run(
                ["git", "-C", str(self.project_path), "log", "-1", "--format=%aI"],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                metrics.last_commit = datetime.fromisoformat(result.stdout.strip())

        except Exception as e:
            logger.warning(f"Error collecting git metrics: {e}")

        return metrics

    def _collect_test_metrics(self) -> TestMetrics:
        """Collect test metrics from coverage data."""
        metrics = TestMetrics()

        # Try to find coverage data
        self.project_path / ".coverage"
        coverage_json = self.project_path / "coverage.json"
        self.project_path / "htmlcov"

        if coverage_json.exists():
            try:
                import json

                data = json.loads(coverage_json.read_text())

                if "totals" in data:
                    totals = data["totals"]
                    metrics.coverage_percent = totals.get("percent_covered")
                    metrics.covered_lines = totals.get("covered_lines", 0)

            except Exception as e:
                logger.warning(f"Error reading coverage.json: {e}")

        # Count test files
        tests_path = self.project_path / "tests"
        if tests_path.exists():
            for test_file in tests_path.rglob("test_*.py"):
                # Rough count of test functions
                try:
                    content = test_file.read_text()
                    metrics.total_tests += content.count("def test_")
                except Exception:
                    pass

        return metrics

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".tox", "htmlcov"}

        for part in path.parts:
            if part in skip_dirs:
                return True

        return False

    def _ext_to_language(self, ext: str) -> str:
        """Map extension to language name."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return mapping.get(ext, "other")
