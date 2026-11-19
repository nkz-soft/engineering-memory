"""Local durable import bookkeeping; policy remains in ingestion.state.

One writer and independent readers on a local filesystem. Call initialize() at
composition time, or validate() to open an existing database without creating it.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import (
    JSON,
    URL,
    CheckConstraint,
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    func,
    inspect,
    or_,
    select,
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from engineering_memory.ingestion.acquisition_state import AcquisitionRecord, EvidenceKind
from engineering_memory.ingestion.health import ProjectImportEvidence, SourceHealth
from engineering_memory.ingestion.state import (
    ImportRecord,
    ImportStateCorrupt,
    ImportStateUnavailable,
    ImportStatus,
)
from engineering_memory.normalization import Source
from engineering_memory.normalization.base import Slug

_METADATA = MetaData()
_SCHEMA = Table(
    "import_state_schema",
    _METADATA,
    Column("singleton", Integer, primary_key=True, nullable=False),
    Column("version", Integer, nullable=False),
    CheckConstraint("singleton = 1", name="schema_singleton"),
)
_RECORDS = Table(
    "import_records",
    _METADATA,
    Column("source", Text, primary_key=True, nullable=False),
    Column("source_id", Text, primary_key=True, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("document_id", Text, nullable=False),
    Column("recorded_at", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("error", Text, nullable=True),
    CheckConstraint("status IN ('imported', 'failed')", name="record_status"),
    CheckConstraint(
        "(status = 'imported' AND error IS NULL) OR "
        "(status = 'failed' AND error IS NOT NULL AND length(error) > 0)",
        name="record_error",
    ),
)
_ACQUISITIONS = Table(
    "export_acquisitions",
    _METADATA,
    Column("source", Text, primary_key=True, nullable=False),
    Column("digest", Text, primary_key=True, nullable=False),
    Column("mode", Text, nullable=False),
    Column("acquired_at", Text, nullable=False),
    Column("produced_at", Text),
    Column("production_evidence", Text, nullable=False),
    Column("ingested_at", Text),
    CheckConstraint("source = 'chatgpt'", name="acquisition_source"),
    CheckConstraint("mode IN ('manual', 'watcher')", name="acquisition_mode"),
    CheckConstraint(
        "(production_evidence = 'unknown' AND produced_at IS NULL) OR "
        "(production_evidence IN ('source_timestamp', 'zip_member_estimate') "
        "AND produced_at IS NOT NULL)",
        name="acquisition_production_evidence",
    ),
)
_SOURCE_HEALTH = Table(
    "source_health",
    _METADATA,
    Column("source", Text, primary_key=True, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("last_attempt_at", Text),
    Column("last_success_at", Text),
    Column("deferred_count", Integer, nullable=False),
    Column("error_categories", JSON, nullable=False),
)
_PROJECT_HEALTH = Table(
    "project_import_health",
    _METADATA,
    Column("project", Text, primary_key=True, nullable=False),
    Column("started_at", Text, nullable=False),
    Column("completed_at", Text, nullable=False),
)
_TABLES_BY_VERSION = {
    1: (_SCHEMA, _RECORDS),
    2: (_SCHEMA, _RECORDS, _ACQUISITIONS),
    3: tuple(_METADATA.tables.values()),
}
_SCHEMA_VERSION = 3
_PROJECT_SLUG = TypeAdapter(Slug)
_UNAVAILABLE = {
    sqlite3.SQLITE_BUSY,
    sqlite3.SQLITE_LOCKED,
    sqlite3.SQLITE_CANTOPEN,
    sqlite3.SQLITE_IOERR,
    sqlite3.SQLITE_FULL,
    sqlite3.SQLITE_READONLY,
    sqlite3.SQLITE_NOMEM,
    sqlite3.SQLITE_PERM,
}


def _utc_text(stamp: datetime) -> str:
    return stamp.astimezone(UTC).isoformat(timespec="microseconds")


class SQLiteImportState:
    """SQLAlchemy Core adapter for the existing ImportState protocol."""

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = Path(path).absolute()
        self._ready = False
        self._schema_version = 0
        self._engine = create_engine(
            URL.create(
                "sqlite+pysqlite",
                database=self.path.as_uri(),
                query={"mode": "ro" if read_only else "rw", "uri": "true"},
            ),
            connect_args={"autocommit": False, "timeout": 5},
            poolclass=NullPool,
            echo=False,
            hide_parameters=True,
        )

    @contextmanager
    def _errors(self) -> Iterator[None]:
        try:
            yield
        except (SQLAlchemyError, sqlite3.Error, OSError, ValueError) as exc:
            original = getattr(exc, "orig", exc)
            code = getattr(original, "sqlite_errorcode", 0) & 0xFF
            if isinstance(exc, OSError) or code in _UNAVAILABLE:
                raise ImportStateUnavailable("import state storage is unavailable") from exc
            raise ImportStateCorrupt("import state storage is invalid or incompatible") from exc

    def _require_file(self) -> None:
        if not self.path.is_file():
            raise ImportStateUnavailable("import state storage is unavailable")

    def _require_ready(self) -> None:
        if not self._ready:
            raise ImportStateUnavailable(
                "import state storage has not been initialized or validated"
            )
        self._require_file()

    def initialize(self) -> None:
        """Create storage or transactionally migrate a valid older store."""
        self._ready = False
        with self._errors():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.touch(exist_ok=True)
            with self._engine.begin() as connection:
                inspector = inspect(connection)
                if not inspector.get_table_names() and not inspector.get_view_names():
                    _METADATA.create_all(connection)
                    connection.execute(
                        _SCHEMA.insert().values(singleton=1, version=_SCHEMA_VERSION)
                    )
                version = self._validate_schema(connection)
                if version != _SCHEMA_VERSION:
                    for table in _TABLES_BY_VERSION[_SCHEMA_VERSION]:
                        if table not in _TABLES_BY_VERSION[version]:
                            table.create(connection)
                    connection.execute(_SCHEMA.update().values(version=_SCHEMA_VERSION))
                self._schema_version = self._validate_schema(connection)
        self._ready = True

    def validate(self) -> None:
        """Validate existing storage without creating a missing file or tables."""
        self._ready = False
        with self._errors():
            self._require_file()
            with self._engine.connect() as connection:
                self._schema_version = self._validate_schema(connection)
        self._ready = True

    @staticmethod
    def _validate_schema(connection: Connection) -> int:
        inspector = inspect(connection)
        actual_tables = set(inspector.get_table_names())
        version = next(
            (
                number
                for number, tables in _TABLES_BY_VERSION.items()
                if actual_tables == {table.name for table in tables}
            ),
            None,
        )
        if version is None or inspector.get_view_names():
            raise ImportStateCorrupt("import state schema is incompatible")
        for table in _TABLES_BY_VERSION[version]:
            columns = inspector.get_columns(table.name)
            actual = {c["name"]: (str(c["type"]), c["nullable"]) for c in columns}
            expected = {c.name: (str(c.type), c.nullable) for c in table.columns}
            primary = inspector.get_pk_constraint(table.name)["constrained_columns"]

            def normalize(text: str) -> str:
                # Conservative comparison preserves quoted values and their case.
                return text.strip()

            checks = {normalize(c["sqltext"]) for c in inspector.get_check_constraints(table.name)}
            required = {
                normalize(str(c.sqltext))
                for c in table.constraints
                if isinstance(c, CheckConstraint)
            }
            # Reflection omits expression indexes; the SQLite catalog is complete.
            indexes = connection.exec_driver_sql(f'PRAGMA index_list("{table.name}")').mappings()
            if (
                any(index["unique"] and index["origin"] != "pk" for index in indexes)
                or inspector.get_foreign_keys(table.name)
                or actual != expected
                or primary != [c.name for c in table.primary_key]
                or checks != required
            ):
                raise ImportStateCorrupt("import state schema is incompatible")
        versions = connection.execute(select(_SCHEMA)).all()
        if versions != [(1, version)]:
            raise ImportStateCorrupt("import state schema version is unsupported")
        return version

    def find(self, source: Source, source_id: str) -> ImportRecord | None:
        """Return the current committed outcome, or None for an unknown identity."""
        with self._errors():
            self._require_ready()
            with self._engine.connect() as connection:
                row = (
                    connection.execute(
                        select(_RECORDS).where(
                            _RECORDS.c.source == source, _RECORDS.c.source_id == source_id
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                return ImportRecord.model_validate(dict(row)) if row is not None else None

    def iter_records(self) -> Iterator[ImportRecord]:
        """Read validated latest records in deterministic identity order."""
        with self._errors():
            self._require_ready()
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(_RECORDS).order_by(_RECORDS.c.source, _RECORDS.c.source_id)
                ).mappings()
                for row in rows:
                    yield ImportRecord.model_validate(dict(row))

    @staticmethod
    def _record(connection: Connection, record: ImportRecord) -> None:
        values = record.model_dump(mode="json")
        values["recorded_at"] = _utc_text(record.recorded_at)
        connection.execute(
            insert(_RECORDS)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[_RECORDS.c.source, _RECORDS.c.source_id], set_=values
            )
        )

    def record(self, record: ImportRecord) -> None:
        """Atomically replace one identity's outcome, committing before return."""
        with self._errors():
            self._require_ready()
            with self._engine.begin() as connection:
                self._record(connection, record)

    def record_import(self, record: ImportRecord, project: str, started_at: datetime) -> None:
        """Commit a retained conversation and its content-free timestamps together."""
        if record.status is not ImportStatus.IMPORTED:
            raise ValueError("confirmed import required")
        with self._errors():
            self._require_ready()
            project = _PROJECT_SLUG.validate_python(project)
            stamp = _utc_text(record.recorded_at)
            initial = SourceHealth(source=record.source)
            with self._engine.begin() as connection:
                self._record(connection, record)
                connection.execute(
                    insert(_SOURCE_HEALTH)
                    .values(
                        **initial.model_dump(mode="json", exclude={"last_success_at"}),
                        last_success_at=stamp,
                    )
                    .on_conflict_do_update(
                        index_elements=[_SOURCE_HEALTH.c.source],
                        set_={"last_success_at": stamp},
                        where=or_(
                            _SOURCE_HEALTH.c.last_success_at.is_(None),
                            _SOURCE_HEALTH.c.last_success_at < stamp,
                        ),
                    )
                )
                if project not in {"unknown", "unclassified"} and started_at <= record.recorded_at:
                    lower = _utc_text(started_at)
                    columns = _PROJECT_HEALTH.c
                    connection.execute(
                        insert(_PROJECT_HEALTH)
                        .values(project=project, started_at=lower, completed_at=stamp)
                        .on_conflict_do_update(
                            index_elements=[columns.project],
                            set_={
                                "started_at": func.max(columns.started_at, lower),
                                "completed_at": func.max(columns.completed_at, stamp),
                            },
                        )
                    )

    def record_attempt(self, health: SourceHealth) -> None:
        """Record a completed attempt without replacing the last success."""
        if health.last_attempt_at is None or health.outcome == "unobserved":
            raise ValueError("completed source attempt required")
        values = health.model_dump(mode="json", exclude={"source", "last_success_at"})
        stamp = values["last_attempt_at"] = _utc_text(health.last_attempt_at)
        with self._errors():
            self._require_ready()
            with self._engine.begin() as connection:
                connection.execute(
                    insert(_SOURCE_HEALTH)
                    .values(source=health.source, **values)
                    .on_conflict_do_update(
                        index_elements=[_SOURCE_HEALTH.c.source],
                        set_=values,
                        where=or_(
                            _SOURCE_HEALTH.c.last_attempt_at.is_(None),
                            _SOURCE_HEALTH.c.last_attempt_at <= stamp,
                        ),
                    )
                )

    def read_health(
        self, project: str | None = None
    ) -> tuple[list[SourceHealth], ProjectImportEvidence | None]:
        with self._errors():
            self._require_ready()
            if self._schema_version < _SCHEMA_VERSION:
                return [], None
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(_SOURCE_HEALTH).order_by(_SOURCE_HEALTH.c.source)
                ).mappings()
                sources = [SourceHealth.model_validate(dict(row)) for row in rows]
                evidence = None
                if project is not None:
                    columns = _PROJECT_HEALTH.c
                    row = (
                        connection.execute(
                            select(columns.started_at, columns.completed_at).where(
                                columns.project == project
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is not None:
                        evidence = ProjectImportEvidence.model_validate(dict(row))
                return sources, evidence

    def find_acquisition(self, digest: str) -> AcquisitionRecord | None:
        return self._first_acquisition(
            select(_ACQUISITIONS).where(_ACQUISITIONS.c.digest == digest)
        )

    def pending_acquisition(self) -> AcquisitionRecord | None:
        columns = _ACQUISITIONS.c
        return self._first_acquisition(
            select(_ACQUISITIONS)
            .where(columns.ingested_at.is_(None))
            .order_by(columns.acquired_at, columns.digest)
        )

    def latest_acquisition(self) -> AcquisitionRecord | None:
        columns = _ACQUISITIONS.c
        return self._first_acquisition(
            select(_ACQUISITIONS)
            .where(columns.ingested_at.is_not(None))
            .order_by(columns.ingested_at.desc(), columns.digest)
        )

    def latest_production(self, evidence: EvidenceKind) -> AcquisitionRecord | None:
        columns = _ACQUISITIONS.c
        return self._first_acquisition(
            select(_ACQUISITIONS)
            .where(
                columns.ingested_at.is_not(None),
                columns.produced_at.is_not(None),
                columns.production_evidence == evidence,
            )
            .order_by(columns.produced_at.desc(), columns.digest)
        )

    def _first_acquisition(self, query) -> AcquisitionRecord | None:
        with self._errors():
            if not self._ready:
                if not self.path.exists():
                    return None
                self.validate()
            self._require_ready()
            if self._schema_version == 1:
                return None
            with self._engine.connect() as connection:
                row = connection.execute(query.limit(1)).mappings().first()
                return AcquisitionRecord.model_validate(dict(row)) if row is not None else None

    def record_acquisition(self, record: AcquisitionRecord) -> None:
        if not self._ready or self._schema_version != _SCHEMA_VERSION:
            self.initialize()
        values = record.model_dump(mode="json")
        for field in ("acquired_at", "produced_at", "ingested_at"):
            stamp = getattr(record, field)
            values[field] = stamp.isoformat(timespec="microseconds") if stamp is not None else None
        with self._errors(), self._engine.begin() as connection:
            connection.execute(_ACQUISITIONS.insert().values(**values))

    def complete_acquisition(self, digest: str, ingested_at: datetime) -> None:
        self._require_ready()
        columns = _ACQUISITIONS.c
        with self._errors(), self._engine.begin() as connection:
            result = connection.execute(
                _ACQUISITIONS.update()
                .where(columns.digest == digest, columns.ingested_at.is_(None))
                .values(ingested_at=ingested_at.astimezone(UTC).isoformat(timespec="microseconds"))
            )
            if result.rowcount != 1:
                raise ImportStateCorrupt("pending acquisition is missing")

    def close(self) -> None:
        """Dispose resources; reopening requires explicit validation."""
        self._ready = False
        self._engine.dispose()
