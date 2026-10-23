# Candidate research contributions

Status: the pilot has not been run. Nothing below is a result; these are plans to be tested.

## Candidate contributions

### C1. Controlled single-agent vs role-based comparison
The related-work comparison found no comparison of single-agent and role-based extraction with the same backbone, token budget, judge and repeated runs. C1 tests this with an extractor plus a separate verifier against a single-prompt extractor.
- Testable claim: separating verification from extraction improves fact retention enough to justify the extra tokens.
- Measure: MINE fact retention with a fixed judge, and tokens per method, logged separately for extractor and verifier.
- Falsified if: the quality gain is not larger than the gain from the control in C2, or the extra tokens are not justified by the gain.

### C2. One-call control
A single call that contains both the extraction and the verifier instructions.
- Testable claim: part of the gain from a separate verifier comes from the extra instructions, not from role separation.
- Measure: same metrics and token accounting as C1.
- Falsified if: the one-call control matches the separate verifier at similar token cost.

### C3. Small model with verifier vs larger model alone
- Testable claim: a small extractor with a verifier gets closer to a larger extractor's quality at lower total token cost.
- Measure: quality and total tokens for (small + verifier) vs (large alone).
- Falsified if: the larger model alone is better or cheaper.

## Choice

**Primary: C1.** It answers the main research question and the gap found in the related work. It needs only the baseline, the verifier and the existing metrics, so it fits the pilot.

**Fallback: C2.** If the verifier or the judge is unavailable, C2 can still be run with the single-prompt baseline, and it shows how much of a gain could come from prompt instructions alone.

**Later: C3.** It needs several model sizes and more budget, so it is outside the pilot.

## Pilot evidence vs later experiments

| | Pilot (first month) | Later semester work |
|---|---|---|
| Scale | small controlled sample | full samples |
| Seeds | few or single | several seeds |
| Models | limited by access and the token cap | cross-size verifier/extractor pairs |
| Baselines | single-prompt, one-call control, batched verifier | plus EDC, LLMGraphTransformer, REBEL |
| Retention metric | unvalidated until manual calibration (S12) | validated |
| Claims allowed | feasibility, direction of the effect, token costs | conclusions about the hypotheses |

The pilot cannot settle the full hypotheses. It shows whether the comparison is feasible and whether the effect is worth testing at scale.
