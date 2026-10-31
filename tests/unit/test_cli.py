"""CLI usage and the operator commands specified by feature 020."""

import pytest
from rich.text import Text
from typer import rich_utils
from typer.testing import CliRunner

from engineering_memory.cli import app


def test_help_exits_zero_and_names_the_application():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "engineering-memory" in result.output.lower().replace("_", "-")


@pytest.mark.parametrize("force_terminal", [False, True])
def test_operator_command_help_lists_json_option(monkeypatch, force_terminal):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(rich_utils, "FORCE_TERMINAL", force_terminal)
    for command in ("provision", "import", "status"):
        result = CliRunner().invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--json" in Text.from_ansi(result.output).plain
