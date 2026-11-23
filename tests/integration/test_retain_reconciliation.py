"""Synthetic manual and automatic import recovery through the CLI composition."""

import json
import os
import subprocess
import sys
from uuid import uuid4

import httpx
import pytest
from typer.testing import CliRunner

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.cli import app, runtime
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStateUnavailable
from engineering_memory.memory.hindsight.retry import RetryPolicy
from engineering_memory.memory.hindsight.store import HindsightStore
from tests.integration.test_chatgpt_acquisition_cli import write_export
from tests.integration.test_live_hindsight_contract import wait_until
from tests.synthetic import chatgpt_export, codex


@pytest.fixture
def session(monkeypatch, tmp_path):
    from engineering_memory import settings

    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "rollout-synthetic.jsonl"
    original = codex.encode(codex.debugging())
    path.write_bytes(original)
    os.utime(path, (1, 1))
    archive = tmp_path / "archive"
    monkeypatch.setattr(settings, "DEFAULT_ENV_FILE", None)
    for key, value in {
        "ARCHIVE_ROOT": archive,
        "IMPORT_STATE_PATH": tmp_path / "state.db",
        "HINDSIGHT__BASE_URL": "http://engine.invalid",
        "HINDSIGHT__BANK_ID": "synthetic-reconciliation",
        "LLM__BASE_URL": "http://proxy.invalid",
        "SESSION_IMPORT__CODEX_ROOT": root,
    }.items():
        monkeypatch.setenv("ENGINEERING_MEMORY_" + key, str(value))
    return path, original, archive


def invoke(args):
    result = CliRunner().invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


def engine(monkeypatch, handler, *, attempts=1):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        runtime,
        "make_memory",
        lambda settings: HindsightStore(
            settings,
            client=client,
            completion_timeout=0.1,
            poll_interval=0.01,
            retry_policy=RetryPolicy(max_attempts=attempts, initial=0.001, maximum=0.001, jitter=0),
        ),
    )
    return client


@pytest.mark.parametrize("automatic", [False, True], ids=["manual", "automatic"])
@pytest.mark.parametrize(
    "submission", ["accepted", "lost", "malformed", "offline", "rejected", "failed"]
)
def test_retain_reconciliation(monkeypatch, session, automatic, submission):
    path, original, archive = session
    raw_archive = LocalRawArchive(archive)
    submit_ids = []
    checks = []
    archived_at_submit = []
    sent = []
    operation_status = "pending"
    child_status = "processing"
    child = str(uuid4())

    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            operation = body["operation_id"]
            submit_ids.append(operation)
            sent.append(request.content)
            archived_at_submit.append(
                raw_archive.load_original(body["items"][0]["document_id"]).content == original
            )
            if submission == "offline":
                raise httpx.ConnectError("synthetic connection refused", request=request)
            if submission == "lost":
                raise httpx.ReadTimeout("synthetic response loss", request=request)
            if submission == "malformed":
                return httpx.Response(200, json={})
            if submission == "rejected":
                return httpx.Response(422)
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": operation}
            )
        operation = request.url.path.rsplit("/", 1)[-1]
        checks.append(operation)
        assert operation == submit_ids[0]
        return httpx.Response(
            200,
            json={
                "operation_id": operation,
                "status": "failed" if submission == "failed" else operation_status,
                "child_operations": [{"operation_id": child, "status": child_status}],
            },
        )

    args = (
        ["import-sessions"] if automatic else ["import", "--source", "codex", "--export", str(path)]
    )
    with engine(monkeypatch, handler):
        code, data = invoke(args)
        row = data["sources"][0] if automatic else data
        assert len(sent) == 1
        assert b"synthetic-secret-123" not in sent[0]
        assert archived_at_submit == [True]
        if submission in {"offline", "rejected", "failed"}:
            assert code == 1 and row["failed"] == 1
            assert invoke(["status"])[1]["records"][0]["status"] == "failed"
            assert len(submit_ids) == 1
            return
        expected = "pending" if submission == "accepted" else "uncertain"
        assert code == 1 and row.get(expected) == 1 and row["failed"] == 0, json.dumps(data)
        _, status = invoke(["status"])
        assert status["records"][0]["status"] == expected
        assert submit_ids[0] not in json.dumps(status)

        if submission == "accepted":
            # The backend can finish its child while aggregate status still says pending.
            path.unlink()
            child_status = "completed"
            if not automatic:
                args = ["import", "--source", "codex", "--from-archive", "--force"]
        else:
            operation_status = "not_found"
            code, data = invoke(args)
            row = data["sources"][0] if automatic else data
            assert code == 1 and row["uncertain"] == 1 and row["failed"] == 0
            assert len(submit_ids) == 1
            operation_status = "completed"
        code, data = invoke(args)
        row = data["sources"][0] if automatic else data
        assert code == 0 and row["imported"] == 1 and row["failed"] == 0
        assert len(submit_ids) == 1
        assert checks
        assert raw_archive.load_original("codex:session-one").content == original
        if not path.exists():
            path.write_bytes(original)
            os.utime(path, (1, 1))
        args = (
            ["import-sessions"]
            if automatic
            else ["import", "--source", "codex", "--export", str(path)]
        )
        code, data = invoke(args)
        row = data["sources"][0] if automatic else data
        assert code == 0 and row["unchanged" if automatic else "skipped"] == 1
        assert len(submit_ids) == 1


