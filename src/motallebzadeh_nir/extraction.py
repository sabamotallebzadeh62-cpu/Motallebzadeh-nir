"""Single-prompt triple extraction: one chunk in, validated triples out.

The extractor does not raise for a bad model answer. It returns a record that says what
happened: ok (the graph may be empty) or failed with a reason (truncated, invalid_json,
invalid_schema, api_error). The raw answers and the number of attempts are always kept.
"""

from __future__ import annotations

import json
import re
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
    attempts: int


def build_client(settings: Settings) -> OpenAI:
    """Client for an OpenAI-compatible API. A missing address is an explicit blocker."""
    if not settings.llm_base_url:
        raise ValueError("LLM_BASE_URL is empty: set it in .env (API access is not configured)")
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value() or "missing",
        timeout=settings.llm_timeout_s,
        max_retries=settings.llm_max_retries,
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


def _usage(response: ChatCompletion) -> Usage:
    raw = response.usage
    if raw is None:
        return Usage()
    return Usage(input_tokens=raw.prompt_tokens, output_tokens=raw.completion_tokens)


def _failed(
    chunk: Chunk,
    settings: Settings,
    raws: list[str],
    usage: Usage | None,
    kind: FailureKind,
    message: str,
    attempts: int,
    usage_complete: bool = True,
) -> ExtractionRecord:
    result = ExtractionResult(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        model_id=settings.extractor_model,
        status=Status.FAILED,
        error=f"{kind.value}: {message}",
        usage=usage or Usage(),
        usage_complete=usage_complete,
    )
    return ExtractionRecord(result, tuple(raws), kind, attempts)


def extract(
    client: OpenAI, chunk: Chunk, cfg: ExtractionConfig, settings: Settings
) -> ExtractionRecord:
    """Extract triples from one chunk with at most one format-repair retry."""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": cfg.system_prompt()},
        {"role": "user", "content": chunk.text},
    ]
    raws: list[str] = []
    total: Usage | None = None

    for attempt in (1, 2):
        try:
            response = client.chat.completions.create(
                model=settings.extractor_model,
                messages=messages,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                seed=settings.seed,
            )
        except openai.OpenAIError as exc:
            message = f"{type(exc).__name__}: {exc}"
            return _failed(
                chunk,
                settings,
                raws,
                total,
                FailureKind.API_ERROR,
                message,
                attempt,
                usage_complete=False,
            )

        used = _usage(response)
        total = used if total is None else add_usage(total, used)
        if not response.choices:
            return _failed(
                chunk, settings, raws, total, FailureKind.API_ERROR, "no choices", attempt
            )
        choice = response.choices[0]
        raw = choice.message.content or ""
        raws.append(raw)

        if choice.finish_reason == "length":
            return _failed(
                chunk, settings, raws, total, FailureKind.TRUNCATED, "hit max_tokens", attempt
            )
        try:
            triples = parse_triples(chunk.document_id, raw)
        except ParseError as exc:
            if attempt == 2:
                return _failed(chunk, settings, raws, total, exc.kind, str(exc), attempt)
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": REPAIR_MESSAGE.format(problem=exc)})
            continue

        result = ExtractionResult(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            model_id=settings.extractor_model,
            status=Status.OK,
            triples=triples,
            usage=total,
        )
        return ExtractionRecord(result, tuple(raws), None, attempt)

    raise AssertionError("unreachable: the loop always returns")
