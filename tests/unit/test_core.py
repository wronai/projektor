"""
Tests for core module.
"""


from projektor.core.config import Config, LLMConfig, ProjectConfig
from projektor.core.events import Event, EventBus, EventType
from projektor.core.ticket import (
    Priority,
    Ticket,
    TicketStatus,
    TicketType,
    create_bug,
    create_feature,
    create_tech_debt,
)


class TestTicket:
    """Tests for Ticket class."""

    def test_create_basic_ticket(self):
        ticket = Ticket(id="TEST-1", title="Test ticket", description="Test description")

        assert ticket.id == "TEST-1"
        assert ticket.title == "Test ticket"
        assert ticket.status == TicketStatus.BACKLOG
        assert ticket.priority == Priority.MEDIUM

    def test_ticket_workflow(self):
        ticket = Ticket(id="TEST-1", title="Test")

        # Use transition_to (actual API)
        ticket.transition_to(TicketStatus.TODO)
        assert ticket.status == TicketStatus.TODO

        ticket.transition_to(TicketStatus.IN_PROGRESS)
        assert ticket.status == TicketStatus.IN_PROGRESS

    def test_ticket_acceptance_criteria(self):
        ticket = Ticket(id="TEST-1", title="Test")

        ticket.add_acceptance_criteria("AC 1")
        ticket.add_acceptance_criteria("AC 2")

        assert len(ticket.acceptance_criteria) == 2

        # Use mark_complete method
        ticket.acceptance_criteria[0].mark_complete()
        assert ticket.acceptance_criteria[0].completed

    def test_ticket_blocking(self):
        ticket = Ticket(id="TEST-1", title="Test")

        # Need to transition through valid states
        ticket.transition_to(TicketStatus.TODO)
        ticket.transition_to(TicketStatus.BLOCKED)
        assert ticket.status == TicketStatus.BLOCKED

    def test_create_bug(self):
        bug = create_bug(
            id="BUG-1", title="Login fails", description="Cannot login with valid credentials"
        )

        assert bug.type == TicketType.BUG
        assert bug.priority == Priority.HIGH

    def test_create_feature(self):
        feature = create_feature(
            id="FEAT-1", title="Dark mode", description="Add dark mode support"
        )

        assert feature.type == TicketType.FEATURE

    def test_create_tech_debt(self):
        tech_debt = create_tech_debt(
            id="TECH-1", title="Refactor auth module", description="Reduce complexity"
        )

        assert tech_debt.type == TicketType.TECH_DEBT


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        config = Config()

        assert config.project is not None
        assert config.llm is not None
        assert config.orchestration is not None

    def test_project_config(self):
        config = ProjectConfig(name="test-project", language="python")

        assert config.name == "test-project"
        assert config.language == "python"

    def test_llm_config(self):
        config = LLMConfig(model="claude-sonnet-4-20250514", temperature=0.2)

        assert config.model == "claude-sonnet-4-20250514"
        assert config.temperature == 0.2


class TestEvents:
    """Tests for Event system."""

    def test_event_creation(self):
        # Check actual Event constructor
        event = Event(type=EventType.TICKET_CREATED, data={"ticket_id": "TEST-1"})

        assert event.type == EventType.TICKET_CREATED
        assert event.data["ticket_id"] == "TEST-1"

    def test_event_bus_on_emit(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        # Use actual API (on instead of subscribe)
        bus.on(EventType.TICKET_CREATED, handler)

        event = Event(type=EventType.TICKET_CREATED, data={"ticket_id": "TEST-1"})
        bus.emit(event)

        assert len(received) == 1
        assert received[0].data["ticket_id"] == "TEST-1"

    def test_event_bus_off(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.on(EventType.TICKET_CREATED, handler)
        bus.off(EventType.TICKET_CREATED, handler)

        event = Event(type=EventType.TICKET_CREATED, data={})
        bus.emit(event)

        assert len(received) == 0
