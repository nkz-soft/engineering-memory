"""Operator commands exercise the normal Typer entry point."""

import json

from typer.testing import CliRunner

from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.cli import app
from tests.contracts import conversations as fixture


def test_stage_review_and_approve(tmp_path, monkeypatch):
    root = tmp_path / "archive"
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(root))
    record = fixture.enrich(fixture.conversation_using_every_field(), project="orchard")
    LocalRawArchive(root).store(
        record, OriginalPayload(content=b"original", media_type="text/plain")
    )
    source = tmp_path / "draft.json"
    source.write_text(
        json.dumps(
            {
                "title": "Release",
                "steps": ["First\nAnother line", "Second"],
                "examples": [record.document_id],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    scope = ["--project", "orchard", "--id", "release"]
    staged = runner.invoke(app, ["playbooks", "stage", *scope, "--file", str(source)])
    assert staged.exit_code == 0, staged.output
    revision = staged.output.strip()
    review = runner.invoke(app, ["playbooks", "review", *scope])
    assert review.exit_code == 0, review.output
    assert revision in review.output
    assert "1. First\n   Another line\n2. Second" in review.output
    assert review.output.index("1. First") < review.output.index("2. Second")
    assert record.document_id in review.output
    approved = runner.invoke(app, ["playbooks", "approve", *scope, "--revision", revision])
    assert approved.exit_code == 0, approved.output
    assert approved.output.strip() == "1"
