"""Regression tests for the review findings on the one-call control (PR #34)."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai import OpenAI

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import ExtractionConfig, FailureKind, ParseError, extract
from motallebzadeh_nir.extraction_run import read_chunks, run_extraction
from motallebzadeh_nir.extraction_types import Chunk, Status
from motallebzadeh_nir.one_call import normalise, parse_one_call, read_prepared_inputs

SOURCE = "Paris is the capital of France."
CHUNK = Chunk(document_id="d1", chunk_id="d1", text=SOURCE)
CFG = ExtractionConfig(
    name="t", dataset="d", input_path="x.jsonl", prompt="Extract.", max_format_repairs=0
)


def _answer(evidence: str | None) -> str:
    triple: dict[str, Any] = {"subject": "Paris", "predicate": "capital of", "object": "France"}
    if evidence is not None:
        triple["evidence"] = evidence
    return json.dumps({"triples": [triple]})


def test_quote_present_in_source_is_accepted() -> None:
    triples = parse_one_call("d1", _answer("Paris is the capital of France."), SOURCE)
    assert len(triples) == 1


def test_quote_that_differs_only_in_whitespace_is_accepted() -> None:
    triples = parse_one_call("d1", _answer("Paris  is the\ncapital of France."), SOURCE)
    assert len(triples) == 1


def test_missing_evidence_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_one_call("d1", _answer(None), SOURCE)


def test_empty_evidence_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_one_call("d1", _answer(""), SOURCE)


def test_evidence_not_in_source_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_one_call("d1", _answer("Paris is in Germany."), SOURCE)


def test_normalise_matches_the_paired_verifier() -> None:
    # PR #35 collapses whitespace with " ".join(text.split()); the contract must stay identical.
    assert normalise("a \n b\t c") == "a b c"


def test_empty_triple_list_is_still_valid() -> None:
    assert parse_one_call("d1", '{"triples": []}', SOURCE) == []


def _fake_client(contents: list[str]) -> OpenAI:
    def reply(content: str) -> Any:
        choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")
        return SimpleNamespace(
            choices=[choice], usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1)
        )

    replies = [reply(c) for c in contents]
    completions = SimpleNamespace(create=lambda **_: replies.pop(0))
    return cast(OpenAI, SimpleNamespace(chat=SimpleNamespace(completions=completions)))


def _settings() -> Settings:
    return Settings.model_construct(
        llm_base_url="http://x", llm_max_retries=2, extractor_model="m", seed=42
    )


def test_extract_with_one_call_parser_fails_without_evidence() -> None:
    record = extract(_fake_client([_answer(None)]), CHUNK, CFG, _settings(), parse_one_call)
    assert record.result.status is Status.FAILED
    assert record.failure_kind is FailureKind.INVALID_SCHEMA


def test_extract_with_one_call_parser_fails_for_a_false_quote() -> None:
    answer = _answer("Paris is in Germany.")
    record = extract(_fake_client([answer]), CHUNK, CFG, _settings(), parse_one_call)
    assert record.result.status is Status.FAILED


def test_extract_with_one_call_parser_accepts_a_real_quote() -> None:
    answer = _answer("Paris is the capital of France.")
    record = extract(_fake_client([answer]), CHUNK, CFG, _settings(), parse_one_call)
    assert record.result.status is Status.OK
    assert len(record.result.triples) == 1


def test_baseline_default_still_accepts_missing_evidence() -> None:
    record = extract(_fake_client([_answer(None)]), CHUNK, CFG, _settings())
    assert record.result.status is Status.OK


def _write_prepared(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_prepared_inputs_keep_the_original_ids(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(path, [{"id": "ont_3_airport_train_141", "text": "A.", "ontology": "o"}])
    chunks = read_prepared_inputs(path)
    assert chunks[0].document_id == "ont_3_airport_train_141"
    assert chunks[0].chunk_id == "ont_3_airport_train_141"
    assert chunks[0].text == "A."


def test_the_old_reader_cannot_read_prepared_data(tmp_path: Path) -> None:
    # This is the review finding: the prepared format has no document_id / chunk_id.
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(path, [{"id": "x", "text": "A.", "ontology": "o"}])
    with pytest.raises(ValueError):
        read_chunks(path)


def test_prepared_inputs_reject_a_gold_field(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(
        path, [{"id": "x", "text": "A.", "ontology": "o", "triples": [["a", "b", "c"]]}]
    )
    with pytest.raises(ValueError, match="exactly"):
        read_prepared_inputs(path)


def test_prepared_inputs_reject_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    row = {"id": "x", "text": "A.", "ontology": "o"}
    _write_prepared(path, [row, row])
    with pytest.raises(ValueError, match="duplicate"):
        read_prepared_inputs(path)


def _run_settings(tmp_path: Path) -> Settings:
    return Settings.model_construct(
        llm_base_url="http://x",
        llm_max_retries=2,
        extractor_model="m",
        seed=42,
        data_dir=tmp_path / "data",
        mlflow_tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        mlflow_experiment_name="test-one-call",
        llm_timeout_s=5.0,
    )


def test_run_with_one_call_contract_reads_prepared_data_and_keeps_ids(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(path, [{"id": "ont_3_airport_train_141", "text": SOURCE, "ontology": "o"}])
    cfg = ExtractionConfig(
        name="t",
        dataset="d",
        input_path=str(path),
        prompt="Extract.",
        max_format_repairs=0,
        contract="one_call",
    )
    client = _fake_client([_answer("Paris is the capital of France.")])
    result = run_extraction(cfg, _run_settings(tmp_path), client=client)
    assert result.n_chunks == 1
    assert result.n_ok == 1
    line = json.loads(result.raw_path.read_text(encoding="utf-8").splitlines()[0])
    assert line["document_id"] == "ont_3_airport_train_141"


def test_run_with_one_call_contract_rejects_a_triple_without_a_quote(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(path, [{"id": "x", "text": SOURCE, "ontology": "o"}])
    cfg = ExtractionConfig(
        name="t",
        dataset="d",
        input_path=str(path),
        prompt="Extract.",
        max_format_repairs=0,
        contract="one_call",
    )
    result = run_extraction(cfg, _run_settings(tmp_path), client=_fake_client([_answer(None)]))
    assert result.n_failed == 1


def test_unknown_contract_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dev_inputs.jsonl"
    _write_prepared(path, [{"id": "x", "text": SOURCE, "ontology": "o"}])
    cfg = ExtractionConfig(
        name="t", dataset="d", input_path=str(path), prompt="Extract.", contract="nope"
    )
    with pytest.raises(ValueError, match="unknown contract"):
        run_extraction(cfg, _run_settings(tmp_path), client=_fake_client([]))
