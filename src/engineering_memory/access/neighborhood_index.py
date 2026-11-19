"""A rebuildable SQLite projection for bounded, local evidence lookups."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    Connection,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    select,
    tuple_,
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from engineering_memory.access.neighborhood import NeighborhoodUnavailable
from engineering_memory.access.neighborhood_evidence import (
    EvidenceEdge,
    Node,
    project_evidence,
    project_of,
)
from engineering_memory.archive import (
    ArchiveDocumentNotFound,
    ArchiveListingRejected,
    ArchiveRejected,
    ArchiveUnavailable,
    RawArchive,
)

_LIMIT = 30
_VERSION = 1
_METADATA = MetaData()
_COVERAGE = Table(
    "coverage",
    _METADATA,
    Column("version", Integer, primary_key=True),
    Column("completed_at", String, nullable=False),
    Column("indexed", Integer, nullable=False),
    Column("skipped", Integer, nullable=False),
)


def _endpoint_columns(side: str) -> list[Column]:
    return [
        Column(f"{side}_{name}", String, nullable=False)
        for name in ("kind", "repository", "identity", "label")
    ]


_EDGES = Table(
    "edges",
    _METADATA,
    Column("project", String, primary_key=True),
    Column("edge_key", String, primary_key=True),
    *_endpoint_columns("origin"),
    *_endpoint_columns("target"),
    Column("relation", String, nullable=False),
    Column("handle", String, nullable=False),
    Column("document_id", String, nullable=False),
    Column("message", Integer, nullable=False),
    Column("tool", Integer, nullable=False),
    Column("field", String, nullable=False),
    Column("observed_at", String, nullable=False),
    Column("snapshot", String, nullable=False),
)
_ADJACENCY = {
    side: tuple(_EDGES.c[f"{side}_{name}"] for name in ("kind", "repository", "identity"))
    for side in ("origin", "target")
}
for _side, _columns in _ADJACENCY.items():
    Index(
        f"edges_by_{_side}",
        _EDGES.c.project,
        *_columns,
        _EDGES.c.observed_at.desc(),
        _EDGES.c.edge_key,
    )
Index("edges_by_handle", _EDGES.c.project, _EDGES.c.handle, unique=True)

_SESSIONS = Table(
    "classified_sessions",
    MetaData(),
    Column("project", String, primary_key=True),
    Column("document_id", String, primary_key=True),
    prefixes=["TEMPORARY"],
)
_SESSION_EXISTS = (
    select(_SESSIONS.c.document_id)
    .where(
        _SESSIONS.c.project == _EDGES.c.project,
        _SESSIONS.c.document_id == _EDGES.c.target_identity,
    )
    .exists()
)
_INSERT_EDGE = insert(_EDGES)
_EVENT_COLUMNS = ("observed_at", "document_id", "message", "tool", "field")
_UPSERT_EDGE = _INSERT_EDGE.on_conflict_do_update(
    index_elements=[_EDGES.c.project, _EDGES.c.edge_key],
    set_={
        column.name: _INSERT_EDGE.excluded[column.name]
        for column in _EDGES.columns
        if not column.primary_key
    },
    where=tuple_(*(_INSERT_EDGE.excluded[name] for name in _EVENT_COLUMNS))
    > tuple_(*(_EDGES.c[name] for name in _EVENT_COLUMNS)),
)


class IndexUnavailable(NeighborhoodUnavailable):
    """The index cannot be read or safely rebuilt."""


class NeighborhoodIndex:
    """Keep the published graph visible during refresh via SQLite WAL snapshots."""

    def __init__(self, path: Path) -> None:
        self._path = path.absolute()
        self._reader = self._engine("ro", timeout=5)
        self._writer = self._engine("rwc", timeout=0)

    def _check_paths(self) -> None:
        paths = (
            self._path.parent,
            self._path,
            *(
                self._path.with_name(self._path.name + suffix)
                for suffix in (
                    "-wal",
                    "-shm",
                    "-journal",
                )
            ),
        )
        if any(path.is_symlink() or path.is_junction() for path in paths):
            raise IndexUnavailable("neighborhood index storage is unavailable")

    def _engine(self, mode: str, *, timeout: int) -> Engine:
        return create_engine(
            URL.create(
                "sqlite+pysqlite",
                database=self._path.as_uri(),
                query={"mode": mode, "uri": "true"},
            ),
            connect_args={"timeout": timeout, "isolation_level": None},
            poolclass=NullPool,
            hide_parameters=True,
        )

    def rebuild(self, archive: RawArchive) -> dict:
        """Publish one completed pass, or leave the previous projection readable."""
        try:
            self._check_paths()
            self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with suppress(FileExistsError):
                descriptor = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
            with self._writer.connect() as connection:
                journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
                if journal_mode != "wal":
                    journal_mode = connection.exec_driver_sql(
                        "PRAGMA journal_mode=WAL"
                    ).scalar_one()
                if journal_mode != "wal":
                    raise IndexUnavailable("neighborhood index storage is unavailable")
                # Acquire the single-writer lock before scanning the archive.
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                _METADATA.create_all(connection)
                _coverage(connection)
                connection.execute(_COVERAGE.delete())
                connection.execute(_EDGES.delete())
                _SESSIONS.create(connection)
                indexed, skipped = _populate(connection, archive)
                connection.execute(
                    _EDGES.delete().where(_EDGES.c.target_kind == "session", ~_SESSION_EXISTS)
                )
                coverage = {
                    "completed_at": datetime.now(UTC).isoformat(timespec="microseconds"),
                    "indexed": indexed,
                    "skipped": skipped,
                }
                connection.execute(_COVERAGE.insert().values(version=_VERSION, **coverage))
                connection.commit()
                return coverage
        except (ArchiveRejected, ArchiveUnavailable, OSError, SQLAlchemyError) as failure:
            raise IndexUnavailable("neighborhood index could not be rebuilt") from failure

    @contextmanager
    def _read(self) -> Iterator[Connection | None]:
        try:
            self._check_paths()
            if not self._path.exists():
                yield None
                return
            with self._reader.connect() as connection:
                connection.exec_driver_sql("BEGIN")
                yield connection if inspect(connection).has_table(_COVERAGE.name) else None
        except (OSError, SQLAlchemyError) as failure:
            raise IndexUnavailable("neighborhood index could not be read") from failure

    def neighborhood(self, project: str, root: Node) -> dict:
        with self._read() as connection:
            coverage = _coverage(connection) if connection is not None else None
            if coverage is None:
                return {"status": "unindexed", "edges": [], "truncated": False}
            neighbors = {}
            for kind, repository, identity in _ADJACENCY.values():
                statement = (
                    select(_EDGES)
                    .where(
                        _EDGES.c.project == project,
                        kind == root.kind,
                        repository == (root.repository or ""),
                        identity == root.identity,
                    )
                    .order_by(_EDGES.c.observed_at.desc(), _EDGES.c.edge_key)
                    .limit(_LIMIT + 1)
                )
                for row in connection.execute(statement).mappings():
                    neighbors[row["edge_key"]] = row
            # Merge just the indexed prefixes, preserving the SQL tie order across directions.
            rows = [neighbors[key] for key in sorted(neighbors)]
            rows.sort(key=lambda row: row["observed_at"], reverse=True)
            return {
                "status": "partial" if coverage["skipped"] else "ready",
                "coverage": coverage,
                "edges": [_public_edge(row) for row in rows[:_LIMIT]],
                "truncated": len(rows) > _LIMIT,
            }

    def evidence(self, project: str, handle: str) -> EvidenceEdge | None:
        with self._read() as connection:
            if connection is None or _coverage(connection) is None:
                return None
            row = (
                connection.execute(
                    select(_EDGES).where(_EDGES.c.project == project, _EDGES.c.handle == handle)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            return EvidenceEdge(
                project=project,
                origin=_node(row, "origin"),
                target=_node(row, "target"),
                relation=row["relation"],
                document_id=row["document_id"],
                message=row["message"],
                tool=None if row["tool"] == -1 else row["tool"],
                field=row["field"],
                observed_at=row["observed_at"],
                snapshot=row["snapshot"],
            )


def _coverage(connection: Connection) -> dict | None:
    row = connection.execute(select(_COVERAGE)).mappings().one_or_none()
    if row is None:
        return None
    coverage = dict(row)
    if coverage.pop("version") != _VERSION:
        raise IndexUnavailable("neighborhood index version is unsupported")
    return coverage


def _populate(connection: Connection, archive: RawArchive) -> tuple[int, int]:
    indexed = skipped = 0
    documents = archive.iter_document_ids()
    sessions = []
    edges = []
    try:
        while True:
            try:
                document_id = next(documents)
            except StopIteration:
                break
            except ArchiveListingRejected:
                raise
            except ArchiveRejected:
                skipped += 1
                continue
            try:
                archived = archive.load(document_id)
            except ArchiveListingRejected:
                raise
            except (ArchiveDocumentNotFound, ArchiveRejected, ArchiveUnavailable):
                skipped += 1
                continue
            project = project_of(archived)
            if project is None:
                continue
            indexed += 1
            sessions.append({"project": project, "document_id": document_id})
            for edge in project_evidence(archived):
                edges.append(_edge_values(edge))
                if len(edges) == 500:
                    connection.execute(_UPSERT_EDGE, edges)
                    edges.clear()
            if len(sessions) == 500:
                connection.execute(_SESSIONS.insert(), sessions)
                sessions.clear()
        if sessions:
            connection.execute(_SESSIONS.insert(), sessions)
        if edges:
            connection.execute(_UPSERT_EDGE, edges)
    finally:
        close = getattr(documents, "close", None)
        if close is not None:
            close()
    return indexed, skipped


def _edge_values(edge: EvidenceEdge) -> dict:
    origin, target = edge.origin, edge.target
    # Scope and endpoint type are part of identity. Keep labels out of the deduplication key.
    key = json.dumps(
        [
            origin.kind,
            origin.repository,
            origin.identity,
            target.kind,
            target.repository,
            target.identity,
            edge.relation,
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return {
        "project": edge.project,
        "edge_key": key,
        "origin_kind": origin.kind,
        "origin_repository": origin.repository or "",
        "origin_identity": origin.identity,
        "origin_label": origin.label,
        "target_kind": target.kind,
        "target_repository": target.repository or "",
        "target_identity": target.identity,
        "target_label": target.label,
        "relation": edge.relation,
        "handle": uuid4().hex,
        "document_id": edge.document_id,
        "message": edge.message,
        "tool": -1 if edge.tool is None else edge.tool,
        "field": edge.field,
        "observed_at": edge.observed_at,
        "snapshot": edge.snapshot,
    }


def _node(row: Mapping[str, Any], side: str) -> Node:
    return Node(
        kind=row[f"{side}_kind"],
        identity=row[f"{side}_identity"],
        label=row[f"{side}_label"],
        repository=row[f"{side}_repository"] or None,
    )


def _public_edge(row: Mapping[str, Any]) -> dict:
    return {
        "origin": asdict(_node(row, "origin")),
        "target": asdict(_node(row, "target")),
        "relation": row["relation"],
        "handle": row["handle"],
    }
