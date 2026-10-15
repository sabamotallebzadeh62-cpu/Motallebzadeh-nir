"""Call accounting: retry, missing usage and stage separation, with mocked model calls."""

from collections.abc import Callable
from pathlib import Path

import pytest

from motallebzadeh_nir.call_logging import CallLogger
from motallebzadeh_nir.call_records import Stage
from motallebzadeh_nir.call_summary import summarize_run
from motallebzadeh_nir.extraction_types import Usage


def _call(
    logger: CallLogger,
    stage: Stage,
    call_id: str,
    attempt: int,
    fn: Callable[[], tuple[object, Usage]],
) -> object:
    return logger.call(
        fn,
        stage=stage,
        document_id="d1",
        chunk_id="c1",
        method="single_prompt",
        node="node_a",
        call_id=call_id,
        attempt=attempt,
        model_id="mock-model",
        prompt_version="v1",
    )


def _fail() -> tuple[object, Usage]:
    raise RuntimeError("mock API error")


def test_success_is_recorded(tmp_path: Path) -> None:
    logger = CallLogger(tmp_path, "run1")
    _call(
        logger,
        Stage.EXTRACTION,
        "c-1",
        1,
        lambda: ("ok", Usage(input_tokens=100, output_tokens=20)),
    )
    s = summarize_run(tmp_path / "run1")[Stage.EXTRACTION]
    assert s.n_calls == 1
    assert s.n_failed == 0
    assert s.input_tokens_reported == 100
    assert s.output_tokens_reported == 20
    assert s.n_unknown_usage == 0


def test_retry_cost_is_kept(tmp_path: Path) -> None:
    logger = CallLogger(tmp_path, "run1")
    with pytest.raises(RuntimeError):
        _call(logger, Stage.EXTRACTION, "c-1", 1, _fail)
    _call(
        logger,
        Stage.EXTRACTION,
        "c-1",
        2,
        lambda: ("ok", Usage(input_tokens=100, output_tokens=20)),
    )
    s = summarize_run(tmp_path / "run1")[Stage.EXTRACTION]
    assert s.n_calls == 2
    assert s.n_failed == 1
    assert s.n_retries == 1
    assert s.input_tokens_reported == 100


def test_missing_usage_is_not_zero(tmp_path: Path) -> None:
    logger = CallLogger(tmp_path, "run1")
    _call(logger, Stage.EXTRACTION, "c-1", 1, lambda: ("ok", Usage()))
    _call(
        logger, Stage.EXTRACTION, "c-2", 1, lambda: ("ok", Usage(input_tokens=50, output_tokens=10))
    )
    s = summarize_run(tmp_path / "run1")[Stage.EXTRACTION]
    assert s.n_calls == 2
    assert s.n_unknown_usage == 1
    assert s.input_tokens_reported == 50


def test_judge_is_separate_from_extraction(tmp_path: Path) -> None:
    logger = CallLogger(tmp_path, "run1")
    _call(
        logger, Stage.EXTRACTION, "c-1", 1, lambda: ("ok", Usage(input_tokens=10, output_tokens=5))
    )
    _call(logger, Stage.JUDGE, "j-1", 1, lambda: ("ok", Usage(input_tokens=30, output_tokens=7)))
    summary = summarize_run(tmp_path / "run1")
    assert summary[Stage.EXTRACTION].input_tokens_reported == 10
    assert summary[Stage.JUDGE].input_tokens_reported == 30
    assert summary[Stage.VERIFIER].n_calls == 0
    assert (tmp_path / "run1" / "extraction.jsonl").exists()
    assert (tmp_path / "run1" / "judge.jsonl").exists()
