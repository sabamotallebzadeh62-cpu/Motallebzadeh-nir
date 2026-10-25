# MINE Retention Evaluator Protocol

## Status

- Implementation status: protocol specification
- Evaluation status: not validated
- Judge access: unconfirmed; do not make live judge calls until S07 confirms access
- Retention claims remain unvalidated until the manual calibration in S12 is completed

## 1. Upstream provenance

The reference implementation is `stair-lab/kg-gen`, pinned to commit:

`6259b4c71523ceae75dafb4acec2eb833bef8f8e`

Relevant upstream files:

- `experiments/MINE/README.md`
- `experiments/MINE/_1_evaluation.py`
- `src/kg_gen/kg_gen.py`, especially `KGGen.retrieve` and graph-context construction

The upstream evaluation script uses a DSPy evaluator. Its default judge is `openai/gpt-5`; this is reference behavior, not authorization to use that model in this project. The project judge must remain fixed across extraction methods. Use `gpt-oss-120b` only after S07 confirms that the intended endpoint and model are accessible.

The upstream retrieval path selects relevant graph nodes and builds evidence from graph edges and neighboring nodes. It does not establish that the full graph is always passed to the judge. Our implementation must document the exact evidence-construction mode and use the same mode for every extraction method.

## 2. Information boundary

The evaluator answers this question:

> Can the reference fact be recovered from the supplied knowledge graph evidence?

The judge may receive:
- The graph-derived evidence context.
- The reference fact being assessed.
- The fixed evaluation prompt and response-format instructions.

The judge must not receive:
- The source article or source essay.
- Source passages that reveal or restate the answer.
- Extraction-model explanations or private reasoning.
- Other information unavailable from the graph evidence.

The reference fact is a target for comparison, not evidence that the graph contains it. Keep it in a distinct input field from the graph-derived evidence. Never append the reference fact or source text to the evidence context.

## 3. Evaluation unit and outcomes

One evaluation unit is one eligible reference fact paired with one candidate graph.

Each unit must end in exactly one explicit outcome:
- `retained`: a valid judge response indicates that the graph evidence supports recovery of the fact.
- `not_retained`: a valid judge response indicates that the graph evidence does not support recovery of the fact.
- `failed`: no valid decision could be obtained, including exhausted retries, transport/API errors, or invalid responses.

A failed judgment is neither retained nor not retained. Do not silently coerce errors, malformed output, or missing responses to `0`, `false`, or `not_retained`.

The implementation must validate judge output against the agreed schema and retry only according to a documented, bounded retry policy. Preserve the final error category and attempt count. Do not log secrets or full sensitive request headers.

## 4. Fixed judge configuration

All extraction methods in a comparison must use the same:
- Judge model identifier and endpoint configuration.
- Prompt and prompt-version identifier.
- Output schema and validation rules.
- Retry policy and timeout policy.
- Evidence-construction and truncation policy.
- Evaluation code version.

Record non-secret configuration metadata with every run. Never record API keys or other credentials.

If access to the required judge cannot be confirmed, record a blocker and do not substitute an unrelated metric or an unapproved judge.

## 5. Traceability and report fields

Record a result for every eligible fact, including failures. At minimum, each record should identify:
- Run ID and extraction method.
- Graph/dataset identifier and fact identifier.
- Upstream commit and local evaluator version.
- Judge model identifier and prompt version.
- Outcome: `retained`, `not_retained`, or `failed`.
- Validated response or a safe response summary.
- Attempt count, failure category, and error details with secrets redacted.
- Token usage and estimated judge cost when returned by the provider.

The development report must include:
- `eligible_count`: all facts eligible for evaluation.
- `judged_count`: facts with a valid binary judgment (`retained` or `not_retained`).
- `failed_count`: facts for which no valid judgment was obtained.
- `denominator`: the number of valid judgments used in the reported retention rate.
- `retention_rate`: `retained_count / judged_count`, when `judged_count > 0`.
- `coverage`: `judged_count / eligible_count`, when `eligible_count > 0`.
- Judge cost, run ID, model identifier, prompt version, and failure counts.

Report the eligible-fact count separately from the valid-judgment denominator. Never conceal failures by excluding them from the report. If there are zero valid judgments, retention rate is undefined, not zero.

Store detailed run reports in ignored run storage. Commit only the reproducible protocol, tests, and a safe summary/run identifier; do not commit raw source data, credentials, or large generated artifacts.

## 6. Required fixtures

The evaluator must have deterministic tests for:
1. A fact supported by graph evidence: `retained`.
2. A fact absent from graph evidence: `not_retained`.
3. An empty graph/evidence context: handled explicitly and consistently by the protocol.
4. An invalid judge response: retried according to policy and ultimately represented as `failed` if no valid response is obtained.

Tests must use a fake/stub judge and must not require network access or credentials. A fixture passing does not establish real-model accuracy.

## 7. Validation and calibration

The evaluator is not validated merely because its code and fixtures pass. S12 must compare judge decisions with 100 manual fact assessments and record disagreements and calibration results. Until then, report retention estimates as unvalidated.

## 8. Reproduction checklist

- [ ] Confirm S07 access to the approved judge.
- [ ] Confirm dependencies S06, S08, and S10 are satisfied.
- [ ] Pin the upstream revision and local prompt/code versions.
- [ ] Run deterministic fixtures without network access.
- [ ] Run a controlled evaluation with a fixed judge configuration.
- [ ] Save detailed results to ignored run storage.
- [ ] Commit a safe summary and run ID.
- [ ] Complete S12 manual calibration before claiming validated retention.
