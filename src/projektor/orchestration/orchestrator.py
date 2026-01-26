"""
Orchestrator - główny komponent orkiestracji LLM.

Koordynuje pracę między LLM, wykonawcami kodu i systemem DevOps.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from projektor.core.project import Project
    from projektor.core.ticket import Ticket
    from projektor.orchestration.executor import ExecutionResult, PlanExecutor
    from projektor.orchestration.planner import TaskPlan, TaskPlanner

logger = logging.getLogger(__name__)


class OrchestrationStatus(Enum):
    """Status orkiestracji."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    TESTING = "testing"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class WorkResult:
    """Wynik pracy nad ticketem."""

    ticket_id: str
    status: OrchestrationStatus

    # Plan
    plan_generated: bool = False
    plan_steps: int = 0

    # Execution
    steps_completed: int = 0
    steps_failed: int = 0
    files_modified: list[str] = field(default_factory=list)

    # Tests
    tests_run: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    coverage: float | None = None

    # Git
    commits: list[str] = field(default_factory=list)
    branch: str | None = None

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    # Errors
    errors: list[str] = field(default_factory=list)

    # LLM usage
    llm_tokens_used: int = 0
    llm_cost_estimate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "status": self.status.value,
            "plan_generated": self.plan_generated,
            "plan_steps": self.plan_steps,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "files_modified": self.files_modified,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "coverage": self.coverage,
            "commits": self.commits,
            "branch": self.branch,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "llm_tokens_used": self.llm_tokens_used,
            "llm_cost_estimate": self.llm_cost_estimate,
        }


