"""Exercise real archive evidence through the local browser and SQLite index."""

import json
from datetime import UTC, datetime
from time import perf_counter
from unittest.mock import Mock

from engineering_memory.access.neighborhood_index import NeighborhoodIndex
from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.ingestion.codex.parser import parse_session
from engineering_memory.normalization import ProjectTag
from engineering_memory.normalization.enrichment import enrich
from tests.integration.test_explorer_browser import explorer as explorer

REPOSITORY = "https://github.com/example/orchard.git"
FILE = "src/app.py"
WHEN = "2026-01-01T00:00:00Z"
OID = "0123456789abcdef0123456789abcdef01234567"
PATCH = f"*** Begin Patch\n*** Update File: {FILE}\n@@\n-old\n+new\n*** End Patch"
EDIT_RESULT = f"Success. Updated the following files:\nM {FILE}"
PR = "https://github.com/example/orchard/pull/7"


def _native(document, *, project="orchard", evidence=False, edit=False):
    events = [
        {
            "type": "session_meta",
            "payload": {
                "id": document,
                "timestamp": WHEN,
                "cwd": "/work/orchard",
                "git": {"repository_url": REPOSITORY},
            },
        }
    ]

    def add(kind, **fields):
        events.append(
            {"type": "response_item", "timestamp": WHEN, "payload": {"type": kind, **fields}}
        )

    if edit or evidence:
        add(
            "function_call",
            call_id="root",
            name="exec_command",
            arguments=json.dumps({"cmd": "git rev-parse --show-toplevel"}),
        )
        add(
            "function_call_output",
            call_id="root",
            output=json.dumps({"exit_code": 0, "stdout": "/work/orchard\n"}),
        )
        add("custom_tool_call", name="apply_patch", call_id="edit", input=PATCH)
        add("custom_tool_call_output", call_id="edit", output=EDIT_RESULT)
    if evidence:
        add(
            "function_call",
            call_id="commit",
            name="exec_command",
            arguments=json.dumps({"cmd": "git commit -m 'Improve app'"}),
        )
        add(
            "function_call_output",
            call_id="commit",
            output=json.dumps({"exit_code": 0, "stdout": f"[main {OID}] Improve app"}),
        )
        add(
            "message",
            role="user",
            content=[{"type": "input_text", "text": "Continue from codex:prior"}],
        )
        add("message", role="assistant", content=[{"type": "output_text", "text": f"Review {PR}"}])

    raw = "\n".join(json.dumps(event) for event in events).encode()
    item = enrich(
        parse_session(raw),
        ProjectTag(value=project),
        importer_version="test",
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        repository=REPOSITORY,
    )
    return item, OriginalPayload(content=raw, media_type="application/jsonl")


def _connect(access, index, archive):
    reads = MemoryAccess(Mock(), archive, neighborhood_index=index)
    for name in (
        "get_conversation",
        "get_neighborhood_conversation",
        "neighborhood",
        "neighborhood_evidence",
    ):
        getattr(access, name).side_effect = getattr(reads, name)


