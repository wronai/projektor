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

__version__ = "0.1.13"
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
from projektor.planning.roadmap import Goal, Roadmap
from projektor.planning.sprint import Sprint, create_sprint

# Integration
from projektor.integration import (
    # Install API (główne)
    install,
    uninstall,
    is_installed,
    get_handler,
    load_config,
    # Decorators
    track_errors,
    track_async_errors,
    catch_errors,
    catch_async_errors,
    # Context managers
    ErrorTracker,
    projektor_guard,
    # Error handling
    ErrorHandler,
    install_global_handler,
    uninstall_global_handler,
    # Hooks
    Hook,
    HookType,
    Hooks,
    on_error,
    on_start,
    on_success,
    # Config
    IntegrationConfig,
    load_integration_config,
    load_from_pyproject,
)

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
    "Goal",
    "Milestone",
    "Sprint",
    "create_sprint",
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
    # Integration - Install API
    "install",
    "uninstall",
    "is_installed",
    "get_handler",
    "load_config",
    # Integration - Decorators
    "track_errors",
    "track_async_errors",
    "catch_errors",
    "catch_async_errors",
    # Integration - Context managers
    "ErrorTracker",
    "projektor_guard",
    # Integration - Error handling
    "ErrorHandler",
    "install_global_handler",
    "uninstall_global_handler",
    # Integration - Hooks
    "Hook",
    "HookType",
    "Hooks",
    "on_error",
    "on_start",
    "on_success",
    # Integration - Config
    "IntegrationConfig",
    "load_integration_config",
    "load_from_pyproject",
]
