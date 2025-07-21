"""Tests for the CLI module."""

import pytest
from click.testing import CliRunner

from tsm.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


def test_cli_help(runner):
    """Test that the CLI shows help."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "TSM" in result.output
    assert "Traefik Service Manager" in result.output


def test_cli_version(runner):
    """Test the version command."""
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "TSM Version Information" in result.output


def test_cli_steps(runner):
    """Test the steps command."""
    result = runner.invoke(cli, ["steps"])
    assert result.exit_code == 0
    assert "Path to deploy a project" in result.output


def test_cli_discover_without_file(runner):
    """Test discover command without a file."""
    result = runner.invoke(cli, ["discover"])
    # Should fail because no docker-compose.yml exists
    assert result.exit_code != 0


def test_cli_generate_without_file(runner):
    """Test generate command without a file."""
    result = runner.invoke(cli, ["generate"])
    # Should fail because no docker-compose.yml exists
    assert result.exit_code != 0
