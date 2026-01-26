"""
DevOps module - automatyzacja CI/CD i operacje Git.
"""

from projektor.devops.git_ops import GitOps, CommitInfo
from projektor.devops.test_runner import TestRunner, TestResult, TestWatcher
from projektor.devops.code_executor import CodeExecutor, CodeChange

__all__ = [
    "GitOps",
    "CommitInfo",
    "TestRunner",
    "TestResult",
    "TestWatcher",
    "CodeExecutor",
    "CodeChange",
]
