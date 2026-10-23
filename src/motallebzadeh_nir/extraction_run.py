"""Run the single-prompt extractor over a JSONL file of chunks and log the run to MLflow.

Input: one JSON object per line with `document_id`, `chunk_id` and `text`. Other keys are
ignored, so gold triples stored beside the text never reach the prompt.
Every chunk gets exactly one line in the raw log (ok, empty or failed); none is dropped.
The raw log goes to `<data_dir>/logs/<run_id>/`, which git ignores.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
from openai import OpenAI

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import (
    ExtractionConfig,
    ExtractionRecord,
    FailureKind,
    build_client,
    extract,
)
from motallebzadeh_nir.extraction_types import Chunk, Status
from motallebzadeh_nir.pipeline import current_commit


@dataclass(frozen=True)
class ExtractionRunResult:
    run_id: str
    n_chunks: int
    n_ok: int
    n_empty: int
    n_failed: int
    raw_path: Path


def read_chunks(path: Path) -> list[Chunk]:
    """Read chunks from JSONL. A bad line or a repeated ID stops the run with its line number."""
    chunks: list[Chunk] = []
    seen: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                chunk = Chunk.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: invalid chunk: {exc}") from exc
            key = (chunk.document_id, chunk.chunk_id)
            if key in seen:
                raise ValueError(f"{path}:{number}: duplicate chunk {key}")
            seen.add(key)
            chunks.append(chunk)
    if not chunks:
        raise ValueError(f"{path}: no chunks found")
    return chunks


def record_to_dict(record: ExtractionRecord) -> dict[str, Any]:
    """One raw-log line: the result plus the raw answers, failure kind and attempts."""
    data: dict[str, Any] = record.result.model_dump(mode="json")
    data["failure_kind"] = record.failure_kind.value if record.failure_kind else None
    data["attempts"] = record.attempts
    data["raw_responses"] = list(record.raw_responses)
    return data


def summarize(records: list[ExtractionRecord]) -> dict[str, float]:
    """Counts for MLflow. Unknown token usage is counted apart, never added as 0."""
    kinds = Counter(r.failure_kind.value for r in records if r.failure_kind is not None)
    unknown = sum(
        not r.result.usage_complete
        or r.result.usage.input_tokens is None
        or r.result.usage.output_tokens is None
        for r in records
    )
    metrics: dict[str, float] = {
        "n_chunks": len(records),
        "n_ok": sum(r.result.status is Status.OK for r in records),
        "n_empty": sum(r.result.status is Status.OK and not r.result.triples for r in records),
        "n_failed": sum(r.result.status is Status.FAILED for r in records),
        "n_triples": sum(len(r.result.triples) for r in records),
        "n_repair_retries": sum(r.attempts > 1 for r in records),
        "n_unknown_usage": unknown,
        "input_tokens_reported": sum(r.result.usage.input_tokens or 0 for r in records),
        "output_tokens_reported": sum(r.result.usage.output_tokens or 0 for r in records),
    }
    for kind in FailureKind:
        metrics[f"n_failed_{kind.value}"] = kinds.get(kind.value, 0)
    return metrics


def run_extraction(
    cfg: ExtractionConfig,
    settings: Settings,
    config_path: Path | None = None,
    client: OpenAI | None = None,
    pr: str = "pending",
) -> ExtractionRunResult:
    """Extract every chunk, keep every raw answer, and record the run in MLflow."""
    chunks = read_chunks(Path(cfg.input_path))
    api = client if client is not None else build_client(settings)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    with mlflow.start_run(run_name=cfg.name) as run:
        run_id = str(run.info.run_id)
        mlflow.set_tags(
            {
                "stage": cfg.stage,
                "dataset": cfg.dataset,
                "model_family": cfg.model_family,
                "commit": current_commit(),
                "pr": pr,
            }
        )
        prompt_sha = hashlib.sha256(cfg.system_prompt().encode("utf-8")).hexdigest()[:12]
        mlflow.log_params(
            {
                "seed": settings.seed,
                "model_id": settings.extractor_model,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "timeout_s": settings.llm_timeout_s,
                "sdk_max_retries": settings.llm_max_retries,
                "prompt_sha256": prompt_sha,
                "input_path": cfg.input_path,
                "n_allowed_predicates": len(cfg.allowed_predicates),
            }
        )
        if config_path is not None:
            mlflow.log_artifact(str(config_path))

        raw_path = settings.data_dir / "logs" / run_id / "extraction_raw.jsonl"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        records: list[ExtractionRecord] = []
        with raw_path.open("w", encoding="utf-8") as fh:
            for chunk in chunks:
                record = extract(api, chunk, cfg, settings)
                fh.write(json.dumps(record_to_dict(record), ensure_ascii=False) + "\n")
                fh.flush()
                records.append(record)

        metrics = summarize(records)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(raw_path))

    return ExtractionRunResult(
        run_id=run_id,
        n_chunks=int(metrics["n_chunks"]),
        n_ok=int(metrics["n_ok"]),
        n_empty=int(metrics["n_empty"]),
        n_failed=int(metrics["n_failed"]),
        raw_path=raw_path,
    )
