"""
Analysis module - analiza kodu i metryki projektu.
"""

from projektor.analysis.metrics import (
    CodeMetrics,
    ComplexityMetrics,
    GitMetrics,
    MetricsCollector,
    ProjectMetrics,
    TestMetrics,
)
from projektor.analysis.reports import ReportGenerator
from projektor.analysis.toon_parser import (
    FunctionInfo,
    ModuleInfo,
    ProjectStructure,
    ToonParser,
)

__all__ = [
    # TOON Parser
    "ToonParser",
    "ProjectStructure",
    "ModuleInfo",
    "FunctionInfo",
    # Metrics
    "MetricsCollector",
    "ProjectMetrics",
    "CodeMetrics",
    "ComplexityMetrics",
    "TestMetrics",
    "GitMetrics",
    # Reports
    "ReportGenerator",
]
