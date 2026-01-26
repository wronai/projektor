"""
Projektor CLI - interfejs wiersza poleceń.
"""

from __future__ import annotations

import asyncio
import json
import logging
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


def _configure_logging(project_path: Path, verbose: bool) -> None:
    log_dir = project_path / ".projektor"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "projektor.log"

    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler_exists = any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == str(log_file)
        for h in root.handlers
    )
    if not file_handler_exists:
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    if verbose:
        stream_handler_exists = any(isinstance(h, logging.StreamHandler) for h in root.handlers)
        if not stream_handler_exists:
            sh = logging.StreamHandler()
            sh.setLevel(level)
            sh.setFormatter(formatter)
            root.addHandler(sh)


def _sync_ticket_state(project, ticket):
    from projektor.core.ticket import TicketStatus

    tid = ticket.id

    if ticket.status in (TicketStatus.DONE, TicketStatus.CANCELLED):
        if tid in project.state.active_tickets:
            project.state.active_tickets.remove(tid)
        if tid in project.state.blocked_tickets:
            project.state.blocked_tickets.remove(tid)
        if ticket.status == TicketStatus.DONE and tid not in project.state.completed_tickets:
            project.state.completed_tickets.append(tid)
        return

    if tid not in project.state.active_tickets:
        project.state.active_tickets.append(tid)
    if tid in project.state.completed_tickets:
        project.state.completed_tickets.remove(tid)

    if ticket.status == TicketStatus.BLOCKED:
        if tid not in project.state.blocked_tickets:
            project.state.blocked_tickets.append(tid)
    else:
        if tid in project.state.blocked_tickets:
            project.state.blocked_tickets.remove(tid)


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

    _configure_logging(project_path, verbose)

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
            load_dotenv(dotenv_path=project_env, override=True)
    except ImportError:
        pass


@cli.command("doctor")
@click.pass_context
def doctor(ctx):
    """Show diagnostics for LLM configuration and environment variables."""
    project_path: Path = ctx.obj["project_path"]
    cfg = ctx.obj.get("config")

    try:
        import projektor as projektor_pkg
        projektor_path = getattr(projektor_pkg, "__file__", None)
    except Exception:
        projektor_path = None

    model = getattr(getattr(cfg, "llm", None), "model", None)
    console.print("[bold]Projektor Doctor[/bold]\n")
    console.print(f"[bold]Project:[/bold] {project_path}")
    console.print(f"[bold]Python:[/bold] {sys.executable}")
    if projektor_path:
        console.print(f"[bold]Projektor package:[/bold] {projektor_path}")
    console.print(f"[bold]Model:[/bold] {model or '[dim]unknown[/dim]'}")

    project_env = project_path / ".env"
    console.print(f"[bold].env:[/bold] {'[green]found[/green]' if project_env.exists() else '[yellow]missing[/yellow]'} ({project_env})")

    def _mask(v: str) -> str:
        if len(v) <= 10:
            return "***"
        return f"{v[:6]}...{v[-4:]}"

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    console.print("\n[bold]LLM Auth Env Vars:[/bold]")
    console.print(
        f"  OPENROUTER_API_KEY: {'[green]set[/green] ' + _mask(openrouter_key) if openrouter_key else '[red]missing[/red]'}"
    )
    console.print(
        f"  OPENAI_API_KEY: {'[green]set[/green] ' + _mask(openai_key) if openai_key else '[dim]missing[/dim]'}"
    )
    console.print(
        f"  ANTHROPIC_API_KEY: {'[green]set[/green] ' + _mask(anthropic_key) if anthropic_key else '[dim]missing[/dim]'}"
    )

    console.print("\n[bold]Tips:[/bold]")
    console.print("  - Put OPENROUTER_API_KEY in your project .env (project root)")
    console.print("  - Or export it in the same shell before running `projektor`")
    console.print("  - If OPENROUTER_API_KEY is set but empty, run: unset OPENROUTER_API_KEY")


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