def test_browser_follows_all_four_recorded_relations(explorer, tmp_path):
    from playwright.sync_api import expect

    page, access = explorer
    archive = LocalRawArchive(tmp_path / "archive")
    for item, original in (
        _native("current", evidence=True),
        _native("prior"),
        _native("foreign", project="elsewhere", edit=True),
    ):
        archive.store(item, original)
    index = NeighborhoodIndex(tmp_path / "index.sqlite3")
    index.rebuild(archive)
    _connect(access, index, archive)
    origin = page.url.split("#", 1)[0]
    source = "#view=session&project=orchard&document=codex%3Acurrent&message=0"

    for label, expected, message, field in [
        ("recorded file edit", FILE, 3, "tool_result"),
        ("recorded commit", OID, 5, "tool_result"),
        ("explicit continuation", "Continue from codex:prior", 6, "text"),
        ("PR reference", PR, 7, "text"),
    ]:
        page.goto(origin + source)
        page.get_by_role("button", name="Open session neighborhood").click()
        panel = page.get_by_role("region", name="Evidence neighborhood")
        panel.get_by_role("button", name=f"Inspect {label}").press("Enter")
        expect(panel.locator("#neighborhood-detail pre")).to_contain_text(expected)
        link = panel.get_by_role("link", name="Open supporting field")
        assert f"message={message}" in link.get_attribute("href")
        link.click()
        target = page.locator(".cited:focus")
        expect(target).to_be_visible()
        if field == "tool_result":
            expect(target).to_have_attribute("data-field", field)
        expect(panel).to_be_hidden()

    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Browse a file").click()
    page.get_by_label("Repository identity").fill(REPOSITORY)
    page.get_by_label("Project-relative file path").fill(FILE)
    page.get_by_role("button", name="Open file neighborhood").click()
    expect(page.get_by_role("button", name="Browse codex:current")).to_be_visible()
    expect(page.get_by_role("button", name="Browse codex:foreign")).to_have_count(0)


def test_browser_opens_a_bounded_neighborhood_on_a_large_index(explorer, tmp_path, record_property):
    from playwright.sync_api import expect

    page, access = explorer
    idle, _ = _native("idle")
    edited, _ = _native("edit", edit=True)

    class SyntheticArchive:
        def iter_document_ids(self):
            return (f"codex:s-{ordinal:05d}" for ordinal in range(50_000))

        def load(self, document_id):
            _, source_id = document_id.split(":", 1)
            template = edited if int(source_id[2:]) < 2_500 else idle
            return template.model_copy(
                update={
                    "conversation": template.conversation.model_copy(
                        update={"source_id": source_id}
                    ),
                    "provenance": template.provenance.model_copy(update={"source_id": source_id}),
                }
            )

    archive = SyntheticArchive()
    index = NeighborhoodIndex(tmp_path / "index.sqlite3")
    assert index.rebuild(archive)["indexed"] == 50_000
    _connect(access, index, archive)
    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Browse a file").click()
    page.get_by_label("Repository identity").fill(REPOSITORY)
    page.get_by_label("Project-relative file path").fill(FILE)
    open_file = page.get_by_role("button", name="Open file neighborhood")
    neighbors = page.get_by_role("list", name="Direct connections").get_by_role("listitem")

    start = perf_counter()
    open_file.press("Enter")
    expect(neighbors).to_have_count(30, timeout=2_000)
    elapsed = perf_counter() - start
    record_property("busy_neighborhood_seconds", elapsed)
    print(f"Busy browser neighborhood: {elapsed:.3f} seconds")
    assert elapsed < 2
    expect(page.get_by_text("Showing a limited set", exact=False)).to_be_visible()
    selection = neighbors.all_text_contents()
    open_file.press("Enter")
    expect(neighbors).to_have_count(30)
    assert neighbors.all_text_contents() == selection


def test_evidence_link_accepts_encoded_native_unicode_identity(explorer, tmp_path):
    from playwright.sync_api import expect

    page, access = explorer
    archive = LocalRawArchive(tmp_path / "archive")
    item, original = _native("ж" * 800, edit=True)
    archive.store(item, original)
    index = NeighborhoodIndex(tmp_path / "index.sqlite3")
    index.rebuild(archive)
    _connect(access, index, archive)

    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Browse a file").click()
    page.get_by_label("Repository identity").fill(REPOSITORY)
    page.get_by_label("Project-relative file path").fill(FILE)
    page.get_by_role("button", name="Open file neighborhood").click()
    panel = page.get_by_role("region", name="Evidence neighborhood")
    panel.get_by_role("button", name="Inspect recorded file edit").click()
    link = panel.get_by_role("link", name="Open supporting field")
    assert 4096 < len(link.get_attribute("href")) < 13000
    link.click()
    expect(page.locator('[data-field="tool_result"].cited')).to_be_focused(timeout=2000)
