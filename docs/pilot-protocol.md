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

- Commit column: none of the four method implementations is merged to main yet (single-prompt baseline on feat/extraction-baseline, one-call control in PR #34, batched verifier in PR #35, KGGen adapter not started); commits are recorded after merge.
- Judge: TBD (candidate: gpt-oss-120b, answers via the lab gateway; reasoning model, needs a large max_tokens).
- Extraction model: TBD (originally qwen2.5-72b, currently unusable; proposed qwen3.8-27b, pending curator approval). No silent substitution.
- Seed: TBD (one seed for the whole pilot). Determinism settings: TBD.
- Decoding/context limits: TBD. Retries: default llm_max_retries = 2 (src/motallebzadeh_nir/config.py); the one-call config sets max_format_repairs: 1 (PR #34, not merged). Input schemas, evaluator versions: TBD.
- Structured JSON output of the proposed models is not tested yet.

## Data

- Source: Text2KGBench, DBpedia-WebNLG part (upstream commit 50a3d255371b8817cdff70fd88459ac82b339cfe). Derived from WebNLG 3.0 (CC BY-NC-SA 4.0); research use only. No raw data is committed.
- Manifest: configs/data-manifest.json (version 1, status: proposal; ontology choice pending curator approval). SHA-256 of the ten source files is recorded there. Selection seed 42 applies to data selection only; the extraction seed is TBD.
- Ontologies (proposed): ont_3_airport, ont_4_building, ont_5_athlete, ont_11_meanoftransportation, ont_8_celestialbody.
- Text2KGBench development: 30 sentences (6 random train sentences per ontology). Evaluation: 100 sentences (20 random test sentences per ontology, excluding items that share a subject entity with a development item of the same ontology).
- Source grouping: group_id = ontology + alphabetically smallest subject entity (an approximation; upstream files have no original WebNLG IDs). The bootstrap resamples these groups. The 100 evaluation sentences fall into 40 distinct groups (airport 9, building 9, athlete 7, meanoftransportation 9, celestialbody 6); the largest group has 7 sentences, so group-level intervals will be wide.
- Not yet covered: MINE (10 development articles, 30 evaluation articles / 450 facts) and the separate WebNLG sample (30 development, 100 evaluation texts) have no manifest yet. Cross-benchmark overlap (WebNLG vs Text2KGBench, which is derived from WebNLG) has not been checked.
- Gold triples never enter extraction inputs.
- Small-model diagnostic subset: 10 evaluation MINE articles and 20 examples per other benchmark; never used for tuning. IDs: TBD.

## Analysis plan

- Paired comparisons per benchmark on identical inputs.
- Bootstrap grouped by source article / triple set (facts are not independent).
- H1/Q2 thresholds: TBD (not found in the repository; to be copied from the roadmap).
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