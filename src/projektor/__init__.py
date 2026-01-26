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

__version__ = "0.1.0"
__author__ = "Softreck"

# Core
from projektor.core.project import Project
from projektor.core.ticket import Ticket, TicketType, TicketStatus, Priority
from projektor.core.config import Config, ProjectConfig
from projektor.core.events import Event, EventBus

# Planning
from projektor.planning.roadmap import Roadmap
from projektor.planning.milestone import Milestone
from projektor.planning.sprint import Sprint
from projektor.planning.backlog import Backlog

# Orchestration
from projektor.orchestration.orchestrator import Orchestrator
from projektor.orchestration.planner import TaskPlanner, TaskPlan
from projektor.orchestration.executor import PlanExecutor, ExecutionResult

# DevOps
from projektor.devops.git_ops import GitOps
from projektor.devops.test_runner import TestRunner, TestResult
from projektor.devops.code_executor import CodeExecutor, CodeChange

# Analysis
from projektor.analysis.toon_parser import ToonParser
from projektor.analysis.metrics import MetricsCollector, ProjectMetrics
from projektor.analysis.reports import ReportGenerator

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
