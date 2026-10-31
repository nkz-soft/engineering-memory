from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from engineering_memory.ingestion.report import ConversationOutcome, RunReport, RunStatus, Stage
from engineering_memory.ingestion.state import ImportStatus
from engineering_memory.normalization import Source

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def outcome(status):
    return ConversationOutcome(
        source=Source.CHATGPT,
        status=status,
        completed_at=NOW,
        error=Stage.RETAIN if status == ImportStatus.FAILED else None,
    )


@pytest.mark.parametrize(
    ("statuses", "terminal", "expected", "counts"),
    [
        ([], None, RunStatus.SUCCESS, (0, 0, 0)),
        ([ImportStatus.SKIPPED], None, RunStatus.SUCCESS, (0, 1, 0)),
        ([ImportStatus.FAILED], None, RunStatus.FAILURE, (0, 0, 1)),
        ([ImportStatus.IMPORTED, ImportStatus.FAILED], None, RunStatus.PARTIAL_SUCCESS, (1, 0, 1)),
        ([], Stage.SOURCE, RunStatus.FAILURE, (0, 0, 0)),
        ([ImportStatus.SKIPPED], Stage.SOURCE, RunStatus.PARTIAL_SUCCESS, (0, 1, 0)),
    ],
)
def test_aggregate_distinguishes_progress_from_total_failure(statuses, terminal, expected, counts):
    report = RunReport(outcomes=tuple(outcome(s) for s in statuses), terminal_error=terminal)
    assert report.status == expected
    assert (report.imported, report.skipped, report.failed) == counts


@pytest.mark.parametrize(
    ("status", "error", "secondary"),
    [
        (ImportStatus.FAILED, None, False),
        (ImportStatus.IMPORTED, Stage.RETAIN, False),
        (ImportStatus.SKIPPED, None, True),
    ],
)
def test_outcome_rejects_untrustworthy_failure_diagnostics(status, error, secondary):
    with pytest.raises(ValidationError):
        ConversationOutcome(
            source=Source.CHATGPT,
            status=status,
            completed_at=NOW,
            error=error,
            state_record_failed=secondary,
        )