@pytest.mark.parametrize("later_response", [200, 422])
def test_submission_retries_reuse_the_payload(monkeypatch, session, later_response):
    path, _, _ = session
    posts = []

    def handler(request):
        if request.method == "POST":
            posts.append(request.content)
            if len(posts) == 1:
                return httpx.Response(503)
            return httpx.Response(
                later_response,
                json={
                    "success": True,
                    "async": True,
                    "operation_id": json.loads(posts[0])["operation_id"],
                },
            )
        return httpx.Response(
            200, json={"operation_id": json.loads(posts[0])["operation_id"], "status": "completed"}
        )

    with engine(monkeypatch, handler, attempts=2):
        code, result = invoke(["import", "--source", "codex", "--export", str(path)])
    assert len(posts) == 2 and posts[0] == posts[1]
    if later_response == 200:
        assert code == 0 and result["imported"] == 1
    else:
        assert code == 1 and result["uncertain"] == 1 and result["failed"] == 0


@pytest.mark.parametrize("unrelated", [False, True])
def test_acquisition_after_an_earlier_retain(monkeypatch, session, unrelated):
    path, _, _ = session
    older, newer = path.with_suffix(".zip"), path.with_name("updated.zip")
    write_export(older)
    write_export(
        newer,
        records=[
            chatgpt_export.linear_record(
                "different" if unrelated else "a", chatgpt_export.message("user", "changed text")
            )
        ],
    )
    posts = []
    operation_status = "processing"

    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            posts.append(body)
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": body["operation_id"]}
            )
        operation = request.url.path.rsplit("/", 1)[-1]
        status = operation_status if operation == posts[0]["operation_id"] else "completed"
        return httpx.Response(200, json={"operation_id": operation, "status": status})

    with engine(monkeypatch, handler):
        code, result = invoke(["import", "--export", str(older)])
        assert code == 1 and result["pending"] == 1
        if not unrelated:
            operation_status = "completed"
        code, result = invoke(["acquire-chatgpt", "--file", str(newer)])
        assert code == 0 and result["outcome"] == "imported"
        assert len(posts) == 2
        assert posts[0]["operation_id"] != posts[1]["operation_id"]
        assert "changed text" in posts[1]["items"][0]["content"]


