"""Durable SQLite catalog with serialized, idempotent publication."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from engineering_memory.playbooks.interface import CatalogUnavailable
from engineering_memory.playbooks.models import ApprovedPlaybook, Draft, PlaybookContent, Summary

_SCHEMA_VERSION = 1
_CREATE_DRAFTS = """
    CREATE TABLE IF NOT EXISTS drafts (
        project TEXT NOT NULL, id TEXT NOT NULL, draft TEXT NOT NULL,
        PRIMARY KEY (project, id)
    )
"""
_CREATE_APPROVALS = """
    CREATE TABLE IF NOT EXISTS approvals (
        project TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL,
        revision TEXT NOT NULL, approved_at TEXT NOT NULL,
        title TEXT NOT NULL, content TEXT NOT NULL,
        PRIMARY KEY (project, id, version),
        UNIQUE (project, id, revision)
    )
"""


class SQLitePlaybookCatalog:
    def __init__(self, path: Path) -> None:
        self.path = path.absolute()
        self._reader = self._engine("ro")
        self._writer = self._engine("rwc")

    def _engine(self, mode: str):
        url = URL.create(
            "sqlite",
            database=self.path.as_uri(),
            query={"mode": mode, "uri": "true"},
        )
        return create_engine(url, poolclass=NullPool, hide_parameters=True)

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[Connection | None]:
        try:
            if write:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            else:
                try:
                    self.path.stat()
                except FileNotFoundError:
                    yield None
                    return
            engine = self._writer if write else self._reader
            with engine.connect() as connection:
                if write:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
                if version == 0 and write:
                    tables = connection.exec_driver_sql(
                        "SELECT name FROM sqlite_schema WHERE type = 'table' LIMIT 1"
                    ).first()
                    if tables:
                        raise CatalogUnavailable("catalog_unavailable")
                    connection.exec_driver_sql(_CREATE_DRAFTS)
                    connection.exec_driver_sql(_CREATE_APPROVALS)
                    connection.exec_driver_sql(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                elif version != _SCHEMA_VERSION:
                    raise CatalogUnavailable("catalog_unavailable")
                yield connection
                if write:
                    connection.commit()
        except (OSError, SQLAlchemyError, ValidationError):
            raise CatalogUnavailable("catalog_unavailable") from None

    def stage(self, project: str, id: str, draft: Draft) -> None:
        with self._connection(write=True) as connection:
            connection.execute(
                text("""
                    INSERT INTO drafts (project, id, draft) VALUES (:project, :id, :draft)
                    ON CONFLICT (project, id) DO UPDATE SET draft = excluded.draft
                """),
                {"project": project, "id": id, "draft": draft.model_dump_json()},
            )

    @staticmethod
    def _draft(connection: Connection, keys: dict) -> Draft | None:
        raw = connection.execute(
            text("SELECT draft FROM drafts WHERE project = :project AND id = :id"), keys
        ).scalar_one_or_none()
        return Draft.model_validate_json(raw) if raw is not None else None

    def review(self, project: str, id: str) -> Draft | None:
        with self._connection() as connection:
            if connection is None:
                return None
            return self._draft(connection, {"project": project, "id": id})

    def approve(self, project: str, id: str, revision: str, verify) -> int:
        keys = {"project": project, "id": id, "revision": revision}
        with self._connection(write=True) as connection:
            approved = connection.execute(
                text("""
                    SELECT version FROM approvals
                    WHERE project = :project AND id = :id AND revision = :revision
                """),
                keys,
            ).scalar_one_or_none()
            if approved is not None:
                return approved
            draft = self._draft(connection, keys)
            if draft is None or draft.revision != revision:
                raise ValueError("draft_changed")
            verify(draft.content)
            version = connection.execute(
                text("""
                    SELECT coalesce(max(version), 0) + 1 FROM approvals
                    WHERE project = :project AND id = :id
                """),
                keys,
            ).scalar_one()
            connection.execute(
                text("""
                    INSERT INTO approvals
                        (project, id, version, revision, approved_at, title, content)
                    VALUES (:project, :id, :version, :revision, :approved_at, :title, :content)
                """),
                keys
                | {
                    "version": version,
                    "approved_at": datetime.now(UTC).isoformat(),
                    "title": draft.content.title,
                    "content": draft.content.model_dump_json(),
                },
            )
            connection.execute(
                text("DELETE FROM drafts WHERE project = :project AND id = :id"), keys
            )
            return version

    def list_approved(self, project: str, after_id: str | None, limit: int) -> list[Summary]:
        with self._connection() as connection:
            if connection is None:
                return []
            rows = connection.execute(
                text("""
                    WITH page AS (
                        SELECT id, max(version) AS version FROM approvals
                        WHERE project = :project AND id > :after_id
                        GROUP BY id ORDER BY id LIMIT :limit
                    )
                    SELECT a.id, a.title, a.version FROM page
                    JOIN approvals a USING (id, version)
                    WHERE a.project = :project ORDER BY a.id
                """),
                {"project": project, "after_id": after_id or "", "limit": limit},
            ).mappings()
            return [Summary.model_validate(row) for row in rows]

    def get_approved(self, project: str, id: str, version: int | None) -> ApprovedPlaybook | None:
        with self._connection() as connection:
            if connection is None:
                return None
            row = (
                connection.execute(
                    text("""
                    WITH latest AS (
                        SELECT max(version) AS latest_version FROM approvals
                        WHERE project = :project AND id = :id
                    )
                    SELECT a.version, a.approved_at, a.content, latest.latest_version
                    FROM approvals a CROSS JOIN latest
                    WHERE a.project = :project AND a.id = :id
                        AND a.version = coalesce(:version, latest.latest_version)
                """),
                    {"project": project, "id": id, "version": version},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            return ApprovedPlaybook(
                project=project,
                id=id,
                version=row["version"],
                latest_version=row["latest_version"],
                approved_at=datetime.fromisoformat(row["approved_at"]),
                content=PlaybookContent.model_validate_json(row["content"]),
            )
