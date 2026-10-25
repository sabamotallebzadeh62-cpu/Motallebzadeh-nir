"""Offline tests for the MINE evaluator contract."""

from pathlib import Path

from motallebzadeh_nir.mine_evaluator import (
    FactResult,
    evaluate_fact,
    summarize_results,
)


def test_supported_fact_is_retained() -> None:
    calls: list[tuple[str, str]] = []

    def judge(evidence: str, fact: str) -> int:
        calls.append((evidence, fact))
        return 1

    result = evaluate_fact(
        "Ada Lovelace worked on the Analytical Engine.",
        "Ada Lovelace worked on the Analytical Engine.",
        judge,
    )

    assert result == FactResult(outcome="retained", attempts=1, response=1)
    assert calls == [
        (
            "Ada Lovelace worked on the Analytical Engine.",
            "Ada Lovelace worked on the Analytical Engine.",
        )
    ]


def test_absent_fact_is_not_retained() -> None:
    result = evaluate_fact(
        "The graph describes the Analytical Engine.",
        "Ada Lovelace was born in London.",
        lambda _evidence, _fact: 0,
    )

    assert result == FactResult(outcome="not_retained", attempts=1, response=0)


def test_empty_evidence_is_not_retained_without_calling_judge() -> None:
    def unexpected_judge(_evidence: str, _fact: str) -> int:
        raise AssertionError("The judge must not be called for empty evidence.")

    result = evaluate_fact("", "A reference fact", unexpected_judge)

    assert result == FactResult(outcome="not_retained", attempts=0)


def test_invalid_response_retries_then_fails() -> None:
    calls = 0

    def invalid_judge(_evidence: str, _fact: str) -> str:
        nonlocal calls
        calls += 1
        return "probably"

    result = evaluate_fact(
        "Graph evidence.",
        "A reference fact",
        invalid_judge,
        max_retries=2,
    )

    assert result == FactResult(
        outcome="failed",
        attempts=3,
        failure_category="invalid_response",
    )
    assert calls == 3


def test_summary_excludes_failures_from_metric_denominator() -> None:
    summary = summarize_results(
        [
            FactResult(outcome="retained", attempts=1),
            FactResult(outcome="not_retained", attempts=1),
            FactResult(
                outcome="failed",
                attempts=3,
                failure_category="invalid_response",
            ),
        ]
    )

    assert summary.eligible_count == 3
    assert summary.judged_count == 2
    assert summary.failed_count == 1
    assert summary.denominator == 2
    assert summary.retained_count == 1
    assert summary.retention_rate == 0.5
    assert summary.coverage == 2 / 3


def test_no_valid_judgments_has_undefined_retention_rate() -> None:
    summary = summarize_results(
        [FactResult(outcome="failed", attempts=3, failure_category="judge_error")]
    )

    assert summary.denominator == 0
    assert summary.retention_rate is None
    assert summary.coverage == 0.0


def test_run_report_records_summary_and_unvalidated_status(tmp_path: Path) -> None:
    import json

    from motallebzadeh_nir.mine_evaluator import FactRecord, write_run_report

    records = [
        FactRecord(
            fact_id="fact-1",
            graph_id="graph-1",
            extraction_method="method-a",
            result=FactResult(outcome="retained", attempts=1, response=1),
        ),
        FactRecord(
            fact_id="fact-2",
            graph_id="graph-1",
            extraction_method="method-a",
            result=FactResult(
                outcome="failed",
                attempts=3,
                failure_category="invalid_response",
            ),
        ),
    ]

    run_id, report_path = write_run_report(
        records,
        results_dir=tmp_path / "results",
        judge_model=None,
        prompt_version="mine-prompt-v1",
        upstream_commit="6259b4c71523ceae75dafb4acec2eb833bef8f8e",
        evaluator_version="working-tree",
    )

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))

    assert report["run_id"] == run_id
    assert report["evaluation_status"] == "unvalidated_pending_S12_calibration"
    assert report["judge"]["model"] is None
    assert report["judge"]["cost_usd"] is None
    assert report["summary"]["eligible_count"] == 2
    assert report["summary"]["judged_count"] == 1
    assert report["summary"]["failed_count"] == 1
    assert report["summary"]["denominator"] == 1
    assert report["summary"]["retention_rate"] == 1.0
    assert len(report["facts"]) == 2
    assert report["facts"][0]["response"] == 1
    assert report["facts"][1]["failure_category"] == "invalid_response"
    assert report["facts"][1]["response"] is None


def test_judge_value_error_is_recorded_as_judge_error() -> None:
    def judge(_evidence: str, _fact: str) -> int:
        raise ValueError("simulated provider failure")

    result = evaluate_fact("graph evidence", "target fact", judge, max_retries=0)

    assert result.outcome == "failed"
    assert result.failure_category == "judge_error"
    assert result.response is None


def test_invalid_judge_response_is_recorded_separately() -> None:
    result = evaluate_fact(
        "graph evidence",
        "target fact",
        lambda _evidence, _fact: "yes",
        max_retries=0,
    )

    assert result.outcome == "failed"
    assert result.failure_category == "invalid_response"
    assert result.response is None
