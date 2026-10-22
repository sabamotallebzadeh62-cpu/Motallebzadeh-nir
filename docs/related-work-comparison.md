# Related work comparison

Source: docs/reading-log.md. Search date: 2026-10-07. Six papers read in detail; four screened by abstract only. Paper versions and code commits are listed in [Sources (pinned)](#sources-pinned).

## Table 1. Papers read in detail

| Work | Question | Roles / stages | Model | Dataset | Baseline | Quality metrics | Token / cost accounting | Repetitions | Code | Limitations (authors) |
|---|---|---|---|---|---|---|---|---|---|---|
| [KGGen](#sources-pinned) | Dense, high-quality KG from plain text; sparsity of OpenIE and GraphRAG graphs | One LLM, three stages: two-step extraction (entities, then triples), aggregation without LLM, entity and edge resolution (embeddings, k-means, BM25, LLM de-duplication) | Gemini 2.0 Flash via DSPy; also Claude Sonnet 3.5 and GPT-4o on MINE-1 | MINE-1 (100 articles, 15 facts each), MINE-2 on WikiQA, 100 SemEval-2010 sentences | OpenIE, GraphRAG | Fact retention (LLM judge), QA answer containment (LLM judge), manual validity of 100 triples per method | KGGen only: 5.37M tokens and $0.84 for 1M characters (Table 3); GraphRAG: time only | Not reported for MINE-1 | github.com/stair-lab/kg-gen (public repository verified) | Over- or under-de-duplication; tested on corpora up to about 5M tokens; domain-specific knowledge may be limited. |
| [KARMA](#sources-pinned) | Enrich an existing KG from scientific text | Central controller with eight to nine LLM agents: ingestion, reader, summarizer, entity, relation, schema alignment, conflict resolution, evaluator | GLM-4, GPT-4o or DeepSeek-v3 (one backbone per run); judge DeepSeek-v3 | 1,200 PubMed articles (genomics 720, proteomics 360, metabolomics 120) | Single-agent GLM-4 (one generation); ablations without summarizer, conflict resolution or evaluator | LLM-judged correctness, QA coherence, conflict ratio, coverage and connectivity gain, human score (two experts) | Token and time distributions per article (Fig. 3); no totals; baseline not reported | Not reported in the text read | github.com/YuxingLu613/KARMA (public repository verified) | Mostly LLM-based metrics; weaker on metabolomics |
| [SocraticKG](#sources-pinned) | Coverage versus connectivity in LLM-based KG construction | One LLM, three prompt stages: 5W1H QA generation, triples from each QA pair, KGGen-style canonicalization | Qwen-2.5 7B, GPT-4o-mini, GPT-4o, Gemini-2.5-Flash-Lite, Claude-4-Sonnet; MINE judge GPT-4o; HotpotQA answerer GPT-4.1 | MINE (100 articles), HotpotQA 800 Hard Bridge questions | Direct extraction, GraphRAG, KGGen, SoKG without 5W1H, Naive RAG | Fact retention, average degree, triple count, fragmentation index (NFI), HotpotQA accuracy, uniqueness, granularity, human factual precision | Total tokens up to triple extraction for every method and tokens per triple (Table 7) | Not reported (temperature 0) | github.com/LABA-SNU/SocraticKG (public repository verified) | Higher token usage; dependent on the underlying LLM; limited to binary triples. |
| [Ilves et al.](#sources-pinned) (KG-LLM @ LREC26, 2026) | How to evaluate complete typed KGs from LLMs under a closed ontology (Sec. 1, 3) | One LLM; single-step (entities and triples jointly) or two-step (entities, then relations conditioned on them); optional GLiNER for entities; no verifier or canonicalization (Sec. 3) | Gemini 3 Pro, GPT-5.1, Claude Opus 4.5, Mistral 7B via OpenRouter (Sec. 5.1, 7) | DocRED, 10 stratified documents, 6 entity types, 96 relations (Sec. 4, 5, 8) | None (compares LLMs, not methods) | Entity F1, strict triple F1 (Hungarian matching), schema violations, per-document mean/std over repeated runs (Sec. 5.1); manual review of one model (Sec. 5.2) | Not reported in text read (only latency and truncation flags, Sec. 3) | Supported (Sec. 3, 5.1); stability numbers not found in text read | github.com/SukSev/kg_benchmarking (Sec. 7; public repository verified at README level, 2026-10-18) | 10 documents; schema derived from DocRED; prompt sensitivity; manual review of one model only (Sec. 8) |
| [GraphJudge](#sources-pinned) (Huang et al., EMNLP 2025) | Reduce noise, domain-knowledge gaps and hallucination in LLM KG construction (Sec. 1) | Extractor LLM: entities, text denoising, triples (Sec. 4.2); fine-tuned 7B yes/no judge filters each triple against the denoised text (Sec. 4.3, 4.4, Alg. 1) | GPT-4o-mini extractor; LLaMA-2-7B (LoRA) judge (Sec. 5.1.3) | REBEL-Sub, GenWiki, SCIERC, Re-DocRED Windows subset (Sec. 5.1.1; abstract mentions three datasets) | GPT-4o-mini, GPT-4o, RAKG, iText2KG, KGGen, PiVe (Sec. 5.1.2) | G-BERTScore, G-BLEU, G-ROUGE accuracy/recall/F1, soft matching (Sec. 5.1.4, App. B) | Not reported; cost-effectiveness argued by model size (Sec. 5.2) | Not reported in text read | github.com/hhy-huang/GraphJudge (public, MIT; repository verified at README level, 2026-10-18) | Entity-level triples as units; quality of ground-truth KGs questionable (Sec. 7) |
| [Wesslund et al.](#sources-pinned) (2026) | Ontology-driven triple extraction from financial reports without gold data; manual vs induced ontology (Sec. 1) | One LLM call per 5-sentence chunk with ontology and examples (Sec. 4.1); ontology induced chunk by chunk (Sec. 4.2.3); regex plus LLM judge used only to measure hallucination, not to filter triples (Sec. 4.3) | Gemini-2.5 Flash, Llama 4 Maverick; judge model not named (Sec. 4.2.1, 4.3) | Volvo 2024 annual report; Elekta 2022/23, first 25% only (Sec. 4.2.2) | None from other methods (compares strict regex vs hybrid check, manual vs induced ontology) | Ontology conformance, subject/object/relation hallucination; recall not measured (Sec. 3.3, 6.4) | Not reported | Not reported (one run per configuration) | Not found in text | Two reports; Elekta partial; no recall; judge checked on 10 decisions (Sec. 5.1, 6.4) |

## Table 2. Papers screened (abstract only)

| Work | Setting (from abstract) | Everything else |
|---|---|---|
| EDC (Zhang and Soh, 2024, arXiv 2404.03868) | Open extraction, schema definition, canonicalization; optional schema retriever | Not verified; code stated in abstract: github.com/clear-nus/edc |
| MAGG (arXiv 2608.28642, authors not verified) | Multi-agent KG construction with domain-expert review | Token-count claim not verified; authors and figures not verified |
| Tran et al. (arXiv 2604.02460) | Single vs multi-agent under equal thinking-token budgets, multi-hop reasoning | Not verified; not a KG extraction task |
| Phase Transition for Budgeted Multi-Agent Synergy (arXiv 2601.17311, authors not verified) | Fixed-budget comparison theory | Not verified |

## Synthesis: what controlled comparison is missing

Authors' claims (as reported):
- KGGen reports better information retention than GraphRAG on MINE-1 and comparable results on MINE-2 (Sec. 6).
- KARMA reports that its multi-agent pipeline beats a single-agent baseline (Table 1, Sec. 5).
- SocraticKG reports higher fact retention than direct extraction on five backbones, at a higher token cost (Table 1, Table 7).
- GraphJudge reports that filtering triples with a fine-tuned judge improves quality over the same extractor without the judge (Table 2 of that paper).

My assessment (to be checked against the papers):
1. KARMA's single-agent GLM-4 baseline and multi-agent GLM-4 comparison control for the underlying model, but token usage for the baseline is not reported, so the comparison does not establish performance under an equal token budget. The larger performance gap involving DeepSeek-v3 may reflect both model choice and agent architecture, so their effects cannot be isolated (Table 1, Sec. 5.4).
2. KGGen reports token cost only for itself; SocraticKG reports tokens per method but all methods are single-LLM pipelines; GraphJudge and Wesslund et al. report no token totals in the text I read. I did not find a comparison that combines single-agent and role-based multi-agent extraction under the same token budget, backbone and judge.
3. None of the six papers reports repeated-run results for its main tables in the text I read. Ilves et al. support repeated runs, but I did not find stability numbers in the text.
4. A separate verification stage is not by itself a new idea: GraphJudge shows a filtering stage helps. What I did not find is a comparison between a prompt-only verifier (no fine-tuning) and a single call with the same extraction and verification rules, with token use recorded. PiVe and SAC-KG, which GraphJudge cites as related verifier work, were not read and could cover part of this (not verified).
5. The "two-step" extraction in Ilves et al. means entities first, then relations; it is not a verification stage.
6. Evaluation relies on LLM judges in KGGen, KARMA, SocraticKG and Wesslund et al.; GraphJudge uses soft matching metrics and Ilves et al. use strict triple matching against an incomplete gold standard.

Open question: under an equal token budget, same backbone and repeated runs, does role-based decomposition beat a single-agent extractor on KG quality? Related budget-controlled evidence exists for multi-hop reasoning (Tran et al., abstract only), but I did not identify such a comparison for KG extraction among the papers reviewed.

## Slide version (compact table + short summary)

| Work | Structure | Models | Token cost reported | Repeats | Main caveat |
|---|---|---|---|---|---|
| KGGen | One LLM, 3 stages | Gemini 2.0 Flash (also Claude Sonnet 3.5, GPT-4o on MINE-1) | KGGen only (5.37M tokens, $0.84 per 1M chars) | not reported | over- or under-de-duplication |
| KARMA | 8-9 role agents | GLM-4, GPT-4o, DeepSeek-v3 | distributions only, baseline not reported | not reported | LLM judge, no equal-budget test |
| SocraticKG | One LLM, 3 prompt stages | five backbones | all methods (Table 7); higher than direct extraction | not reported | no equal-budget quality comparison |
| GraphJudge | Extractor LLM + fine-tuned 7B triple judge | GPT-4o-mini, LLaMA-2-7B | not reported | not reported | judge needs training data; soft matching metrics |

KGGen, KARMA, SocraticKG and GraphJudge split KG extraction into stages, roles or a separate judge, but they differ in backbone, metrics and token accounting, and none reports repeated runs or a token-matched control in the text I read. The open question is whether a decomposed pipeline beats a single call with the same rules once model, judge and token use are controlled. Proposed (untested): compare decomposed and single-call extraction with the same model and judge on MINE fact retention while recording realised tokens; the equal-budget comparison with repeated seeds is planned for the semester, because the first-month pilot uses one seed.

## Sources (pinned)

| Work | Paper (version) | Code (commit) | Checked |
|---|---|---|---|
| KGGen (NeurIPS 2025) | [arXiv:2502.09956v2](https://arxiv.org/abs/2502.09956v2) | [stair-lab/kg-gen @ 6259b4c](https://github.com/stair-lab/kg-gen/tree/6259b4c71523ceae75dafb4acec2eb833bef8f8e) | 2026-10-13 |
| KARMA (NeurIPS 2025) | [arXiv:2502.06472v2](https://arxiv.org/abs/2502.06472v2) | [YuxingLu613/KARMA @ 23610bc](https://github.com/YuxingLu613/KARMA/tree/23610bc2a93ddc9f75322a1234ae6f688f87bdff) | 2026-10-13 |
| SocraticKG (ACL Findings 2026) | [arXiv:2601.10003v2](https://arxiv.org/abs/2601.10003v2) | [LABA-SNU/SocraticKG @ e77062c](https://github.com/LABA-SNU/SocraticKG/tree/e77062ce9304a899636c03a49efb5bd253d5e2e8) | 2026-10-13 |
| Ilves et al. (KG-LLM @ LREC26) | [ACL Anthology 2026.kallm-1.21](https://aclanthology.org/2026.kallm-1.21/) (accessed 2026-10-13) | [SukSev/kg_benchmarking @ ee95299](https://github.com/SukSev/kg_benchmarking/tree/ee952994112d3a1ce1a3c29dbed8dbacdc1b69a2) | 2026-10-13 (paper), 2026-10-18 (code) |
| GraphJudge (EMNLP 2025) | [arXiv:2411.17388v4](https://arxiv.org/abs/2411.17388v4) | [hhy-huang/GraphJudge @ 0ae5913](https://github.com/hhy-huang/GraphJudge/tree/0ae5913d49d8b530c254cbc0cefa71a57d107bb5) | 2026-10-13 (paper), 2026-10-18 (code) |
| Wesslund et al. | [arXiv:2602.11886v1](https://arxiv.org/abs/2602.11886v1) | not found | 2026-10-13 |

Commit hashes are the repository HEAD on the check date, not necessarily the version used by the authors.