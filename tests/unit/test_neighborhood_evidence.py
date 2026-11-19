import json
from datetime import UTC, datetime, timedelta

import pytest

from engineering_memory.access import neighborhood_evidence as evidence
from engineering_memory.normalization import (
    Conversation,
    Message,
    ProjectTag,
    Role,
    Source,
    ToolActivity,
)
from engineering_memory.normalization.enrichment import enrich

NOW = datetime(2026, 1, 2, tzinfo=UTC)
OID = "0123456789abcdef0123456789abcdef01234567"
REMOTE = "https://github.com/example/demo.git"
PATCH = """*** Begin Patch
*** Update File: src/Visible.py
@@
-old
+new
*** Update File: src/Unconfirmed.py
@@
-old
+new
*** End Patch"""


def archive(*messages, source=Source.CODEX, repo=REMOTE, cwd="/work/demo", project="demo"):
    item = Conversation(
        source=source,
        source_id="current",
        started_at=NOW,
        messages=messages,
        working_directory=cwd,
        repository=repo,
    )
    return enrich(
        item, ProjectTag(value=project), importer_version="test", imported_at=NOW, repository=repo
    )


def call(name, call_id, args, source=Source.CODEX, *, recorded_cwd="/work/demo"):
    if source == Source.CLAUDE_CODE:
        data = {"id": call_id, "input": args}
    elif name == "apply_patch":
        data = {"call_id": call_id, "input": args}
    else:
        data = {"call_id": call_id, "arguments": args}
    if recorded_cwd is not None:
        data["recorded_cwd"] = recorded_cwd
    return Message(
        role=Role.ASSISTANT,
        text="",
        tool_activity=(ToolActivity(name=name, request=json.dumps(data)),),
    )


def result(name, call_id, output, source=Source.CODEX, *, failed=False):
    if source == Source.CLAUDE_CODE:
        data = {"tool_use_id": call_id, "is_error": failed, "content": output}
    else:
        data = {"call_id": call_id, "output": output}
    return Message(
        role=Role.TOOL,
        text="",
        sent_at=NOW,
        tool_activity=(ToolActivity(name=name, result=json.dumps(data)),),
    )


def checkout_root(root="/work/demo", *, cwd="/work/demo"):
    return (
        call("exec_command", "scope", {"cmd": "git rev-parse --show-toplevel"}, recorded_cwd=cwd),
        result("exec_command", "scope", {"exit_code": 0, "stdout": f"{root}\n"}),
    )


def test_codex_edit_is_a_confirmed_patch_path_in_verified_checkout():
    item = archive(
        *checkout_root(),
        call("apply_patch", "edit", PATCH),
        result("apply_patch", "edit", "Success. Updated the following files:\nM src/Visible.py"),
    )
    (edge,) = evidence.project_evidence(item)
    assert (edge.relation, edge.target.identity, edge.target.repository) == (
        "file_edit",
        "src/Visible.py",
        REMOTE,
    )
    assert (edge.message, edge.tool, edge.field) == (3, 0, "tool_result")


def test_legacy_relative_patch_without_operation_cwd_is_ambiguous():
    edit = call("apply_patch", "edit", PATCH, recorded_cwd=None)
    item = archive(
        *checkout_root(),
        edit,
        result("apply_patch", "edit", "Success. Updated the following files:\nM src/Visible.py"),
    )
    assert list(evidence.project_evidence(item)) == []


def test_codex_relative_edits_are_resolved_from_subdirectory():
    cwd = "/work/demo/package"
    item = archive(
        *checkout_root(cwd=cwd),
        call("apply_patch", "edit", PATCH, recorded_cwd=cwd),
        result("apply_patch", "edit", "Success. Updated the following files:\nM src/Visible.py"),
        cwd=cwd,
    )
    (edge,) = evidence.project_evidence(item)
    assert edge.target.identity == "package/src/Visible.py"


@pytest.mark.parametrize("case", ["unverified-root", "mismatched-id", "failed", "duplicates"])
def test_uncorroborated_patch_is_omitted(case):
    messages = list(checkout_root()) if case != "unverified-root" else []
    messages.append(call("apply_patch", "edit", PATCH))
    output = "Success. Updated the following files:\nM src/Visible.py"
    messages.append(
        result(
            "apply_patch",
            "foreign" if case == "mismatched-id" else "edit",
            {"exit_code": 1, "stdout": output} if case == "failed" else output,
        )
    )
    if case == "duplicates":
        messages.append(result("apply_patch", "edit", "Failed to apply patch"))
    assert list(evidence.project_evidence(archive(*messages))) == []


