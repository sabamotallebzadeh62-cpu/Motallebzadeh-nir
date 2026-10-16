"""Records for LLM triple extraction: input chunk, triples, usage and result.

A valid empty graph (status ok, no triples) is different from a failed extraction
(status failed, error set). Unknown token usage is None, never 0.
"""

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Status(StrEnum):
    """OK means the call returned a valid result; the graph may still be empty."""

    OK = "ok"
    FAILED = "failed"


class Chunk(BaseModel):
    """One piece of source text. Gold references are stored elsewhere."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)



def make_triple_id(document_id: str, subject: str, predicate: str, obj: str) -> str:
    """Stable ID: the same document and triple always give the same ID."""
    import json

    parts = [part.strip().lower() for part in (document_id, subject, predicate, obj)]
    key = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]

class Triple(BaseModel):
    """One extracted fact, with optional source evidence."""

    model_config = ConfigDict(frozen=True)

    triple_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    evidence: str | None = None


class Usage(BaseModel):
    """Token counts of one call. None means the provider did not report it."""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class ExtractionResult(BaseModel):
    """Result of one extraction call for one chunk."""

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    status: Status
    triples: list[Triple] = Field(default_factory=list)
    error: str | None = None
    usage: Usage = Field(default_factory=Usage)

    @model_validator(mode="after")
    def _check_status(self) -> "ExtractionResult":
        if self.status is Status.FAILED:
            if not self.error:
                raise ValueError("a failed result needs an error message")
            if self.triples:
                raise ValueError("a failed result must not contain triples")
        elif self.error is not None:
            raise ValueError("an ok result must not have an error")

        for triple in self.triples:
            if triple.document_id != self.document_id:
                raise ValueError(
                    "triple document_id must match result document_id"
                )

        return self
