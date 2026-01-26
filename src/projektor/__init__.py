"""
Projektor - LLM-Orchestrated Project Management with DevOps Automation.

Framework do automatycznego zarządzania projektami programistycznymi
z wykorzystaniem LLM do planowania i orkiestracji procesów DevOps.

Example:
    >>> from projektor import Project, Ticket, Orchestrator
    >>> project = Project.load("/path/to/project")
    >>> orchestrator = Orchestrator(project)
    >>> result = await orchestrator.work_on_ticket("PROJ-42")
"""

__version__ = "0.1.2"
__author__ = "Softreck"

# Core
from projektor.analysis.metrics import MetricsCollector, ProjectMetrics
from projektor.analysis.reports import ReportGenerator

# Analysis
from projektor.analysis.toon_parser import ToonParser
from projektor.core.config import Config, ProjectConfig
from projektor.core.events import Event, EventBus
from projektor.core.project import Project
from projektor.core.ticket import Priority, Ticket, TicketStatus, TicketType
from projektor.devops.code_executor import CodeChange, CodeExecutor

# DevOps
from projektor.devops.git_ops import GitOps
from projektor.devops.test_runner import TestResult, TestRunner
from projektor.orchestration.executor import ExecutionResult, PlanExecutor

# Orchestration
from projektor.orchestration.orchestrator import Orchestrator
from projektor.orchestration.planner import TaskPlan, TaskPlanner
from projektor.planning.backlog import Backlog
from projektor.planning.milestone import Milestone

# Planning
from projektor.planning.roadmap import Roadmap
from projektor.planning.sprint import Sprint

__all__ = [
    # Version
    "__version__",
    # Core
    "Project",
    "Ticket",
    "TicketType",
    "TicketStatus",
    "Priority",
    "Config",
    "ProjectConfig",
    "Event",
    "EventBus",
    # Planning
    "Roadmap",
    "Milestone",
    "Sprint",
    "Backlog",
    # Orchestration
    "Orchestrator",
    "TaskPlanner",
    "TaskPlan",
    "PlanExecutor",
    "ExecutionResult",
    # DevOps
    "GitOps",
    "TestRunner",
    "TestResult",
    "CodeExecutor",
    "CodeChange",
    # Analysis
    "ToonParser",
    "MetricsCollector",
    "ProjectMetrics",
    "ReportGenerator",
]
