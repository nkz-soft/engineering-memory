"""Credential-free extraction dependency; never implements engine operations."""

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
        matches = re.findall(r"Synthetic contract fact: ([^\n]+)", text)
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
            result = extraction(json.loads(self.rfile.read(size)))
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
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(result)},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )


if __name__ == "__main__":
    FixtureServer(("0.0.0.0", 8080)).serve_forever()
