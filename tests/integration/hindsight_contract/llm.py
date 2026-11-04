"""Credential-free extraction dependency; never implements engine operations."""

import contextlib
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def extraction(body):
    """Accept only the pinned fact-extraction protocol and synthetic marker."""
    try:
        schema = body["response_format"]["json_schema"]["schema"]
        assert "facts" in schema["properties"]
        messages = body["messages"]
        assert len(messages) == 2 and messages[1]["role"] == "user"
        text = messages[1]["content"]
        # Adapter requests embed the conversation as JSON; raw contract requests
        # carry a plain line. Accept only the same bounded synthetic fact in either.
        matches = re.findall(
            r'Synthetic contract fact: (Orchard [A-Za-z0-9 .,\-]+)(?=\\*["\n]|$)', text
        )
        assert len(matches) == 1
        fact = matches[0].strip()
        assert re.fullmatch(r"Orchard [A-Za-z0-9 .,\-]+", fact)
    except (KeyError, TypeError, AssertionError):
        raise ValueError("unsupported extraction request") from None
    return {
        "facts": [
            {
                "what": fact,
                "when": "N/A",
                "where": "N/A",
                "who": "N/A",
                "why": "N/A",
                "fact_kind": "conversation",
                "fact_type": "world",
                "occurred_start": None,
                "occurred_end": None,
                "entities": [],
                "causal_relations": [],
                "from_attachments": [],
            }
        ]
    }


def completion(body):
    """Pinned reflect tool protocol over synthetic tool-returned facts only.

    This is deterministic protocol evidence, never real synthesis-quality acceptance.
    """
    if not body.get("tools"):
        return {"role": "assistant", "content": json.dumps(extraction(body))}
    if "FORCE_FIXTURE_FAILURE" in json.dumps(body["messages"]):
        raise ValueError("deliberately failed synthetic synthesis")
    names = {tool["function"]["name"] for tool in body["tools"]}
    choice = body.get("tool_choice")
    forced = choice.get("function", {}).get("name") if isinstance(choice, dict) else None
    facts = {}

    def collect(value):
        if isinstance(value, dict):
            if (
                isinstance(value.get("id"), str)
                and isinstance(value.get("text"), str)
                and value["text"].startswith("Orchard ")
            ):
                facts[value["id"]] = value["text"]
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    for message in body["messages"]:
        if message.get("role") == "tool":
            with contextlib.suppress(ValueError, TypeError):
                collect(json.loads(message["content"]))
    name = forced or (
        "answer_ready"
        if facts and "answer_ready" in names
        else "done"
        if facts and "done" in names
        else "recall"
    )
    if name == "done":
        arguments = {
            "document": {
                "sections": [
                    {
                        "heading": "Project summary",
                        "level": 2,
                        "blocks": list(facts.values()) or ["Insufficient evidence."],
                    }
                ]
            },
            "answer_found": bool(facts),
            "memory_ids": list(facts),
            "observation_ids": [],
            "mental_model_ids": [],
        }
    elif name == "answer_ready":
        arguments = {"answer_found": bool(facts)}
    else:
        arguments = {
            "reason": "synthetic protocol validation",
            "query": "Orchard",
            "max_tokens": 4096,
        }
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "fixture-call",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }
        ],
    }


class FixtureServer(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, Handler)
        self.lock = threading.Lock()
        self.calls = 0
        self.errors = 0
        self.release = threading.Event()
        self.release.set()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No prompts, headers or bodies in CI logs.

    def respond(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/stats":
            return self.respond(404, {})
        with self.server.lock:
            self.respond(200, {"calls": self.server.calls, "errors": self.server.errors})

    def do_POST(self):
        if self.path in {"/hold", "/release"}:
            if self.path == "/hold":
                self.server.release.clear()
            else:
                self.server.release.set()
            return self.respond(200, {})
        try:
            if self.path != "/v1/chat/completions":
                raise ValueError("unsupported route")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 100_000:
                raise ValueError("unsupported size")
            result = completion(json.loads(self.rfile.read(size)))
            with self.server.lock:
                self.server.calls += 1
            if not self.server.release.wait(60):
                raise ValueError("barrier timeout")
        except (ValueError, TypeError):
            with self.server.lock:
                self.server.errors += 1
            return self.respond(400, {"error": {"message": "unsupported fixture request"}})
        self.respond(
            200,
            {
                "id": "synthetic-extraction",
                "object": "chat.completion",
                "created": 0,
                "model": "contract",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls" if result.get("tool_calls") else "stop",
                        "message": result,
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )


if __name__ == "__main__":
    FixtureServer(("0.0.0.0", 8080)).serve_forever()
