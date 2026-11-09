"""Validate and archive a complete export, then run incremental ingestion."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from engineering_memory.archive.export_blobs import ExportBlobs
from engineering_memory.ingestion.acquisition_intent import AcquisitionIntent
from engineering_memory.ingestion.acquisition_source import (
    AcquisitionError,
    ExportCandidate,
    ExportSource,
)
from engineering_memory.ingestion.acquisition_state import AcquisitionRecord, AcquisitionState
from engineering_memory.ingestion.chatgpt_preflight import DEFAULT_LIMITS, validate_export
from engineering_memory.ingestion.report import RunReport, RunStatus


class ExportAcquisition:
    def __init__(
        self,
        *,
        source: ExportSource,
        blobs: ExportBlobs,
        state: AcquisitionState,
        intent: AcquisitionIntent,
        ingest: Callable[[Path], RunReport],
        report: Callable[[str, RunReport | None, str | None], None],
        acknowledge: Callable[[ExportCandidate, str], None] | None = None,
        zip_offset_minutes: int | None = None,
    ) -> None:
        self.source = source
        self.blobs = blobs
        self.state = state
        self.intent = intent
        self.ingest = ingest
        self.report = report
        self.acknowledge = acknowledge
        self.zip_offset_minutes = zip_offset_minutes

    def run(self) -> None:
        self._recover_publication()
        pending = self.state.pending_acquisition()
        if pending is not None and not self._import(pending.digest):
            return

        for candidate in self.source.discover():
            digest = self._acquire(candidate)
            if digest is None:
                return
            if self.acknowledge is not None:
                self.acknowledge(candidate, digest)

    def _recover_publication(self) -> None:
        record = self.intent.read()
        if record is None:
            return
        self.report("pending", None, record.digest)
        previous = self.state.find_acquisition(record.digest)
        if previous is None and self.blobs.find_published(record.digest) is not None:
            self.state.record_acquisition(record)
        self.intent.clear()
        self.report("empty", None, None)

    def _acquire(self, candidate: ExportCandidate) -> str | None:
        with self.blobs.stage(candidate, max_bytes=DEFAULT_LIMITS.compressed_bytes) as staged:
            previous = self.state.find_acquisition(staged.digest)
            if previous is not None:
                self.report("duplicate", None, staged.digest)
                return staged.digest

            evidence = validate_export(staged.path, zip_offset_minutes=self.zip_offset_minutes)
            if evidence.produced_at is not None:
                latest = self.state.latest_production(evidence.kind)
                if latest is not None and latest.produced_at > evidence.produced_at:
                    raise AcquisitionError("stale_export")
            record = AcquisitionRecord(
                digest=staged.digest,
                mode=candidate.mode,
                acquired_at=datetime.now(UTC),
                produced_at=evidence.produced_at,
                production_evidence=evidence.kind,
            )
            self.report("pending", None, record.digest)
            self.intent.save(record)
            path = self.blobs.publish(staged)
            self.state.record_acquisition(record)
            self.intent.clear()
        return staged.digest if self._import(staged.digest, path) else None

    def _import(self, digest: str, path: Path | None = None) -> bool:
        self.report("pending", None, digest)
        report = self.ingest(path if path is not None else self.blobs.verified_path(digest))
        complete = report.status == RunStatus.SUCCESS
        if complete:
            self.state.complete_acquisition(digest, datetime.now(UTC))
        self.report("imported" if complete else "import_failed", report, digest)
        return complete
