"""
Pytest configuration and fixtures.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure."""
    # Create directories
    src_dir = temp_dir / "src" / "myproject"
    src_dir.mkdir(parents=True)

    tests_dir = temp_dir / "tests"
    tests_dir.mkdir()

    # Create sample files
    (src_dir / "__init__.py").write_text('__version__ = "0.1.0"')
    (src_dir / "main.py").write_text(
        '''
def main():
    """Main entry point."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
    )

    (tests_dir / "test_main.py").write_text(
        """
def test_main():
    assert True
"""
    )

    # Create projektor.yaml
    (temp_dir / "projektor.yaml").write_text(
        """
project:
  name: myproject
  language: python
  version: "0.1.0"
"""
    )

    yield temp_dir


@pytest.fixture
def sample_ticket():
    """Create a sample ticket."""
    from projektor.core.ticket import Priority, Ticket, TicketType

    return Ticket(
        id="TEST-1",
        title="Sample ticket",
        description="This is a sample ticket for testing",
        type=TicketType.TASK,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def sample_sprint():
    """Create a sample sprint."""
    from projektor.planning.sprint import create_sprint

    sprint = create_sprint(
        id="SPRINT-1",
        name="Test Sprint",
        goal="Complete test implementation",
        duration_weeks=2,
    )
    return sprint
