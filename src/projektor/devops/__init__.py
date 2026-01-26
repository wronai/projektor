"""
DevOps module - automatyzacja CI/CD i operacje Git.
"""

from projektor.devops.code_executor import CodeChange, CodeExecutor
from projektor.devops.git_ops import CommitInfo, GitOps
from projektor.devops.test_runner import TestResult, TestRunner, TestWatcher

__all__ = [
    "GitOps",
    "CommitInfo",
    "TestRunner",
    "TestResult",
    "TestWatcher",
    "CodeExecutor",
    "CodeChange",
]
