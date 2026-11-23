"""Synchronous memory boundary backed by bounded asynchronous engine extraction."""

import asyncio
import hashlib
import json
import math
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx

from engineering_memory.memory.hindsight.retry import (
    RetryPolicy,
    TransientFailure,
    transient_transport,
)
from engineering_memory.memory.hindsight.serialization import (
    decode_reflection,
    decode_result,
    item_for,
)
from engineering_memory.memory.interface import (
    MemoryStoreRejected,
    MemoryStoreUnavailable,
    ReflectionResult,
    RetainProgress,
)
from engineering_memory.normalization import AnyTag, EnrichedConversation
from engineering_memory.settings import HindsightSettings


class _RetainNotSent(MemoryStoreUnavailable):
    """The transport failed before it could send the submission."""


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
        self._receipt_scope = hashlib.sha256((self._base + self._root).encode()).hexdigest()

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
        tracked_submission=False,
    ):
        self._request_ordinal += 1
        kind = "poll" if method == "GET" else path.rsplit("/", 1)[-1]
        if kind == "memories":
            kind = "retain"

        possibly_sent = False

        def request_once():
            nonlocal reject_identity, possibly_sent
            try:
                return self._single_request(
                    method,
                    path,
                    deadline,
                    content=content,
                    reject_identity=reject_identity,
                    tracked_submission=tracked_submission,
                )
            except _RetainNotSent:
                raise TransientFailure("connection_unavailable") from None
            except (TransientFailure, MemoryStoreUnavailable):
                # A later refusal cannot resolve an earlier ambiguous response.
                possibly_sent = True
                reject_identity = None
                raise
            except MemoryStoreRejected:
                if tracked_submission and possibly_sent:
                    raise MemoryStoreUnavailable("retain submission status is unknown") from None
                raise

        try:
            return self._retry.run(
                request_once,
                deadline,
                operation=kind,
                request_ordinal=self._request_ordinal,
                bank=self._bank,
                operation_id=operation_id,
                document_id=document_id,
            )
        except MemoryStoreUnavailable:
            if tracked_submission and not possibly_sent:
                raise _RetainNotSent("memory connection unavailable") from None
            raise

    def _single_request(
        self,
        method,
        path,
        deadline,
        *,
        content=None,
        reject_identity=None,
        tracked_submission=False,
    ):
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
            if tracked_submission and isinstance(
                error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
            ):
                raise _RetainNotSent("memory connection unavailable") from None
            category = transient_transport(error)
            if category is not None and time.monotonic() < deadline:
                raise TransientFailure(category) from None
            raise MemoryStoreUnavailable("memory operation unavailable") from None
        if time.monotonic() >= deadline:
            raise MemoryStoreUnavailable("memory operation unavailable: deadline exceeded")
        if response.status_code in {429, 502, 503, 504}:
            raise TransientFailure("http_status", response.status_code)
        if not response.is_success:
            if tracked_submission and response.status_code not in {400, 401, 403, 404, 413, 422}:
                raise MemoryStoreUnavailable("retain submission status is unknown")
            if reject_identity is not None:
                self._pending.pop(reject_identity, None)
            raise MemoryStoreRejected("memory operation rejected")
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, UnicodeError):
            if tracked_submission:
                raise MemoryStoreUnavailable("retain submission status is unknown") from None
            raise MemoryStoreRejected("invalid memory response") from None

    @staticmethod
    def _encode(body):
        return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _acknowledged(result: dict, operation: str) -> bool:
        return (
            result.get("success") is True
            and result.get("async") is True
            and result.get("operation_id") == operation
            and result.get("operation_ids") in (None, [operation])
        )

    def _retain_body(self, item: dict, operation: str) -> bytes:
        body = self._encode({"items": [item], "async": True, "operation_id": operation})
        if len(body) > self._max_bytes:
            raise MemoryStoreRejected("conversation exceeds request size limit")
        return body

    def retain_tracked(
        self, enriched: EnrichedConversation, checkpoint: Callable[[str, bool], None]
    ) -> RetainProgress:
        """Submit with a saved identity, then wait within the CLI budget."""
        operation = str(uuid4())
        body = self._retain_body(item_for(enriched), operation)
        receipt = f"{self._receipt_scope}:{operation}"
        checkpoint(receipt, False)
        deadline = time.monotonic() + self._completion
        try:
            result = self._request(
                "POST",
                self._root + "/memories",
                deadline,
                content=body,
                operation_id=operation,
                document_id=enriched.document_id,
                tracked_submission=True,
            )
        except (MemoryStoreRejected, _RetainNotSent):
            return RetainProgress.FAILED
        except MemoryStoreUnavailable:
            return RetainProgress.UNKNOWN
        if not self._acknowledged(result, operation):
            return RetainProgress.UNKNOWN
        checkpoint(receipt, True)
        while time.monotonic() < deadline:
            status = self._retain_progress(operation, deadline)
            if status is not RetainProgress.PENDING:
                return status
            time.sleep(min(self._interval, max(0, deadline - time.monotonic())))
        return RetainProgress.PENDING

    def check_retain(self, receipt: str) -> RetainProgress:
        scope, _, operation = receipt.partition(":")
        if scope != self._receipt_scope:
            return RetainProgress.UNKNOWN
        try:
            operation = str(UUID(operation))
        except ValueError:
            return RetainProgress.UNKNOWN
        return self._retain_progress(operation, time.monotonic() + self._timeout)

    def _retain_progress(self, operation: str, deadline: float) -> RetainProgress:
        try:
            result = self._request(
                "GET", self._root + "/operations/" + operation, deadline, operation_id=operation
            )
        except (MemoryStoreRejected, MemoryStoreUnavailable):
            return RetainProgress.UNKNOWN
        if result.get("operation_id") != operation:
            return RetainProgress.UNKNOWN
        status = result.get("status")
        if status == "completed":
            return RetainProgress.COMPLETED
        if status in ("failed", "cancelled"):
            return RetainProgress.FAILED
        if status not in ("pending", "processing"):
            return RetainProgress.UNKNOWN

        # The aggregate can lag its children. Only an entirely terminal child set
        # resolves the batch.
        children = result.get("child_operations")
        if isinstance(children, list) and children:
            statuses = [
                child.get("status") if isinstance(child, dict) else None for child in children
            ]
            if all(state in ("completed", "failed", "cancelled") for state in statuses):
                if all(state == "completed" for state in statuses):
                    return RetainProgress.COMPLETED
                return RetainProgress.FAILED
        return RetainProgress.PENDING

    def retain(self, enriched: EnrichedConversation) -> None:
        item = item_for(enriched)
        fingerprint = hashlib.sha256(self._encode(item)).hexdigest()
        identity = enriched.document_id
        with self._lock:
            previous = self._pending.get(identity)
            replaying = bool(previous and previous[0] == fingerprint)
            operation = previous[1] if replaying else str(uuid4())
            body = self._retain_body(item, operation)
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
            if not self._acknowledged(result, operation):
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
        return tuple(decode_result(fact, tag_values) for fact in facts[:limit])

    def reflect(self, query: str, tags: tuple[AnyTag, ...]) -> ReflectionResult:
        if not isinstance(query, str) or not query.strip() or not tags:
            raise MemoryStoreRejected("reflection needs a query and scope")
        tag_values = [str(tag) for tag in tags]
        body = self._encode(
            {
                "query": query,
                "tags": tag_values,
                "tags_match": "all_strict",
                "budget": "mid",
                "include": {"facts": {}},
            }
        )
        result = self._request(
            "POST", self._root + "/reflect", time.monotonic() + self._timeout, content=body
        )
        return decode_reflection(result, tag_values)
