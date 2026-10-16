# Cost accounting for model calls

Proposed for issue #9. Describes how model calls, tokens and latency are recorded.

## What is recorded

Every attempt of every model call is one record (`call_records.CallRecord`): run ID,
document and chunk ID, method, node, call ID, attempt number, model, prompt version,
start and finish time, latency, input and output tokens, status and error type.
A retry or a failed call is its own record, so retry cost is never lost.
Credentials are not part of the record.

## Where it is stored

- Per-call JSONL: `<log_dir>/<run_id>/<stage>.jsonl`, one file per stage
  (`extraction`, `verifier`, `clustering`, `judge`). Runtime logs stay in ignored storage
  and are not committed. Only small sanitised fixtures may be committed.
- MLflow: per-stage summaries as metrics, for example `extraction.n_calls` and
  `judge.input_tokens_reported`. Run config, commit and seed are logged by the run itself.

## Primary costs

Raw tokens, number of calls and latency are the primary costs. Extraction and judge
costs are always reported separately.

## Unknown usage

If the provider does not report token usage, the value is `None`, never 0.
Token sums cover only calls with reported usage. `n_unknown_usage` shows how many calls
are missing from the sums. A tokenizer estimate, if ever used, must be stored as a
separate, labelled field and must not overwrite a reported count.
If the provider hides usage completely, this limitation stays visible, and no fully
observed token comparison is claimed.

## What is only a proxy

Parameters x tokens is a rough proxy for compute. It is not measured FLOPs.

## Prices

A reference price table, if added, must carry its date and stay separate from actual
billed or GPU cost. Public prices are reference values, not measured cost.

## Reconciliation

Totals are always rebuilt from the per-call records (`call_summary.summarize_run`),
not kept as a separate running counter.
