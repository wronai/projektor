#!/usr/bin/env python3
"""
Basic usage example for Projektor.

This example demonstrates:
- Creating a project
- Adding tickets
- Setting up sprints
- Basic orchestration workflow
"""

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from projektor import (
    Project, Ticket, TicketType, Priority,
    Roadmap, Goal, Milestone, Sprint, create_sprint, Backlog,
    Orchestrator,
)


def demo_tickets():
    """Demonstrate ticket management."""
    print("\n" + "="*60)
    print("📝 TICKET MANAGEMENT")
    print("="*60)
    
    # Create tickets
    bug = Ticket(
        id="BUG-1",
        title="Login button not working on mobile",
        description="Users report that the login button is unresponsive on iOS devices",
        ticket_type=TicketType.BUG,
        priority=Priority.HIGH,
    )
    
    feature = Ticket(
        id="FEAT-1",
        title="Add dark mode support",
        description="Implement a dark mode theme for the application",
        ticket_type=TicketType.FEATURE,
        priority=Priority.MEDIUM,
    )
    
    tech_debt = Ticket(
        id="TECH-1",
        title="Refactor authentication module",
        description="Reduce cyclomatic complexity in auth.py from 35 to < 15",
        ticket_type=TicketType.TECH_DEBT,
        priority=Priority.LOW,
    )
    
    # Add acceptance criteria
    feature.add_acceptance_criteria("Dark mode toggle in settings")
    feature.add_acceptance_criteria("Persist user preference")
    feature.add_acceptance_criteria("System default option available")
    
    print(f"\n🐛 Bug: {bug.id} - {bug.title}")
    print(f"   Status: {bug.status.value}, Priority: {bug.priority.value}")
    
    print(f"\n✨ Feature: {feature.id} - {feature.title}")
    print(f"   Status: {feature.status.value}")
    print(f"   Acceptance Criteria: {len(feature.acceptance_criteria)} items")
    
    print(f"\n🔧 Tech Debt: {tech_debt.id} - {tech_debt.title}")
    
    # Workflow demonstration
    print("\n--- Starting work on bug ---")
    bug.start()
    print(f"   Status: {bug.status.value}")
    
    print("\n--- Bug completed! ---")
    bug.complete()
    print(f"   Status: {bug.status.value}")
    print(f"   Completed at: {bug.completed_at}")


def demo_sprint():
    """Demonstrate sprint management."""
    print("\n" + "="*60)
    print("🏃 SPRINT MANAGEMENT")
    print("="*60)
    
    # Create sprint
    sprint = create_sprint(
        id="SPRINT-1",
        name="Sprint 1 - Core Features",
        goal="Implement authentication and basic user management",
        duration_weeks=2,
    )
    
    print(f"\n📅 Sprint: {sprint.name}")
    print(f"   Duration: {sprint.duration_days} days")
    print(f"   Start: {sprint.start_date.strftime('%Y-%m-%d')}")
    print(f"   End: {sprint.end_date.strftime('%Y-%m-%d')}")
    
    # Add tickets
    sprint.add_ticket("AUTH-1", points=5)
    sprint.add_ticket("AUTH-2", points=3)
    sprint.add_ticket("USER-1", points=8)
    
    print(f"\n   Tickets: {len(sprint.tickets)}")
    print(f"   Total points: {sprint.metrics.planned_points}")
    
    # Start sprint
    sprint.start()
    print(f"\n   Sprint started! Status: {sprint.status.value}")
    
    # Complete some work
    sprint.complete_ticket("AUTH-1")
    sprint.complete_ticket("AUTH-2")
    
    metrics = sprint.metrics
    print(f"\n   Progress: {sprint.progress:.1f}%")
    print(f"   Completed: {metrics.completed_points}/{metrics.planned_points} points")
    print(f"   Velocity: {metrics.velocity:.1f}")


