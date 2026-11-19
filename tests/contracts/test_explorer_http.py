"""The explorer's local transport forwards authorized read operations."""

import asyncio
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from engineering_memory.access.service import AccessError, MemoryAccess

AUTHORITY = "127.0.0.1:8123"
TOKEN = "fixture-launch-token"
HEADERS = {"Origin": f"http://{AUTHORITY}", "Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def explorer():
    from engineering_memory.api.explorer import create_explorer_app

    access = Mock(spec=MemoryAccess)
    with TestClient(
        create_explorer_app(access, token=TOKEN, authority=AUTHORITY),
        base_url=f"http://{AUTHORITY}",
    ) as client:
        yield client, access


@pytest.mark.parametrize(
    ("route", "payload", "method", "arguments", "result"),
    [
        (
            "search",
            {"query": "queue", "project": "orchard"},
            "search_memory",
            {"query": "queue", "tags": ["project:orchard"]},
            {"results": [{"document_id": "codex:one"}]},
        ),
        (
            "deep-recall",
            {"query": "queue", "project": "orchard"},
            "deep_recall",
            {"query": "queue", "project": "orchard"},
            {"status": "partial", "timeline": [], "coverage": {}, "uncertainty": ["limited"]},
        ),
        (
            "conversation",
            {"document_id": "codex:one", "offset": 51, "page_size": 50},
            "get_conversation",
            {"document_id": "codex:one", "offset": 51, "page_size": 50},
            {"document_id": "codex:one", "offset": 51, "messages": [], "next_offset": None},
        ),
    ],
)
def test_forwards_reads_and_preserves_payloads(explorer, route, payload, method, arguments, result):
    client, access = explorer
    read = getattr(access, method)
    read.return_value = result

    response = client.post(f"/api/{route}", json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == result
    assert response.headers["Cache-Control"] == "no-store"
    read.assert_called_once_with(**arguments)


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"Origin": "https://foreign.example"}, 403),
        ({"Origin": "null"}, 403),
        ({"Origin": ""}, 403),
        ({"Host": "foreign.example"}, 403),
        ({"Authorization": ""}, 401),
        ({"Authorization": "Bearer previous-launch"}, 401),
        ({"Authorization": "Bearer é"}, 401),
        ({"Content-Type": "text/plain"}, 400),
    ],
)
def test_rejects_untrusted_requests_before_dispatch(explorer, headers, status):
    client, access = explorer
    headers = [
        (name.encode(), value.encode("latin1")) for name, value in (HEADERS | headers).items()
    ]

    response = client.post("/api/search", json={"query": "private"}, headers=headers)

    assert response.status_code == status
    assert "private" not in response.text
    assert "access-control-allow-origin" not in response.headers
    assert not access.mock_calls


