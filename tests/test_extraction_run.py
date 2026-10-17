"""Tests for the extraction run: nothing is dropped, failures stay visible, raw log is kept."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import openai
import pytest
from openai import OpenAI

from motallebzadeh_nir.__main__ import main
from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import ExtractionConfig
from motallebzadeh_nir.extraction_run import read_chunks, run_extraction

GOOD = '{"triples": [{"subject": "Paris", "predicate": "capital of", "object": "France"}]}'
EMPTY = '{"triples": []}'


def reply(content: str, finish: str = "stop") -> Any:
    choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)
    return SimpleNamespace(
        choices=[choice], usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    )


class FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)

    def create(self, **kwargs: Any) -> Any:
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def fake_client(replies: list[Any]) -> OpenAI:
    return cast(OpenAI, SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(replies))))


def write_chunks(path: Path, count: int) -> None:
    lines = [
        json.dumps({"document_id": f"d{i}", "chunk_id": "c1", "text": f"Text number {i}."})
        for i in range(count)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        mlflow_tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        data_dir=tmp_path / "data",
        llm_base_url="http://fake",
    )


def make_cfg(input_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        name="t", dataset="d", input_path=str(input_path), prompt="Extract triples as JSON."
    )


def test_every_chunk_gets_one_raw_line(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_chunks(chunks, 4)
    client = fake_client([reply(GOOD), reply(EMPTY), reply("{", finish="length"), reply(GOOD)])
    result = run_extraction(make_cfg(chunks), make_settings(tmp_path), client=client)

    assert (result.n_chunks, result.n_ok, result.n_empty, result.n_failed) == (4, 3, 1, 1)
    lines = [json.loads(x) for x in result.raw_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 4
    assert [x["document_id"] for x in lines] == ["d0", "d1", "d2", "d3"]
    assert lines[2]["status"] == "failed"
    assert lines[2]["failure_kind"] == "truncated"
    assert lines[2]["raw_responses"] == ["{"]
    assert lines[1]["status"] == "ok"
    assert lines[1]["triples"] == []


def test_api_error_is_kept_not_dropped(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_chunks(chunks, 2)
    client = fake_client([openai.OpenAIError("down"), reply(GOOD)])
    result = run_extraction(make_cfg(chunks), make_settings(tmp_path), client=client)

    assert (result.n_chunks, result.n_ok, result.n_failed) == (2, 1, 1)
    first = json.loads(result.raw_path.read_text(encoding="utf-8").splitlines()[0])
    assert first["failure_kind"] == "api_error"


def test_gold_triples_beside_text_are_ignored(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    row = {"document_id": "d", "chunk_id": "c", "text": "Some text.", "gold": [["a", "b", "c"]]}
    chunks.write_text(json.dumps(row) + "\n", encoding="utf-8")
    loaded = read_chunks(chunks)
    assert len(loaded) == 1
    assert not hasattr(loaded[0], "gold")


def test_bad_line_stops_with_line_number(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text('{"document_id": "d", "chunk_id": "c", "text": ""}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"chunks.jsonl:1"):
        read_chunks(chunks)


def test_duplicate_chunk_is_rejected(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    row = json.dumps({"document_id": "d", "chunk_id": "c", "text": "x"})
    chunks.write_text(f"{row}\n{row}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_chunks(chunks)


def test_empty_input_is_rejected(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no chunks"):
        read_chunks(chunks)


def test_main_reports_missing_api_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    chunks = tmp_path / "chunks.jsonl"
    write_chunks(chunks, 1)
    config = tmp_path / "extraction.yaml"
    config.write_text(
        f"kind: extraction\nname: t\ndataset: d\ninput_path: {chunks}\nprompt: Extract.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        main(["--config", str(config)])