def demo_backlog():
    """Demonstrate backlog management."""
    print("\n" + "="*60)
    print("📋 BACKLOG MANAGEMENT")
    print("="*60)
    
    backlog = Backlog()
    
    # Add items with story points
    backlog.add("STORY-1", points=5)
    backlog.add("STORY-2", points=8)
    backlog.add("STORY-3", points=3)
    backlog.add("STORY-4", points=13)
    backlog.add("STORY-5", points=2)
    
    print(f"\n📊 Backlog has {len(backlog.items)} items")
    print(f"   Total points: {backlog.total_points}")
    
    print("\n   Top 3 items:")
    for item in backlog.get_top(3):
        print(f"   {item.priority}. {item.ticket_id} ({item.points} pts)")
    
    # Sprint planning
    print("\n--- Sprint Planning (capacity: 15 pts) ---")
    sprint_items = backlog.get_for_sprint(capacity=15)
    
    print(f"   Selected for sprint:")
    for item in sprint_items:
        print(f"   - {item.ticket_id} ({item.points} pts)")
    
    total = sum(i.points for i in sprint_items)
    print(f"   Total: {total} points")
    
    # Reprioritize
    print("\n--- Reprioritizing STORY-5 to top ---")
    backlog.move_to_top("STORY-5")
    
    print("   New order:")
    for item in backlog.get_top(3):
        print(f"   {item.priority}. {item.ticket_id}")


def demo_roadmap():
    """Demonstrate roadmap and milestone management."""
    print("\n" + "="*60)
    print("🗺️ ROADMAP")
    print("="*60)
    
    roadmap = Roadmap(
        vision="Build the most developer-friendly project management tool",
        goals=[
            Goal(
                id="G1",
                title="Launch MVP",
                description="Release minimum viable product to early adopters",
                target_date=datetime.now() + timedelta(days=90),
            ),
            Goal(
                id="G2",
                title="Enterprise Ready",
                description="Add features required for enterprise customers",
                target_date=datetime.now() + timedelta(days=180),
            ),
        ]
    )
    
    # Add milestones
    m1 = Milestone(
        id="M1",
        name="Core Features Complete",
        description="All core features implemented and tested",
        deadline=datetime.now() + timedelta(days=45),
    )
    m1.add_ticket("CORE-1")
    m1.add_ticket("CORE-2")
    m1.complete_ticket("CORE-1")
    
    m2 = Milestone(
        id="M2",
        name="Beta Release",
        description="Public beta available",
        deadline=datetime.now() + timedelta(days=75),
    )
    m2.add_ticket("BETA-1")
    m2.add_ticket("BETA-2")
    m2.add_ticket("BETA-3")
    
    roadmap.add_milestone(m1)
    roadmap.add_milestone(m2)
    
    print(f"\n🎯 Vision: {roadmap.vision}")
    
    print(f"\n📎 Goals:")
    for goal in roadmap.goals:
        status = "✅" if goal.completed else "⬜"
        print(f"   {status} {goal.title}")
    
    print(f"\n🏁 Milestones:")
    for milestone in roadmap.milestones:
        print(f"   • {milestone.name}")
        print(f"     Deadline: {milestone.deadline.strftime('%Y-%m-%d')}")
        print(f"     Progress: {milestone.progress:.0f}%")
        print(f"     Days remaining: {milestone.days_remaining}")
    
    print(f"\n📈 Overall Progress: {roadmap.progress:.1f}%")


async def demo_orchestration():
    """Demonstrate orchestration (mock/simplified)."""
    print("\n" + "="*60)
    print("🎬 ORCHESTRATION")
    print("="*60)
    
    print("\n⚠️ Note: Full orchestration requires a project setup and LLM.")
    print("   This is a conceptual demonstration.\n")
    
    # Show workflow concept
    print("   Orchestration workflow:")
    print("   1. 📥 Receive ticket")
    print("   2. 🔍 Analyze codebase (TOON)")
    print("   3. 📋 Generate plan (LLM)")
    print("   4. ✏️  Execute changes")
    print("   5. 🧪 Run tests")
    print("   6. 📤 Commit changes")
    
    print("\n   Example command:")
    print('   $ projektor work on TECH-1')
    print()
    print("   This would:")
    print("   - Load ticket TECH-1 details")
    print("   - Analyze code structure")
    print("   - Generate refactoring plan")
    print("   - Apply code changes")
    print("   - Run pytest")
    print("   - Commit with message referencing TECH-1")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("🎬 PROJEKTOR - LLM-Orchestrated Project Management")
    print("="*60)
    
    demo_tickets()
    demo_sprint()
    demo_backlog()
    demo_roadmap()
    
    asyncio.run(demo_orchestration())
    
    print("\n" + "="*60)
    print("✅ Demo complete!")
    print("="*60)
    print("\nFor more information:")
    print("  $ projektor --help")
    print("  $ projektor project init myproject")
    print("  $ projektor ticket create 'My first ticket'")
    print()


if __name__ == "__main__":
    main()
