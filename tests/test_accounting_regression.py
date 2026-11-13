from typing import Any

import openai
from openai.types.chat import ChatCompletion
from pydantic import SecretStr

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import ExtractionConfig, build_client, extract
from motallebzadeh_nir.extraction_types import Chunk

GOOD = '{"triples": [{"subject": "Paris", "predicate": "capital_of", "object": "France"}]}'


def _settings() -> Settings:
    """Settings that never read .env: the tests must not depend on real credentials."""
    return Settings.model_construct(
        llm_base_url="http://x",
        llm_max_retries=2,
        extractor_model="test-model",
        seed=42,
    )


def _completion(
    content: str, usage: tuple[int, int] | None, finish: str = "stop"
) -> ChatCompletion:
    data: dict[str, Any] = {
        "id": "x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content},
            }
        ],
    }
    if usage is not None:
        data["usage"] = {
            "prompt_tokens": usage[0],
            "completion_tokens": usage[1],
            "total_tokens": usage[0] + usage[1],
        }
    return ChatCompletion.model_validate(data)


class _Completions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def create(self, **_: object) -> ChatCompletion:
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome  # type: ignore[no-any-return]


class _Chat:
    def __init__(self, outcomes: list[Any]) -> None:
        self.completions = _Completions(outcomes)


class _Client:
    def __init__(self, outcomes: list[Any]) -> None:
        self.chat = _Chat(outcomes)


def _run(outcomes: list[Any], repairs: int = 1) -> tuple[Any, _Client]:
    settings = _settings()
    cfg = ExtractionConfig(
        name="t", dataset="d", input_path="p", prompt="extract", max_format_repairs=repairs
    )
    chunk = Chunk(document_id="d1", chunk_id="c1", text="Paris is the capital of France.")
    client = _Client(outcomes)
    return extract(client, chunk, cfg, settings), client  # type: ignore[arg-type]


def _timeout() -> openai.APIConnectionError:
    """A transport failure that the SDK itself classifies as retryable."""
    return openai.APIConnectionError(request=None)  # type: ignore[arg-type]


def test_build_client_has_no_hidden_sdk_retries() -> None:
    settings = Settings.model_construct(
        llm_base_url="http://x",
        llm_api_key=SecretStr("test"),
        llm_timeout_s=5.0,
        llm_max_retries=2,
    )
    assert build_client(settings).max_retries == 0


def test_timeout_then_success_is_two_attempts_and_incomplete_usage() -> None:
    record, client = _run([_timeout(), _completion(GOOD, (10, 5))])
    assert client.chat.completions.calls == 2
    assert record.attempts == 2
    assert record.result.usage_complete is False
    assert record.n_unknown_usage == 1
    assert record.reported_tokens == (10, 5)


def test_known_then_unknown_keeps_known_subtotal() -> None:
    record, _ = _run([_completion("not json", (10, 5)), _completion(GOOD, None)])
    assert record.result.usage_complete is False
    assert record.n_unknown_usage == 1
    assert record.reported_tokens == (10, 5)
    assert record.result.usage.input_tokens is None


def test_unknown_then_known_keeps_known_subtotal() -> None:
    record, _ = _run([_completion("not json", None), _completion(GOOD, (7, 3))])
    assert record.result.usage_complete is False
    assert record.reported_tokens == (7, 3)


def test_all_known_is_complete() -> None:
    record, _ = _run([_completion(GOOD, (10, 5))])
    assert record.result.usage_complete is True
    assert record.n_unknown_usage == 0
    assert record.result.usage.input_tokens == 10


def test_transport_retries_are_bounded() -> None:
    record, client = _run([_timeout(), _timeout(), _timeout(), _timeout()])
    assert client.chat.completions.calls == 3  # first request + llm_max_retries=2 retries
    assert record.attempts == 3
    assert record.result.status.value == "failed"
    assert record.result.usage_complete is False
