"""One record per model call attempt: who called what, for which input, and what it cost.

Every attempt, including a retry or a failed call, is its own record. Unknown token usage
stays None (never 0). The record has no field for credentials, so none can be stored.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from motallebzadeh_nir.extraction_types import Status, Usage


class Stage(StrEnum):
    """Which part of the pipeline made the call; costs are reported per stage."""

    EXTRACTION = "extraction"
    VERIFIER = "verifier"
    CLUSTERING = "clustering"
    JUDGE = "judge"


class CallRecord(BaseModel):
    """One attempt of one model call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    method: str = Field(min_length=1)
    node: str = Field(min_length=1)
    stage: Stage
    call_id: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    latency_s: float = Field(ge=0)
    usage: Usage = Field(default_factory=Usage)
    status: Status
    error_type: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "CallRecord":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at is earlier than started_at")
        if self.status is Status.FAILED and not self.error_type:
            raise ValueError("a failed call needs an error_type")
        if self.status is Status.OK and self.error_type is not None:
            raise ValueError("an ok call must not have an error_type")
        return self
