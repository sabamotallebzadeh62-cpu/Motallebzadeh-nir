# Pilot protocol (draft)

## Decision record

- Decision: **NO-GO** (execution blocked)
- Date: 2026-11-11
- Blockers:
  - #13: judge not yet validated against 100 manual fact assessments (hard blocker)
  - #14: KGGen adapter to the shared evaluation interface not implemented (only call documentation exists)
  - #12, #15, #16: implemented on branches, not yet merged to main; protocol cannot reference final commits
  - #17: local Qwen3-8B readiness not checked (a documented limitation would be acceptable)
  - Model access: see the access matrix; confirmation of qwen2.5-72b and gpt-oss-120b to be recorded here
- This protocol is not frozen. Nothing below may be used for evaluation until the blockers are resolved and the curator has reviewed it.

## Scope and non-claims

This pilot compares extraction methods on a small controlled sample. It cannot establish the full H1/Q2 hypotheses, 5A completion, or equal-budget superiority. Negative or inconclusive results are acceptable.

## Methods (all on the same large model)

| Config | Description | Model/checkpoint ID | Prompt hash | Commit |
|---|---|---|---|---|
| single-prompt | one extraction call | TBD | TBD | TBD |
| one-call control | extraction + verifier instructions | TBD | TBD | TBD |
| KGGen | KGGen adapter (0.4.0 pinned) | TBD | TBD | TBD |
| extraction + verifier | separate batched verifier | TBD | TBD | TBD |
| local diagnostic (conditional) | Qwen3-8B | TBD | TBD | TBD |

- Judge: TBD (candidate: gpt-oss-120b, subject to confirmed access).
- Extraction model: TBD (candidate: qwen2.5-72b, subject to confirmed access). Missing access is recorded as a blocker; no silent substitution.
- Seed: TBD (one seed for the whole pilot). Determinism settings: TBD.
- Decoding/context limits, retries, input schemas, evaluator versions: TBD.

## Data

- Development: 10 MINE articles, 30 WebNLG texts, 30 Text2KGBench sentences.
- Evaluation: 30 MINE articles (450 facts), 100 WebNLG texts, 100 Text2KGBench sentences (five ontologies).
- Exact versions and grouped IDs: TBD (manifest reference: TBD).
- Paraphrases and original triple sets are grouped; cross-benchmark overlap is checked.
- Gold triples never enter extraction inputs.
- Local diagnostic: 10 evaluation articles and 20 examples per other benchmark; never used for tuning.

## Analysis plan

- Paired comparisons per benchmark on identical inputs.
- Bootstrap grouped by source article / triple set (facts are not independent).
- H1/Q2 thresholds: TBD (copy from the roadmap).
- Failure handling: TBD.
- Extraction and judge costs reported separately; all calls logged (MLflow + per-call JSONL), unknown usage recorded explicitly.
- No prompt tuning after evaluation outputs are seen.

## Budget

- Cap: 1.5M API tokens (development, judge and retries included) and 6 T4 GPU-hours, subject to lab quota.
- Usage so far: TBD. Forecast from development runs: TBD.
- Per-call/per-run limits and retry reserve: TBD.
- If the full sample does not fit, a revised sample plan is submitted before evaluation.

## Change control

Changes to the sample, models or scientific scope require curator review (Anastasia Filatova) before execution. The protocol is not relaxed after results are seen.
