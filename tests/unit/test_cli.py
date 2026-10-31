"""CLI usage and the operator commands specified by feature 020."""

from typer.testing import CliRunner

from engineering_memory.cli import app


def test_help_exits_zero_and_names_the_application():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "engineering-memory" in result.output.lower().replace("_", "-")


def test_only_specified_command_is_registered():
    for command in ("provision", "import", "status"):
        result = CliRunner().invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
