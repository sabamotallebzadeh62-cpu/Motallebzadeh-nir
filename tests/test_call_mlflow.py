"""Stage summaries reach MLflow, with unknown usage kept visible."""

from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

from motallebzadeh_nir.call_logging import CallLogger
from motallebzadeh_nir.call_mlflow import log_stage_summaries
from motallebzadeh_nir.call_records import Stage
from motallebzadeh_nir.call_summary import summarize_run
from motallebzadeh_nir.extraction_types import Usage


def _log_one(logger: CallLogger, stage: Stage, call_id: str, usage: Usage) -> None:
    logger.call(
        lambda: ("ok", usage),
        stage=stage,
        document_id="d1",
        chunk_id="c1",
        method="single_prompt",
        node="node_a",
        call_id=call_id,
        attempt=1,
        model_id="mock-model",
        prompt_version="v1",
    )


def test_summaries_are_logged_to_mlflow(tmp_path: Path) -> None:
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    mlflow.set_experiment("test-call-accounting")
    logger = CallLogger(tmp_path, "run1")
    _log_one(logger, Stage.EXTRACTION, "c-1", Usage(input_tokens=10, output_tokens=5))
    _log_one(logger, Stage.EXTRACTION, "c-2", Usage())
    summaries = summarize_run(tmp_path / "run1")

    with mlflow.start_run() as run:
        log_stage_summaries(summaries)

    metrics = MlflowClient().get_run(run.info.run_id).data.metrics
    assert metrics["extraction.n_calls"] == 2
    assert metrics["extraction.n_unknown_usage"] == 1
    assert metrics["extraction.input_tokens_reported"] == 10
    assert metrics["judge.n_calls"] == 0
