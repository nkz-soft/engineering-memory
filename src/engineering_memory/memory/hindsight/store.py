"""Synchronous memory boundary backed by bounded asynchronous engine extraction."""

import asyncio
import hashlib
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from uuid import uuid4

import httpx

from engineering_memory.memory.hindsight.retry import (
    RetryPolicy,
    TransientFailure,
    transient_transport,
)
from engineering_memory.memory.hindsight.serialization import decode_result, item_for
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.normalization import AnyTag, EnrichedConversation
from engineering_memory.settings import HindsightSettings


class HindsightStore:
    """One writer per instance; pending identities survive uncertain in-process retries.

    An injected client belongs to the caller. Otherwise use close() or a context
    manager. Cross-process retry coordination belongs to the import orchestrator.
    """

    def __init__(
        self,
        settings: HindsightSettings,
        *,
        client: httpx.Client | None = None,
        request_timeout: float = 30,
        completion_timeout: float = 240,
        poll_interval: float = 0.25,
        max_request_bytes: int = 8 * 1024 * 1024,
        retry_policy: RetryPolicy | None = None,
    ):
        if any(not math.isfinite(v) or v <= 0 for v in (request_timeout, completion_timeout)):
            raise ValueError("timeouts must be positive and finite")
        if not math.isfinite(poll_interval) or poll_interval < 0:
            raise ValueError("poll interval must be finite and nonnegative")
        if type(max_request_bytes) is not int or max_request_bytes <= 0:
            raise ValueError("request size must be positive")
        url = httpx.URL(str(settings.base_url))
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("engine URL must not contain credentials, query or fragment")
        self._base = str(url).rstrip("/")
        self._root = "/v1/default/banks/" + quote(settings.bank_id, safe="")
        self._headers = {}
        if settings.token is not None:
            self._headers["Authorization"] = "Bearer " + settings.token.get_secret_value()
        self._owned = client is None
        self._client = client
        self._executor = ThreadPoolExecutor(max_workers=1) if self._owned else None
        self._timeout = request_timeout
        self._completion = completion_timeout
        self._interval = poll_interval
        self._max_bytes = max_request_bytes
        self._pending: dict[str, tuple[str, str]] = {}
        self._lock = threading.Lock()
        self._retry = retry_policy or RetryPolicy()
        self._request_ordinal = 0
        self._bank = settings.bank_id

    def close(self):
        if self._owned:
            self._executor.shutdown(wait=True, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def _async_request(self, method, path, deadline, content):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        async with asyncio.timeout(remaining):
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                return await client.request(
                    method,
                    self._base + path,
                    content=content,
                    headers={**self._headers, "Content-Type": "application/json"},
                    timeout=min(self._timeout, remaining),
                )

    def _request(
        self,
        method,
        path,
        deadline,
        *,
        content=None,
        reject_identity=None,
        operation_id=None,
        document_id=None,
    ):
        self._request_ordinal += 1
        kind = "poll" if method == "GET" else "recall" if path.endswith("/recall") else "retain"

        def request_once():
            nonlocal reject_identity
            try:
                return self._single_request(
                    method, path, deadline, content=content, reject_identity=reject_identity
                )
            except TransientFailure:
                # Acceptance may have happened before the response was lost. A
                # later refusal cannot resolve that earlier uncertainty.
                reject_identity = None
                raise

        return self._retry.run(
            request_once,
            deadline,
            operation=kind,
            request_ordinal=self._request_ordinal,
            bank=self._bank,
            operation_id=operation_id,
            document_id=document_id,
        )

    def _single_request(self, method, path, deadline, *, content=None, reject_identity=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise MemoryStoreUnavailable("memory operation unavailable: deadline exceeded")
        try:
            if self._owned:
                future = self._executor.submit(
                    lambda: asyncio.run(self._async_request(method, path, deadline, content))
                )
                try:
                    response = future.result(timeout=remaining)
                except TimeoutError:
                    future.cancel()
                    raise
            else:
                response = self._client.request(
                    method,
                    self._base + path,
                    content=content,
                    headers={**self._headers, "Content-Type": "application/json"},
                    timeout=min(self._timeout, remaining),
                    follow_redirects=False,
                )
        except (httpx.TransportError, TimeoutError) as error:
            category = transient_transport(error)
            if category is not None and time.monotonic() < deadline:
                raise TransientFailure(category) from None
            raise MemoryStoreUnavailable("memory operation unavailable") from None
        if time.monotonic() >= deadline:
            raise MemoryStoreUnavailable("memory operation unavailable: deadline exceeded")
        if response.status_code in {429, 502, 503, 504}:
            raise TransientFailure("http_status", response.status_code)
        if not response.is_success:
            if reject_identity is not None:
                self._pending.pop(reject_identity, None)
            raise MemoryStoreRejected("memory operation rejected")
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, UnicodeError):
            raise MemoryStoreRejected("invalid memory response") from None

    @staticmethod
    def _encode(body):
        return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def retain(self, enriched: EnrichedConversation) -> None:
        item = item_for(enriched)
        fingerprint = hashlib.sha256(self._encode(item)).hexdigest()
        identity = enriched.document_id
        with self._lock:
            previous = self._pending.get(identity)
            replaying = bool(previous and previous[0] == fingerprint)
            operation = previous[1] if replaying else str(uuid4())
            body = self._encode({"items": [item], "async": True, "operation_id": operation})
            if len(body) > self._max_bytes:
                raise MemoryStoreRejected("conversation exceeds request size limit")
            if identity not in self._pending and len(self._pending) >= 128:
                raise MemoryStoreUnavailable("too many uncertain memory operations")
            self._pending[identity] = (fingerprint, operation)
            deadline = time.monotonic() + self._completion
            result = self._request(
                "POST",
                self._root + "/memories",
                deadline,
                content=body,
                reject_identity=None if replaying else identity,
                operation_id=operation,
                document_id=identity,
            )
            if (
                result.get("success") is not True
                or result.get("async") is not True
                or result.get("operation_id") != operation
                or result.get("operation_ids") not in (None, [operation])
            ):
                raise MemoryStoreRejected("invalid retain acknowledgement")
            while True:
                result = self._request(
                    "GET",
                    self._root + "/operations/" + operation,
                    deadline,
                    operation_id=operation,
                    document_id=identity,
                )
                status = result.get("status")
                if not isinstance(status, str):
                    raise MemoryStoreRejected("invalid operation response")
                if status == "completed":
                    del self._pending[identity]
                    return
                if status in {"failed", "cancelled"}:
                    del self._pending[identity]
                    raise MemoryStoreRejected("memory extraction failed")
                if status == "not_found":
                    raise MemoryStoreUnavailable("memory operation unavailable")
                if status not in {"pending", "processing"}:
                    raise MemoryStoreRejected("invalid operation response")
                time.sleep(min(self._interval, max(0, deadline - time.monotonic())))

    def recall(self, query: str, tags: tuple[AnyTag, ...] = (), limit: int | None = None):
        if not isinstance(query, str) or not query.strip():
            raise MemoryStoreRejected("query must not be empty")
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise MemoryStoreRejected("limit must be a positive integer")
        tag_values = [str(tag) for tag in tags]
        body = self._encode(
            {
                "query": query,
                "tags": tag_values,
                "tags_match": "all_strict",
                "types": ["world", "experience"],
                "budget": "mid",
                "max_tokens": 4096,
            }
        )
        result = self._request(
            "POST", self._root + "/memories/recall", time.monotonic() + self._timeout, content=body
        )
        facts = result.get("results")
        if not isinstance(facts, list):
            raise MemoryStoreRejected("invalid recall response")
        decoded = tuple(decode_result(fact, tag_values) for fact in facts)
        return decoded if limit is None else decoded[:limit]
