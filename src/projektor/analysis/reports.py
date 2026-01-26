"""
ReportGenerator - generowanie raportów projektu.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from projektor.analysis.metrics import ProjectMetrics
    from projektor.analysis.toon_parser import ProjectStructure


class ReportGenerator:
    """
    Generator raportów projektu.

    Generuje raporty w różnych formatach:
    - Markdown
    - JSON
    - HTML

    Example:
        >>> generator = ReportGenerator()
        >>> report = generator.generate_markdown(metrics)
        >>> Path("report.md").write_text(report)
    """

    def generate_markdown(
        self,
        metrics: ProjectMetrics,
        structure: ProjectStructure | None = None,
        include_recommendations: bool = True,
    ) -> str:
        """
        Generate Markdown report.

        Args:
            metrics: Metryki projektu
            structure: Struktura z TOON (opcjonalnie)
            include_recommendations: Czy dołączyć rekomendacje

        Returns:
            Raport Markdown
        """
        lines = [
            f"# Project Report: {metrics.project_name}",
            "",
            f"Generated: {metrics.collected_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Overview",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Files | {metrics.code.total_files} |",
            f"| Total Lines | {metrics.code.total_lines:,} |",
            f"| Code Lines | {metrics.code.code_lines:,} |",
            f"| Functions | {metrics.complexity.total_functions} |",
            f"| Avg Complexity | {metrics.complexity.avg_cyclomatic:.1f} |",
            f"| Max Complexity | {metrics.complexity.max_cyclomatic} |",
            "",
        ]

        # Code by language
        if metrics.code.by_language:
            lines.append("## Code by Language")
            lines.append("")
            lines.append("| Language | Lines |")
            lines.append("|----------|-------|")
            for lang, loc in sorted(metrics.code.by_language.items(), key=lambda x: -x[1]):
                lines.append(f"| {lang.title()} | {loc:,} |")
            lines.append("")

        # Complexity distribution
        lines.append("## Complexity Distribution")
        lines.append("")
        lines.append("| Range | Count |")
        lines.append("|-------|-------|")
        lines.append(f"| 1-5 (Low) | {metrics.complexity.cc_1_5} |")
        lines.append(f"| 6-10 (Moderate) | {metrics.complexity.cc_6_10} |")
        lines.append(f"| 11-15 (High) | {metrics.complexity.cc_11_15} |")
        lines.append(f"| 16+ (Very High) | {metrics.complexity.cc_16_plus} |")
        lines.append("")

        # Test coverage
        if metrics.tests.coverage_percent is not None:
            lines.append("## Test Coverage")
            lines.append("")
            lines.append(f"- Coverage: **{metrics.tests.coverage_percent:.1f}%**")
            lines.append(f"- Total tests: {metrics.tests.total_tests}")
            lines.append("")

        # Git stats
        if metrics.git.total_commits > 0:
            lines.append("## Git Statistics")
            lines.append("")
            lines.append(f"- Total commits: {metrics.git.total_commits:,}")
            lines.append(f"- Contributors: {metrics.git.contributors}")
            lines.append(f"- Branches: {metrics.git.branches}")
            if metrics.git.last_commit:
                lines.append(f"- Last commit: {metrics.git.last_commit.strftime('%Y-%m-%d')}")
            lines.append("")

        # High complexity functions
        if structure:
            high_cc = structure.get_high_complexity_functions(15)
            if high_cc:
                lines.append("## High Complexity Functions")
                lines.append("")
                lines.append("Functions with cyclomatic complexity > 15:")
                lines.append("")
                lines.append("| File | Function | CC |")
                lines.append("|------|----------|-----|")
                for module_path, func in high_cc[:10]:
                    lines.append(
                        f"| `{module_path}` | `{func.name}` | {func.cyclomatic_complexity} |"
                    )
                lines.append("")

        # Recommendations
        if include_recommendations:
            recommendations = self._generate_recommendations(metrics, structure)
            if recommendations:
                lines.append("## Recommendations")
                lines.append("")
                for rec in recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        return "\n".join(lines)

    def generate_json(self, metrics: ProjectMetrics) -> str:
        """Generate JSON report."""
        return json.dumps(metrics.to_dict(), indent=2)

    def generate_html(
        self,
        metrics: ProjectMetrics,
        structure: ProjectStructure | None = None,
    ) -> str:
        """Generate HTML report."""
        # Simple HTML template
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Project Report: {metrics.project_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        tr:nth-child(even) {{ background-color: #fafafa; }}
        .metric-card {{
            display: inline-block;
            background: #f8f9fa;
            padding: 20px;
            margin: 10px;
            border-radius: 8px;
            min-width: 150px;
            text-align: center;
        }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        .warning {{ color: #dc3545; }}
        .success {{ color: #28a745; }}
    </style>
</head>
<body>
    <h1>📊 Project Report: {metrics.project_name}</h1>
    <p>Generated: {metrics.collected_at.strftime("%Y-%m-%d %H:%M")}</p>

    <h2>Overview</h2>
    <div>
        <div class="metric-card">
            <div class="metric-value">{metrics.code.total_files}</div>
            <div class="metric-label">Files</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.code.total_lines:,}</div>
            <div class="metric-label">Lines of Code</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.complexity.total_functions}</div>
            <div class="metric-label">Functions</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.complexity.avg_cyclomatic:.1f}</div>
            <div class="metric-label">Avg Complexity</div>
        </div>
    </div>

    <h2>Code Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Code Lines</td><td>{metrics.code.code_lines:,}</td></tr>
        <tr><td>Comment Lines</td><td>{metrics.code.comment_lines:,}</td></tr>
        <tr><td>Blank Lines</td><td>{metrics.code.blank_lines:,}</td></tr>
    </table>

    <h2>Complexity Distribution</h2>
    <table>
        <tr><th>Range</th><th>Count</th><th>Status</th></tr>
        <tr><td>1-5 (Low)</td><td>{metrics.complexity.cc_1_5}</td><td class="success">✓ Good</td></tr>
        <tr><td>6-10 (Moderate)</td><td>{metrics.complexity.cc_6_10}</td><td>Acceptable</td></tr>
        <tr><td>11-15 (High)</td><td>{metrics.complexity.cc_11_15}</td><td class="warning">⚠ Review</td></tr>
        <tr><td>16+ (Very High)</td><td>{metrics.complexity.cc_16_plus}</td><td class="warning">⚠ Refactor</td></tr>
    </table>
"""

        # Test coverage
        if metrics.tests.coverage_percent is not None:
            coverage_class = "success" if metrics.tests.coverage_percent >= 80 else "warning"
            html += f"""
    <h2>Test Coverage</h2>
    <div class="metric-card">
        <div class="metric-value {coverage_class}">{metrics.tests.coverage_percent:.1f}%</div>
        <div class="metric-label">Coverage</div>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def _generate_recommendations(
        self,
        metrics: ProjectMetrics,
        structure: ProjectStructure | None = None,
    ) -> list[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        # High complexity
        if metrics.complexity.cc_16_plus > 0:
            recommendations.append(
                f"🔴 {metrics.complexity.cc_16_plus} functions have very high complexity (CC > 15). "
                "Consider refactoring these for better maintainability."
            )

        # Low coverage
        if metrics.tests.coverage_percent is not None and metrics.tests.coverage_percent < 80:
            recommendations.append(
                f"🟡 Test coverage is {metrics.tests.coverage_percent:.1f}%. "
                "Consider adding more tests to reach 80% coverage."
            )

        # No tests
        if metrics.tests.total_tests == 0:
            recommendations.append("🔴 No tests found. Add unit tests to ensure code quality.")

        # High avg complexity
        if metrics.complexity.avg_cyclomatic > 10:
            recommendations.append(
                f"🟡 Average complexity is {metrics.complexity.avg_cyclomatic:.1f}. "
                "Consider simplifying complex functions."
            )

        # Comment ratio
        if metrics.code.code_lines > 0:
            comment_ratio = metrics.code.comment_lines / metrics.code.code_lines
            if comment_ratio < 0.1:
                recommendations.append(
                    "🟡 Comment ratio is low. Consider adding more documentation."
                )

        # No recent git activity
        if metrics.git.last_commit:
            days_since = (datetime.now() - metrics.git.last_commit).days
            if days_since > 30:
                recommendations.append(
                    f"ℹ️ Last commit was {days_since} days ago. Is the project still active?"
                )

        return recommendations

    def generate_sprint_report(
        self,
        sprint_name: str,
        completed_tickets: list[dict[str, Any]],
        metrics_before: ProjectMetrics,
        metrics_after: ProjectMetrics,
    ) -> str:
        """
        Generate sprint completion report.

        Args:
            sprint_name: Nazwa sprintu
            completed_tickets: Lista ukończonych ticketów
            metrics_before: Metryki przed sprintem
            metrics_after: Metryki po sprincie

        Returns:
            Raport Markdown
        """
        lines = [
            f"# Sprint Report: {sprint_name}",
            "",
            f"Completed: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Completed Tickets",
            "",
        ]

        # Tickets
        total_points = 0
        for ticket in completed_tickets:
            points = ticket.get("points", 0)
            total_points += points
            lines.append(f"- [{ticket['id']}] {ticket['title']} ({points} pts)")

        lines.extend(
            [
                "",
                f"**Total points delivered: {total_points}**",
                "",
                "## Code Changes",
                "",
                "| Metric | Before | After | Change |",
                "|--------|--------|-------|--------|",
            ]
        )

        # Compare metrics
        loc_change = metrics_after.code.total_lines - metrics_before.code.total_lines
        func_change = (
            metrics_after.complexity.total_functions - metrics_before.complexity.total_functions
        )
        cc_change = (
            metrics_after.complexity.avg_cyclomatic - metrics_before.complexity.avg_cyclomatic
        )

        lines.append(
            f"| Lines of Code | {metrics_before.code.total_lines:,} | "
            f"{metrics_after.code.total_lines:,} | {loc_change:+,} |"
        )
        lines.append(
            f"| Functions | {metrics_before.complexity.total_functions} | "
            f"{metrics_after.complexity.total_functions} | {func_change:+d} |"
        )
        lines.append(
            f"| Avg Complexity | {metrics_before.complexity.avg_cyclomatic:.1f} | "
            f"{metrics_after.complexity.avg_cyclomatic:.1f} | {cc_change:+.1f} |"
        )

        if metrics_after.tests.coverage_percent is not None:
            cov_before = metrics_before.tests.coverage_percent or 0
            cov_after = metrics_after.tests.coverage_percent
            cov_change = cov_after - cov_before
            lines.append(
                f"| Coverage | {cov_before:.1f}% | {cov_after:.1f}% | {cov_change:+.1f}% |"
            )

        lines.append("")

        return "\n".join(lines)
