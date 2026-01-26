import pytest

from projektor.core.project import Project
from projektor.orchestration.executor import ExecutionResult, PlanExecutor, StepResult
from projektor.orchestration.planner import PlanStep, StepType


class _FakeProc:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_run_command_allows_exact_extensions_test_command(sample_project, monkeypatch):
    (sample_project / "projektor.yaml").write_text(
        """
project:
  name: myproject
  language: javascript
extensions:
  test_command: "npm test"
"""
    )

    project = Project.load(sample_project)
    executor = PlanExecutor(project)

    called = {"count": 0, "cmd": None}

    async def _fake_create_subprocess_shell(cmd, cwd, stdout, stderr):
        called["count"] += 1
        called["cmd"] = cmd
        return _FakeProc(stdout=b"ok\n", stderr=b"", returncode=0)

    import asyncio

    monkeypatch.setattr(asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    step = PlanStep(
        step_number=1,
        step_type=StepType.RUN_COMMAND,
        description="Run tests",
        command="npm test",
    )
    step_result = StepResult(step_number=1, success=False)
    result = ExecutionResult(success=True)

    await executor._execute_run_command(step, step_result, result)

    assert called["count"] == 1
    assert called["cmd"] == "npm test"
    assert step_result.success is True
    assert step_result.error is None
    assert step_result.output == "ok\n"


@pytest.mark.asyncio
async def test_run_command_blocks_non_allowed_npm_command(sample_project, monkeypatch):
    (sample_project / "projektor.yaml").write_text(
        """
project:
  name: myproject
  language: javascript
extensions:
  test_command: "npm test"
"""
    )

    project = Project.load(sample_project)
    executor = PlanExecutor(project)

    called = {"count": 0}

    async def _fake_create_subprocess_shell(cmd, cwd, stdout, stderr):
        called["count"] += 1
        return _FakeProc(stdout=b"should not run\n", stderr=b"", returncode=0)

    import asyncio

    monkeypatch.setattr(asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    step = PlanStep(
        step_number=1,
        step_type=StepType.RUN_COMMAND,
        description="Run build",
        command="npm run build",
    )
    step_result = StepResult(step_number=1, success=False)
    result = ExecutionResult(success=True)

    await executor._execute_run_command(step, step_result, result)

    assert called["count"] == 0
    assert step_result.success is False
    assert step_result.error == "Command not allowed: npm run build"
