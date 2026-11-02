"""Synthetic Claude plain-chat dialect; no private history."""

import json

TIME = "2020-01-02T00:00:00+00:00"


def record(identity="one", text="Synthetic cobalt relay decision"):
    return {
        "uuid": identity,
        "name": "Synthetic decision",
        "created_at": TIME,
        "updated_at": TIME,
        "chat_messages": [{"sender": "human", "text": text, "created_at": TIME}],
    }


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path


def from_conversation(conversation):
    value = record(conversation.source_id)
    value.update(
        name=conversation.title,
        created_at=conversation.started_at.isoformat(),
        updated_at=conversation.last_activity_at.isoformat()
        if conversation.last_activity_at
        else None,
    )
    value["chat_messages"] = [
        {
            "sender": "human" if m.role.value == "user" else "assistant",
            "text": m.text,
            "created_at": m.sent_at.isoformat() if m.sent_at else None,
        }
        for m in conversation.messages
    ]
    return value
