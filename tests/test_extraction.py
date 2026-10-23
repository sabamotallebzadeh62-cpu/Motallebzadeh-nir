"""Tests for the single-prompt extractor. A fake client replaces the real API."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import openai
import pytest
from openai import OpenAI

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import (
    ExtractionConfig,
    FailureKind,
    ParseError,
    build_client,
    extract,
    parse_triples,
)
from motallebzadeh_nir.extraction_types import Chunk, Status

GOOD = '{"triples": [{"subject": "Paris", "predicate": "capital of", "object": "France"}]}'
CHUNK = Chunk(document_id="doc1", chunk_id="c1", text="Paris is the capital of France.")
CFG = ExtractionConfig(
    name="t", dataset="d", input_path="x.jsonl", prompt="Extract triples as JSON."
)


def response(content: str, finish: str = "stop", tokens: tuple[int, int] | None = (10, 5)) -> Any:
    usage = None
    if tokens is not None:
        usage = SimpleNamespace(prompt_tokens=tokens[0], completion_tokens=tokens[1])
    choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)
    return SimpleNamespace(choices=[choice], usage=usage)


class FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def make_client(replies: list[Any]) -> tuple[OpenAI, FakeCompletions]:
    completions = FakeCompletions(replies)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return cast(OpenAI, fake), completions


def settings() -> Settings:
    return Settings(llm_base_url="http://fake")


def test_parse_valid() -> None:
    triples = parse_triples("doc1", GOOD)
    assert len(triples) == 1
    assert triples[0].subject == "Paris"
    assert triples[0].document_id == "doc1"


def test_parse_fenced_json() -> None:
    assert len(parse_triples("doc1", f"```json\n{GOOD}\n```")) == 1


def test_parse_empty_list_is_valid() -> None:
    assert parse_triples("doc1", '{"triples": []}') == []


def test_parse_removes_duplicates() -> None:
    item = '{"subject": "A", "predicate": "p", "object": "B"}'
    assert len(parse_triples("doc1", f'{{"triples": [{item}, {item}]}}')) == 1


def test_parse_invalid_json() -> None:
    with pytest.raises(ParseError) as info:
        parse_triples("doc1", "not json")
    assert info.value.kind is FailureKind.INVALID_JSON


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        '{"facts": []}',
        '{"triples": [1]}',
        '{"triples": [{"subject": "A", "predicate": "p"}]}',
        '{"triples": [{"subject": " ", "predicate": "p", "object": "B"}]}',
    ],
)
def test_parse_invalid_schema(raw: str) -> None:
    with pytest.raises(ParseError) as info:
        parse_triples("doc1", raw)
    assert info.value.kind is FailureKind.INVALID_SCHEMA


def test_extract_success() -> None:
    client, comps = make_client([response(GOOD)])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.OK
    assert len(record.result.triples) == 1
    assert record.failure_kind is None
    assert record.attempts == 1
    assert record.raw_responses == (GOOD,)
    assert record.result.usage.input_tokens == 10
    assert comps.calls[0]["seed"] == 42


def test_extract_empty_graph_is_ok_not_failed() -> None:
    client, _ = make_client([response('{"triples": []}')])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.OK
    assert record.result.triples == []
    assert record.failure_kind is None


def test_extract_truncated() -> None:
    client, _ = make_client([response('{"triples": [', finish="length")])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.FAILED
    assert record.failure_kind is FailureKind.TRUNCATED
    assert record.raw_responses == ('{"triples": [',)


def test_extract_repairs_once_and_sums_usage() -> None:
    client, comps = make_client([response("oops", tokens=(10, 5)), response(GOOD, tokens=(20, 6))])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.OK
    assert record.attempts == 2
    assert record.raw_responses == ("oops", GOOD)
    assert record.result.usage.input_tokens == 30
    assert record.result.usage.output_tokens == 11
    assert len(comps.calls) == 2


def test_extract_gives_up_after_one_repair() -> None:
    client, comps = make_client([response("bad"), response("still bad")])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.FAILED
    assert record.failure_kind is FailureKind.INVALID_JSON
    assert record.attempts == 2
    assert record.raw_responses == ("bad", "still bad")
    assert len(comps.calls) == 2


def test_extract_api_error_is_recorded() -> None:
    client, _ = make_client([openai.OpenAIError("boom")])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.FAILED
    assert record.failure_kind is FailureKind.API_ERROR
    assert record.result.error is not None
    assert "boom" in record.result.error


def test_api_error_after_reported_usage_is_marked_incomplete() -> None:
    client, comps = make_client(
        [response("oops", tokens=(10, 5)), openai.APITimeoutError(request=cast(Any, None))]
    )
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.status is Status.FAILED
    assert record.failure_kind is FailureKind.API_ERROR
    assert record.attempts == 2
    assert record.result.usage.input_tokens == 10
    assert record.result.usage.output_tokens == 5
    assert record.result.usage_complete is False
    assert len(comps.calls) == 2


def test_usage_is_complete_when_every_request_reported() -> None:
    client, _ = make_client([response("oops", tokens=(10, 5)), response(GOOD, tokens=(20, 6))])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.usage_complete is True


def test_unknown_usage_stays_unknown() -> None:
    client, _ = make_client([response(GOOD, tokens=None)])
    record = extract(client, CHUNK, CFG, settings())
    assert record.result.usage.input_tokens is None
    assert record.result.usage.output_tokens is None


def test_ontology_schema_goes_into_prompt() -> None:
    cfg = ExtractionConfig(
        name="t",
        dataset="d",
        input_path="x.jsonl",
        prompt="Extract.",
        allowed_predicates=("birthPlace", "author"),
    )
    client, comps = make_client([response(GOOD)])
    extract(client, CHUNK, cfg, settings())
    system = comps.calls[0]["messages"][0]["content"]
    assert "birthPlace" in system
    assert "author" in system


def test_build_client_needs_base_url() -> None:
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        build_client(Settings(llm_base_url=""))
