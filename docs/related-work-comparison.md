# Related work comparison

Source: docs/reading-log.md. Search date: 2026-10-07. Three papers read in detail; seven screened by abstract only.

## Table 1. Papers read in detail

| Work | Question | Roles / stages | Model | Dataset | Baseline | Quality metrics | Token / cost accounting | Repetitions | Code | Limitations (authors) |
|---|---|---|---|---|---|---|---|---|---|---|
| KGGen (Mo et al., 2025, arXiv 2502.09956) | Dense, high-quality KG from plain text; sparsity of OpenIE and GraphRAG graphs | One LLM, three stages: two-step extraction (entities, then triples), aggregation without LLM, entity and edge resolution (embeddings, k-means, BM25, LLM de-duplication) | Gemini 2.0 Flash via DSPy; also Claude Sonnet 3.5 and GPT-4o on MINE-1 | MINE-1 (100 articles, 15 facts each), MINE-2 on WikiQA, 100 SemEval-2010 sentences | OpenIE, GraphRAG | Fact retention (LLM judge), QA answer containment (LLM judge), manual validity of 100 triples per method | KGGen only: 5.37M tokens and $0.84 for 1M characters (Table 3); GraphRAG: time only | Not reported for MINE-1 | github.com/stair-lab/kg-gen (link stated in paper; not verified) | Over or under de-duplication; corpora up to about 5M tokens; domain-specific knowledge |
| KARMA (Lu et al., 2025, arXiv 2502.06472) | Enrich an existing KG from scientific text | Central controller with eight to nine LLM agents: ingestion, reader, summarizer, entity, relation, schema alignment, conflict resolution, evaluator | GLM-4, GPT-4o or DeepSeek-v3 (one backbone per run); judge DeepSeek-v3 | 1,200 PubMed articles (genomics 720, proteomics 360, metabolomics 120) | Single-agent GLM-4 (one generation); ablations without summarizer, conflict resolution or evaluator | LLM-judged correctness, QA coherence, conflict ratio, coverage and connectivity gain, human score (two experts) | Token and time distributions per article (Fig. 3); no totals; baseline not reported | Not found in the text | github.com/YuxingLu613/KARMA (link seen in the paper text; not verified) | Mostly LLM-based metrics; weaker on metabolomics |
| SocraticKG (Choi et al., 2026, arXiv 2601.10003) | Coverage versus connectivity in LLM-based KG construction | One LLM, three prompt stages: 5W1H QA generation, triples from each QA pair, KGGen-style canonicalization | Qwen-2.5 7B, GPT-4o-mini, GPT-4o, Gemini-2.5-Flash-Lite, Claude-4-Sonnet; MINE judge GPT-4o; HotpotQA answerer GPT-4.1 | MINE (100 articles), HotpotQA 800 Hard Bridge questions | Direct extraction, GraphRAG, KGGen, SoKG without 5W1H, Naive RAG | Fact retention, average degree, triple count, fragmentation index (NFI), HotpotQA accuracy, uniqueness, granularity, human factual precision | Total tokens up to triple extraction for every method and tokens per triple (Table 7) | Not reported (temperature 0) | github.com/LABA-SNU/SocraticKG (link stated in paper; not verified) | Higher token use; depends on LLM; binary triples only |

## Table 2. Papers screened (abstract only)

| Work | Setting (from abstract) | Everything else |
|---|---|---|
| EDC (Zhang and Soh, 2024, arXiv 2404.03868) | Open extraction, schema definition, canonicalization; optional schema retriever | Not verified; code stated in abstract: github.com/clear-nus/edc |
| GraphJudge (Huang et al., 2025, arXiv 2411.17388) | Fine-tuned LLM judges triples; denoising and instruction tuning | Not verified; code stated in abstract: github.com/hhy-huang/GraphJudge |
| MAGG (arXiv 2608.28642, authors not verified) | Multi-agent KG construction with domain-expert review | Search snippet shows token tables (about 80k vs 29k per document on SciERC); not verified |
| Tran et al. (arXiv 2604.02460) | Single vs multi-agent under equal thinking-token budgets, multi-hop reasoning | Not verified; not a KG extraction task |
| Phase Transition for Budgeted Multi-Agent Synergy (arXiv 2601.17311, authors not verified) | Fixed-budget comparison theory | Not verified |
| Wesslund et al. (arXiv 2602.11886) | Triplet extraction with regex plus LLM-as-judge verification | Not verified |
| Ilves et al. (LREC26 KG-LLM) | Schema-constrained evaluation, single-step vs two-step, repeated-run stability on DocRED | Not verified; no link yet |

## Synthesis: what controlled comparison is missing

Authors' claims (as reported):
- KGGen reports better information retention than GraphRAG on MINE-1 and comparable results on MINE-2 (Sec. 6).
- KARMA reports that its multi-agent pipeline beats a single-agent baseline (Table 1, Sec. 5).
- SocraticKG reports higher fact retention than direct extraction on five backbones, at about two to four times the tokens (Table 1, Table 7).

My assessment (to be checked against the papers):
1. KARMA's single-agent baseline is the weakest backbone (GLM-4) and its token cost is not reported for the baseline, so architecture and model effects and budget are mixed (Table 1, Sec. 5.4).
2. KGGen reports token cost only for itself; SocraticKG reports tokens per method but all methods are single-LLM pipelines; none of the three compares single-agent and role-based multi-agent extraction at the same token budget, same backbone and same judge.
3. None of the three reports repeated runs for the main tables in the text I read, so small gaps are weak evidence.
4. Judges are LLMs in all three papers.

Open question: under an equal token budget, same backbone and repeated runs, does role-based decomposition beat a single-agent extractor on KG quality? Related budget-controlled evidence exists for multi-hop reasoning (Tran et al., abstract only), not for KG extraction in the papers I read.

## Slide version (2 to 3 sentences)

KGGen, KARMA and SocraticKG decompose KG extraction into stages or roles, but their comparisons differ in backbone, judge and token accounting, and none reports repeated runs. What is missing is a controlled comparison of single-agent and role-based extraction at equal token budget. [Proposed contribution: write one sentence in your own words, framed as a proposal to be tested, not as an advantage already shown.]