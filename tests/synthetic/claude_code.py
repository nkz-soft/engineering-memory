"""Invented coding history: never reads private Claude Code files."""

import json


def record(role="user", content="Investigate the synthetic relay failure", **extra):
    return dict(
        type=role,
        sessionId="session-one",
        uuid="turn-one",
        timestamp="2026-03-04T09:30:00Z",
        cwd="/work/orchard",
        message={"role": role, "content": content},
        **extra,
    )


def debugging(session="session-one"):
    blocks = [
        record(content="Why does the relay fail?"),
        record(
            "assistant",
            [
                {"type": "text", "text": "Investigating the command"},
                {
                    "type": "tool_use",
                    "id": "call-1",
                    "name": "Bash",
                    "input": {"command": "relay --check"},
                },
                {
                    "type": "tool_use",
                    "id": "call-2",
                    "name": "Read",
                    "input": {"file_path": "relay.conf"},
                },
            ],
        ),
        record(
            content=[
                {"type": "tool_result", "tool_use_id": "call-2", "content": "port=0"},
                {
                    "type": "tool_result",
                    "tool_use_id": "call-1",
                    "is_error": True,
                    "content": (
                        "Cobalt relay fails because port zero is disabled. "
                        "password=" + "synthetic-secret-123"
                    ),
                },
            ]
        ),
        record(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "call-3",
                    "name": "Edit",
                    "input": {"old_string": "port=0", "new_string": "port=8123"},
                },
                {"type": "text", "text": "Fixed the configuration; retry succeeds."},
            ],
        ),
    ]
    for index, value in enumerate(blocks):
        value.update(sessionId=session, uuid=f"turn-{index}")
    return blocks


def encode(records):
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n").encode()


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(records))
    return path