def test_rejects_missing_origin_and_duplicate_header(explorer):
    client, access = explorer
    assert (
        client.post(
            "/api/search", json={}, headers={"Authorization": HEADERS["Authorization"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/search",
            json={},
            headers=[*HEADERS.items(), ("Origin", "https://foreign.example")],
        ).status_code
        == 403
    )
    assert not access.mock_calls


@pytest.mark.parametrize("body", [b"{", b"[]", b'{"project":3}', b"x" * 17000])
def test_rejects_invalid_payload_without_echoing_it(explorer, body):
    client, access = explorer
    response = client.post(
        "/api/search", content=body, headers=HEADERS | {"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_input"}
    assert not access.mock_calls


@pytest.mark.parametrize(
    ("error", "code", "status"),
    [
        (AccessError("invalid_input"), "invalid_input", 400),
        (AccessError("not_found"), "not_found", 404),
        (AccessError("unavailable"), "unavailable", 503),
        (AccessError("corrupt_record"), "corrupt_record", 500),
        (AccessError("private diagnostic"), "internal", 500),
        (RuntimeError("private diagnostic"), "internal", 500),
    ],
)
def test_errors_are_fixed_and_safe(explorer, error, code, status):
    client, access = explorer
    access.deep_recall.side_effect = error

    response = client.post(
        "/api/deep-recall", json={"query": "queue", "project": "orchard"}, headers=HEADERS
    )

    assert response.status_code == status
    assert response.json() == {"error": code}


def test_serves_public_shell_and_assets_without_exposing_other_routes(explorer):
    client, access = explorer
    shell = client.get("/")
    assert shell.status_code == 200
    assert TOKEN not in shell.text
    assert "frame-ancestors 'none'" in shell.headers["Content-Security-Policy"]
    assert client.get("/assets/explorer.js").status_code == 200
    assert client.get("/assets/explorer.css").status_code == 200
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/", headers={"Host": "foreign.example"}).status_code == 403
    assert client.get("/api/search").status_code == 405
    assert not access.mock_calls


def test_decision_history_mode(explorer):
    client, access = explorer
    result = {"status": "completed", "events": [], "conflicts": []}
    access.decision_history.return_value = result
    payload = {"project": "orchard", "query": "queue", "mode": "decision_history"}
    response = client.post("/api/deep-recall", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == result
    access.decision_history.assert_called_once_with(project="orchard", query="queue")
    access.deep_recall.assert_not_called()


@pytest.mark.parametrize(
    "headers,status",
    [
        ({"Origin": "https://wrong.example"}, 403),
        ({"Host": "wrong.example"}, 403),
        ({"Authorization": "Bearer wrong"}, 401),
    ],
)
def test_decision_history_requires_local_auth(explorer, headers, status):
    client, access = explorer
    response = client.post(
        "/api/deep-recall",
        json={"project": "orchard", "query": "queue", "mode": "decision_history"},
        headers=HEADERS | headers,
    )
    assert response.status_code == status
    assert not access.mock_calls


@pytest.mark.parametrize("mode", ["wrong", None, 1])
def test_rejects_invalid_decision_mode(explorer, mode):
    client, access = explorer
    response = client.post(
        "/api/deep-recall",
        json={"project": "orchard", "query": "queue", "mode": mode},
        headers=HEADERS,
    )
    assert response.json() == {"error": "invalid_input"}
    assert not access.mock_calls


@pytest.mark.parametrize(
    ("payload", "headers", "code"),
    [
        ({"project": "orchard"}, {}, 200),
        ({}, {}, 200),
        ({"project": "unknown"}, {}, 400),
        ({"project": "includes space"}, {}, 400),
        ({"project": 3}, {}, 400),
        ({"token": "PRIVATE_INPUT"}, {}, 400),
        ({}, {"Origin": "https://foreign.example"}, 403),
        ({}, {"Host": "foreign.example"}, 403),
        ({}, {"Authorization": "Bearer wrong"}, 401),
    ],
)
def test_status_read_is_protected_and_scoped(payload, headers, code):
    from engineering_memory.api.explorer import create_explorer_app

    result = {"source_status": "available", "sources": [], "models": []}
    read_status = Mock(return_value=result)
    app = create_explorer_app(
        Mock(spec=MemoryAccess),
        token=TOKEN,
        authority=AUTHORITY,
        read_status=read_status,
    )

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=f"http://{AUTHORITY}",
        ) as client:
            return await client.post("/api/status", json=payload, headers=HEADERS | headers)

    response = asyncio.run(request())
    assert response.status_code == code
    assert response.headers["Cache-Control"] == "no-store"
    assert "PRIVATE_INPUT" not in response.text
    if code == 200:
        read_status.assert_called_once_with(project=payload.get("project"))
        assert response.json() == result
    else:
        read_status.assert_not_called()


def test_handoff_uses_authenticated_scope_and_fixed_explorer_origin(explorer):
    client, access = explorer
    payload = {"document_id": "codex:one", "project": "orchard"}
    read = getattr(access, "session_handoff", Mock())
    read.return_value = {"markdown": "# Session handoff"}
    assert client.post("/api/session-handoff", json=payload).status_code == 403
    assert (
        client.post(
            "/api/session-handoff", json=payload | {"link_origin": "http://evil"}, headers=HEADERS
        ).status_code
        == 400
    )
    response = client.post("/api/session-handoff", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == read.return_value
    assert response.headers["Cache-Control"] == "no-store"
    read.assert_called_once_with(**payload, link_origin=f"http://{AUTHORITY}")