def test_claude_successful_absolute_path_edit():
    source = Source.CLAUDE_CODE
    edited = r"D:\demo\src\Main.py"
    item = archive(
        call("Edit", "edit", {"file_path": edited}, source, recorded_cwd=None),
        result("Edit", "edit", f"The file {edited} has been updated.", source),
        source=source,
        cwd=r"D:\demo",
        repo=r"D:\demo",
    )
    (edge,) = evidence.project_evidence(item)
    assert edge.target.identity == "src/Main.py"


@pytest.mark.parametrize(
    "path", ["../app.py", "/app.py", "d:/app.py", "a//b", "a/[REDACTED]", "a\r"]
)
def test_invalid_file_selector_does_not_alias_a_file(path):
    assert evidence.normalize_file_path(path) is None


def test_linux_literal_backslash_does_not_alias_a_folder():
    assert evidence.normalize_file_path(r"src\Main.py") is None


def test_commit_requires_direct_call_and_successful_verified_identity():
    stated_commit = Message(role=Role.ASSISTANT, text=f"Committed {OID}.")
    item = archive(
        stated_commit,
        *checkout_root(),
        call("exec_command", "commit", {"cmd": "git commit -m 'Add cache'"}),
        result("exec_command", "commit", {"exit_code": 0, "stdout": f"[main {OID}] Add cache"}),
    )
    (edge,) = evidence.project_evidence(item)
    assert (edge.relation, edge.target.identity, edge.field) == ("commit", OID, "tool_result")


def test_abbreviation_expands_from_same_scope_only():
    item = archive(
        *checkout_root(),
        call("exec_command", "commit", {"cmd": "git commit -m 'Add cache'"}),
        result("exec_command", "commit", {"exit_code": 0, "stdout": f"[main {OID[:8]}] Add cache"}),
        call("exec_command", "head", {"cmd": "git rev-parse HEAD"}),
        result("exec_command", "head", {"exit_code": 0, "stdout": OID}),
    )
    (edge,) = evidence.project_evidence(item)
    assert edge.target.identity == OID


@pytest.mark.parametrize(
    "command",
    [
        "echo git commit -m fake",
        "git -C /work/other commit",
        "git commit --dry-run",
        "git commit && echo done",
    ],
)
def test_unverified_command_does_not_report_a_commit(command):
    item = archive(
        *checkout_root(),
        call("exec_command", "commit", {"cmd": command}),
        result("exec_command", "commit", {"exit_code": 0, "stdout": f"[main {OID}] Add cache"}),
    )
    assert list(evidence.project_evidence(item)) == []


def test_refs_use_exact_message_and_ignore_bare_or_assistant_continuations():
    item = archive(
        Message(role=Role.ASSISTANT, text="Continue from codex:wrong"),
        Message(role=Role.USER, text="In codex:mentioned it was discussed."),
        Message(role=Role.USER, text="Continue from codex:previous."),
        Message(
            role=Role.ASSISTANT,
            text="See #3, [the PR](https://GitHub.com/example/demo/pull/73?tab=files#diff).",
        ),
    )
    edges = evidence.project_evidence(item)
    assert [(edge.relation, edge.target.identity, edge.message) for edge in edges] == [
        ("continuation", "codex:previous", 2),
        ("pr_reference", "https://github.com/example/demo/pull/73", 3),
    ]


def test_no_project_if_scope_conflicts_or_is_unknown():
    item = archive()
    assert evidence.project_of(item) == "demo"
    assert evidence.project_of(archive(project="unknown")) is None
    assert evidence.project_of(archive(project="unclassified")) is None
    assert evidence.project_of(item.model_copy(update={"tags": ()})) is None


def test_snapshot_commits_to_context_and_original_message_time():
    message = Message(role=Role.USER, text="Continue from codex:previous", sent_at=NOW)
    snapshot = evidence.snapshot_of(archive(message))
    assert len(snapshot) == 64 and int(snapshot, 16)
    assert snapshot == evidence.snapshot_of(archive(message))
    assert snapshot != evidence.snapshot_of(archive(message, cwd="/work/other"))
    assert snapshot != evidence.snapshot_of(archive(message, project="other"))
    later = message.model_copy(update={"sent_at": NOW + timedelta(seconds=1)})
    assert snapshot != evidence.snapshot_of(archive(later))


def test_conflicting_checkout_roots_do_not_establish_repository_scope():
    item = archive(
        *checkout_root("/work"),
        call("exec_command", "commit", {"cmd": "git commit -m 'Add cache'"}),
        result("exec_command", "commit", {"exit_code": 0, "stdout": f"[main {OID}] Add cache"}),
        repo="/work/demo",
    )
    assert list(evidence.project_evidence(item)) == []


