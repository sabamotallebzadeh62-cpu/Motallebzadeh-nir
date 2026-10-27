# One-call control vs two-step method — prompt differences

Issue: #15 (one-call control with verifier instructions)

## Same across both methods
- Source text: same development data (`data/dev/text2kgbench_dev_chunks.jsonl`)
- Allowed schema: same triple schema (subject, predicate, object, evidence)
- Model: same model, resolved from `.env` (not hard-coded in the config)
- Final output contract: `{"triples": [{"subject","predicate","object","evidence"}]}`
- Verification rules: supported / unsupported / uncertain, source text only, exact evidence quote

## Different (execution structure only)
- Two-step: one extraction call, then a separate verifier call over the candidates
- One-call: extraction and verification rules are combined in a single prompt, with one normal
  generation call that checks its candidate triples before returning the final supported triples
- `max_format_repairs: 1` is a bounded format-repair retry. Any retry is counted and disclosed;
  no equal-budget claim is made between the two methods.

## Explicitly not added
- No entity canonicalization
- No relation renaming
- No external evidence or facts beyond the given text

This keeps the comparison about execution structure, not about extra canonicalization or
external evidence.
