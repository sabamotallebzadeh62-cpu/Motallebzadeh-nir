"""Records for the batched verifier: one decision per triple, one record per model call.

A verified graph is only valid when status is ok. A failed verification never carries a
verified graph, so a broken model answer cannot look like an empty but successful result.
Unknown token usage is None, never 0.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from motallebzadeh_nir.extraction_types import Status, Triple, Usage

VERIFIER_NODE = "verifier"


class Decision(StrEnum):
    """What the source text says about one triple."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


class DecisionRecord(BaseModel):
    """The verifier's decision for one triple, traceable to the call that made it."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    triple_id: str = Field(min_length=1)
    decision: Decision
    reason: str = Field(min_length=1)
    evidence: str | None = None
    call_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_evidence(self) -> "DecisionRecord":
        if self.decision is Decision.SUPPORTED and not self.evidence:
            raise ValueError("a supported decision needs an evidence quote")
        return self


class CallRecord(BaseModel):
    """One model call (first try or retry) made by the verifier."""

    model_config = ConfigDict(frozen=True)

    call_id: str = Field(min_length=1)
    node: str = VERIFIER_NODE
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    n_triples: int = Field(ge=0)
    attempt: int = Field(ge=1)
    is_retry: bool
    usage: Usage = Field(default_factory=Usage)
    latency_s: float | None = Field(default=None, ge=0)
    outcome: str = Field(min_length=1)  # "ok" or the reason the answer was rejected


class VerificationResult(BaseModel):
    """Result of verifying all triples of one chunk."""

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    status: Status
    n_input: int = Field(ge=0)
    verified_triples: list[Triple] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    calls: list[CallRecord] = Field(default_factory=list)
    error: str | None = None
    usage: Usage = Field(default_factory=Usage)
    usage_complete: bool = True  # False if any call's consumption is unknown

    @model_validator(mode="after")
    def _check_status(self) -> "VerificationResult":
        if self.status is Status.FAILED:
            if not self.error:
                raise ValueError("a failed result needs an error message")
            if self.verified_triples:
                raise ValueError("a failed result must not contain a verified graph")
            return self

        if self.error is not None:
            raise ValueError("an ok result must not have an error")
        decided = [d.triple_id for d in self.decisions]
        if len(decided) != len(set(decided)):
            raise ValueError("a triple has more than one decision")
        if len(decided) != self.n_input:
            raise ValueError("every input triple needs exactly one decision")
        supported = {d.triple_id for d in self.decisions if d.decision is Decision.SUPPORTED}
        if {t.triple_id for t in self.verified_triples} != supported:
            raise ValueError("the verified graph must hold exactly the supported triples")
        return self