def test_codex_patch_accepts_native_windows_line_endings():
    item = archive(
        call("apply_patch", "edit", PATCH.replace("\n", "\r\n"), recorded_cwd=r"D:\demo"),
        result(
            "apply_patch",
            "edit",
            "Success. Updated the following files:\r\nM src/Visible.py",
        ),
        repo=r"D:\demo",
        cwd=r"D:\demo",
    )
    (edge,) = evidence.project_evidence(item)
    assert edge.target.identity == "src/Visible.py"


def test_windows_alternate_path_spelling_does_not_create_a_second_identity():
    source = Source.CLAUDE_CODE
    path = r"D:\demo\src\Main.py."
    item = archive(
        call("Edit", "edit", {"file_path": path}, source, recorded_cwd=r"D:\demo"),
        result("Edit", "edit", f"The file {path} has been updated.", source),
        repo=r"D:\demo",
        cwd=r"D:\demo",
        source=source,
    )
    assert list(evidence.project_evidence(item)) == []


def test_commit_for_remote_needs_recorded_checkout_scope():
    item = archive(
        call("exec_command", "commit", {"cmd": "git commit -m 'Other repository'"}),
        result("exec_command", "commit", {"exit_code": 0, "stdout": f"[main {OID}] External"}),
    )
    assert list(evidence.project_evidence(item)) == []


def test_codex_mixed_turn_cwd_does_not_attribute_an_edit_to_the_initial_checkout():
    from engineering_memory.ingestion.codex.parser import parse_session

    timestamp = NOW.isoformat()
    events = [
        {
            "type": "session_meta",
            "payload": {
                "id": "mixed",
                "timestamp": timestamp,
                "cwd": "/work/demo",
                "git": {"repository_url": REMOTE},
            },
        }
    ]

    def turn(cwd):
        events.append({"type": "turn_context", "payload": {"cwd": cwd}})

    def emit(kind, **payload):
        events.append(
            {
                "timestamp": timestamp,
                "type": "response_item",
                "payload": {"type": kind, **payload},
            }
        )

    turn("/work/demo")
    emit(
        "function_call",
        name="exec_command",
        call_id="root",
        arguments=json.dumps({"cmd": "git rev-parse --show-toplevel"}),
    )
    emit(
        "function_call_output",
        call_id="root",
        output=json.dumps({"exit_code": 0, "stdout": "/work/demo\n"}),
    )

    for cwd, identifier in [("/work/another", "outside"), ("/work/demo", "inside")]:
        turn(cwd)
        emit("custom_tool_call", name="apply_patch", call_id=identifier, input=PATCH)
        emit(
            "custom_tool_call_output",
            call_id=identifier,
            output="Success. Updated the following files:\nM src/Visible.py",
        )

    conversation = parse_session("\n".join(json.dumps(event) for event in events).encode())
    item = enrich(
        conversation,
        ProjectTag(value="demo"),
        importer_version="test",
        imported_at=NOW,
        repository=REMOTE,
    )

    [edge] = evidence.project_evidence(item)
    assert edge.message == 5
    assert edge.target.identity == "src/Visible.py"


def test_claude_cwd_only_import_can_use_confirmed_checkout_scope():
    from engineering_memory.ingestion.claude_code.parser import parse_session
    from tests.synthetic.claude_code import encode, record

    edits = [
        record(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "root",
                    "name": "Bash",
                    "input": {"command": "git rev-parse --show-toplevel"},
                }
            ],
        ),
        record(
            content=[{"type": "tool_result", "tool_use_id": "root", "content": "/work/orchard\n"}]
        ),
        record(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "outside",
                    "name": "Edit",
                    "input": {"file_path": "src/foreign.py"},
                }
            ],
        ),
        record(
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "outside",
                    "content": "The file src/foreign.py has been updated.",
                }
            ]
        ),
        record(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "edit",
                    "name": "Edit",
                    "input": {"file_path": "/work/orchard/src/Visible.py"},
                }
            ],
        ),
        record(
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "edit",
                    "content": "The file /work/orchard/src/Visible.py has been updated.",
                }
            ]
        ),
    ]
    for index, entry in enumerate(edits):
        entry["uuid"] = f"item-{index}"
    edits[2]["cwd"] = "/work/another"
    conversation = parse_session(encode(edits))
    assert conversation is not None and conversation.repository is None
    item = enrich(conversation, ProjectTag(value="demo"), importer_version="test", imported_at=NOW)

    [edge] = evidence.project_evidence(item)
    assert edge.target.identity == "src/Visible.py"
    assert edge.target.repository == "/work/orchard"
