"""Run the recall benchmark and paired reflection evaluation."""

from pathlib import Path
from typing import Annotated, NoReturn

import anyio
import typer

from engineering_memory.evaluation.benchmark import load_benchmark
from engineering_memory.evaluation.reflect import ReflectCaseSet
from engineering_memory.evaluation.reports import (
    RunProfile,
    RunReport,
    compare_reports,
    write_report,
)
from engineering_memory.evaluation.runner import RecallFailed, run_recall, run_reflect

app = typer.Typer(no_args_is_help=True, help="Evaluate recall and reflection.")


def _fail(category: str) -> NoReturn:
    typer.echo(category, err=True)
    raise typer.Exit(1)


@app.command("recall")
def recall(
    benchmark: Annotated[Path, typer.Option(help="Path to the benchmark manifest.")],
    profile: Annotated[Path, typer.Option(help="Path to the public run profile.")],
    output: Annotated[Path, typer.Option(help="Destination for the complete report.")],
) -> None:
    """Score the benchmark through the configured read-only memory server."""
    try:
        dataset = load_benchmark(benchmark)
        run_profile = RunProfile.model_validate_json(profile.read_bytes())
    except (ValueError, OSError):
        _fail("invalid evaluation input")

    try:
        report = anyio.run(run_recall, dataset, run_profile)
    except RecallFailed:
        _fail("recall failed")

    try:
        write_report(report, output)
    except OSError:
        _fail("report write failed")


@app.command("compare")
def compare(
    baseline: Annotated[Path, typer.Option(help="Path to the baseline report.")],
    candidate: Annotated[Path, typer.Option(help="Path to the candidate report.")],
    output: Annotated[Path, typer.Option(help="Destination for the comparison.")],
) -> None:
    """Compare compatible completed reports in percentage points."""
    try:
        before = RunReport.model_validate_json(baseline.read_bytes())
        after = RunReport.model_validate_json(candidate.read_bytes())
        comparison = compare_reports(before, after)
    except (ValueError, OSError):
        _fail("invalid or incompatible evaluation reports")

    try:
        write_report(comparison, output)
    except OSError:
        _fail("report write failed")


@app.command("reflect")
def reflect(
    cases: Annotated[Path, typer.Option(help="Case set under the local data directory.")],
    output: Annotated[Path, typer.Option(help="Paired report under the local data directory.")],
) -> None:
    """Compare recall and reflection on a private case set."""
    try:
        private = Path.cwd().resolve() / "data"
        cases, output = cases.resolve(strict=True), output.resolve()
        if (
            private.resolve() != private
            or private not in cases.parents
            or private not in output.parents
            or output == cases
            or not cases.is_file()
        ):
            raise ValueError("invalid private paths")
        case_set = ReflectCaseSet.model_validate_json(cases.read_bytes())
    except (ValueError, OSError):
        _fail("invalid reflection evaluation input")

    report = anyio.run(run_reflect, case_set)
    try:
        write_report(report, output, exclude_none=True)
    except OSError:
        _fail("report write failed")
    if report.has_errors:
        _fail("reflection evaluation failed")
