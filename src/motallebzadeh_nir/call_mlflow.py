"""Log per-stage call totals to the active MLflow run.

Token sums cover only calls with reported usage; `n_unknown_usage` says how many calls are
missing from them. Nothing here is a measured FLOP or a billed cost.
"""

import mlflow

from motallebzadeh_nir.call_records import Stage
from motallebzadeh_nir.call_summary import StageSummary


def log_stage_summaries(summaries: dict[Stage, StageSummary]) -> None:
    """Write one set of metrics per stage, e.g. `extraction.n_calls`, to the active run."""
    for stage, s in summaries.items():
        prefix = stage.value
        mlflow.log_metrics(
            {
                f"{prefix}.n_calls": s.n_calls,
                f"{prefix}.n_failed": s.n_failed,
                f"{prefix}.n_retries": s.n_retries,
                f"{prefix}.n_unknown_usage": s.n_unknown_usage,
                f"{prefix}.input_tokens_reported": s.input_tokens_reported,
                f"{prefix}.output_tokens_reported": s.output_tokens_reported,
                f"{prefix}.latency_s": s.latency_s,
            }
        )