class Orchestrator:
    """
    Główny orkiestrator projektu.

    Koordynuje cały proces pracy nad ticketem:
    1. Analiza ticketu przez LLM
    2. Generowanie planu implementacji
    3. Wykonywanie kroków planu
    4. Uruchamianie testów
    5. Commit i push zmian

    Example:
        >>> orchestrator = Orchestrator(project)
        >>> result = await orchestrator.work_on_ticket("PROJ-42")
        >>> print(f"Status: {result.status}")
        >>> print(f"Commits: {len(result.commits)}")
    """

    def __init__(
        self,
        project: Project,
        model: str = "openrouter/x-ai/grok-3-fast",
        auto_commit: bool = True,
        run_tests: bool = True,
        max_iterations: int = 10,
        dry_run: bool = False,
    ):
        """
        Inicjalizacja orkiestratora.

        Args:
            project: Projekt do orkiestracji
            model: Model LLM do użycia
            auto_commit: Czy automatycznie commitować zmiany
            run_tests: Czy uruchamiać testy
            max_iterations: Maksymalna liczba iteracji
            dry_run: Tryb testowy (bez zmian)
        """
        if model == "openrouter/x-ai/grok-3-fast":
            env_model = os.environ.get("OPENROUTER_MODEL")
            if env_model:
                if not env_model.startswith("openrouter/"):
                    env_model = f"openrouter/{env_model}"
                model = env_model

        self.project = project
        self.model = model
        self.auto_commit = auto_commit
        self.run_tests = run_tests
        self.max_iterations = max_iterations
        self.dry_run = dry_run

        self.status = OrchestrationStatus.IDLE
        self._current_result: WorkResult | None = None

        # Lazy-loaded components
        self._planner: TaskPlanner | None = None
        self._executor: PlanExecutor | None = None

    @property
    def planner(self) -> TaskPlanner:
        """Lazy-load planner."""
        if self._planner is None:
            from projektor.orchestration.planner import TaskPlanner

            self._planner = TaskPlanner(model=self.model)
        return self._planner

    @property
    def executor(self) -> PlanExecutor:
        """Lazy-load executor."""
        if self._executor is None:
            from projektor.orchestration.executor import PlanExecutor

            self._executor = PlanExecutor(
                project=self.project,
                dry_run=self.dry_run,
            )
        return self._executor

    async def work_on_ticket(
        self,
        ticket_id: str,
        context: dict[str, Any] | None = None,
    ) -> WorkResult:
        """
        Pracuj nad ticketem.

        Pełny cykl: analiza -> planowanie -> wykonanie -> testy -> commit

        Args:
            ticket_id: ID ticketu
            context: Dodatkowy kontekst dla LLM

        Returns:
            Wynik pracy
        """
        result = WorkResult(ticket_id=ticket_id, status=OrchestrationStatus.PLANNING)
        self._current_result = result

        try:
            # Pobierz ticket
            ticket = self.project.get_ticket(ticket_id)
            if ticket is None:
                result.errors.append(f"Ticket {ticket_id} not found")
                result.status = OrchestrationStatus.FAILED
                return result

            # 1. Planning
            logger.info(f"[{ticket_id}] Generating plan...")
            self.status = OrchestrationStatus.PLANNING

            plan = await self.planner.plan(
                ticket=ticket,
                project=self.project,
                context=context,
            )

            if not plan.success:
                result.errors.append(f"Planning failed: {plan.error}")
                result.status = OrchestrationStatus.FAILED
                return result

            result.plan_generated = True
            result.plan_steps = len(plan.steps)
            result.llm_tokens_used += plan.tokens_used

            logger.info(f"[{ticket_id}] Plan generated with {result.plan_steps} steps")

            # 2. Execution
            logger.info(f"[{ticket_id}] Executing plan...")
            self.status = OrchestrationStatus.EXECUTING

            exec_result = await self.executor.execute(plan)

            result.steps_completed = exec_result.steps_completed
            result.steps_failed = exec_result.steps_failed
            result.files_modified = exec_result.files_modified
            result.errors.extend(exec_result.errors)

            if exec_result.failed:
                logger.warning(f"[{ticket_id}] Execution had failures, attempting rollback...")
                await self.executor.rollback()
                result.status = OrchestrationStatus.ROLLED_BACK
                return result

            logger.info(f"[{ticket_id}] Executed {result.steps_completed} steps")

            # 3. Testing
            if self.run_tests and result.files_modified:
                logger.info(f"[{ticket_id}] Running tests...")
                self.status = OrchestrationStatus.TESTING

                test_result = await self._run_tests()

                result.tests_run = True
                result.tests_passed = test_result.get("passed", 0)
                result.tests_failed = test_result.get("failed", 0)
                result.coverage = test_result.get("coverage")

                if result.tests_failed > 0:
                    logger.warning(f"[{ticket_id}] Tests failed: {result.tests_failed}")
                    result.errors.append(f"Tests failed: {result.tests_failed}")

                    # Rollback if tests fail
                    await self.executor.rollback()
                    result.status = OrchestrationStatus.ROLLED_BACK
                    return result

                logger.info(f"[{ticket_id}] Tests passed: {result.tests_passed}")

            # 4. Commit
            if self.auto_commit and result.files_modified and not self.dry_run:
                logger.info(f"[{ticket_id}] Committing changes...")
                self.status = OrchestrationStatus.COMMITTING

                commit_result = await self._commit_changes(ticket, result.files_modified)

                if commit_result:
                    result.commits.append(commit_result)
                    result.branch = await self._get_current_branch()

                logger.info(f"[{ticket_id}] Committed: {commit_result}")

            # 5. Complete
            result.status = OrchestrationStatus.COMPLETED
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            # Update ticket
            ticket.add_work_log(
                action="orchestration_complete",
                description=f"Completed {result.steps_completed} steps, "
                f"modified {len(result.files_modified)} files",
                commit_hash=result.commits[0] if result.commits else None,
            )

            logger.info(f"[{ticket_id}] Work completed in {result.duration_seconds:.1f}s")

        except Exception as e:
            logger.exception(f"[{ticket_id}] Orchestration error")
            result.errors.append(str(e))
            result.status = OrchestrationStatus.FAILED

            # Attempt rollback
            try:
                await self.executor.rollback()
            except Exception:
                pass

        finally:
            self.status = OrchestrationStatus.IDLE
            self._current_result = None

        return result

    async def plan_ticket(
        self,
        ticket_id: str,
        context: dict[str, Any] | None = None,
    ) -> TaskPlan:
        """
        Tylko wygeneruj plan dla ticketu (bez wykonania).

        Args:
            ticket_id: ID ticketu
            context: Dodatkowy kontekst

        Returns:
            Wygenerowany plan
        """
        ticket = self.project.get_ticket(ticket_id)
        if ticket is None:
            from projektor.orchestration.planner import TaskPlan

            return TaskPlan(success=False, error=f"Ticket {ticket_id} not found")

        return await self.planner.plan(
            ticket=ticket,
            project=self.project,
            context=context,
        )

    async def execute_plan(
        self,
        plan: TaskPlan,
        commit: bool = True,
    ) -> ExecutionResult:
        """
        Wykonaj wcześniej wygenerowany plan.

        Args:
            plan: Plan do wykonania
            commit: Czy commitować zmiany

        Returns:
            Wynik wykonania
        """
        result = await self.executor.execute(plan)

        if commit and not result.failed and result.files_modified and not self.dry_run:
            # Commit with generic message
            await self._commit_changes_generic(result.files_modified)

        return result

    async def _run_tests(self) -> dict[str, Any]:
        """Uruchom testy projektu."""
        from projektor.devops.test_runner import TestRunner

        runner = TestRunner(project_path=self.project.root_path)
        result = await runner.run()

        return {
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
            "coverage": result.coverage,
        }

    async def _commit_changes(
        self,
        ticket: Ticket,
        files: list[str],
    ) -> str | None:
        """Commituj zmiany dla ticketu."""
        from projektor.devops.git_ops import GitOps

        git = GitOps(repo_path=self.project.root_path)

        # Generuj commit message
        message = f"feat({ticket.id}): {ticket.title}\n\n[projektor] Auto-generated commit"

        # Stage files
        for file in files:
            git.stage(file)

        # Commit
        commit_hash = git.commit(message)

        return commit_hash

    async def _commit_changes_generic(self, files: list[str]) -> str | None:
        """Commituj zmiany bez kontekstu ticketu."""
        from projektor.devops.git_ops import GitOps

        git = GitOps(repo_path=self.project.root_path)

        message = f"chore: Auto-generated changes\n\n[projektor] Modified {len(files)} files"

        for file in files:
            git.stage(file)

        return git.commit(message)

    async def _get_current_branch(self) -> str | None:
        """Pobierz aktualną gałąź."""
        from projektor.devops.git_ops import GitOps

        git = GitOps(repo_path=self.project.root_path)
        return git.current_branch

    def get_status(self) -> dict[str, Any]:
        """Pobierz aktualny status orkiestratora."""
        return {
            "status": self.status.value,
            "project": self.project.metadata.name,
            "model": self.model,
            "auto_commit": self.auto_commit,
            "run_tests": self.run_tests,
            "dry_run": self.dry_run,
            "current_work": self._current_result.to_dict() if self._current_result else None,
        }
