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


def desktop_rollout():
    user = message(text="Which cable specification did we choose?")
    assistant = message("assistant", "We chose a shielded cable rated for 60 volts.")
    assistant["timestamp"] = "2026-03-04T09:31:00Z"
    return [
        record("session_meta", id="desktop-fixture", timestamp=TIME, cwd="/work/relay"),
        record("response_item", type="additional_tools", role="developer", tools=[]),
        record("world_state", context="fixture-world-state"),
        record("event_msg", type="thread_settings_applied", thread_settings={}),
        user,
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "UserMessage",
                "id": "user-event",
                "content": [{"type": "text", "text": user["payload"]["content"][0]["text"]}],
            },
        ),
        record(
            "response_item",
            type="custom_tool_call",
            call_id="call-1",
            name="exec",
            input="inspect-cable",
        ),
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "CommandExecution",
                "id": "command-event",
                "source": "unified_exec_startup",
                "command": ["inspect-cable"],
                "aggregated_output": "fixture-ui-result",
            },
        ),
        record(
            "response_item",
            type="custom_tool_call_output",
            call_id="call-1",
            output=[{"type": "input_text", "text": "60 volts. password=fixture-test-secret"}],
        ),
        record("token_usage_record", usage={"total_tokens": 100}),
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "AgentMessage",
                "id": "agent-event",
                "content": [{"type": "Text", "text": assistant["payload"]["content"][0]["text"]}],
            },
        ),
        assistant,
    ]
