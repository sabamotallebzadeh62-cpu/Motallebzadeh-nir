"""Totals per stage, rebuilt from the per-call JSONL records.

A call without reported usage is NOT counted as zero: the token sums cover only calls with
reported usage, and `n_unknown_usage` says how many calls are missing from them.
"""

from dataclasses import dataclass
from pathlib import Path

from motallebzadeh_nir.call_records import CallRecord, Stage
from motallebzadeh_nir.extraction_types import Status


@dataclass(frozen=True)
class StageSummary:
    stage: Stage
    n_calls: int
    n_failed: int
    n_retries: int
    n_unknown_usage: int
    input_tokens_reported: int
    output_tokens_reported: int
    latency_s: float


def read_records(path: Path) -> list[CallRecord]:
    """Read one JSONL file; a missing file means no calls in that stage."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [CallRecord.model_validate_json(line) for line in fh if line.strip()]


def summarize(records: list[CallRecord], stage: Stage) -> StageSummary:
    """Totals for one stage. Failed attempts and retries are included."""
    in_tokens = 0
    out_tokens = 0
    unknown = 0
    for rec in records:
        if rec.usage.input_tokens is None or rec.usage.output_tokens is None:
            unknown += 1
        if rec.usage.input_tokens is not None:
            in_tokens += rec.usage.input_tokens
        if rec.usage.output_tokens is not None:
            out_tokens += rec.usage.output_tokens
    return StageSummary(
        stage=stage,
        n_calls=len(records),
        n_failed=sum(r.status is Status.FAILED for r in records),
        n_retries=sum(r.attempt > 1 for r in records),
        n_unknown_usage=unknown,
        input_tokens_reported=in_tokens,
        output_tokens_reported=out_tokens,
        latency_s=sum(r.latency_s for r in records),
    )


def summarize_run(run_dir: Path) -> dict[Stage, StageSummary]:
    """One summary per stage, each read from its own JSONL file."""
    return {
        stage: summarize(read_records(run_dir / f"{stage.value}.jsonl"), stage) for stage in Stage
    }
