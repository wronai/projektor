"""
Tests for planning module.
"""

from datetime import date, timedelta

from projektor.planning.backlog import Backlog, BacklogItem
from projektor.planning.milestone import Milestone
from projektor.planning.roadmap import Goal, Roadmap
from projektor.planning.sprint import SprintStatus, create_sprint


class TestMilestone:
    """Tests for Milestone class."""

    def test_create_milestone(self):
        deadline = date.today() + timedelta(days=30)
        milestone = Milestone(
            name="MVP Release", description="First public release", deadline=deadline
        )

        assert milestone.name == "MVP Release"
        assert milestone.description == "First public release"
        assert not milestone.completed

    def test_milestone_add_tickets(self):
        milestone = Milestone(name="Test", deadline=date.today() + timedelta(days=30))

        milestone.add_ticket("T1")
        milestone.add_ticket("T2")

        assert len(milestone.tickets) == 2
        assert "T1" in milestone.tickets

    def test_milestone_overdue(self):
        past = date.today() - timedelta(days=1)
        milestone = Milestone(name="Test", deadline=past)

        assert milestone.is_overdue
        assert milestone.days_remaining < 0

    def test_milestone_not_overdue_when_completed(self):
        past = date.today() - timedelta(days=1)
        milestone = Milestone(name="Test", deadline=past)
        milestone.complete()

        assert not milestone.is_overdue  # Completed milestones aren't overdue


class TestRoadmap:
    """Tests for Roadmap class."""

    def test_create_roadmap(self):
        roadmap = Roadmap(
            vision="Build the best project management tool",
            goals=["Launch MVP", "Enterprise Ready"],  # Can use strings
        )

        assert roadmap.vision is not None
        assert len(roadmap.goals) == 2
        # Goals should be converted to Goal objects
        assert isinstance(roadmap.goals[0], Goal)

    def test_roadmap_add_milestone(self):
        roadmap = Roadmap(vision="Test")

        milestone = Milestone(name="Test", deadline=date.today() + timedelta(days=30))
        roadmap.add_milestone(milestone)

        assert len(roadmap.milestones) == 1

    def test_roadmap_progress(self):
        roadmap = Roadmap(vision="Test")

        m1 = Milestone(name="Test 1", deadline=date.today() + timedelta(days=30))
        m1.complete()  # Mark as completed

        m2 = Milestone(name="Test 2", deadline=date.today() + timedelta(days=60))

        roadmap.add_milestone(m1)
        roadmap.add_milestone(m2)

        assert roadmap.progress == 50.0


class TestSprint:
    """Tests for Sprint class."""

    def test_create_sprint(self):
        sprint = create_sprint(
            id="S1", name="Sprint 1", goal="Complete core features", duration_weeks=2
        )

        assert sprint.id == "S1"
        assert sprint.status == SprintStatus.PLANNING
        assert sprint.duration_days == 14

    def test_sprint_workflow(self):
        sprint = create_sprint(id="S1", name="Test", duration_weeks=2)

        assert sprint.status == SprintStatus.PLANNING

        sprint.start()
        assert sprint.status == SprintStatus.ACTIVE
        assert sprint.is_active

        sprint.complete()
        assert sprint.status == SprintStatus.COMPLETED

    def test_sprint_tickets(self):
        sprint = create_sprint(id="S1", name="Test", duration_weeks=2)

        sprint.add_ticket("T1", points=3)
        sprint.add_ticket("T2", points=5)

        assert len(sprint.tickets) == 2
        assert sprint.total_points == 8

        sprint.complete_ticket("T1")
        assert sprint.completed_points == 3


class TestBacklog:
    """Tests for Backlog class."""

    def test_create_backlog(self):
        backlog = Backlog()

        assert len(backlog.items) == 0
        assert backlog.size == 0

    def test_backlog_add_items(self):
        backlog = Backlog()

        backlog.add("T1", priority=0)
        backlog.add("T2", priority=1)
        backlog.add("T3", priority=2)

        assert len(backlog.items) == 3
        assert backlog.items[0].ticket_id == "T1"

    def test_backlog_get_top(self):
        backlog = Backlog()

        backlog.add("T1", priority=0)
        backlog.add("T2", priority=1)
        backlog.add("T3", priority=2)

        top = backlog.get_top(2)

        assert len(top) == 2
        assert top[0] == "T1"
        assert top[1] == "T2"

    def test_backlog_move_to_top(self):
        backlog = Backlog()

        backlog.add("T1", priority=0)
        backlog.add("T2", priority=1)
        backlog.add("T3", priority=2)

        backlog.move_to_top("T3")

        assert backlog.items[0].ticket_id == "T3"

    def test_backlog_get_for_sprint(self):
        backlog = Backlog()

        backlog.add("T1")
        backlog.add("T2")
        backlog.add("T3")
        backlog.add("T4")

        # Define points mapping
        ticket_points = {
            "T1": 3,
            "T2": 5,
            "T3": 2,
            "T4": 8,
        }

        # Capacity of 10 points
        items = backlog.get_for_sprint(points_capacity=10, ticket_points=ticket_points)

        assert len(items) == 3  # T1(3) + T2(5) + T3(2) = 10
        total_points = sum(ticket_points[t] for t in items)
        assert total_points == 10

    def test_backlog_remove(self):
        backlog = Backlog()

        backlog.add("T1")
        backlog.add("T2")

        assert len(backlog) == 2

        backlog.remove("T1")
        assert len(backlog) == 1
        assert backlog.find("T1") is None


class TestGoal:
    """Tests for Goal class."""

    def test_create_goal(self):
        goal = Goal(description="Launch MVP")

        assert goal.description == "Launch MVP"
        assert not goal.completed

    def test_goal_to_dict(self):
        goal = Goal(description="Test")
        data = goal.to_dict()

        assert data["description"] == "Test"
        assert not data["completed"]


class TestBacklogItem:
    """Tests for BacklogItem class."""

    def test_create_item(self):
        item = BacklogItem(ticket_id="T1", priority_order=0)

        assert item.ticket_id == "T1"
        assert item.priority_order == 0

    def test_item_serialization(self):
        item = BacklogItem(ticket_id="T1", priority_order=5)
        data = item.to_dict()

        restored = BacklogItem.from_dict(data)

        assert restored.ticket_id == item.ticket_id
        assert restored.priority_order == item.priority_order
