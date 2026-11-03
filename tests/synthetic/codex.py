"""Invented Codex rollout records; no private sessions are accessed."""

from tests.synthetic.claude_code import encode, write  # noqa: F401

TIME = "2026-03-04T09:30:00Z"


def record(kind, **payload):
    return {"timestamp": TIME, "type": kind, "payload": payload}


def message(role="user", text="Why does the relay fail?"):
    return record(
        "response_item",
        type="message",
        role=role,
        content=[{"type": "input_text" if role == "user" else "output_text", "text": text}],
    )


def debugging(session="session-one"):
    return [
        record("session_meta", id=session, timestamp=TIME, cwd="/work/orchard"),
        message(),
        record("event_msg", type="user_message", message="Why does the relay fail?"),
        record(
            "response_item",
            type="function_call",
            call_id="call-1",
            name="exec_command",
            arguments='{"cmd":"relay --check"}',
        ),
        record(
            "response_item",
            type="function_call_output",
            call_id="call-1",
            output="Cobalt relay fails because port zero is disabled. password="
            + "synthetic-secret-123",
        ),
        record(
            "response_item",
            type="custom_tool_call",
            call_id="call-2",
            name="apply_patch",
            input="new_string: port=8123",
        ),
        message("assistant", "Fixed the configuration; retry succeeds."),
    ]
