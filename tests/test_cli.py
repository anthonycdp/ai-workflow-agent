"""
Tests for the command-line interface.
"""

from typer.testing import CliRunner

from workflow_agent.cli import app

runner = CliRunner()


def test_cli_help_loads():
    """CLI help should render without crashing."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "AI Agent for Workflow Automation" in result.stdout


def test_cli_list_workflows():
    """Listing workflows should succeed."""
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Available Workflows" in result.stdout
    assert "email_triage" in result.stdout
