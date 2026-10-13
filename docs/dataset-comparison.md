# Benchmark versions and roles (issue #6)

Status: DRAFT, 2026-10-13. Everything marked **TO VERIFY** was not confirmed at the source.
Final data versions and grouped IDs are fixed after inspection in issue #7.

## 1. Comparison table

| | MINE | WebNLG v3.0 (en) | Text2KGBench, DBpedia-WebNLG part | Text2KGBench-LettrIA |
|---|---|---|---|---|
| Proposed role | retention of facts | triple precision/recall | ontology conformance and hallucination proxies | candidate replacement, pending approval |
| Task direction | text to KG | text to RDF (semantic parsing) | text to triples given an ontology | same as Text2KGBench |
| Ontology given as input | no | no (closed DBpedia predicates) | yes | yes |
| Gold | 15 facts per article | RDF triple sets | triples per sentence (3-triple sets) | re-annotated triples |
| Size | paper: 100 articles; HF: 105 rows | train 13,211 / dev 1,667 / test 1,779 triple sets (data-to-text) | 19 ontologies, 4,860 sentences (train + test) | same 4,860 sentences, over 14,000 triples |
| Access | open (Hugging Face) | open (GitLab); registration closed but download allowed | open (GitHub, Zenodo) | **on request only** |
| Data license | not declared | CC BY-NC-SA 4.0 | inconsistent, see 2.3 | unknown |
| Code license | MIT | GPL-3.0 (evaluation script) | Apache-2.0 | n/a |
| Overlap risk | low (LLM-generated articles), not checked | high with Text2KGBench and LettrIA | high with WebNLG and LettrIA | high with both |
| Preparation effort | clean fence and title, build IDs | parse XML, group paraphrases | group paraphrases, pick 5 ontologies | blocked until access |

## 2. Per-benchmark details

