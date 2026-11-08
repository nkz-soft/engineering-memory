from hashlib import sha256
from pathlib import Path

import pytest

from engineering_memory.evaluation.benchmark import (
    Question,
    RecallMatch,
    load_benchmark,
    score_question,
)
from engineering_memory.evaluation.reports import RunProfile, RunReport, compare_reports

DATA = Path(__file__).resolve().parents[2] / "evaluation" / "recall-v1"


def digest(text):
    return sha256(text.encode()).hexdigest()


def question():
    return Question.model_validate(
        {
            "id": "cache-layout",
            "category": "architecture-decisions",
            "query": "How does the cache work?",
            "topics": [
                {
                    "id": "layout",
                    "aliases": ["two tier"],
                    "document_ids": ["chatgpt:source"],
                },
                {
                    "id": "eviction",
                    "aliases": ["clock"],
                    "document_ids": ["chatgpt:source"],
                },
            ],
        }
    )


def test_scoring_uses_provenance_whole_tokens_and_distinct_topics():
    matches = [
        RecallMatch(document_id="chatgpt:other", content="clock"),
        RecallMatch(document_id="chatgpt:source", content="CLOCKWISE"),
        RecallMatch(document_id="chatgpt:source", content="\uff34\uff37\uff2f-tier"),
        RecallMatch(document_id="chatgpt:source", content="\uff34wo tier"),
    ]
    outcome = score_question(question(), matches)
    assert outcome.expected_topic_ids == ["layout", "eviction"]
    assert outcome.matched_topic_ids == ["layout"]
    assert outcome.score == 0.5
    assert score_question(question(), []).score == 0


@pytest.mark.parametrize("alias", ["", "   ", "***"])
def test_empty_and_tokenless_aliases_are_invalid(alias):
    raw = question().model_dump()
    raw["topics"][0]["aliases"] = [alias]
    with pytest.raises(ValueError):
        Question.model_validate(raw)


def test_published_benchmark_is_complete():
    benchmark = load_benchmark(DATA / "benchmark.json")
    assert len(benchmark.questions) >= 30
    assert len({row.category for row in benchmark.questions}) == 7


def test_benchmark_rejects_corpus_drift(tmp_path):
    for name in ("benchmark.json", "conversations.json", "projects.toml"):
        (tmp_path / name).write_bytes((DATA / name).read_bytes())
    corpus = tmp_path / "conversations.json"
    corpus.write_bytes(corpus.read_bytes() + b" ")
    with pytest.raises(ValueError):
        load_benchmark(tmp_path / "benchmark.json")


def report(run_id, *, match=False):
    benchmark = load_benchmark(DATA / "benchmark.json")
    profile = RunProfile(
        run_id=run_id,
        engine_version="1.2.0",
        extractor_id="synthetic-test-model",
        mission_sha256=digest(run_id),
    )
    outcomes = []
    for row in benchmark.questions:
        evidence = [
            RecallMatch(document_id=topic.document_ids[0], content=topic.aliases[0])
            for topic in row.topics
        ]
        outcomes.append(score_question(row, evidence if match else []))
    return RunReport.from_outcomes(benchmark, profile, outcomes)


def test_comparison_validates_keys_and_recomputes_scores():
    baseline = report("baseline", match=True)
    candidate = report("candidate")
    assert baseline.overall_score == 1
    assert candidate.overall_score == 0
    comparison = compare_reports(baseline, candidate)
    assert comparison.overall_delta_pp == -100
    assert set(comparison.category_delta_pp.values()) == {-100}

    raw = baseline.model_dump()
    raw["overall_score"] = 0
    with pytest.raises(ValueError):
        RunReport.model_validate(raw)

    raw = candidate.model_dump()
    raw["questions"][0]["id"] = "changed-question"
    with pytest.raises(ValueError):
        compare_reports(baseline, RunReport.model_validate(raw))


def test_report_rejects_untrusted_profile_fields():
    raw = report("baseline").model_dump()
    raw["profile"]["endpoint"] = "https://private.example"
    with pytest.raises(ValueError):
        RunReport.model_validate(raw)


@pytest.mark.parametrize("defect", ["missing-mapping", "invalid-role"])
def test_malformed_export_is_reported_as_invalid_input(tmp_path, defect):
    import json

    for name in ("benchmark.json", "projects.toml"):
        (tmp_path / name).write_bytes((DATA / name).read_bytes())
    if defect == "missing-mapping":
        corpus = '[{"conversation_id":"PRIVATE_SENTINEL","mapping":null}]'
    else:
        record = json.loads((DATA / "conversations.json").read_bytes())[0]
        message = next(node["message"] for node in record["mapping"].values() if node["message"])
        message["author"]["role"] = ["PRIVATE_SENTINEL"]
        corpus = json.dumps([record])
    (tmp_path / "conversations.json").write_text(corpus, encoding="utf-8")
    manifest = tmp_path / "benchmark.json"
    raw = json.loads(manifest.read_bytes())
    raw["corpus_sha256"] = digest(corpus)
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid corpus conversation") as error:
        load_benchmark(manifest)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_atomic_report_write_keeps_prior_output_on_replace_failure(tmp_path, monkeypatch):
    from engineering_memory.evaluation import reports

    destination = tmp_path / "report.json"
    destination.write_text("prior", encoding="utf-8")

    def reject_replace(*args):
        raise OSError("replace rejected")

    monkeypatch.setattr(reports.os, "replace", reject_replace)
    with pytest.raises(OSError):
        reports.write_report(report("baseline"), destination)
    assert destination.read_text(encoding="utf-8") == "prior"
    assert list(tmp_path.iterdir()) == [destination]


def test_compare_cli_writes_only_compatible_reports(tmp_path):
    from typer.testing import CliRunner

    from engineering_memory.cli import app
    from engineering_memory.evaluation.reports import Comparison

    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    output = tmp_path / "comparison.json"
    baseline.write_text(report("baseline", match=True).model_dump_json(), encoding="utf-8")
    candidate.write_text(report("candidate").model_dump_json(), encoding="utf-8")

    args = [
        "evaluate",
        "compare",
        "--baseline",
        str(baseline),
        "--candidate",
        str(candidate),
        "--output",
        str(output),
    ]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    original = output.read_bytes()
    assert Comparison.model_validate_json(original).overall_delta_pp == -100
    candidate.write_text("PRIVATE_SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert "PRIVATE_SENTINEL" not in result.output
    assert output.read_bytes() == original
