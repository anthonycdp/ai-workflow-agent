"""
Command-line interface for the AI Workflow Agent.

This CLI provides commands for:
- Running workflows
- Managing workflows
- Viewing execution history
- Handling approvals
"""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.syntax import Syntax

from workflow_agent.agent import WorkflowAgent
from workflow_agent.config import AgentConfig
from workflow_agent.tools import (
    EmailTool,
    ReportGeneratorTool,
    DataProcessingTool,
    NotificationTool,
)
from workflow_agent.workflows import WorkflowOrchestrator
from workflow_agent.workflows.templates import (
    get_template,
    list_templates,
    WORKFLOW_TEMPLATES,
)
from workflow_agent.models import ApprovalDecision, WorkflowStatus

app = typer.Typer(
    name="workflow-agent",
    help="AI Agent for Workflow Automation with Human-in-the-Loop Supervision",
)
console = Console()


def create_agent(config: Optional[AgentConfig] = None) -> WorkflowAgent:
    """Create and configure the workflow agent."""
    config = config or AgentConfig()
    agent = WorkflowAgent(config=config)

    # Register tools
    agent.register_tool(EmailTool())
    agent.register_tool(ReportGeneratorTool())
    agent.register_tool(DataProcessingTool())
    agent.register_tool(NotificationTool())

    return agent


def create_orchestrator(config: Optional[AgentConfig] = None) -> WorkflowOrchestrator:
    """Create and configure the workflow orchestrator."""
    agent = create_agent(config)
    orchestrator = WorkflowOrchestrator(agent=agent, config=config)

    # Register template workflows
    for template_name in WORKFLOW_TEMPLATES:
        workflow = get_template(template_name)
        if workflow:
            orchestrator.register_workflow(workflow)

    return orchestrator


@app.command()
def run(
    workflow: str = typer.Argument(..., help="Name of the workflow to run"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        "-i/-n",
        help="Interactive mode",
    ),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Config file path"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results"),
):
    """
    Run a workflow.

    Example:
        workflow-agent run email_triage
        workflow-agent run report_generation --non-interactive
    """
    config = AgentConfig()
    if not interactive:
        config.auto_approve_safe_actions = True

    orchestrator = create_orchestrator(config)

    # Check if workflow exists
    if not orchestrator.get_workflow(workflow):
        console.print(f"[red]Error:[/red] Workflow '{workflow}' not found")
        console.print("\nAvailable workflows:")
        for wf in orchestrator.list_workflows():
            console.print(f"  - {wf.id}")
        raise typer.Exit(1)

    # Run the workflow
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Running {workflow}...", total=None)

        result = asyncio.run(orchestrator.execute(workflow))

    # Display results
    display_result(result)

    # Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        console.print(f"\nResults saved to {output}")


@app.command()
def chat():
    """
    Start an interactive chat session with the agent.

    Use this for ad-hoc tasks and conversations with the agent.
    """
    console.print(
        Panel.fit(
            "[bold blue]AI Workflow Agent Chat[/bold blue]\n"
            "Type your requests and the agent will help automate your workflows.\n"
            "Type 'quit' or 'exit' to end the session.",
            title="Welcome",
        )
    )

    agent = create_agent()

    console.print("\n[bold]Agent ready![/bold] What would you like to do?\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")

            if user_input.lower() in ["quit", "exit", "bye"]:
                console.print("\n[bold blue]Goodbye![/bold blue]")
                break

            if not user_input.strip():
                continue

            # Process with agent
            with console.status("[bold blue]Thinking...[/bold blue]"):
                result = asyncio.run(agent.process(user_input))

            # Display response
            if result.output.get("response"):
                console.print(f"\n[bold yellow]Agent:[/bold yellow] {result.output['response']}")

            if result.errors:
                for error in result.errors:
                    console.print(f"\n[red]Error: {error}[/red]")

            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[bold blue]Goodbye![/bold blue]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


@app.command("list")
def list_workflows():
    """List all available workflows."""
    templates = list_templates()

    table = Table(title="Available Workflows")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")

    for template in templates:
        table.add_row(
            template["id"],
            template["name"],
            template["description"],
        )

    console.print(table)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show"),
):
    """View workflow execution history."""
    orchestrator = create_orchestrator()
    history_records = orchestrator.get_execution_history()[:limit]

    if not history_records:
        console.print("[yellow]No execution history found.[/yellow]")
        return

    table = Table(title="Execution History")
    table.add_column("Workflow ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Steps", justify="right")
    table.add_column("Errors", justify="right")

    for record in history_records:
        status_color = {
            WorkflowStatus.COMPLETED: "green",
            WorkflowStatus.FAILED: "red",
            WorkflowStatus.CANCELLED: "yellow",
            WorkflowStatus.RUNNING: "blue",
        }.get(record.status, "white")

        table.add_row(
            record.workflow_id[:8] + "...",
            f"[{status_color}]{record.status.value}[/{status_color}]",
            f"{record.steps_completed}/{record.steps_total}",
            str(len(record.errors)),
        )

    console.print(table)


