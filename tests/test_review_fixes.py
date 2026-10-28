"""Regression tests for the review findings on the extraction baseline."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

from openai import OpenAI

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import ExtractionConfig, extract
from motallebzadeh_nir.extraction_run import summarize
from motallebzadeh_nir.extraction_types import Chunk, make_triple_id

GOOD = '{"triples": [{"subject": "Paris", "predicate": "capital of", "object": "France"}]}'
CHUNK = Chunk(document_id="doc1", chunk_id="c1", text="Paris is the capital of France.")
CFG = ExtractionConfig(name="t", dataset="d", input_path="x.jsonl", prompt="Extract triples.")


def reply(content: str) -> Any:
    choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1)
    return SimpleNamespace(choices=[choice], usage=usage)


class FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)

    def create(self, **kwargs: Any) -> Any:
        return self.replies.pop(0)


def run(contents: list[str], repairs: int) -> Any:
    fake = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions([reply(c) for c in contents]))
    )
    return extract(
        cast(OpenAI, fake),
        CHUNK,
        replace(CFG, max_format_repairs=repairs),
        Settings(llm_base_url="http://fake"),
    )


def test_repair_retries_count_attempts_not_chunks() -> None:
    records = [
        run([GOOD], repairs=1),  # 1 attempt, 0 repairs
        run(["bad", GOOD], repairs=1),  # 2 attempts, 1 repair
        run(["bad", "worse", GOOD], repairs=2),  # 3 attempts, 2 repairs
    ]
    assert summarize(records)["n_repair_retries"] == 3


def test_document_ids_that_differ_only_in_case_get_different_triple_ids() -> None:
    assert make_triple_id("Doc1", "a", "b", "c") != make_triple_id("doc1", "a", "b", "c")


def test_triple_text_is_still_case_and_space_insensitive() -> None:
    assert make_triple_id("d1", "Paris", "Capital_Of", "France") == make_triple_id(
        " d1 ", " paris ", "capital_of", "france"
    )