@ticket.command("assign")
@click.argument("ticket_id")
@click.option("--assignee", "-a", default=None, help="Assignee name (empty to unassign)")
@click.pass_context
def ticket_assign(ctx, ticket_id: str, assignee: str | None):
    """Assign/unassign a ticket."""
    from projektor.core.project import Project

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
        ticket = project.get_ticket(ticket_id)

        if not ticket:
            console.print(f"[red]✗[/red] Ticket {ticket_id} not found")
            sys.exit(1)

        ticket.assignee = assignee or None
        _sync_ticket_state(project, ticket)
        project.save()

        console.print(
            f"[green]✓[/green] Assigned [cyan]{ticket_id}[/cyan] to {ticket.assignee or 'Unassigned'}"
        )

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@ticket.command("update")
@click.argument("ticket_id")
@click.option(
    "--status",
    "-s",
    default=None,
    type=click.Choice(
        [
            "backlog",
            "todo",
            "in_progress",
            "in_review",
            "testing",
            "done",
            "blocked",
            "cancelled",
        ]
    ),
    help="New status",
)
@click.option("--assignee", "-a", default=None, help="Assignee name")
@click.pass_context
def ticket_update(ctx, ticket_id: str, status: str | None, assignee: str | None):
    """Update ticket fields (status/assignee)."""
    from projektor.core.project import Project
    from projektor.core.ticket import TicketStatus

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
        ticket = project.get_ticket(ticket_id)

        if not ticket:
            console.print(f"[red]✗[/red] Ticket {ticket_id} not found")
            sys.exit(1)

        if assignee is not None:
            ticket.assignee = assignee or None

        if status is not None:
            desired = TicketStatus(status)

            if desired == TicketStatus.IN_PROGRESS:
                if ticket.status == TicketStatus.BACKLOG:
                    ticket.transition_to(TicketStatus.TODO)
                ok = ticket.start()
                if not ok:
                    console.print(
                        f"[red]✗[/red] Cannot set status to in_progress from: {ticket.status.value}"
                    )
                    sys.exit(1)
            elif desired == TicketStatus.DONE:
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
                        f"[red]✗[/red] Cannot set status to done from: {ticket.status.value}"
                    )
                    sys.exit(1)
            elif desired == TicketStatus.BLOCKED:
                ok = ticket.block()
                if not ok:
                    console.print(
                        f"[red]✗[/red] Cannot set status to blocked from: {ticket.status.value}"
                    )
                    sys.exit(1)
            else:
                ok = ticket.transition_to(desired)
                if not ok:
                    console.print(
                        f"[red]✗[/red] Invalid status transition: {ticket.status.value} -> {desired.value}"
                    )
                    sys.exit(1)

        _sync_ticket_state(project, ticket)
        project.save()

        console.print(
            f"[green]✓[/green] Updated [cyan]{ticket_id}[/cyan] (status={ticket.status.value}, assignee={ticket.assignee or 'Unassigned'})"
        )

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


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

        _sync_ticket_state(project, ticket)

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

        _sync_ticket_state(project, ticket)

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


