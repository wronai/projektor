"""
Projektor CLI - interfejs wiersza poleceń.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import click
from click.core import ParameterSource
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_async(coro):
    """Helper to run async functions."""
    return asyncio.run(coro)


@click.group()
@click.option("--project", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, project: str, verbose: bool):
    """
    🎬 Projektor - LLM-orchestrated project management.

    Manage projects, tickets, sprints, and automated development workflows.
    """
    ctx.ensure_object(dict)
    if ctx.get_parameter_source("project") == ParameterSource.DEFAULT:
        env_project = os.environ.get("PROJEKTOR_PROJECT")
        if env_project:
            project = env_project

    project_path = Path(project).resolve()
    if project_path.is_file():
        project_path = project_path.parent
    ctx.obj["project_path"] = project_path
    ctx.obj["verbose"] = verbose

    try:
        from projektor.core.config import Config

        config_path = project_path / "projektor.yaml"
        if config_path.exists():
            ctx.obj["config"] = Config.load(config_path)
        else:
            ctx.obj["config"] = Config.default(project_name=project_path.name)
    except Exception:
        ctx.obj["config"] = None

    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)

        project_env = project_path / ".env"
        if project_env.exists():
            load_dotenv(dotenv_path=project_env, override=False)
    except ImportError:
        pass


# ==================== Project Commands ====================


@cli.group()
def project():
    """Project management commands."""
    pass


@project.command("init")
@click.argument("name")
@click.option("--language", "-l", default="python", help="Project language")
@click.option("--description", "-d", default="", help="Project description")
@click.pass_context
def project_init(ctx, name: str, language: str, description: str):
    """Initialize a new project."""
    from projektor.core.project import Project

    path = ctx.obj["project_path"]

    try:
        Project.init(
            path=path,
            name=name,
            language=language,
            description=description,
        )

        console.print(f"[green]✓[/green] Project '{name}' initialized at {path}")
        console.print(f"  Language: {language}")
        console.print(f"  Config: {path / 'projektor.yaml'}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize: {e}")
        sys.exit(1)


@project.command("info")
@click.pass_context
def project_info(ctx):
    """Show project information."""
    from projektor.core.project import Project

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)

        console.print(
            Panel(
                f"[bold]{project.metadata.name}[/bold] v{project.metadata.version}\n"
                f"{project.metadata.description or 'No description'}\n\n"
                f"Language: {project.metadata.language}\n"
                f"Repository: {project.get_git_remote() or 'Not set'}",
                title="Project Info",
            )
        )

        # State
        console.print("\n[bold]State:[/bold]")
        console.print(f"  Active tickets: {len(project.state.active_tickets)}")
        console.print(f"  Completed: {len(project.state.completed_tickets)}")
        console.print(f"  Blocked: {len(project.state.blocked_tickets)}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load project: {e}")
        sys.exit(1)


@project.command("status")
@click.pass_context
def project_status(ctx):
    """Show project status."""
    from projektor.core.project import Project

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)

        # Tickets table
        tickets = project.list_tickets()

        if not tickets:
            console.print("[dim]No tickets found[/dim]")
            return

        table = Table(title="Tickets")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Status", style="green")
        table.add_column("Priority")

        for ticket in tickets[:20]:  # Limit to 20
            table.add_row(
                ticket.id,
                ticket.title[:50],
                ticket.status.value,
                ticket.priority.value,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


# ==================== Ticket Commands ====================


@cli.group()
def ticket():
    """Ticket management commands."""
    pass


@ticket.command("create")
@click.argument("title")
@click.option(
    "--type",
    "-t",
    "ticket_type",
    default="task",
    type=click.Choice(["task", "bug", "feature", "story", "tech_debt"]),
)
@click.option(
    "--priority", "-p", default="medium", type=click.Choice(["critical", "high", "medium", "low"])
)
@click.option("--description", "-d", default="")
@click.pass_context
def ticket_create(ctx, title: str, ticket_type: str, priority: str, description: str):
    """Create a new ticket."""
    from projektor.core.project import Project
    from projektor.core.ticket import Priority, Ticket, TicketType

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)

        # Generate ID
        existing_ids = [t.id for t in project.list_tickets()]
        prefix = project.metadata.name[:4].upper()
        num = len(existing_ids) + 1
        ticket_id = f"{prefix}-{num}"

        ticket = Ticket(
            id=ticket_id,
            title=title,
            description=description,
            type=TicketType(ticket_type),
            priority=Priority(priority),
        )

        project.add_ticket(ticket)
        project.save()

        console.print(f"[green]✓[/green] Created ticket [cyan]{ticket_id}[/cyan]: {title}")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@ticket.command("show")
@click.argument("ticket_id")
@click.pass_context
def ticket_show(ctx, ticket_id: str):
    """Show ticket details."""
    from projektor.core.project import Project

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
        ticket = project.get_ticket(ticket_id)

        if not ticket:
            console.print(f"[red]✗[/red] Ticket {ticket_id} not found")
            sys.exit(1)

        console.print(
            Panel(
                f"[bold]{ticket.title}[/bold]\n\n"
                f"{ticket.description or 'No description'}\n\n"
                f"Type: {ticket.type.value}\n"
                f"Status: {ticket.status.value}\n"
                f"Priority: {ticket.priority.value}\n"
                f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"Assignee: {ticket.assignee or 'Unassigned'}",
                title=f"[cyan]{ticket_id}[/cyan]",
            )
        )

        # Acceptance criteria
        if ticket.acceptance_criteria:
            console.print("\n[bold]Acceptance Criteria:[/bold]")
            for ac in ticket.acceptance_criteria:
                status = "✅" if ac.completed else "⬜"
                console.print(f"  {status} {ac.description}")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@ticket.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--type", "-t", "ticket_type", help="Filter by type")
@click.option("--limit", "-n", default=20, help="Max tickets to show")
@click.pass_context
def ticket_list(ctx, status: str | None, ticket_type: str | None, limit: int):
    """List tickets."""
    from projektor.core.project import Project
    from projektor.core.ticket import TicketStatus, TicketType

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)

        # Filters
        status_filter = TicketStatus(status) if status else None
        type_filter = TicketType(ticket_type) if ticket_type else None

        tickets = project.list_tickets(status=status_filter.value if status_filter else None)

        if type_filter:
            tickets = [t for t in tickets if t.type == type_filter]

        if not tickets:
            console.print("[dim]No tickets found[/dim]")
            return

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Status", style="green")
        table.add_column("Priority")

        for ticket in tickets[:limit]:
            table.add_row(
                ticket.id,
                ticket.title[:40] + ("..." if len(ticket.title) > 40 else ""),
                ticket.type.value,
                ticket.status.value,
                ticket.priority.value,
            )

        console.print(table)

        if len(tickets) > limit:
            console.print(f"\n[dim]Showing {limit} of {len(tickets)} tickets[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@ticket.command("start")
@click.argument("ticket_id")
@click.pass_context
def ticket_start(ctx, ticket_id: str):
    """Start working on a ticket."""
    from projektor.core.project import Project
    from projektor.core.ticket import TicketStatus

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
        ticket = project.get_ticket(ticket_id)

        if not ticket:
            console.print(f"[red]✗[/red] Ticket {ticket_id} not found")
            sys.exit(1)

        if ticket.status == TicketStatus.BACKLOG:
            ticket.transition_to(TicketStatus.TODO)

        ok = ticket.start()
        if not ok:
            console.print(
                f"[red]✗[/red] Cannot start ticket {ticket_id} from status: {ticket.status.value}"
            )
            sys.exit(1)

        project.save()

        console.print(f"[green]✓[/green] Started work on [cyan]{ticket_id}[/cyan]")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@ticket.command("complete")
@click.argument("ticket_id")
@click.pass_context
def ticket_complete(ctx, ticket_id: str):
    """Mark ticket as complete."""
    from projektor.core.project import Project
    from projektor.core.ticket import TicketStatus

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
        ticket = project.get_ticket(ticket_id)

        if not ticket:
            console.print(f"[red]✗[/red] Ticket {ticket_id} not found")
            sys.exit(1)

        if not ticket.all_criteria_met:
            console.print(
                f"[red]✗[/red] Cannot complete {ticket_id}: acceptance criteria not met"
            )
            sys.exit(1)

        if ticket.status == TicketStatus.BACKLOG:
            ticket.transition_to(TicketStatus.TODO)
        if ticket.status == TicketStatus.TODO:
            ticket.transition_to(TicketStatus.IN_PROGRESS)
        if ticket.status == TicketStatus.IN_PROGRESS:
            ticket.transition_to(TicketStatus.IN_REVIEW)
        if ticket.status == TicketStatus.IN_REVIEW:
            ticket.transition_to(TicketStatus.TESTING)

        ok = ticket.complete()
        if not ok:
            console.print(
                f"[red]✗[/red] Cannot complete ticket {ticket_id} from status: {ticket.status.value}"
            )
            sys.exit(1)

        project.save()

        console.print(f"[green]✓[/green] Completed [cyan]{ticket_id}[/cyan]")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


# ==================== Sprint Commands ====================


@cli.group()
def sprint():
    """Sprint management commands."""
    pass


@sprint.command("create")
@click.argument("name")
@click.option("--goal", "-g", default="", help="Sprint goal")
@click.option("--weeks", "-w", default=2, help="Duration in weeks")
@click.pass_context
def sprint_create(ctx, name: str, goal: str, weeks: int):
    """Create a new sprint."""
    from projektor.planning.sprint import create_sprint

    # Generate ID
    sprint_id = f"SPRINT-{name.replace(' ', '-').upper()}"

    sprint = create_sprint(
        id=sprint_id,
        name=name,
        goal=goal,
        duration_weeks=weeks,
    )

    console.print(f"[green]✓[/green] Created sprint [cyan]{sprint_id}[/cyan]")
    console.print(f"  Name: {name}")
    console.print(f"  Goal: {goal or 'Not set'}")
    console.print(f"  Duration: {weeks} weeks")
    console.print(f"  Start: {sprint.start_date}")
    console.print(f"  End: {sprint.end_date}")


# ==================== Orchestration Commands ====================


@cli.group()
def work():
    """Orchestration and automation commands."""
    pass


@work.command("on")
@click.argument("ticket_id")
@click.option("--dry-run", is_flag=True, help="Don't make changes")
@click.option("--no-commit", is_flag=True, help="Don't auto-commit")
@click.option("--no-tests", is_flag=True, help="Skip tests")
@click.pass_context
def work_on(ctx, ticket_id: str, dry_run: bool, no_commit: bool, no_tests: bool):
    """Work on a ticket using LLM orchestration."""
    from projektor.core.project import Project
    from projektor.orchestration.orchestrator import Orchestrator

    path = ctx.obj["project_path"]
    cfg = ctx.obj.get("config")

    try:
        project = Project.load(path)

        model = getattr(getattr(cfg, "llm", None), "model", "openrouter/x-ai/grok-3-fast")
        max_iterations = getattr(getattr(cfg, "orchestration", None), "max_iterations", 10)

        if ctx.get_parameter_source("no_commit") == ParameterSource.DEFAULT:
            auto_commit = getattr(getattr(cfg, "orchestration", None), "auto_commit", True)
        else:
            auto_commit = not no_commit

        if ctx.get_parameter_source("no_tests") == ParameterSource.DEFAULT:
            run_tests = getattr(getattr(cfg, "orchestration", None), "run_tests", True)
        else:
            run_tests = not no_tests

        if ctx.get_parameter_source("dry_run") == ParameterSource.DEFAULT:
            dry_run_effective = getattr(getattr(cfg, "orchestration", None), "dry_run", False)
        else:
            dry_run_effective = dry_run

        orchestrator = Orchestrator(
            project=project,
            model=model,
            auto_commit=auto_commit,
            run_tests=run_tests,
            max_iterations=max_iterations,
            dry_run=dry_run_effective,
        )

        console.print(f"[bold]Working on [cyan]{ticket_id}[/cyan]...[/bold]")

        if dry_run_effective:
            console.print("[yellow]DRY RUN - no changes will be made[/yellow]")

        result = run_async(orchestrator.work_on_ticket(ticket_id))

        # Display result
        if result.status.value == "completed":
            console.print("\n[green]✓[/green] Work completed!")
        else:
            console.print(f"\n[red]✗[/red] Work failed: {result.status.value}")

        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Steps: {result.steps_completed} completed, {result.steps_failed} failed")
        console.print(f"  Files modified: {len(result.files_modified)}")

        if result.tests_run:
            console.print(f"  Tests: {result.tests_passed} passed, {result.tests_failed} failed")
            if result.coverage:
                console.print(f"  Coverage: {result.coverage:.1f}%")

        if result.commits:
            console.print(f"  Commits: {', '.join(result.commits[:3])}")

        if result.errors:
            console.print("\n[red]Errors:[/red]")
            for error in result.errors:
                console.print(f"  - {error}")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@work.command("plan")
@click.argument("ticket_id")
@click.option("--output", "-o", type=click.Path(), help="Save plan to file")
@click.pass_context
def work_plan(ctx, ticket_id: str, output: str | None):
    """Generate a plan for a ticket (without executing)."""
    from projektor.core.project import Project
    from projektor.orchestration.orchestrator import Orchestrator

    path = ctx.obj["project_path"]
    cfg = ctx.obj.get("config")

    try:
        project = Project.load(path)

        model = getattr(getattr(cfg, "llm", None), "model", "openrouter/x-ai/grok-3-fast")
        orchestrator = Orchestrator(project=project, model=model, dry_run=True)

        console.print(f"[bold]Planning for [cyan]{ticket_id}[/cyan]...[/bold]")

        plan = run_async(orchestrator.plan_ticket(ticket_id))

        if not plan.success:
            console.print(f"[red]✗[/red] Planning failed: {plan.error}")
            sys.exit(1)

        console.print(f"\n[green]✓[/green] Plan generated with {len(plan.steps)} steps")
        console.print(f"  Estimated time: {plan.estimated_time_minutes} minutes")

        console.print("\n[bold]Steps:[/bold]")
        for step in plan.steps:
            console.print(f"  {step.step_number}. [{step.step_type.value}] {step.description}")
            if step.target_file:
                console.print(f"      File: {step.target_file}")

        if output:
            with open(output, "w") as f:
                json.dump(plan.to_dict(), f, indent=2)
            console.print(f"\n[dim]Plan saved to {output}[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


# ==================== Test Commands ====================


@cli.group()
def test():
    """Test management commands."""
    pass


@test.command("run")
@click.option("--coverage", "-c", is_flag=True, help="Include coverage")
@click.option("--file", "-f", "test_file", help="Specific test file")
@click.option("--name", "-k", "test_name", help="Test name pattern")
@click.pass_context
def test_run(ctx, coverage: bool, test_file: str | None, test_name: str | None):
    """Run project tests."""
    from projektor.devops.test_runner import TestRunner

    path = ctx.obj["project_path"]

    runner = TestRunner(project_path=path, coverage=coverage)

    console.print("[bold]Running tests...[/bold]")

    result = run_async(runner.run(test_file=test_file, test_name=test_name))

    # Display results
    if result.success:
        console.print("\n[green]✓[/green] All tests passed!")
    else:
        console.print("\n[red]✗[/red] Tests failed!")

    console.print("\n[bold]Results:[/bold]")
    console.print(f"  Passed: {result.passed}")
    console.print(f"  Failed: {result.failed}")
    console.print(f"  Skipped: {result.skipped}")
    console.print(f"  Duration: {result.duration_seconds:.2f}s")

    if result.coverage is not None:
        console.print(f"  Coverage: {result.coverage:.1f}%")

    if result.failed_tests:
        console.print("\n[red]Failed tests:[/red]")
        for test in result.failed_tests:
            console.print(f"  - {test}")

    sys.exit(0 if result.success else 1)


# ==================== Git Commands ====================


@cli.group()
def git():
    """Git operations."""
    pass


@git.command("status")
@click.pass_context
def git_status(ctx):
    """Show git status."""
    from projektor.devops.git_ops import GitOps

    path = ctx.obj["project_path"]

    try:
        git = GitOps(path)
        status = git.status()

        console.print(f"[bold]Branch:[/bold] {git.current_branch}")

        if git.is_clean:
            console.print("[green]Working directory clean[/green]")
            return

        if status["staged"]:
            console.print("\n[green]Staged:[/green]")
            for f in status["staged"]:
                console.print(f"  {f}")

        if status["modified"]:
            console.print("\n[yellow]Modified:[/yellow]")
            for f in status["modified"]:
                console.print(f"  {f}")

        if status["untracked"]:
            console.print("\n[dim]Untracked:[/dim]")
            for f in status["untracked"]:
                console.print(f"  {f}")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@git.command("log")
@click.option("--count", "-n", default=10, help="Number of commits")
@click.pass_context
def git_log(ctx, count: int):
    """Show recent commits."""
    from projektor.devops.git_ops import GitOps

    path = ctx.obj["project_path"]

    try:
        git = GitOps(path)
        commits = git.get_recent_commits(count)

        for commit in commits:
            console.print(
                f"[cyan]{commit.short_hash}[/cyan] "
                f"{commit.message[:60]} "
                f"[dim]({commit.author})[/dim]"
            )

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


def main():
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
