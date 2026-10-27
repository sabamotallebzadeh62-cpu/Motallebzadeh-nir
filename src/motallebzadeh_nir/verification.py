"""Batched verifier: check extracted triples against the source text they came from.

The verifier never raises for a bad model answer. It returns a VerificationResult that is
ok (every triple has exactly one decision) or failed with a reason. Only triples labelled
`supported` enter the verified graph; the others stay in the decision log unchanged.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum

import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from motallebzadeh_nir.config import Settings
from motallebzadeh_nir.extraction import add_usage
from motallebzadeh_nir.extraction_types import Chunk, ExtractionResult, Status, Triple, Usage
from motallebzadeh_nir.verification_types import (
    CallRecord,
    Decision,
    DecisionRecord,
    VerificationResult,
)

PROMPT_VERSION = "verifier-v1"
MAX_BATCH_SIZE = 10

SYSTEM_PROMPT = (
    "You check facts extracted from a text. You get the source text and a numbered list of "
    "triples (subject, predicate, object). For each triple decide using ONLY the source text, "
    "never your own knowledge:\n"
    '- "supported": the text states the fact. Give an exact quote from the text as evidence.\n'
    '- "unsupported": the text contradicts the fact or does not say it.\n'
    '- "uncertain": the text is ambiguous or only partly covers the fact.\n'
    "Give a short reason for every triple. Reply with only valid JSON of the form "
    '{"decisions": [{"id": "...", "decision": "supported|unsupported|uncertain", '
    '"reason": "...", "evidence": "exact quote or null"}]} '
    "with exactly one entry for every id you were given and no other ids."
)

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class RejectKind(StrEnum):
    """Why a verifier answer was rejected."""

    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    MISSING_IDS = "missing_ids"
    EXTRA_IDS = "extra_ids"
    DUPLICATE_IDS = "duplicate_ids"
    BAD_EVIDENCE = "bad_evidence"


class VerifierParseError(Exception):
    """The model answer cannot be accepted as one decision per requested triple."""

    def __init__(self, kind: RejectKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class ParsedDecision:
    triple_id: str
    decision: Decision
    reason: str
    evidence: str | None


def _normalise(text: str) -> str:
    """Collapse whitespace so a quote that only differs in line breaks still matches."""
    return " ".join(text.split())


def parse_decisions(raw: str, requested_ids: list[str], source_text: str) -> list[ParsedDecision]:
    """Validate one model answer; raise VerifierParseError if it cannot be accepted."""
    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VerifierParseError(RejectKind.INVALID_JSON, f"not valid JSON ({exc})") from exc

    items = data.get("decisions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise VerifierParseError(
            RejectKind.INVALID_SCHEMA, 'expected an object {"decisions": [...]}'
        )

    parsed: list[ParsedDecision] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise VerifierParseError(RejectKind.INVALID_SCHEMA, f"entry {index} is not an object")
        triple_id = item.get("id")
        reason = item.get("reason")
        evidence = item.get("evidence")
        if not isinstance(triple_id, str) or not triple_id:
            raise VerifierParseError(RejectKind.INVALID_SCHEMA, f"entry {index} has no id")
        if not isinstance(reason, str) or not reason.strip():
            raise VerifierParseError(RejectKind.INVALID_SCHEMA, f"entry {index} has no reason")
        try:
            raw_decision = item.get("decision")
            if not isinstance(raw_decision, str):
                raise ValueError("decision is not text")
            decision = Decision(raw_decision)
        except ValueError as exc:
            raise VerifierParseError(
                RejectKind.INVALID_SCHEMA, f"entry {index} has an unknown decision"
            ) from exc
        if evidence is not None and not isinstance(evidence, str):
            raise VerifierParseError(RejectKind.INVALID_SCHEMA, f"entry {index}: evidence not text")
        parsed.append(ParsedDecision(triple_id, decision, reason.strip(), evidence or None))

    seen: set[str] = set()
    for entry in parsed:
        if entry.triple_id in seen:
            raise VerifierParseError(RejectKind.DUPLICATE_IDS, f"id {entry.triple_id} repeated")
        seen.add(entry.triple_id)
    extra = seen - set(requested_ids)
    if extra:
        raise VerifierParseError(RejectKind.EXTRA_IDS, f"ids not requested: {sorted(extra)}")
    missing = set(requested_ids) - seen
    if missing:
        raise VerifierParseError(RejectKind.MISSING_IDS, f"ids not answered: {sorted(missing)}")

    source = _normalise(source_text)
    for entry in parsed:
        if entry.decision is not Decision.SUPPORTED:
            continue
        if not entry.evidence or _normalise(entry.evidence) not in source:
            raise VerifierParseError(
                RejectKind.BAD_EVIDENCE, f"id {entry.triple_id}: quote is not in the source text"
            )
    return parsed


REPAIR_MESSAGE = (
    "Your previous reply could not be used: {problem}. Reply again with only valid JSON "
    'of the form {{"decisions": [{{"id": "...", "decision": "supported|unsupported|uncertain", '
    '"reason": "...", "evidence": "exact quote or null"}}]}} '
    "with exactly one entry for every id you were given."
)


@dataclass(frozen=True)
class VerificationRecord:
    """One verification outcome with everything needed to audit it."""

    result: VerificationResult
    raw_responses: tuple[str, ...]
    failure_kind: str | None


def _batches(triples: list[Triple], size: int = MAX_BATCH_SIZE) -> list[list[Triple]]:
    return [triples[i : i + size] for i in range(0, len(triples), size)]


def _user_message(source_text: str, batch: list[Triple]) -> str:
    listed = "\n".join(f"{t.triple_id}: ({t.subject}; {t.predicate}; {t.object})" for t in batch)
    return f"Source text:\n{source_text}\n\nTriples:\n{listed}"


def _response_usage(response: ChatCompletion) -> Usage:
    raw = response.usage
    if raw is None:
        return Usage()
    return Usage(input_tokens=raw.prompt_tokens, output_tokens=raw.completion_tokens)


def _usage_known(usage: Usage) -> bool:
    return usage.input_tokens is not None and usage.output_tokens is not None


def _call_record(
    chunk: Chunk,
    settings: Settings,
    n_triples: int,
    call_id: str,
    attempt: int,
    usage: Usage,
    latency_s: float,
    outcome: str,
) -> CallRecord:
    return CallRecord(
        call_id=call_id,
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        model_id=settings.extractor_model,
        prompt_version=PROMPT_VERSION,
        n_triples=n_triples,
        attempt=attempt,
        is_retry=attempt > 1,
        usage=usage,
        latency_s=latency_s,
        outcome=outcome,
    )


def _failed_record(
    chunk: Chunk,
    settings: Settings,
    n_input: int,
    kind: str,
    message: str,
    calls: list[CallRecord],
    raws: list[str],
    usage: Usage | None,
    usage_complete: bool = True,
) -> VerificationRecord:
    result = VerificationResult(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        model_id=settings.extractor_model,
        prompt_version=PROMPT_VERSION,
        status=Status.FAILED,
        n_input=n_input,
        calls=calls,
        error=f"{kind}: {message}",
        usage=usage or Usage(),
        usage_complete=usage_complete,
    )
    return VerificationRecord(result, tuple(raws), kind)


def verify_chunk(
    client: OpenAI,
    chunk: Chunk,
    extraction: ExtractionResult,
    settings: Settings,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    max_format_repairs: int = 1,
) -> VerificationRecord:
    """Verify the triples of one chunk in batches of at most MAX_BATCH_SIZE.

    The extraction result is never changed. A rejected answer is retried at most
    max_format_repairs times; if it is still invalid the whole chunk is failed.
    """
    if max_format_repairs < 0:
        raise ValueError("max_format_repairs must be >= 0")
    triples = list(extraction.triples)
    n_input = len(triples)

    if extraction.status is Status.FAILED:
        message = f"the extraction failed ({extraction.error})"
        return _failed_record(chunk, settings, n_input, "extraction_failed", message, [], [], None)
    if (extraction.document_id, extraction.chunk_id) != (chunk.document_id, chunk.chunk_id):
        message = "the extraction result does not belong to this chunk"
        return _failed_record(chunk, settings, n_input, "invalid_input", message, [], [], None)
    ids = [t.triple_id for t in triples]
    if len(ids) != len(set(ids)):
        message = "the input has repeated triple ids"
        return _failed_record(chunk, settings, n_input, "invalid_input", message, [], [], None)

    calls: list[CallRecord] = []
    raws: list[str] = []
    total: Usage | None = None
    complete = True
    answers: dict[str, tuple[ParsedDecision, str]] = {}
    last_attempt = max_format_repairs + 1

    for batch in _batches(triples):
        batch_ids = [t.triple_id for t in batch]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_message(chunk.text, batch)},
        ]
        for attempt in range(1, last_attempt + 1):
            call_id = uuid.uuid4().hex[:12]
            started = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=settings.extractor_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    seed=settings.seed,
                )
            except openai.OpenAIError as exc:
                latency = time.perf_counter() - started
                calls.append(
                    _call_record(
                        chunk, settings, len(batch), call_id, attempt, Usage(), latency, "api_error"
                    )
                )
                message = f"{type(exc).__name__}: {exc}"
                return _failed_record(
                    chunk, settings, n_input, "api_error", message, calls, raws, total, False
                )

            latency = time.perf_counter() - started
            used = _response_usage(response)
            total = used if total is None else add_usage(total, used)
            complete = complete and _usage_known(used)

            if not response.choices:
                calls.append(
                    _call_record(
                        chunk, settings, len(batch), call_id, attempt, used, latency, "no_choices"
                    )
                )
                return _failed_record(
                    chunk,
                    settings,
                    n_input,
                    "api_error",
                    "no choices",
                    calls,
                    raws,
                    total,
                    complete,
                )
            choice = response.choices[0]
            raw = choice.message.content or ""
            raws.append(raw)

            if choice.finish_reason == "length":
                calls.append(
                    _call_record(
                        chunk, settings, len(batch), call_id, attempt, used, latency, "truncated"
                    )
                )
                return _failed_record(
                    chunk,
                    settings,
                    n_input,
                    "truncated",
                    "hit max_tokens",
                    calls,
                    raws,
                    total,
                    complete,
                )
            try:
                parsed = parse_decisions(raw, batch_ids, chunk.text)
            except VerifierParseError as exc:
                calls.append(
                    _call_record(
                        chunk, settings, len(batch), call_id, attempt, used, latency, exc.kind.value
                    )
                )
                if attempt == last_attempt:
                    return _failed_record(
                        chunk,
                        settings,
                        n_input,
                        exc.kind.value,
                        str(exc),
                        calls,
                        raws,
                        total,
                        complete,
                    )
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": REPAIR_MESSAGE.format(problem=exc)})
                continue

            calls.append(
                _call_record(chunk, settings, len(batch), call_id, attempt, used, latency, "ok")
            )
            for entry in parsed:
                answers[entry.triple_id] = (entry, call_id)
            break

    decisions = [
        DecisionRecord(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            triple_id=t.triple_id,
            decision=answers[t.triple_id][0].decision,
            reason=answers[t.triple_id][0].reason,
            evidence=answers[t.triple_id][0].evidence,
            call_id=answers[t.triple_id][1],
        )
        for t in triples
    ]
    verified = [
        t for t, d in zip(triples, decisions, strict=True) if d.decision is Decision.SUPPORTED
    ]
    result = VerificationResult(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        model_id=settings.extractor_model,
        prompt_version=PROMPT_VERSION,
        status=Status.OK,
        n_input=n_input,
        verified_triples=verified,
        decisions=decisions,
        calls=calls,
        usage=total or Usage(),
        usage_complete=complete,
    )
    return VerificationRecord(result, tuple(raws), None)
