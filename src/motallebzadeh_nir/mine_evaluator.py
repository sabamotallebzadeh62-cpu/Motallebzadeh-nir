"""Deterministic MINE retention evaluation contract.

This module deliberately does not implement a live LLM client. Inject a judge
callable after the approved model and endpoint have been confirmed.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

Outcome = Literal["retained", "not_retained", "failed"]
Judge = Callable[[str, str], object]


@dataclass(frozen=True)
class FactResult:
    """Traceable outcome for one reference fact and one graph."""

    outcome: Outcome
    attempts: int
    failure_category: str | None = None
    response: int | None = None


@dataclass(frozen=True)
class EvaluationSummary:
    """Counts that keep failed judgments separate from the metric denominator."""

    eligible_count: int
    judged_count: int
    failed_count: int
    denominator: int
    retained_count: int
    retention_rate: float | None
    coverage: float | None


def _parse_judge_response(response: object) -> bool:
    """Accept only the binary integer output required by the judge contract."""
    if type(response) is not int or response not in (0, 1):
        raise ValueError("Judge response must be the integer 0 or 1.")
    return response == 1


def evaluate_fact(
    evidence_context: str,
    reference_fact: str,
    judge: Judge,
    *,
    max_retries: int = 2,
) -> FactResult:
    """Evaluate recoverability from graph evidence, never from source text.

    An empty evidence context is explicitly classified as not_retained without
    calling the judge. ``max_retries`` counts retries after the initial attempt.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative.")
    if not reference_fact.strip():
        raise ValueError("reference_fact must not be empty.")

    if not evidence_context.strip():
        return FactResult(outcome="not_retained", attempts=0)

    last_failure = "judge_error"
    for attempt in range(1, max_retries + 2):
        try:
            raw_response = judge(evidence_context, reference_fact)
        except Exception:
            last_failure = "judge_error"
            continue

        try:
            retained = _parse_judge_response(raw_response)
        except ValueError:
            last_failure = "invalid_response"
            continue

        return FactResult(
            outcome="retained" if retained else "not_retained",
            attempts=attempt,
            response=1 if retained else 0,
        )

    return FactResult(
        outcome="failed",
        attempts=max_retries + 1,
        failure_category=last_failure,
    )


def summarize_results(results: Sequence[FactResult]) -> EvaluationSummary:
    """Summarize outcomes without silently dropping failed judgments."""
    eligible_count = len(results)
    judged = [result for result in results if result.outcome != "failed"]
    failed_count = eligible_count - len(judged)
    denominator = len(judged)
    retained_count = sum(result.outcome == "retained" for result in judged)

    return EvaluationSummary(
        eligible_count=eligible_count,
        judged_count=denominator,
        failed_count=failed_count,
        denominator=denominator,
        retained_count=retained_count,
        retention_rate=retained_count / denominator if denominator else None,
        coverage=denominator / eligible_count if eligible_count else None,
    )


@dataclass(frozen=True)
class FactRecord:
    """Metadata and outcome for one fact evaluated against one candidate graph."""

    fact_id: str
    graph_id: str
    extraction_method: str
    result: FactResult


def write_run_report(
    records: Sequence[FactRecord],
    *,
    results_dir: Path,
    judge_model: str | None,
    prompt_version: str,
    upstream_commit: str,
    evaluator_version: str,
    judge_cost_usd: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> tuple[str, Path]:
    """Write a traceable JSON report without inventing missing usage or cost data.

    The caller is responsible for passing graph-derived evidence to ``evaluate_fact``;
    source documents and credentials must never be included in report records.
    """
    if not prompt_version.strip():
        raise ValueError("prompt_version must not be empty.")
    if not upstream_commit.strip():
        raise ValueError("upstream_commit must not be empty.")
    if not evaluator_version.strip():
        raise ValueError("evaluator_version must not be empty.")
    if judge_cost_usd is not None and judge_cost_usd < 0:
        raise ValueError("judge_cost_usd must be non-negative.")
    if input_tokens is not None and input_tokens < 0:
        raise ValueError("input_tokens must be non-negative.")
    if output_tokens is not None and output_tokens < 0:
        raise ValueError("output_tokens must be non-negative.")

    run_id = uuid4().hex
    summary = summarize_results([record.result for record in records])
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "evaluation_status": "unvalidated_pending_S12_calibration",
        "judge": {
            "model": judge_model,
            "prompt_version": prompt_version,
            "cost_usd": judge_cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "upstream_commit": upstream_commit,
        "evaluator_version": evaluator_version,
        "summary": asdict(summary),
        "facts": [
            {
                "fact_id": record.fact_id,
                "graph_id": record.graph_id,
                "extraction_method": record.extraction_method,
                **asdict(record.result),
            }
            for record in records
        ],
    }

    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"mine-{run_id}.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return run_id, report_path