def test_terminal_result_survives_failed_local_commit(monkeypatch, session):
    path, _, _ = session
    posts = []

    def handler(request):
        if request.method == "POST":
            operation = json.loads(request.content)["operation_id"]
            posts.append(operation)
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": operation}
            )
        return httpx.Response(200, json={"operation_id": posts[0], "status": "completed"})

    confirm = SQLiteImportState._confirm_import

    def fail_after_writes(self, *args):
        confirm(self, *args)
        raise ImportStateUnavailable("synthetic transaction failure")

    args = ["import", "--source", "codex", "--export", str(path)]
    with engine(monkeypatch, handler):
        with monkeypatch.context() as patch:
            patch.setattr(SQLiteImportState, "_confirm_import", fail_after_writes)
            code, result = invoke(args)
            assert code == 1 and result["outcomes"][0]["error"] == "state_write"
        assert invoke(["status"])[1]["records"][0]["status"] == "pending"

        # An endpoint or bank change must not resolve a receipt against a different target.
        with monkeypatch.context() as patch:
            patch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", "other-bank")
            code, result = invoke(args)
            assert code == 1 and result["pending"] == 1

        code, result = invoke(args)
        assert code == 0 and result["imported"] == 1
        assert len(posts) == 1


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)
def test_slow_live_retain_reconciles_in_a_new_cli_process(tmp_path):
    import anyio
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters

    bank = "synthetic-reconciliation-" + uuid4().hex
    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    fixture_url = os.environ.get("CONTRACT_FIXTURE_URL", "http://127.0.0.1:8890")
    root = f"/v1/default/banks/{bank}"
    sessions = tmp_path / "sessions"
    archive = tmp_path / "archive"
    fact = "Orchard uses the cobalt relay for recovery."
    document = "codex:synthetic-slow"
    path = codex.write(
        sessions / "rollout-synthetic.jsonl",
        [
            codex.record("session_meta", id="synthetic-slow", timestamp=codex.TIME),
            codex.message(text="Synthetic contract fact: " + fact),
        ],
    )
    os.utime(path, (1, 1))
    original = path.read_bytes()
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("ENGINEERING_MEMORY_")
    }
    env.update(
        ENGINEERING_MEMORY_ARCHIVE_ROOT=str(archive),
        ENGINEERING_MEMORY_IMPORT_STATE_PATH=str(tmp_path / "state.db"),
        ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=url,
        ENGINEERING_MEMORY_HINDSIGHT__BANK_ID=bank,
        ENGINEERING_MEMORY_LLM__BASE_URL="http://unused.invalid",
        ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT=str(sessions),
        ENGINEERING_MEMORY_PROJECT_RULES_PATH=str(tmp_path / "projects.toml"),
    )
    (tmp_path / "projects.toml").write_text("projects = []\n", encoding="utf-8")

    bootstrap = """
from engineering_memory import settings
from engineering_memory.cli import main, runtime
from engineering_memory.memory.hindsight.store import HindsightStore
settings.DEFAULT_ENV_FILE = None
runtime.make_memory = lambda config: HindsightStore(config, completion_timeout=3)
main()
"""

    def child_cli(*args, expected=0):
        run = subprocess.run(
            [sys.executable, "-c", bootstrap, *args, "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp_path,
            timeout=45,
        )
        assert run.returncode == expected, run.stdout
        return json.loads(run.stdout)

    with (
        httpx.Client(base_url=url, trust_env=False, timeout=30) as engine,
        httpx.Client(base_url=fixture_url, trust_env=False, timeout=30) as llm,
    ):

        def operations():
            response = engine.get(root + "/operations")
            response.raise_for_status()
            return response.json()["operations"]

        def calls():
            return llm.get("/stats").raise_for_status().json()["calls"]

        try:
            before = calls()
            llm.post("/hold").raise_for_status()
            result = child_cli("import", "--source", "codex", "--export", str(path), expected=1)
            assert (result["status"], result["pending"], result["failed"]) == ("pending", 1, 0)
            assert child_cli("status")["records"][0]["status"] == "pending"
            wait_until(lambda: calls() > before, seconds=25)
            submitted = operations()
            assert any(row["status"] == "processing" for row in submitted)
            assert LocalRawArchive(archive).load_original(document).content == original
            path.unlink()

            llm.post("/release").raise_for_status()
            wait_until(
                lambda: all(row["status"] == "completed" for row in operations()), seconds=35
            )
            result = child_cli("import-sessions")
            assert result["sources"][0]["imported"] == 1
            assert child_cli("status")["records"][0]["status"] == "imported"
            assert {row["id"] for row in operations()} == {row["id"] for row in submitted}
            assert calls() == before + 1

            async def check_memory():
                parameters = StdioServerParameters(
                    command=sys.executable, args=["-c", bootstrap, "serve"], env=env, cwd=tmp_path
                )
                with anyio.fail_after(45):
                    async with Client(parameters, mode="legacy") as client:
                        search = await client.call_tool(
                            "search_memory",
                            {"query": "Orchard cobalt relay", "tags": ["source:codex"]},
                        )
                        assert not search.is_error
                        assert any(
                            row["document_id"] == document and fact in row["content"]
                            for row in search.structured_content["results"]
                        )
                        page = await client.call_tool("get_conversation", {"document_id": document})
                        assert not page.is_error
                        assert fact in page.structured_content["messages"][0]["text"]

            anyio.run(check_memory)
        finally:
            llm.post("/release").raise_for_status()
            assert engine.delete(root).status_code in {200, 204, 404}
