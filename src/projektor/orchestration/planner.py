"""
TaskPlanner - planowanie zadań przez LLM.

Analizuje tickety i generuje plany implementacji.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from projektor.core.project import Project
    from projektor.core.ticket import Ticket

logger = logging.getLogger(__name__)


class StepType(Enum):
    """Typ kroku w planie."""

    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    RUN_COMMAND = "run_command"
    RUN_TESTS = "run_tests"
    ANALYZE = "analyze"
    REFACTOR = "refactor"


@dataclass
class PlanStep:
    """Krok planu implementacji."""

    step_number: int
    step_type: StepType
    description: str

    # Target
    target_file: str | None = None

    # Details
    changes: str | None = None  # Opis zmian lub nowa zawartość
    command: str | None = None  # Komenda do wykonania

    # Dependencies
    depends_on: list[int] = field(default_factory=list)

    # Metadata
    rationale: str = ""  # Uzasadnienie kroku
    estimated_complexity: str = "low"  # low, medium, high

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "description": self.description,
            "target_file": self.target_file,
            "changes": self.changes,
            "command": self.command,
            "depends_on": self.depends_on,
            "rationale": self.rationale,
            "estimated_complexity": self.estimated_complexity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        return cls(
            step_number=data["step_number"],
            step_type=StepType(data["step_type"]),
            description=data["description"],
            target_file=data.get("target_file"),
            changes=data.get("changes"),
            command=data.get("command"),
            depends_on=data.get("depends_on", []),
            rationale=data.get("rationale", ""),
            estimated_complexity=data.get("estimated_complexity", "low"),
        )


@dataclass
class TaskPlan:
    """Plan realizacji zadania."""

    success: bool
    steps: list[PlanStep] = field(default_factory=list)

    # Summary
    summary: str = ""
    estimated_time_minutes: int = 0

    # Error (if failed)
    error: str | None = None

    # LLM usage
    tokens_used: int = 0
    model_used: str = ""

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
            "summary": self.summary,
            "estimated_time_minutes": self.estimated_time_minutes,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskPlan:
        return cls(
            success=data["success"],
            steps=[PlanStep.from_dict(s) for s in data.get("steps", [])],
            summary=data.get("summary", ""),
            estimated_time_minutes=data.get("estimated_time_minutes", 0),
            error=data.get("error"),
            tokens_used=data.get("tokens_used", 0),
            model_used=data.get("model_used", ""),
            generated_at=(
                datetime.fromisoformat(data["generated_at"])
                if "generated_at" in data
                else datetime.now()
            ),
        )


class TaskPlanner:
    """
    Planner zadań wykorzystujący LLM.

    Analizuje ticket i kontekst projektu, generując szczegółowy
    plan implementacji z krokami do wykonania.

    Example:
        >>> planner = TaskPlanner(model="openrouter/x-ai/grok-3-fast")
        >>> plan = await planner.plan(ticket, project)
        >>> for step in plan.steps:
        ...     print(f"{step.step_number}. {step.description}")
    """

    SYSTEM_PROMPT = """Jesteś ekspertem programistą pomagającym w planowaniu implementacji.

Twoim zadaniem jest analiza ticketu i wygenerowanie szczegółowego planu implementacji.

Plan musi zawierać konkretne kroki do wykonania, każdy z:
- Numerem kroku
- Typem (create_file, modify_file, delete_file, run_command, run_tests, analyze, refactor)
- Opisem co zrobić
- Plikiem docelowym (jeśli dotyczy)
- Szczegółami zmian
- Uzasadnieniem

Ważne zasady:
- `target_file` musi być realną ścieżką pliku w repozytorium (relative do root projektu)
- Nigdy nie używaj pseudo-ścieżek typu `<string>`, `<stdin>`, `-` itp.

Odpowiedz w formacie JSON:
{
    "summary": "Krótkie podsumowanie planu",
    "estimated_time_minutes": 30,
    "steps": [
        {
            "step_number": 1,
            "step_type": "analyze",
            "description": "Analiza obecnej struktury",
            "target_file": "src/module.py",
            "changes": null,
            "rationale": "Potrzebujemy zrozumieć obecny kod",
            "estimated_complexity": "low"
        },
        ...
    ]
}

