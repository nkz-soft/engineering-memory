"""Authenticated, loopback-only HTTP adapter for the shared read service."""

import json
from collections.abc import Callable
from hmac import compare_digest
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from engineering_memory.access.neighborhood import (
    BrowserConversationRequest,
    NeighborhoodEvidenceRequest,
    NeighborhoodRequest,
)
from engineering_memory.access.service import (
    AccessError,
    DeepRecallRequest,
    MemoryAccess,
    SessionHandoffRequest,
    SynthesisUnconfigured,
)
from engineering_memory.normalization.base import Slug

ASSETS = Path(__file__).with_name("explorer_assets")
MAX_BODY_BYTES = 16 * 1024
ERROR_STATUS = {
    "invalid_input": 400,
    "not_found": 404,
    "unavailable": 503,
    "corrupt_record": 500,
    "rejected": 500,
    "internal": 500,
    "synthesis_invalid": 502,
    "synthesis_response_limit": 502,
    "synthesis_timeout": 504,
}


class _BrowserDeepRecallRequest(DeepRecallRequest):
    mode: Literal["decision_history"] | None = None

    @field_validator("mode")
    @classmethod
    def require_mode_if_present(cls, value):
        if value is None:
            raise ValueError("mode cannot be null")
        return value


class _StatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project: Slug | None = None

    @field_validator("project")
    @classmethod
    def require_classified_project(cls, value):
        if value in {"unknown", "unclassified"}:
            raise ValueError("a classified project is required")
        return value


def _error(code: str, status: int) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status)


async def _read_json(request: Request) -> dict:
    content_types = request.headers.getlist("content-type")
    if (
        len(content_types) != 1
        or content_types[0].partition(";")[0].strip().lower() != "application/json"
    ):
        raise AccessError("invalid_input")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise AccessError("invalid_input")
        body.extend(chunk)
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        raise AccessError("invalid_input") from None
    if not isinstance(data, dict):
        raise AccessError("invalid_input")
    return data


def create_explorer_app(
    access: MemoryAccess,
    *,
    token: str,
    authority: str,
    read_status: Callable[..., dict] | None = None,
) -> FastAPI:
    """Expose the browser shell and authenticated read operations."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
    origin = f"http://{authority}"
    expected_authorization = f"Bearer {token}".encode("ascii")

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.headers.getlist("host") != [authority]:
            response = _error("forbidden", 403)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/")
    async def index():
        return Response((ASSETS / "index.html").read_bytes(), media_type="text/html")

    @app.get("/assets/explorer.css")
    async def stylesheet():
        return Response((ASSETS / "explorer.css").read_bytes(), media_type="text/css")

    @app.get("/assets/explorer.js")
    async def script():
        return Response((ASSETS / "explorer.js").read_bytes(), media_type="text/javascript")

    async def dispatch(request: Request, model, read) -> JSONResponse:
        if request.headers.getlist("origin") != [origin]:
            return _error("forbidden", 403)
        authorization = request.headers.getlist("authorization")
        if len(authorization) != 1 or not compare_digest(
            authorization[0].encode("latin1"), expected_authorization
        ):
            return _error("unauthorized", 401)
        try:
            payload = model.model_validate(await _read_json(request))
            result = await run_in_threadpool(read, **payload.model_dump())
            return JSONResponse(result)
        except ValidationError:
            return _error("invalid_input", 400)
        except SynthesisUnconfigured:
            return _error("synthesis_unconfigured", 503)
        except AccessError as error:
            code = str(error)
            return (
                _error(code, ERROR_STATUS[code])
                if code in ERROR_STATUS
                else _error("internal", 500)
            )
        except Exception:
            return _error("internal", 500)

    def search(query: str, project: str) -> dict:
        return access.search_memory(query=query, tags=[f"project:{project}"])

    @app.post("/api/search")
    async def search_memory(request: Request):
        return await dispatch(request, DeepRecallRequest, search)

    def read_synthesis(query: str, project: str, mode: str | None = None) -> dict:
        read = access.decision_history if mode == "decision_history" else access.deep_recall
        return read(query=query, project=project)

    @app.post("/api/deep-recall")
    async def deep_recall(request: Request):
        return await dispatch(request, _BrowserDeepRecallRequest, read_synthesis)

    def read_conversation(project: str | None, snapshot: str | None, **page) -> dict:
        if snapshot is not None:
            return access.get_neighborhood_conversation(project=project, snapshot=snapshot, **page)
        return access.get_conversation(**page)

    @app.post("/api/conversation")
    async def conversation(request: Request):
        return await dispatch(request, BrowserConversationRequest, read_conversation)

    @app.post("/api/neighborhood")
    async def neighborhood(request: Request):
        return await dispatch(request, NeighborhoodRequest, access.neighborhood)

    @app.post("/api/neighborhood/evidence")
    async def neighborhood_evidence(request: Request):
        return await dispatch(request, NeighborhoodEvidenceRequest, access.neighborhood_evidence)

    def read_handoff(document_id: str, project: str) -> dict:
        return access.session_handoff(document_id=document_id, project=project, link_origin=origin)

    @app.post("/api/session-handoff")
    async def session_handoff(request: Request):
        return await dispatch(request, SessionHandoffRequest, read_handoff)

    if read_status is not None:

        @app.post("/api/status")
        async def status(request: Request):
            return await dispatch(request, _StatusRequest, read_status)

    return app
