"""Wrap a model call so every attempt is written to a per-stage JSONL file."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from motallebzadeh_nir.call_records import CallRecord, Stage
from motallebzadeh_nir.extraction_types import Status, Usage


class CallLogger:
    """Writes one JSON line per attempt to `<log_dir>/<run_id>/<stage>.jsonl`."""

    def __init__(self, log_dir: Path, run_id: str) -> None:
        self.run_id = run_id
        self.dir = log_dir / run_id
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, stage: Stage) -> Path:
        return self.dir / f"{stage.value}.jsonl"

    def write(self, record: CallRecord) -> None:
        with self.path_for(record.stage).open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")

    def call(
        self,
        fn: Callable[[], tuple[object, Usage]],
        *,
        stage: Stage,
        document_id: str,
        chunk_id: str,
        method: str,
        node: str,
        call_id: str,
        attempt: int,
        model_id: str,
        prompt_version: str,
    ) -> object:
        """Run `fn` once, log the attempt (ok or failed), return its result.

        `fn` returns (result, usage). On an exception a failed record is written
        and the exception is raised again, so the caller decides about retries.
        """
        started = datetime.now(UTC)
        t0 = perf_counter()
        try:
            result, usage = fn()
        except Exception as exc:
            self._log(started, t0, Status.FAILED, Usage(), type(exc).__name__, locals())
            raise
        self._log(started, t0, Status.OK, usage, None, locals())
        return result

    def _log(
        self,
        started: datetime,
        t0: float,
        status: Status,
        usage: Usage,
        error_type: str | None,
        ctx: dict[str, object],
    ) -> None:
        self.write(
            CallRecord(
                run_id=self.run_id,
                document_id=str(ctx["document_id"]),
                chunk_id=str(ctx["chunk_id"]),
                method=str(ctx["method"]),
                node=str(ctx["node"]),
                stage=Stage(str(ctx["stage"])),
                call_id=str(ctx["call_id"]),
                attempt=int(str(ctx["attempt"])),
                model_id=str(ctx["model_id"]),
                prompt_version=str(ctx["prompt_version"]),
                started_at=started,
                finished_at=datetime.now(UTC),
                latency_s=perf_counter() - t0,
                usage=usage,
                status=status,
                error_type=error_type,
            )
        )
