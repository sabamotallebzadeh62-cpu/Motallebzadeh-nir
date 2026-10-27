"""Tests for the batched verifier. A fake client replaces the real API."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

from openai import OpenAI

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction_types import (
    Chunk,
    ExtractionResult,
    Status,
    Triple,
    make_triple_id,
)
from motallebzadeh_nir.verification import verify_chunk
from motallebzadeh_nir.verification_types import Decision

SOURCE = "Marie Curie was born in Warsaw and worked in Paris."
CHUNK = Chunk(document_id="doc1", chunk_id="c1", text=SOURCE)


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


def triple(subject: str, predicate: str, obj: str) -> Triple:
    return Triple(
        triple_id=make_triple_id("doc1", subject, predicate, obj),
        document_id="doc1",
        subject=subject,
        predicate=predicate,
        object=obj,
    )


def extraction(triples: list[Triple]) -> ExtractionResult:
    return ExtractionResult(
        document_id="doc1",
        chunk_id="c1",
        model_id="extractor",
        status=Status.OK,
        triples=triples,
    )


def answer(*entries: dict[str, Any]) -> str:
    return json.dumps({"decisions": list(entries)})


def test_supported_relation_enters_verified_graph() -> None:
    born = triple("Marie Curie", "born in", "Warsaw")
    result_in = extraction([born])
    before = result_in.model_dump()
    reply = answer(
        {
            "id": born.triple_id,
            "decision": "supported",
            "reason": "stated",
            "evidence": "born in Warsaw",
        }
    )
    client, completions = make_client([response(reply)])

    record = verify_chunk(client, CHUNK, result_in, settings())

    result = record.result
    assert result.status is Status.OK
    assert [t.triple_id for t in result.verified_triples] == [born.triple_id]
    assert len(result.decisions) == 1
    assert result.decisions[0].decision is Decision.SUPPORTED
    assert result.decisions[0].call_id == result.calls[0].call_id
    assert result.calls[0].node == "verifier"
    assert len(completions.calls) == 1
    assert result_in.model_dump() == before  # the input graph is unchanged


def test_empty_input_makes_no_call() -> None:
    client, completions = make_client([])

    record = verify_chunk(client, CHUNK, extraction([]), settings())

    assert record.result.status is Status.OK
    assert record.result.n_input == 0
    assert record.result.verified_triples == []
    assert record.result.decisions == []
    assert record.result.calls == []
    assert completions.calls == []


def test_contradicted_relation_stays_in_log_only() -> None:
    right = triple("Marie Curie", "born in", "Warsaw")
    wrong = triple("Marie Curie", "born in", "Paris")
    reply = answer(
        {
            "id": right.triple_id,
            "decision": "supported",
            "reason": "stated",
            "evidence": "born in Warsaw",
        },
        {
            "id": wrong.triple_id,
            "decision": "unsupported",
            "reason": "the text says Warsaw",
            "evidence": None,
        },
    )
    client, _ = make_client([response(reply)])

    record = verify_chunk(client, CHUNK, extraction([right, wrong]), settings())

    result = record.result
    assert result.status is Status.OK
    assert [t.triple_id for t in result.verified_triples] == [right.triple_id]
    by_id = {d.triple_id: d for d in result.decisions}
    assert by_id[wrong.triple_id].decision is Decision.UNSUPPORTED
    assert set(by_id) == {right.triple_id, wrong.triple_id}  # every triple is accounted for


def test_insufficient_evidence_is_uncertain_and_not_verified() -> None:
    vague = triple("Marie Curie", "won", "Nobel Prize")
    reply = answer(
        {
            "id": vague.triple_id,
            "decision": "uncertain",
            "reason": "the text does not mention prizes",
            "evidence": None,
        }
    )
    client, _ = make_client([response(reply)])

    record = verify_chunk(client, CHUNK, extraction([vague]), settings())

    result = record.result
    assert result.status is Status.OK
    assert result.verified_triples == []
    assert result.decisions[0].decision is Decision.UNCERTAIN
    assert result.n_input == 1


def test_more_than_ten_triples_are_split_into_batches() -> None:
    many = [triple("Marie Curie", "related to", f"thing {i}") for i in range(12)]

    def unsure(batch: list[Triple]) -> str:
        return answer(
            *[
                {"id": t.triple_id, "decision": "uncertain", "reason": "no info", "evidence": None}
                for t in batch
            ]
        )

    client, completions = make_client([response(unsure(many[:10])), response(unsure(many[10:]))])

    record = verify_chunk(client, CHUNK, extraction(many), settings())

    result = record.result
    assert result.status is Status.OK
    assert len(completions.calls) == 2
    assert [c.n_triples for c in result.calls] == [10, 2]
    assert len(result.decisions) == 12
    first_prompt = completions.calls[0]["messages"][1]["content"]
    assert many[0].triple_id in first_prompt
    assert many[10].triple_id not in first_prompt  # a request holds only its own batch


def test_invalid_answer_after_retry_fails_without_a_graph() -> None:
    born = triple("Marie Curie", "born in", "Warsaw")
    client, completions = make_client([response("not json"), response("still not json")])

    record = verify_chunk(client, CHUNK, extraction([born]), settings())

    result = record.result
    assert result.status is Status.FAILED
    assert result.error is not None
    assert result.verified_triples == []
    assert result.decisions == []
    assert len(completions.calls) == 2
    assert [c.is_retry for c in result.calls] == [False, True]
    assert all(c.node == "verifier" for c in result.calls)
