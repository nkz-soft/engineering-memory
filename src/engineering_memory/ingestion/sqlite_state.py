"""Local durable import bookkeeping; policy remains in ingestion.state.

One writer and independent readers on a local filesystem. Call initialize() at
composition time, or validate() to open an existing database without creating it.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import (
    URL,
    CheckConstraint,
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from engineering_memory.ingestion.acquisition_state import AcquisitionRecord, EvidenceKind
from engineering_memory.ingestion.state import (
    ImportRecord,
    ImportStateCorrupt,
    ImportStateUnavailable,
)
from engineering_memory.normalization import Source

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
_LEGACY_TABLES = (_SCHEMA, _RECORDS)
_SCHEMA_VERSION = 2
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
        except (SQLAlchemyError, sqlite3.Error, OSError, ValidationError) as exc:
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
        """Create storage or transactionally migrate a valid v1 store."""
        self._ready = False
        with self._errors():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.touch(exist_ok=False)
            with self._engine.begin() as connection:
                inspector = inspect(connection)
                if not inspector.get_table_names() and not inspector.get_view_names():
                    _METADATA.create_all(connection)
                    connection.execute(
                        _SCHEMA.insert().values(singleton=1, version=_SCHEMA_VERSION)
                    )
                if self._validate_schema(connection) == 1:
                    _ACQUISITIONS.create(connection)
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
        legacy = {table.name for table in _LEGACY_TABLES}
        current = set(_METADATA.tables)
        if actual_tables not in (legacy, current) or inspector.get_view_names():
            raise ImportStateCorrupt("import state schema is incompatible")
        version = 1 if actual_tables == legacy else _SCHEMA_VERSION
        for table in _LEGACY_TABLES if version == 1 else _METADATA.tables.values():
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

    def record(self, record: ImportRecord) -> None:
        """Atomically replace one identity's outcome, committing before return."""
        with self._errors():
            self._require_ready()
            values = record.model_dump(mode="json")
            values["recorded_at"] = record.recorded_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            )
            with self._engine.begin() as connection:
                key = (_RECORDS.c.source == record.source) & (
                    _RECORDS.c.source_id == record.source_id
                )
                found = connection.execute(select(_RECORDS.c.source).where(key)).first()
                if found is None:
                    connection.execute(_RECORDS.insert().values(**values))
                else:
                    connection.execute(_RECORDS.update().where(key).values(**values))

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
