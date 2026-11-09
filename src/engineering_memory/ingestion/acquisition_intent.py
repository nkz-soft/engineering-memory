"""Recover the gap between publishing an export and committing its ledger row."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol

from pydantic import ValidationError

from engineering_memory.archive.local import _publish, _redirected
from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.ingestion.acquisition_state import AcquisitionRecord


class AcquisitionIntent(Protocol):
    def read(self) -> AcquisitionRecord | None: ...

    def save(self, record: AcquisitionRecord) -> None: ...

    def clear(self) -> None: ...


class LocalAcquisitionIntent:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> AcquisitionRecord | None:
        try:
            if _redirected(self.path):
                raise AcquisitionError("intent_unavailable")
            with self.path.open("rb") as source:
                record = AcquisitionRecord.model_validate_json(source.read(8193))
            if record.ingested_at is not None:
                raise AcquisitionError("intent_invalid")
            return record
        except FileNotFoundError:
            return None
        except ValidationError as error:
            raise AcquisitionError("intent_invalid") from error
        except OSError as error:
            raise AcquisitionError("intent_unavailable") from error

    def save(self, record: AcquisitionRecord) -> None:
        temporary = None
        try:
            with NamedTemporaryFile(dir=self.path.parent, suffix=".staging", delete=False) as file:
                temporary = Path(file.name)
                file.write(record.model_dump_json().encode("utf-8"))
                file.flush()
                os.fsync(file.fileno())
            _publish(temporary, self.path)
        except OSError as error:
            raise AcquisitionError("intent_unavailable") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as error:
            raise AcquisitionError("intent_unavailable") from error
