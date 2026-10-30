"""CLI usage and the command specified by feature 016."""

from typer.testing import CliRunner

from engineering_memory.cli import app


def test_help_exits_zero_and_names_the_application():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "engineering-memory" in result.output.lower().replace("_", "-")


def test_only_specified_command_is_registered():
    assert [command.name for command in app.registered_commands] == ["provision"]
