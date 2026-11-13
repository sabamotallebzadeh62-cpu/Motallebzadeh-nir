"""Single-prompt triple extraction: one chunk in, validated triples out.

The extractor does not raise for a bad model answer. It returns a record that says what
happened: ok (the graph may be empty) or failed with a reason (truncated, invalid_json,
invalid_schema, api_error). The raw answers, every HTTP attempt and its token usage are
always kept.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import openai
import yaml
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction_types import (
    Chunk,
    ExtractionResult,
    Status,
    Triple,
    Usage,
    make_triple_id,
)

REPAIR_MESSAGE = (
    "Your previous reply could not be used: {problem}. Reply again with only valid JSON "
    'of the form {{"triples": [{{"subject": "...", "predicate": "...", "object": "...", '
    '"evidence": "..."}}]}}.'
)

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

_RETRYABLE = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)


class FailureKind(StrEnum):
    """Why an extraction failed. A successful empty extraction is not a failure."""

    TRUNCATED = "truncated"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    API_ERROR = "api_error"


class ParseError(Exception):
    """The model answer cannot be turned into triples."""

    def __init__(self, kind: FailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class AttemptKind(StrEnum):
    """One HTTP request: it got a reply, or it failed before a usable reply."""

    RESPONSE = "response"
    TRANSPORT_ERROR = "transport_error"


@dataclass(frozen=True)
class AttemptRecord:
    """One HTTP request. A request that failed in transport has unknown usage."""

    kind: AttemptKind
    usage: Usage
    error: str | None = None


@dataclass(frozen=True)
class ExtractionConfig:
    """Everything about the prompt and the data that must be saved with a run.

    The model, seed, timeout and API address come from Settings (.env), not from here.
    """

    name: str
    dataset: str
    input_path: str
    prompt: str
    stage: str = "development"
    model_family: str = "llm-single-prompt"
    max_tokens: int = 2048
    temperature: float = 0.0
    max_format_repairs: int = 1  # 0 = no format-repair retry
    allowed_predicates: tuple[str, ...] = ()

    @classmethod
    def from_yaml(cls, path: Path) -> ExtractionConfig:
        with path.open(encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        raw.pop("kind", None)  # selects this run type in __main__; not a config field
        if "allowed_predicates" in raw:
            raw["allowed_predicates"] = tuple(raw["allowed_predicates"])
        return cls(**raw)

    def system_prompt(self) -> str:
        """The fixed prompt; for ontology-guided data only the allowed schema is added."""
        if not self.allowed_predicates:
            return self.prompt
        listed = ", ".join(self.allowed_predicates)
        return f"{self.prompt}\nUse only these predicates: {listed}."


@dataclass(frozen=True)
class ExtractionRecord:
    """One extraction outcome with everything needed to audit it."""

    result: ExtractionResult
    raw_responses: tuple[str, ...]
    failure_kind: FailureKind | None
    attempts: int  # all HTTP requests, including transport retries
    attempt_log: tuple[AttemptRecord, ...] = ()

    @property
    def reported_tokens(self) -> tuple[int, int]:
        """Known subtotal (input, output) over all attempts; unknown parts add nothing."""
        return reported_tokens(self.attempt_log)

    @property
    def n_unknown_usage(self) -> int:
        """Number of attempts whose input or output usage is unknown."""
        return n_unknown_usage(self.attempt_log)


def build_client(settings: Settings) -> OpenAI:
    """Client for an OpenAI-compatible API. A missing address is an explicit blocker."""
    if not settings.llm_base_url:
        raise ValueError("LLM_BASE_URL is empty: set it in .env (API access is not configured)")
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value() or "missing",
        timeout=settings.llm_timeout_s,
        max_retries=0,  # no hidden SDK retries: extract() retries and logs every request
    )


def parse_triples(document_id: str, raw: str) -> list[Triple]:
    """Turn the model answer into validated triples; raise ParseError if it cannot."""
    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(FailureKind.INVALID_JSON, f"not valid JSON ({exc})") from exc

    items = data.get("triples") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ParseError(FailureKind.INVALID_SCHEMA, 'expected an object {"triples": [...]}')

    triples: dict[str, Triple] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ParseError(FailureKind.INVALID_SCHEMA, f"triple {index} is not an object")
        cleaned: list[str] = []
        for key in ("subject", "predicate", "object"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ParseError(
                    FailureKind.INVALID_SCHEMA,
                    f"triple {index} needs non-empty subject, predicate and object",
                )
            cleaned.append(value.strip())
        subject, predicate, obj = cleaned
        evidence = item.get("evidence")
        if evidence is not None and not isinstance(evidence, str):
            raise ParseError(FailureKind.INVALID_SCHEMA, f"triple {index}: evidence is not text")
        triple_id = make_triple_id(document_id, subject, predicate, obj)
        triples.setdefault(
            triple_id,
            Triple(
                triple_id=triple_id,
                document_id=document_id,
                subject=subject,
                predicate=predicate,
                object=obj,
                evidence=evidence or None,
            ),
        )
    return list(triples.values())


def _add(first: int | None, second: int | None) -> int | None:
    return None if first is None or second is None else first + second


def add_usage(first: Usage, second: Usage) -> Usage:
    """Sum two calls; if either count is unknown the sum is unknown, never 0."""
    return Usage(
        input_tokens=_add(first.input_tokens, second.input_tokens),
        output_tokens=_add(first.output_tokens, second.output_tokens),
    )


def total_usage(log: Sequence[AttemptRecord]) -> Usage:
    """Total over all attempts; a component is unknown if any attempt left it unknown."""
    if not log:
        return Usage()
    total = log[0].usage
    for attempt in log[1:]:
        total = add_usage(total, attempt.usage)
    return total


def reported_tokens(log: Sequence[AttemptRecord]) -> tuple[int, int]:
    """Known subtotal (input, output): only what providers actually reported."""
    known_in = sum(a.usage.input_tokens or 0 for a in log)
    known_out = sum(a.usage.output_tokens or 0 for a in log)
    return known_in, known_out


def n_unknown_usage(log: Sequence[AttemptRecord]) -> int:
    """Number of attempts whose input or output token count is unknown."""
    return sum(1 for a in log if a.usage.input_tokens is None or a.usage.output_tokens is None)


def _usage(response: ChatCompletion) -> Usage:
    raw = response.usage
    if raw is None:
        return Usage()
    return Usage(input_tokens=raw.prompt_tokens, output_tokens=raw.completion_tokens)


def _failed(
    chunk: Chunk,
    settings: Settings,
    raws: list[str],
    log: list[AttemptRecord],
    kind: FailureKind,
    message: str,
) -> ExtractionRecord:
    result = ExtractionResult(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        model_id=settings.extractor_model,
        status=Status.FAILED,
        error=f"{kind.value}: {message}",
        usage=total_usage(log),
        usage_complete=n_unknown_usage(log) == 0,
    )
    return ExtractionRecord(result, tuple(raws), kind, len(log), tuple(log))


def extract(
    client: OpenAI, chunk: Chunk, cfg: ExtractionConfig, settings: Settings
) -> ExtractionRecord:
    """Extract triples from one chunk.

    Bounds: at most cfg.max_format_repairs format-repair retries, and for every request
    at most settings.llm_max_retries transport retries. Every HTTP request is logged.
    """
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": cfg.system_prompt()},
        {"role": "user", "content": chunk.text},
    ]
    if cfg.max_format_repairs < 0:
        raise ValueError("max_format_repairs must be >= 0")
    last_format_attempt = cfg.max_format_repairs + 1
    raws: list[str] = []
    log: list[AttemptRecord] = []

    for format_attempt in range(1, last_format_attempt + 1):
        transport_retries = 0
        while True:
            try:
                response = client.chat.completions.create(
                    model=settings.extractor_model,
                    messages=messages,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                    seed=settings.seed,
                )
                break
            except _RETRYABLE as exc:
                message = f"{type(exc).__name__}: {exc}"
                log.append(AttemptRecord(AttemptKind.TRANSPORT_ERROR, Usage(), message))
                if transport_retries >= settings.llm_max_retries:
                    return _failed(chunk, settings, raws, log, FailureKind.API_ERROR, message)
                transport_retries += 1
            except openai.OpenAIError as exc:
                message = f"{type(exc).__name__}: {exc}"
                log.append(AttemptRecord(AttemptKind.TRANSPORT_ERROR, Usage(), message))
                return _failed(chunk, settings, raws, log, FailureKind.API_ERROR, message)

        log.append(AttemptRecord(AttemptKind.RESPONSE, _usage(response)))
        if not response.choices:
            return _failed(chunk, settings, raws, log, FailureKind.API_ERROR, "no choices")
        choice = response.choices[0]
        raw = choice.message.content or ""
        raws.append(raw)

        if choice.finish_reason == "length":
            return _failed(chunk, settings, raws, log, FailureKind.TRUNCATED, "hit max_tokens")
        try:
            triples = parse_triples(chunk.document_id, raw)
        except ParseError as exc:
            if format_attempt == last_format_attempt:
                return _failed(chunk, settings, raws, log, exc.kind, str(exc))
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": REPAIR_MESSAGE.format(problem=exc)})
            continue

        result = ExtractionResult(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            model_id=settings.extractor_model,
            status=Status.OK,
            triples=triples,
            usage=total_usage(log),
            usage_complete=n_unknown_usage(log) == 0,
        )
        return ExtractionRecord(result, tuple(raws), None, len(log), tuple(log))

    raise AssertionError("unreachable: the loop always returns")