### 2.1 MINE
- Code: `stair-lab/kg-gen`, folder `experiments/MINE`, MIT. Folder commit `3209454`.
- Release "MINE Eval expanded" (2025-11-23) contains `results.zip` (28.6 MB). It appears to hold run results, not input data (**TO VERIFY**).
- Data (Hugging Face): `kyssen/kg-gen-evaluation-essays` (columns `topic`, `content`; 105 rows) and `kyssen/kg-gen-evaluation-answers` (105 rows; each row is a list of exactly 15 `answer` strings; README commit `d45f080`).
- Evaluation: `_1_evaluation.py`, needs `OPENAI_API_KEY`. The meaning of `--evaluation-model local` is unclear (**TO VERIFY**).
- Issues:
  - paper reports 100 articles, datasets have 105 rows; topics are unique (SQL check), cause not identified;
  - `content` starts with a ``` fence and repeats the title, so it must be cleaned before extraction;
  - no stable ID; row alignment between essays and answers by order is **TO VERIFY**;
  - neither Hugging Face dataset declares a license (README has only metadata);
  - the `wikiqa` folder is MINE-2 (downstream QA) and is not used here.

### 2.2 WebNLG v3.0 (English)
- Data: `gitlab.com/shimorina/webnlg-dataset`, folder `release_v3.0`. Mirror: Hugging Face `webnlg-challenge/web_nlg` (uses a loading script, viewer disabled).
- Obstacle: on 2026-10-13 gitlab.com showed a "Welcome to GitLab" sign-up page; whether download needs login is **TO VERIFY**. `webnlg-challenge.loria.fr` showed a browser certificate warning and was not opened.
- Fields: `category`, `eid` (unique only per split and category), `size`, `shape`, `shape_type`, `lex` (text, lid, comment), `original_triple_sets`, `modified_triple_sets`, `test_category`.
- 16 DBpedia categories. Several texts per triple set, so paraphrases must be grouped. Several original triple sets can map to one modified set.
- License: CC BY-NC-SA 4.0 (Hugging Face card); the DBpedia source is CC BY-SA 3.0 and GFDL 1.1. Not confirmed in the GitLab repo (**TO VERIFY**).
- Evaluation script: `github.com/WebNLG/WebNLG-Text-to-triples`, GPL-3.0, commit `6a40950`, no releases.
  - `python3 Evaluation_script.py <reference xml> <candidates xml>`
  - input is XML matched by `category` + `eid`; triples as `subject | predicate | object`
  - metrics: precision, recall, F1 for full triples plus four partial modes (strict, exact, partial, type)
  - needs beautifulsoup4, regex, nervaluate, nltk, scikit-learn; last updated about 5 years ago, works on current Python is **TO VERIFY**
  - use as an external tool, do not copy the code into this repository (GPL-3.0)
- Issues: predicates come from a closed DBpedia vocabulary, so free-form relations score poorly in strict/exact matching; entity names use underscores; crowdsourced text has limited fluency.

### 2.3 Text2KGBench (DBpedia-WebNLG part)
- Repo `cenguix/Text2KGBench`, `main` commit `50a3d25`, release "ISWC 2023 Submission", Zenodo record 7916716. Data folder `data/dbpedia_webnlg` (commit `48ebb10`), test folder commit `bac7669`.
- 19 ontologies, 4,860 sentences in total (train + test). Totals per ontology: Food 398, Artist 386, City 348, WrittenWork 322, Politician 319, Transport 314, Airport 306, Athlete 293, Music 290, Building 275, Film 264, Scientist 259, SportsTeam 235, Celestial 194, University 156, Astronaut 154, Company 153, Comics 102, Monument 92.
- Test files: `ont_<n>_<name>_test.jsonl`, fields `id` and `sent` only (no gold). Gold is in `ground_truth`. The University test file has 71 sentences (of 156 total); test sizes of the other ontologies are **TO VERIFY**.
- Built only from the WebNLG 3.0 English 3-triple split; the same fact is not in both train and test (paper). No manually verified subset for this part (paper), so `selected_ids` is probably absent (**TO VERIFY**).
- Evaluation: `src/evaluation/run_eval.py --eval_config_path config/<config>.json` (webnlg configs exist). Metrics: precision, recall, F1 (computed only over relations present in the gold), ontology conformance, relation/subject/object hallucination. Hallucination measures are proxies (string presence in sentence or ontology).
- Licenses (inconsistent): code Apache-2.0; paper and README say CC BY 4.0; `data/LICENSE` states CC BY-SA 4.0 above the CC BY 4.0 text; Zenodo says CC BY-SA 4.0 and notes the WebNLG part is CC BY-NC-SA 4.0. Treat the data as non-commercial, share-alike, research use only.
- Issues: University test sentences are many paraphrases and combinations of very few entities (AWH Engineering College, Acharya Institute of Technology), so sampling and bootstrap must be by triple set; some source facts are wrong (e.g. "Kerala's leader is Kochi"); the language models may have seen the sentences.

### 2.4 Text2KGBench-LettrIA
- Derived from the DBpedia-WebNLG part: 19 refined ontologies, 4,860 sentences re-annotated, over 14,000 triples (paper).
- Available only on request from the authors. Access requested: PENDING (curator approval asked on 2026-10-13). The CC BY 4.0 in the paper refers to the paper; the data license is unknown.
- Status: documented candidate. It does not replace the original benchmark without curator approval.

## 3. Proposed roles
- **MINE:** how much of the 15 gold facts a graph retains; no ontology involved.
- **WebNLG:** precision/recall of triples with the official script; closed DBpedia predicates.
- **Text2KGBench:** ontology conformance and hallucination proxies (plus precision/recall) when the ontology is given.
- Because the three differ in ontology use and gold style, results must not be pooled into one score.

## 4. Overlap checks (to run in issue #7)
- WebNLG and Text2KGBench-DBpedia share source material. Text2KGBench uses only 3-triple sets, so taking WebNLG evaluation texts from other triple-set sizes may reduce overlap by construction (idea, **TO VERIFY** by matching texts and triples).
- LettrIA uses the same sentences as Text2KGBench.
- MINE against the others: not checked.

## 5. Open items
1. MINE: contents of `results.zip`, `--evaluation-model local`, essays/answers alignment, 105 vs 100.
2. WebNLG: license in the GitLab repo, login requirement, script on current Python, semantic-parsing test file sizes.
3. Text2KGBench: test size of each ontology, selection of 5 ontologies, whether `selected_ids` exists.
4. LettrIA: access and license.

## 6. Decisions requested from the curator
1. May the authors of LettrIA be contacted for access?
2. Is non-commercial, share-alike, research-only use acceptable for all data?