@app.command()
def tools():
    """List available tools."""
    table = Table(title="Available Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Sensitive", justify="center")

    tools_list = [
        ("email_tool", "Email triage, drafting, and sending", "Yes (send)"),
        ("report_generator", "Report generation and scheduling", "Yes (schedule)"),
        ("data_processor", "Data transformation and validation", "No"),
        ("notification", "Notifications via various channels", "Yes (sms, webhook)"),
    ]

    for name, desc, sensitive in tools_list:
        table.add_row(name, desc, sensitive)

    console.print(table)


@app.command()
def approve(
    request_id: Optional[str] = typer.Argument(None, help="Approval request ID"),
    action: str = typer.Option("approve", "--action", "-a", help="approve, reject, edit"),
):
    """
    Approve or reject a pending action.

    Use this to review and approve sensitive actions that require
    human oversight.
    """
    agent = create_agent()
    pending = agent.get_pending_approvals()

    if not pending:
        console.print("[yellow]No pending approvals.[/yellow]")
        return

    if request_id:
        # Find specific request
        request = next((r for r in pending if r.request_id == request_id), None)
        if not request:
            console.print(f"[red]Request {request_id} not found.[/red]")
            return
    else:
        # Show list and let user select
        console.print("[bold]Pending Approvals:[/bold]\n")
        for i, req in enumerate(pending):
            console.print(f"  [{i}] {req.tool_name} - {req.action_description}")
            console.print(f"      Risk: {req.risk_level}")

        selection = Prompt.ask("\nSelect request number", default="0")
        try:
            request = pending[int(selection)]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")
            return

    # Show request details
    console.print(
        Panel.fit(
            f"Tool: {request.tool_name}\n"
            f"Action: {request.action_description}\n"
            f"Risk Level: {request.risk_level}\n\n"
            f"Input:\n{json.dumps(request.proposed_input, indent=2)}",
            title="Approval Request",
        )
    )

    # Get decision
    if action == "approve":
        decision = ApprovalDecision.APPROVE
    elif action == "reject":
        decision = ApprovalDecision.REJECT
    else:
        choice = Prompt.ask(
            "Decision",
            choices=["approve", "reject", "edit"],
            default="approve",
        )
        decision = ApprovalDecision(choice)

    # Process approval
    result = asyncio.run(agent.approve_action(request.request_id, decision))

    if result.success:
        console.print(f"\n[green]Action {decision.value}d successfully![/green]")
    else:
        console.print(f"\n[red]Failed: {result.error}[/red]")


@app.command()
def config():
    """Show current configuration."""
    cfg = AgentConfig()

    table = Table(title="Agent Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("LLM Provider", cfg.llm_provider.value)
    table.add_row("Model", cfg.model_name)
    table.add_row("Temperature", str(cfg.temperature))
    table.add_row("Max Tokens", str(cfg.max_tokens))
    table.add_row("Max Retries", str(cfg.max_retries))
    table.add_row("Auto Approve Safe", str(cfg.auto_approve_safe_actions))
    table.add_row("Require Approval", str(cfg.require_approval_for_sensitive))
    table.add_row("Enable Fallback", str(cfg.enable_fallback))
    table.add_row("Log Level", cfg.log_level)

    console.print(table)

    # Show sensitive actions
    console.print("\n[bold]Sensitive Actions (require approval):[/bold]")
    for action in cfg.sensitive_actions:
        console.print(f"  - {action}")


def display_result(result):
    """Display workflow execution result."""
    status_color = {
        WorkflowStatus.COMPLETED: "green",
        WorkflowStatus.FAILED: "red",
        WorkflowStatus.CANCELLED: "yellow",
        WorkflowStatus.RUNNING: "blue",
        WorkflowStatus.WAITING_APPROVAL: "orange3",
    }.get(result.status, "white")

    console.print(
        Panel.fit(
            f"Status: [{status_color}]{result.status.value}[/{status_color}]\n"
            f"Steps: {result.steps_completed}/{result.steps_total}\n"
            f"Approvals: {result.approvals_granted}/{result.approvals_requested}",
            title=f"Workflow Result: {result.workflow_id[:8]}",
        )
    )

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  - {error}")

    if result.output:
        console.print("\n[bold]Output:[/bold]")
        for key, value in result.output.items():
            if isinstance(value, dict) or isinstance(value, list):
                console.print(f"\n  {key}:")
                syntax = Syntax(json.dumps(value, indent=2), "json", theme="monokai")
                console.print(syntax)
            else:
                console.print(f"  {key}: {value}")


if __name__ == "__main__":
    app()
