# Pilot protocol (draft)

## Decision record

- Decision: **NO-GO** (execution blocked)
- Date: 2026-11-11
- Blockers:
  - #13: judge not validated; no MINE development data or extraction graphs yet; API credentials and models not confirmed (hard blocker)
  - #14: KGGen adapter not implemented (only call documentation exists)
  - #12, #15, #16, #31: open PRs not yet merged; PR #34 (#15) is ready to merge pending review, its development run is blocked by missing API credentials
  - #17: no lab T4 access, so local Qwen3-8B is not planned; proposed replacement Qwen3-32B via API is pending curator approval; the original 8B requirement stays open
  - Model access: iairlab/qwen2.5-72b is listed but returns "Invalid model name"; proposed extractor replacement qwen3.8-27b is pending curator approval; no substitution is made until approved
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
| small-model diagnostic (conditional) | Qwen3-8B not planned; proposed Qwen3-32B via API, pending curator approval | TBD | TBD | TBD |

- Judge: TBD (candidate: gpt-oss-120b, answers via the lab gateway; reasoning model, needs a large max_tokens).
- Extraction model: TBD (originally qwen2.5-72b, currently unusable; proposed qwen3.8-27b, pending curator approval). No silent substitution.
- Seed: TBD (one seed for the whole pilot). Determinism settings: TBD.
- Decoding/context limits, retries, input schemas, evaluator versions: TBD.
- Structured JSON output of the proposed models is not tested yet.

## Data

- Development: 10 MINE articles, 30 WebNLG texts, 30 Text2KGBench sentences.
- Evaluation: 30 MINE articles (450 facts), 100 WebNLG texts, 100 Text2KGBench sentences (five ontologies).
- Exact versions and grouped IDs: TBD (manifest reference: TBD).
- Paraphrases and original triple sets are grouped; cross-benchmark overlap is checked.
- Gold triples never enter extraction inputs.
- Small-model diagnostic: 10 evaluation articles and 20 examples per other benchmark; never used for tuning.

## Analysis plan

- Paired comparisons per benchmark on identical inputs.
- Bootstrap grouped by source article / triple set (facts are not independent).
- H1/Q2 thresholds: TBD (copy from the roadmap).
- Failure handling: TBD.
- Extraction and judge costs reported separately; all calls logged (MLflow + per-call JSONL), unknown usage recorded explicitly.
- No prompt tuning after evaluation outputs are seen.

## Budget

- Cap: 1.5M API tokens (development, judge and retries included) and 6 T4 GPU-hours, subject to lab quota.
- Usage so far (as of 2026-11-07, issue #17): under 1,000 API tokens; 0 GPU hours (no T4 access). To be reconciled with logs.
- Forecast from development runs: TBD. Per-call/per-run limits and retry reserve: TBD.
- If the full sample does not fit, a revised sample plan is submitted before evaluation.

## Change control

Changes to the sample, models or scientific scope require curator review (Anastasia Filatova) before execution. The protocol is not relaxed after results are seen.