@work.command("logs")
@click.argument("ticket_id", required=False)
@click.option(
    "--show",
    type=click.Choice(
        [
            "meta",
            "plan",
            "plan_repaired",
            "execution",
            "validation",
            "tests",
            "tests_stdout",
            "tests_stderr",
            "plan_tests",
            "plan_tests_stdout",
            "plan_tests_stderr",
            "plan_test_command",
            "plan_test_command_stdout",
            "plan_test_command_stderr",
            "result",
            "exception",
        ]
    ),
)
@click.option("--tail", default=200, help="Tail N lines for text outputs")
@click.pass_context
def work_logs(ctx, ticket_id: str | None, show: str | None, tail: int):
    """Show saved logs/artifacts for the most recent orchestration run."""
    path: Path = ctx.obj["project_path"]
    runs_dir = path / ".projektor" / "runs"

    if not runs_dir.exists():
        console.print(f"[dim]No runs directory found at {runs_dir}[/dim]")
        return

    runs = [p for p in runs_dir.iterdir() if p.is_dir()]
    if ticket_id:
        runs = [p for p in runs if p.name.startswith(f"{ticket_id}_")]

    runs.sort(key=lambda p: p.name, reverse=True)
    if not runs:
        console.print("[dim]No runs found[/dim]")
        return

    latest = runs[0]
    console.print(f"[bold]Latest run:[/bold] {latest}")

    mapping = {
        "meta": latest / "meta.json",
        "plan": latest / "plan.json",
        "plan_repaired": latest / "plan_repaired.json",
        "execution": latest / "execution.json",
        "validation": latest / "validation_errors.json",
        "tests": latest / "tests.json",
        "tests_stdout": latest / "tests_stdout.txt",
        "tests_stderr": latest / "tests_stderr.txt",
        "plan_tests": latest / "plan_tests.json",
        "plan_tests_stdout": latest / "plan_tests_stdout.txt",
        "plan_tests_stderr": latest / "plan_tests_stderr.txt",
        "plan_test_command": latest / "plan_test_command.json",
        "plan_test_command_stdout": latest / "plan_test_command_stdout.txt",
        "plan_test_command_stderr": latest / "plan_test_command_stderr.txt",
        "result": latest / "result.json",
        "exception": latest / "exception.txt",
    }

    if not show:
        console.print("\n[bold]Available artifacts:[/bold]")
        for k, fp in mapping.items():
            if fp.exists():
                console.print(f"  - {k}: {fp.name}")
        return

    fp = mapping.get(show)
    if not fp or not fp.exists():
        console.print(f"[dim]Artifact not found: {show}[/dim]")
        return

    if fp.suffix in (".json",):
        try:
            data = json.loads(fp.read_text())
            console.print_json(json.dumps(data, indent=2))
        except Exception:
            console.print(fp.read_text())
        return

    # text
    text = fp.read_text(errors="replace")
    lines = text.splitlines()
    if tail and len(lines) > tail:
        lines = lines[-tail:]
    console.print("\n".join(lines))


