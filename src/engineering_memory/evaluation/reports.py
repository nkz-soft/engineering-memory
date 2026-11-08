"""Publish coverage summaries and compare compatible, internally consistent reports."""

import os
from fractions import Fraction
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from engineering_memory.evaluation.benchmark import (
    CATEGORIES,
    MIN_QUESTIONS,
    Benchmark,
    Category,
    Digest,
    EvaluationModel,
    Limit,
    QuestionOutcome,
    VersionOne,
)

PublicID = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")]
Score = Annotated[float, Field(ge=0, le=1)]


class RunProfile(EvaluationModel):
    run_id: PublicID
    engine_version: PublicID
    extractor_id: PublicID
    mission_sha256: Digest


def _mean(questions: list[QuestionOutcome]) -> Fraction:
    return sum(
        (Fraction(len(q.matched_topic_ids), len(q.expected_topic_ids)) for q in questions),
        start=Fraction(),
    ) / len(questions)


def _means(
    questions: list[QuestionOutcome],
) -> tuple[Fraction, dict[Category, Fraction]]:
    groups: dict[Category, list[QuestionOutcome]] = {category: [] for category in CATEGORIES}
    for question in questions:
        groups[question.category].append(question)
    if not all(groups.values()):
        raise ValueError("report must cover all categories")
    return _mean(questions), {category: _mean(rows) for category, rows in groups.items()}


def _display(value: Fraction) -> float:
    return float(round(value, 4))


def _layout(questions: list[QuestionOutcome]) -> list[tuple[str, Category, list[str]]]:
    return [(row.id, row.category, row.expected_topic_ids) for row in questions]


class RunReport(EvaluationModel):
    schema_version: VersionOne
    scoring_version: VersionOne
    benchmark_sha256: Digest
    corpus_sha256: Digest
    project_rules_sha256: Digest
    project_tag: Literal["project:recall-benchmark"]
    limit: Limit
    profile: RunProfile
    questions: Annotated[list[QuestionOutcome], Field(min_length=MIN_QUESTIONS)]
    overall_score: Score
    category_scores: dict[Category, Score]

    @model_validator(mode="after")
    def validate_scores(self) -> Self:
        if len({row.id for row in self.questions}) != len(self.questions):
            raise ValueError("duplicate report question ID")
        overall, categories = _means(self.questions)
        expected_scores = {category: _display(score) for category, score in categories.items()}
        if self.overall_score != _display(overall) or self.category_scores != expected_scores:
            raise ValueError("report scores do not match question outcomes")
        return self

    @classmethod
    def from_outcomes(
        cls, benchmark: Benchmark, profile: RunProfile, outcomes: list[QuestionOutcome]
    ) -> Self:
        expected = [
            (row.id, row.category, [topic.id for topic in row.topics])
            for row in benchmark.questions
        ]
        if _layout(outcomes) != expected:
            raise ValueError("incomplete benchmark outcomes")
        overall, categories = _means(outcomes)
        return cls(
            schema_version=1,
            scoring_version=1,
            benchmark_sha256=benchmark.manifest_sha256,
            corpus_sha256=benchmark.corpus_sha256,
            project_rules_sha256=benchmark.project_rules_sha256,
            project_tag=benchmark.project_tag,
            limit=benchmark.limit,
            profile=profile,
            questions=outcomes,
            overall_score=_display(overall),
            category_scores={category: _display(score) for category, score in categories.items()},
        )

    def _comparison_key(self) -> tuple:
        return (
            self.schema_version,
            self.scoring_version,
            self.benchmark_sha256,
            self.corpus_sha256,
            self.project_rules_sha256,
            self.project_tag,
            self.limit,
            _layout(self.questions),
        )


class Summary(EvaluationModel):
    profile: RunProfile
    overall_score: Score
    category_scores: dict[Category, Score]


class Comparison(EvaluationModel):
    schema_version: VersionOne
    baseline: Summary
    candidate: Summary
    overall_delta_pp: float
    category_delta_pp: dict[Category, float]


def _summary(report: RunReport) -> Summary:
    return Summary(
        profile=report.profile,
        overall_score=report.overall_score,
        category_scores=report.category_scores,
    )


def compare_reports(baseline: RunReport, candidate: RunReport) -> Comparison:
    if baseline._comparison_key() != candidate._comparison_key():
        raise ValueError("incompatible reports")
    baseline_overall, baseline_categories = _means(baseline.questions)
    candidate_overall, candidate_categories = _means(candidate.questions)
    return Comparison(
        schema_version=1,
        baseline=_summary(baseline),
        candidate=_summary(candidate),
        overall_delta_pp=_display((candidate_overall - baseline_overall) * 100),
        category_delta_pp={
            category: _display(
                (candidate_categories[category] - baseline_categories[category]) * 100
            )
            for category in CATEGORIES
        },
    )


def write_report(report: BaseModel, path: Path, *, exclude_none: bool = False) -> None:
    scratch = None
    try:
        with NamedTemporaryFile(
            dir=path.parent,
            prefix=".recall-",
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
        ) as handle:
            scratch = Path(handle.name)
            handle.write(report.model_dump_json(indent=2, exclude_none=exclude_none) + "\n")
        os.replace(scratch, path)
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)