Skup się na:
1. Minimalizacji zmian (nie przepisuj całego kodu)
2. Zachowaniu backward compatibility
3. Dodaniu testów dla nowych funkcji
4. Używaniu istniejących wzorców z projektu
"""

    def __init__(
        self,
        model: str = "openrouter/x-ai/grok-3-fast",
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ):
        if model == "openrouter/x-ai/grok-3-fast":
            env_model = os.environ.get("OPENROUTER_MODEL")
            if env_model:
                if not env_model.startswith("openrouter/"):
                    env_model = f"openrouter/{env_model}"
                model = env_model

        if temperature == 0.1:
            env_temperature = os.environ.get("OPENROUTER_TEMPERATURE")
            if env_temperature:
                try:
                    temperature = float(env_temperature)
                except ValueError:
                    pass

        if max_tokens == 4000:
            env_max_tokens = os.environ.get("OPENROUTER_MAX_TOKENS")
            if env_max_tokens:
                try:
                    max_tokens = int(env_max_tokens)
                except ValueError:
                    pass

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    async def plan(
        self,
        ticket: Ticket,
        project: Project,
        context: dict[str, Any] | None = None,
    ) -> TaskPlan:
        """
        Wygeneruj plan dla ticketu.

        Args:
            ticket: Ticket do realizacji
            project: Projekt
            context: Dodatkowy kontekst

        Returns:
            Plan implementacji
        """
        try:
            # Build prompt
            prompt = self._build_prompt(ticket, project, context)

            # Call LLM
            response = await self._call_llm(prompt)

            # Parse response
            plan = self._parse_response(response)
            plan.model_used = self.model

            return plan

        except Exception as e:
            logger.exception("Planning failed")
            return TaskPlan(
                success=False,
                error=str(e),
                model_used=self.model,
            )

    def _build_prompt(
        self,
        ticket: Ticket,
        project: Project,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build prompt for LLM."""
        parts = [
            f"# Projekt: {project.metadata.name}",
            f"Język: {project.metadata.language}",
            "",
            "# Ticket",
            ticket.to_llm_prompt(),
            "",
        ]

        # Add a bounded file list to avoid hallucinated paths
        try:
            ignore_dirnames = {".git", ".venv", "venv", "__pycache__", ".projektor"}
            files: list[str] = []
            for p in project.root_path.rglob("*.py"):
                if any(part in ignore_dirnames for part in p.parts):
                    continue
                rel = p.relative_to(project.root_path).as_posix()
                files.append(rel)
                if len(files) >= 200:
                    break

            if files:
                parts.append("# Dostępne pliki w projekcie (lista skrócona)")
                parts.append("Używaj WYŁĄCZNIE ścieżek z tej listy jako target_file.")
                parts.append("```")
                parts.extend(files)
                parts.append("```")
                parts.append("")
        except Exception:
            pass

        # Add project structure if available
        if project.toon_file and project.toon_file.exists():
            parts.append("# Struktura projektu (TOON)")
            parts.append("```")
            with open(project.toon_file) as f:
                # Truncate if too long
                content = f.read()[:5000]
                parts.append(content)
            parts.append("```")
            parts.append("")

        # Add context
        if context:
            parts.append("# Dodatkowy kontekst")
            for key, value in context.items():
                parts.append(f"- {key}: {value}")
            parts.append("")

        parts.append("# Zadanie")
        parts.append("Wygeneruj plan implementacji w formacie JSON.")

        return "\n".join(parts)

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        try:
            import litellm

            api_key: str | None = None
            if isinstance(self.model, str) and self.model.startswith("openrouter/"):
                api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
            elif isinstance(self.model, str) and self.model.startswith("openai/"):
                api_key = os.environ.get("OPENAI_API_KEY")
            elif isinstance(self.model, str) and self.model.startswith("anthropic/"):
                api_key = os.environ.get("ANTHROPIC_API_KEY")

            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key,
            )

            return response.choices[0].message.content

        except ImportError:
            # Fallback without LLM - return simple plan
            logger.warning("litellm not available, using fallback planning")
            return self._fallback_plan()

    def _fallback_plan(self) -> str:
        """Fallback plan when LLM is not available."""
        return json.dumps(
            {
                "summary": "Fallback plan - LLM not available",
                "estimated_time_minutes": 30,
                "steps": [
                    {
                        "step_number": 1,
                        "step_type": "analyze",
                        "description": "Analyze existing code structure",
                        "target_file": None,
                        "changes": None,
                        "rationale": "Understand current implementation",
                        "estimated_complexity": "low",
                    },
                    {
                        "step_number": 2,
                        "step_type": "modify_file",
                        "description": "Implement changes based on ticket requirements",
                        "target_file": "src/main.py",
                        "changes": "TODO: Implement changes",
                        "rationale": "Ticket requirements",
                        "estimated_complexity": "medium",
                    },
                    {
                        "step_number": 3,
                        "step_type": "run_tests",
                        "description": "Run tests to verify changes",
                        "target_file": None,
                        "changes": None,
                        "rationale": "Ensure no regressions",
                        "estimated_complexity": "low",
                    },
                ],
            }
        )

    def _parse_response(self, response: str) -> TaskPlan:
        """Parse LLM response into TaskPlan."""
        # Extract JSON from response
        json_str = response

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return TaskPlan(
                success=False,
                error=f"Failed to parse LLM response: {e}",
            )

        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            try:
                step = PlanStep.from_dict(step_data)
                steps.append(step)
            except Exception as e:
                logger.warning(f"Failed to parse step: {e}")

        return TaskPlan(
            success=True,
            steps=steps,
            summary=data.get("summary", ""),
            estimated_time_minutes=data.get("estimated_time_minutes", 0),
        )

    async def refine_plan(
        self,
        plan: TaskPlan,
        feedback: str,
    ) -> TaskPlan:
        """
        Udoskonal plan na podstawie feedbacku.

        Args:
            plan: Obecny plan
            feedback: Feedback do uwzględnienia

        Returns:
            Ulepszony plan
        """
        prompt = f"""Obecny plan:
{json.dumps(plan.to_dict(), indent=2)}

Feedback:
{feedback}

Wygeneruj poprawiony plan uwzględniający feedback.
"""

        response = await self._call_llm(prompt)
        return self._parse_response(response)