@work.command("on")
@click.argument("ticket_id")
@click.option("--dry-run", is_flag=True, help="Don't make changes")
@click.option("--no-commit", is_flag=True, help="Don't auto-commit")
@click.option("--no-tests", is_flag=True, help="Skip tests")
@click.option("--auto-fix", is_flag=True, help="Enable auto-fix mode (use LLM to fix errors)")
@click.pass_context
def work_on(ctx, ticket_id: str, dry_run: bool, no_commit: bool, no_tests: bool, auto_fix: bool):
    """Work on a ticket using LLM orchestration."""
    from projektor.core.project import Project
    from projektor.orchestration.orchestrator import Orchestrator

    path = ctx.obj["project_path"]
    cfg = ctx.obj.get("config")

    try:
        project = Project.load(path)

        model = getattr(getattr(cfg, "llm", None), "model", "openrouter/x-ai/grok-3-fast")
        max_iterations = getattr(getattr(cfg, "orchestration", None), "max_iterations", 10)

        if isinstance(model, str) and model.startswith("openrouter/"):
            if not (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")):
                console.print("[red]✗[/red] Missing LLM credentials for OpenRouter model")
                console.print("  Expected: OPENROUTER_API_KEY (recommended) or OPENAI_API_KEY")
                console.print(f"  Project .env path: {path / '.env'}")
                console.print("  Run: projektor doctor")
                api_key = input("Enter your OpenRouter API key (or press Enter to exit): ")
                if api_key.strip():
                    os.environ["OPENROUTER_API_KEY"] = api_key
                    console.print("[green]✓[/green] API key set for this session")
                else:
                    console.print("[red]✗[/red] No API key provided. Exiting.")
                    sys.exit(1)

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

        if auto_fix:
            console.print("[green]AUTO-FIX enabled - will attempt to fix errors automatically[/green]")

        result = run_async(orchestrator.work_on_ticket(ticket_id, context={"auto_fix": auto_fix}))

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


# ==================== Integration Commands ====================


@cli.group()
def integrate():
    """Integration and error handling commands."""
    pass


@integrate.command("init")
@click.option("--auto-fix", is_flag=True, help="Enable auto-fix for errors")
@click.option("--global-handler", is_flag=True, help="Install global exception handler")
@click.option("--format", "-f", "output_format", default="yaml", type=click.Choice(["yaml", "toml"]))
@click.pass_context
def integrate_init(ctx, auto_fix: bool, global_handler: bool, output_format: str):
    """Initialize projektor integration in a project.

    This adds configuration to projektor.yaml or pyproject.toml
    for automatic error tracking and bug ticket creation.
    """
    from projektor.integration.config_loader import IntegrationConfig, save_integration_config

    path = ctx.obj["project_path"]

    config = IntegrationConfig(
        enabled=True,
        global_handler=global_handler,
        auto_fix=auto_fix,
        default_labels=["projektor", "auto-reported"],
    )

    if output_format == "yaml":
        target = path / "projektor.yaml"
    else:
        target = path / "pyproject.toml"

    save_integration_config(config, target, format=output_format)

    console.print(f"[green]✓[/green] Integration initialized in {target}")
    console.print(f"  Auto-fix: {'enabled' if auto_fix else 'disabled'}")
    console.print(f"  Global handler: {'enabled' if global_handler else 'disabled'}")

    console.print("\n[bold]Usage in your code:[/bold]")
    console.print("  from projektor.integration import catch_errors, projektor_guard")
    console.print("")
    console.print("  # As decorator")
    console.print("  @catch_errors(auto_fix=True)")
    console.print("  def my_function():")
    console.print("      ...")
    console.print("")
    console.print("  # As context manager")
    console.print("  with projektor_guard():")
    console.print("      risky_operation()")

    if global_handler:
        console.print("")
        console.print("  # Global handler (add to main.py)")
        console.print("  from projektor.integration import install_global_handler")
        console.print("  install_global_handler()")


@integrate.command("status")
@click.pass_context
def integrate_status(ctx):
    """Show integration status."""
    from projektor.integration.config_loader import load_integration_config

    path = ctx.obj["project_path"]

    config = load_integration_config(path)

    console.print(Panel(
        f"[bold]Integration Status[/bold]\n\n"
        f"Enabled: {'[green]Yes[/green]' if config.enabled else '[red]No[/red]'}\n"
        f"Global handler: {'[green]Yes[/green]' if config.global_handler else '[dim]No[/dim]'}\n"
        f"Auto-fix: {'[green]Yes[/green]' if config.auto_fix else '[dim]No[/dim]'}\n"
        f"Priority: {config.priority}\n"
        f"Labels: {', '.join(config.default_labels) or 'none'}",
        title="Projektor Integration",
    ))

    if config.workflows:
        console.print("\n[bold]Workflows:[/bold]")
        for wf in config.workflows:
            status = "[green]✓[/green]" if wf.enabled else "[dim]✗[/dim]"
            console.print(f"  {status} {wf.name} ({wf.trigger})")


@integrate.command("add-workflow")
@click.argument("name")
@click.option("--trigger", "-t", default="on_error",
              type=click.Choice(["on_error", "on_test_fail", "on_commit", "on_start", "on_success"]))
@click.option("--auto-fix", is_flag=True, help="Enable auto-fix")
@click.option("--label", "-l", "labels", multiple=True, help="Labels to add")
@click.pass_context
def integrate_add_workflow(ctx, name: str, trigger: str, auto_fix: bool, labels: tuple):
    """Add a workflow to integration config."""
    from projektor.integration.config_loader import (
        WorkflowConfig,
        load_integration_config,
        save_integration_config,
    )

    path = ctx.obj["project_path"]

    config = load_integration_config(path)

    workflow = WorkflowConfig(
        name=name,
        trigger=trigger,
        auto_fix=auto_fix,
        labels=list(labels) if labels else [],
    )

    config.workflows.append(workflow)

    target = path / "projektor.yaml"
    save_integration_config(config, target, format="yaml")

    console.print(f"[green]✓[/green] Added workflow '{name}'")
    console.print(f"  Trigger: {trigger}")
    console.print(f"  Auto-fix: {'enabled' if auto_fix else 'disabled'}")


@integrate.command("report-error")
@click.argument("message")
@click.option("--file", "-f", "file_path", help="File where error occurred")
@click.option("--line", "-l", "line_num", type=int, help="Line number")
@click.option("--priority", "-p", default="high",
              type=click.Choice(["critical", "high", "medium", "low"]))
@click.option("--auto-fix", is_flag=True, help="Attempt automatic fix")
@click.pass_context
def integrate_report_error(ctx, message: str, file_path: str | None, line_num: int | None,
                           priority: str, auto_fix: bool):
    """Manually report an error as a bug ticket.

    Example:
        projektor integrate report-error "Database connection fails" -f src/db.py -l 42
    """
    from projektor.core.project import Project
    from projektor.core.ticket import Priority, Ticket, TicketType

    path = ctx.obj["project_path"]

    try:
        project = Project.load(path)
    except Exception:
        from projektor.core.project import Project
        project = Project.init(path)

    existing = project.list_tickets()
    prefix = project.metadata.name[:4].upper() if project.metadata.name else "BUG"
    ticket_id = f"{prefix}-{len(existing) + 1}"

    description = f"## Error Report\n\n**Message:** {message}\n"
    if file_path:
        description += f"\n**File:** `{file_path}`"
        if line_num:
            description += f":{line_num}"
    description += "\n\n**Reported via:** CLI"

    ticket = Ticket(
        id=ticket_id,
        title=f"[Error] {message[:80]}",
        description=description,
        type=TicketType.BUG,
        priority=Priority(priority),
        labels=["error-report", "cli-reported"],
    )

    if file_path:
        ticket.affected_files.append(file_path)

    project.add_ticket(ticket)
    project.save()

    console.print(f"[green]✓[/green] Created bug ticket [cyan]{ticket_id}[/cyan]")
    console.print(f"  Title: {ticket.title}")
    console.print(f"  Priority: {priority}")

    if auto_fix:
        console.print("\n[bold]Starting auto-fix...[/bold]")
        ctx.invoke(work_on, ticket_id=ticket_id, dry_run=False, no_commit=False, no_tests=False)


# ==================== Top-level Commands ====================


@cli.command("init")
@click.argument("name", required=False)
@click.option("--language", "-l", default="python", help="Project language")
@click.pass_context
def init_project(ctx, name: str | None, language: str):
    """Initialize projektor in current directory.

    This is a shortcut for 'projektor project init'.
    """
    from projektor.core.project import Project

    path = ctx.obj["project_path"]
    project_name = name or path.name

    try:
        Project.init(
            path=path,
            name=project_name,
            language=language,
        )

        console.print(f"[green]✓[/green] Projektor initialized in {path}")
        console.print(f"  Project: {project_name}")
        console.print(f"  Config: {path / 'projektor.yaml'}")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Add to your code: from projektor import install; install()")
        console.print("  2. Or use CLI: projektor integrate init --global-handler")

    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@cli.command("watch")
@click.option("--paths", "-p", multiple=True, help="Paths to watch")
@click.pass_context
def watch_files(ctx):
    """Watch files for changes and syntax errors.

    Monitors source files and reports syntax errors immediately.
    """
    from projektor.integration.config_loader import load_integration_config

    path = ctx.obj["project_path"]
    config = load_integration_config(path)

    watch_paths = config.watch_paths or ["src", "tests"]

    console.print(f"[bold]Watching for changes in:[/bold]")
    for wp in watch_paths:
        console.print(f"  - {wp}")

    console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        import time
        from pathlib import Path

        # Simple polling-based watcher (watchdog would be better)
        last_modified = {}

        while True:
            for watch_path in watch_paths:
                full_path = path / watch_path
                if not full_path.exists():
                    continue

                for py_file in full_path.rglob("*.py"):
                    # Skip ignored patterns
                    skip = False
                    for pattern in config.ignore_patterns:
                        if pattern.replace("*", "") in str(py_file):
                            skip = True
                            break
                    if skip:
                        continue

                    try:
                        mtime = py_file.stat().st_mtime
                        if str(py_file) in last_modified:
                            if mtime > last_modified[str(py_file)]:
                                # File changed - check syntax
                                console.print(f"[dim]Changed: {py_file.relative_to(path)}[/dim]")
                                _check_syntax(py_file)
                        last_modified[str(py_file)] = mtime
                    except Exception:
                        pass

            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching[/dim]")


def _check_syntax(file_path):
    """Check Python file syntax."""
    import ast

    try:
        with open(file_path) as f:
            source = f.read()
        ast.parse(source)
    except SyntaxError as e:
        console.print(f"[red]✗ Syntax error:[/red] {file_path}")
        console.print(f"  Line {e.lineno}: {e.msg}")

        # Try to create ticket
        try:
            from projektor.integration.installer import get_handler, is_installed

            if is_installed():
                handler = get_handler()
                if handler:
                    from projektor.integration.error_handler import ErrorReport
                    report = ErrorReport(
                        exception_type="SyntaxError",
                        message=e.msg or "Syntax error",
                        traceback_str=str(e),
                        file_path=str(file_path),
                        line_number=e.lineno,
                    )
                    ticket = handler.create_bug_ticket(report)
                    console.print(f"  [cyan]Ticket created: {ticket.id}[/cyan]")
        except Exception:
            pass


@cli.command("errors")
@click.option("--count", "-n", default=10, help="Number of errors to show")
@click.option("--file", "-f", "log_file", help="Error log file")
@click.pass_context
def show_errors(ctx, count: int, log_file: str | None):
    """Show recent errors from log file."""
    from projektor.integration.config_loader import load_integration_config

    path = ctx.obj["project_path"]
    config = load_integration_config(path)

    error_log = Path(log_file) if log_file else path / config.report_file

    if not error_log.exists():
        console.print(f"[dim]No error log found at {error_log}[/dim]")
        console.print("[dim]Errors will appear here after they occur.[/dim]")
        return

    try:
        with open(error_log) as f:
            content = f.read()

        # Split by separator
        errors = content.split("=" * 60)
        errors = [e.strip() for e in errors if e.strip()]

        if not errors:
            console.print("[green]No errors recorded[/green]")
            return

        console.print(f"[bold]Last {min(count, len(errors))} errors:[/bold]\n")

        for error in errors[-count:]:
            # Extract first few lines
            lines = error.split("\n")[:5]
            for line in lines:
                if "ERROR" in line or "Error" in line:
                    console.print(f"[red]{line}[/red]")
                elif "Time:" in line or "Location:" in line:
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(line)
            console.print()

    except Exception as e:
        console.print(f"[red]✗[/red] Error reading log: {e}")


@cli.command("live")
@click.option("--refresh", "-r", default=2, help="Refresh interval in seconds")
@click.pass_context
def live_monitor(ctx, refresh: int):
    """Live monitoring of projektor activity (interactive mode).

    Run this in one terminal while working in another.
    Shows real-time status of tickets, errors, and activity.
    """
    from projektor.integration.config_loader import load_integration_config

    path = ctx.obj["project_path"]

    console.print("[bold]🎬 Projektor Live Monitor[/bold]")
    console.print(f"[dim]Project: {path}[/dim]")
    console.print(f"[dim]Refresh: every {refresh}s | Press Ctrl+C to stop[/dim]\n")

    try:
        import time

        while True:
            # Clear screen (ANSI escape)
            console.print("\033[2J\033[H", end="")

            console.print("[bold]🎬 Projektor Live Monitor[/bold]")
            console.print(f"[dim]{path.name} | {time.strftime('%H:%M:%S')}[/dim]\n")

            # Load config
            config = load_integration_config(path)

            # Status
            console.print("[bold]📊 Status[/bold]")
            console.print(f"  Enabled: {'[green]●[/green]' if config.enabled else '[red]●[/red]'}")
            console.print(f"  Global handler: {'[green]●[/green]' if config.global_handler else '[dim]○[/dim]'}")
            console.print(f"  Auto-fix: {'[green]●[/green]' if config.auto_fix else '[dim]○[/dim]'}")

            # Tickets
            projektor_dir = path / ".projektor"
            tickets_dir = projektor_dir / "tickets"

            if tickets_dir.exists():
                tickets = list(tickets_dir.glob("*.json"))
                console.print(f"\n[bold]🎫 Tickets ({len(tickets)})[/bold]")

                import json
                for ticket_file in sorted(tickets)[-5:]:  # Last 5
                    try:
                        with open(ticket_file) as f:
                            t = json.load(f)
                        status_icon = {
                            "backlog": "⬜",
                            "todo": "📋",
                            "in_progress": "🔄",
                            "done": "✅",
                        }.get(t.get("status", "backlog"), "⬜")
                        console.print(f"  {status_icon} [{t.get('id', '?')}] {t.get('title', 'No title')[:50]}")
                    except Exception:
                        pass

            # Recent errors
            error_log = path / config.report_file
            if error_log.exists():
                try:
                    content = error_log.read_text()
                    error_count = content.count("ERROR CAPTURED")
                    console.print(f"\n[bold]🔴 Errors: {error_count}[/bold]")

                    # Last error
                    if "ERROR CAPTURED" in content:
                        last_error = content.split("ERROR CAPTURED")[-1].split("\n")[0]
                        console.print(f"  Last: {last_error[:60]}...")
                except Exception:
                    pass

            # Workflows
            if config.workflows:
                console.print(f"\n[bold]⚡ Workflows ({len(config.workflows)})[/bold]")
                for wf in config.workflows[:3]:
                    icon = "✓" if wf.enabled else "○"
                    console.print(f"  [{icon}] {wf.name} → {wf.trigger}")

            console.print(f"\n[dim]─── Watching {', '.join(config.watch_paths[:3])} ───[/dim]")

            time.sleep(refresh)

    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped[/dim]")


@cli.command("status")
@click.pass_context
def show_status(ctx):
    """Show projektor status for current project."""
    from projektor.integration.config_loader import load_integration_config

    path = ctx.obj["project_path"]

    # Check if projektor.yaml exists
    config_file = path / "projektor.yaml"
    pyproject_file = path / "pyproject.toml"

    console.print("[bold]Projektor Status[/bold]\n")

    if config_file.exists():
        console.print(f"[green]✓[/green] Config: {config_file}")
    elif pyproject_file.exists():
        console.print(f"[green]✓[/green] Config: {pyproject_file} [tool.projektor]")
    else:
        console.print("[yellow]![/yellow] No projektor config found")
        console.print("  Run: projektor init")
        return

    # Load and show config
    config = load_integration_config(path)

    console.print(f"\n[bold]Integration:[/bold]")
    console.print(f"  Enabled: {'[green]Yes[/green]' if config.enabled else '[red]No[/red]'}")
    console.print(f"  Global handler: {'[green]Yes[/green]' if config.global_handler else '[dim]No[/dim]'}")
    console.print(f"  Auto-fix: {'[green]Yes[/green]' if config.auto_fix else '[dim]No[/dim]'}")

    if config.workflows:
        console.print(f"\n[bold]Workflows:[/bold]")
        for wf in config.workflows:
            status = "[green]✓[/green]" if wf.enabled else "[dim]✗[/dim]"
            console.print(f"  {status} {wf.name} ({wf.trigger})")

    # Check .projektor directory
    projektor_dir = path / ".projektor"
    if projektor_dir.exists():
        tickets_dir = projektor_dir / "tickets"
        if tickets_dir.exists():
            ticket_count = len(list(tickets_dir.glob("*.json")))
            console.print(f"\n[bold]Tickets:[/bold] {ticket_count}")

        error_log = path / config.report_file
        if error_log.exists():
            size = error_log.stat().st_size
            console.print(f"[bold]Error log:[/bold] {size} bytes")


def main():
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
