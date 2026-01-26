"""
ToonParser - parser formatu TOON (Token-Oriented Object Notation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FunctionInfo:
    """Informacje o funkcji."""

    name: str
    kind: str  # function, method
    signature: str
    location: str  # "start-end" lines
    is_async: bool = False
    lines: int = 0
    cyclomatic_complexity: int = 1
    description: str = ""

    @property
    def start_line(self) -> int:
        parts = self.location.split("-")
        return int(parts[0]) if parts else 0

    @property
    def end_line(self) -> int:
        parts = self.location.split("-")
        return int(parts[1]) if len(parts) > 1 else self.start_line


@dataclass
class ModuleInfo:
    """Informacje o module."""

    path: str
    language: str
    item_count: int
    functions: list[FunctionInfo] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return sum(f.lines for f in self.functions)

    @property
    def avg_complexity(self) -> float:
        if not self.functions:
            return 0.0
        return sum(f.cyclomatic_complexity for f in self.functions) / len(self.functions)

    @property
    def max_complexity(self) -> int:
        if not self.functions:
            return 0
        return max(f.cyclomatic_complexity for f in self.functions)


@dataclass
class ProjectStructure:
    """Struktura projektu z TOON."""

    project_name: str
    generated: datetime | None = None
    modules: list[ModuleInfo] = field(default_factory=list)

    @property
    def total_modules(self) -> int:
        return len(self.modules)

    @property
    def total_functions(self) -> int:
        return sum(len(m.functions) for m in self.modules)

    @property
    def total_lines(self) -> int:
        return sum(m.total_lines for m in self.modules)

    @property
    def avg_complexity(self) -> float:
        all_funcs = [f for m in self.modules for f in m.functions]
        if not all_funcs:
            return 0.0
        return sum(f.cyclomatic_complexity for f in all_funcs) / len(all_funcs)

    def get_high_complexity_functions(self, threshold: int = 15) -> list[tuple[str, FunctionInfo]]:
        """Zwróć funkcje o złożoności > threshold."""
        results = []
        for module in self.modules:
            for func in module.functions:
                if func.cyclomatic_complexity > threshold:
                    results.append((module.path, func))
        return sorted(results, key=lambda x: x[1].cyclomatic_complexity, reverse=True)

    def get_large_functions(self, threshold: int = 100) -> list[tuple[str, FunctionInfo]]:
        """Zwróć funkcje o lines > threshold."""
        results = []
        for module in self.modules:
            for func in module.functions:
                if func.lines > threshold:
                    results.append((module.path, func))
        return sorted(results, key=lambda x: x[1].lines, reverse=True)


class ToonParser:
    """
    Parser plików TOON.

    Format TOON to kompaktowy format opisu struktury projektu
    zoptymalizowany pod kątem tokenów (dla LLM).

    Example:
        >>> parser = ToonParser()
        >>> structure = parser.parse_file("project.toon")
        >>> print(f"Modules: {structure.total_modules}")
        >>> print(f"Functions: {structure.total_functions}")
    """

    def parse_file(self, path: Path | str) -> ProjectStructure:
        """
        Parse TOON file.

        Args:
            path: Ścieżka do pliku .toon

        Returns:
            Sparsowana struktura projektu
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"TOON file not found: {path}")

        content = path.read_text()
        return self.parse(content)

    def parse(self, content: str) -> ProjectStructure:
        """
        Parse TOON content.

        Args:
            content: Zawartość pliku TOON

        Returns:
            Sparsowana struktura
        """
        structure = ProjectStructure(project_name="unknown")

        lines = content.strip().split("\n")
        current_section = None
        current_module = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Project name
            if line.startswith("project:"):
                structure.project_name = line.split(":", 1)[1].strip()

            # Generated date
            elif line.startswith("generated:"):
                date_str = line.split(":", 1)[1].strip().strip('"')
                try:
                    structure.generated = datetime.fromisoformat(date_str)
                except ValueError:
                    pass

            # Modules section header
            elif line.startswith("modules["):
                current_section = "modules"

            # Function details header
            elif line.startswith("function_details:"):
                current_section = "functions"

            # Module entry
            elif current_section == "modules" and "," in line:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    module = ModuleInfo(
                        path=parts[0].strip(),
                        language=parts[1].strip(),
                        item_count=int(parts[2].strip()) if parts[2].strip().isdigit() else 0,
                    )
                    structure.modules.append(module)

            # Module in function_details
            elif current_section == "functions" and line.endswith(":"):
                module_path = line.rstrip(":")
                # Find or create module
                current_module = None
                for m in structure.modules:
                    if m.path == module_path:
                        current_module = m
                        break
                if current_module is None:
                    current_module = ModuleInfo(path=module_path, language="python", item_count=0)
                    structure.modules.append(current_module)

            # Function entry in function_details
            elif current_section == "functions" and current_module and "," in line:
                func = self._parse_function_line(line)
                if func:
                    current_module.functions.append(func)

        return structure

    def _parse_function_line(self, line: str) -> FunctionInfo | None:
        """Parse function line from TOON."""
        # Format: name,kind,sig,loc,async,lines,cc,does
        # Example: main,function,() -> None,4-22,true,19,3,main

        # Handle different formats
        parts = line.strip().split(",")

        if len(parts) < 4:
            return None

        try:
            name = parts[0].strip()
            kind = parts[1].strip() if len(parts) > 1 else "function"
            signature = parts[2].strip() if len(parts) > 2 else "()"
            location = parts[3].strip() if len(parts) > 3 else "0-0"
            is_async = parts[4].strip().lower() == "true" if len(parts) > 4 else False
            lines = int(parts[5].strip()) if len(parts) > 5 and parts[5].strip().isdigit() else 0
            cc = int(parts[6].strip()) if len(parts) > 6 and parts[6].strip().isdigit() else 1
            description = parts[7].strip() if len(parts) > 7 else ""

            return FunctionInfo(
                name=name,
                kind=kind,
                signature=signature,
                location=location,
                is_async=is_async,
                lines=lines,
                cyclomatic_complexity=cc,
                description=description,
            )

        except (ValueError, IndexError):
            return None

    def to_summary(self, structure: ProjectStructure) -> str:
        """Generate summary of project structure."""
        lines = [
            f"# Project: {structure.project_name}",
            "",
            f"- Modules: {structure.total_modules}",
            f"- Functions: {structure.total_functions}",
            f"- Total lines: {structure.total_lines}",
            f"- Avg complexity: {structure.avg_complexity:.1f}",
            "",
        ]

        # High complexity
        high_cc = structure.get_high_complexity_functions(15)
        if high_cc:
            lines.append("## High Complexity Functions (CC > 15)")
            lines.append("")
            for module_path, func in high_cc[:10]:
                lines.append(f"- `{module_path}:{func.name}` CC={func.cyclomatic_complexity}")
            lines.append("")

        # Large functions
        large = structure.get_large_functions(100)
        if large:
            lines.append("## Large Functions (> 100 lines)")
            lines.append("")
            for module_path, func in large[:10]:
                lines.append(f"- `{module_path}:{func.name}` {func.lines} lines")
            lines.append("")

        return "\n".join(lines)
