"""CallLogger must reject invalid metadata before the model is called."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from motallebzadeh_nir.call_logging import CallLogger
from motallebzadeh_nir.call_records import Stage
from motallebzadeh_nir.extraction_types import Usage

VALID: dict[str, Any] = {
    "stage": Stage.EXTRACTION,
    "document_id": "doc1",
    "chunk_id": "c1",
    "method": "single-prompt",
    "node": "extractor",
    "call_id": "call-1",
    "attempt": 1,
    "model_id": "m",
    "prompt_version": "v1",
}


@pytest.mark.parametrize(
    "bad",
    [{"attempt": 0}, {"call_id": ""}, {"document_id": ""}, {"model_id": ""}],
)
def test_invalid_metadata_never_calls_the_model(tmp_path: Path, bad: dict[str, Any]) -> None:
    logger = CallLogger(tmp_path, "run1")
    calls: list[int] = []

    def fn() -> tuple[object, Usage]:
        calls.append(1)
        return "answer", Usage(input_tokens=1, output_tokens=1)

    with pytest.raises(ValidationError):
        logger.call(fn, **{**VALID, **bad})
    assert calls == []
    assert not logger.path_for(Stage.EXTRACTION).exists()


def test_provider_error_is_not_masked_and_is_logged(tmp_path: Path) -> None:
    logger = CallLogger(tmp_path, "run1")

    def fn() -> tuple[object, Usage]:
        raise RuntimeError("provider down")

    with pytest.raises(RuntimeError, match="provider down"):
        logger.call(fn, **VALID)
    lines = logger.path_for(Stage.EXTRACTION).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert '"status":"failed"' in lines[0]
