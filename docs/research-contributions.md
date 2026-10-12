# Research contributions (proposal)

Status: proposed for supervisor review. No candidate is approved. Evidence base: [docs/related-work-comparison.md](related-work-comparison.md) (six papers read in detail, four screened by abstract only). Claims I could not check in the full text are marked "not verified".

All candidates use the same fields so they can be compared: question and expected effect; closest works; remaining question; baseline, data, controlled change, measurements; contradicting outcome; main alternative explanation; what the pilot can and cannot establish; novelty status.

## Roadmap hypotheses (kept unchanged)

- H1: [CONFIRM: paste the exact wording and threshold from the topic 1.1 roadmap]
- Q2: [CONFIRM: paste the exact wording and threshold from the topic 1.1 roadmap]

The first-month pilot uses one seed, so it can describe differences but cannot establish H1 or Q2 at these thresholds. They are not replaced or relaxed here.

## Candidate 1: separate verifier versus a one-call control

**Question and expected effect.** Does a separate verification call improve extracted triples more than the same verification rules placed in the single extraction call, once realised token use is recorded? Expected: the separate verifier removes more unsupported triples, at extra token cost; whether the gain exceeds the one-call control's gain is the open point.

**Closest works.**
1. GraphJudge (Huang et al., EMNLP 2025; arXiv 2411.17388v4), Sec. 4.3-4.4 and Table 2. Establishes: filtering with a fine-tuned 7B judge improves quality over the same extractor without it (G-BS-F1 on REBEL-Sub 0.5796 vs 0.4203 without the judge; SCIERC 0.7283 vs 0.7172). Does not establish: a prompt-only verifier, a comparison with a single call carrying the same rules, or token use (not reported). Its judge needs training data and artificial negatives.
2. Ilves et al. (KaLLM @ LREC26, 2026), Sec. 3. Supports single-step and two-step extraction, but "two-step" means entities first, then relations; it is not a verification stage. The text I read reports no single-step versus two-step results (figures not checked: not verified).
3. PiVe (verifier) and SAC-KG (a plain LLM predicts triple correctness): known only from the related-work section of GraphJudge (Sec. 2). Not verified; must be read before claiming a gap.

**Remaining question.** Prompt-only verifier (no fine-tuning) versus one call with the same extraction and verification rules, same model, same documents, with tokens recorded.

**Experiment.**
- Baseline: one call that extracts and applies the verification rules; extractor-only as a second reference.
- Data: [CONFIRM: pilot dataset and number of documents from the pilot protocol, Issue #18].
- Controlled change: verification as a separate call versus inside the extraction call. Same model, same extraction instructions, same verification wording, same judge.
- Measurements: fact retention (MINE); triple count; share of triples unsupported by the text in a manual sample; realised input and output tokens per document for each arm; retention lost through verification.

**Contradicting outcome.** The one-call control matches the verifier's gain within run-to-run variation, or the verifier removes more correct facts than it removes wrong ones, or it costs more tokens with no measurable gain.

**Main alternative explanation.** Any gain may come from the extra compute (a second look) rather than from role separation. Control: report gain per token, and check whether the one-call arm with a second pass behaves like the verifier. Also rule out verifier wording and same-family judge bias.

**Pilot versus semester.** The pilot can give a paired, descriptive comparison on a small sample with realised tokens. It cannot establish significance, an equal-token-budget claim, or H1/Q2. Semester: repeated seeds, larger sample, matched token budgets, second model size.

**Novelty status.** Partly covered (GraphJudge). The narrow gap above is not verified until PiVe and SAC-KG are read.

## Candidate 2: what the verifier removes and what it introduces

**Question and expected effect.** Of the triples a verifier removes or changes, how many were correct, and what new errors does it introduce? Expected: it removes mostly unsupported triples but also a non-trivial share of correct ones.

**Closest works.**
1. GraphJudge, Table 7 (App. E). Entity recall drops slightly after judging (REBEL-Sub 0.9784 to 0.9411) while accuracy rises (0.3709 to 0.5495); entity level only, no triple-level error categories.
2. Ilves et al., Sec. 5.1-5.2. Error categories (missed, hallucinated) and a manual review of one model: 96 of 156 predicted triples were absent from the gold annotations. Shows that gold incompleteness confounds scoring. No verifier.
3. Wesslund et al. (arXiv 2602.11886), Sec. 4.3, 6.4. Measures hallucination only; recall is not measured. The judge is used for evaluation, not to filter triples.

**Remaining question.** A categorised triple-level account of removals and changes made by a verifier, labelled against the source text rather than the gold set.

**Experiment.**
- Baseline: extractor output before verification.
- Data: outputs of Candidate 1 on [CONFIRM: sample size and documents].
- Controlled change: with versus without the verifier, same extractor outputs.
- Measurements: counts of removed-correct, removed-incorrect, changed or added, unchanged-incorrect, and valid-but-missing-from-gold triples, each tied to an evidence span in the text.

**Contradicting outcome.** False removals are negligible and the verifier introduces no new error types.

**Main alternative explanation.** Gold incompleteness (Ilves et al.) and annotator judgement. Control: label against the text, record evidence spans, and add a second annotator in the semester.

**Pilot versus semester.** The pilot can inspect a small sample by hand. It cannot give stable category rates. Semester: larger sample, two annotators, agreement reported.

**Novelty status.** Not verified. Related analyses exist (above), but I did not find a triple-level removal/introduction analysis for a verifier in the papers read.

## Candidate 3: equal-token-budget comparison of role-based and single-agent extraction

**Question and expected effect.** Under an equal token budget, the same model and judge, and repeated seeds, does role-based decomposition beat a single-agent extractor? No direction is claimed.

**Closest works.** KARMA (single-agent GLM-4 baseline; baseline tokens not reported; model and architecture effects not separable, Sec. 5.4); SocraticKG (tokens per method in Table 7, but all methods are single-LLM pipelines); Tran et al. (arXiv 2604.02460; equal thinking-token budgets for multi-hop reasoning, not KG extraction; abstract only, not verified).

**Remaining question and experiment.** Same backbone, same judge, matched budget, repeated seeds, MINE fact retention, realised tokens recorded. [CONFIRM: whether the project data and compute budget allow matched budgets].

**Contradicting outcome.** The single-agent extractor matches or beats the role-based pipeline at equal budget.

**Main alternative explanation.** Prompt-engineering effort differing between arms; budget accounting differences (hidden or reasoning tokens).

**Pilot versus semester.** Not feasible in the pilot: one seed and no matched budgets. Semester only.

**Novelty status.** Not verified; MAGG (arXiv 2608.28642) was screened by abstract only and could overlap.

## Recommendation

- **Primary: Candidate 1.** It needs no training, reuses the extractor outputs the baseline already produces plus one added prompt, and the pilot can give a first paired comparison with realised tokens. [CONFIRM: fits the compute budget in Issue #18].
- **Fallback: Candidate 2.** It reuses Candidate 1's outputs and still yields findings if the main comparison is inconclusive, since it describes errors rather than testing a threshold. If gold-set effects dominate, that is itself a reportable result.
- Candidate 3 is a semester-level question and is not recommended for the pilot.

## Evidence still needed

- Read PiVe and SAC-KG (Candidate 1 novelty).
- Check Ilves et al. Fig. 2-3 for any single-step versus two-step comparison.
- Read the full text of MAGG and Tran et al. before relying on them.
- Confirm roadmap wording for H1 and Q2 and the pilot data and budget (Issue #18).
- Open the code repositories cited in the comparison table (not opened so far).