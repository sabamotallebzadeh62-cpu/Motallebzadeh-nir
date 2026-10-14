# data/

Ignored by Git except this file. Raw data, weights and large files live in MLflow, MinIO or the
cluster storage; the project README says how to fetch them. At most a tiny labelled sample may be
committed here, by agreement with the supervisor.


## Benchmark sources (issue #6)

Raw benchmark data is not committed here. Fetch it from the sources below into local or cluster storage. Versions are pinned after inspection in #7. Details and open items: docs/dataset-comparison.md.

| Benchmark | Source | Version to record | Access | Data license |
|---|---|---|---|---|
| MINE | Hugging Face `kyssen/kg-gen-evaluation-essays` (texts) and `kyssen/kg-gen-evaluation-answers` (gold facts); evaluation code in `stair-lab/kg-gen`, folder `experiments/MINE` | answers commit `d45f080`; code folder commit `3209454`; essays commit TO VERIFY | open; evaluation needs `OPENAI_API_KEY` | not declared (code is MIT) |
| WebNLG v3.0 (en) | `gitlab.com/shimorina/webnlg-dataset`, folder `release_v3.0`; mirror: Hugging Face `webnlg-challenge/web_nlg` | `release_v3.0` | download allowed per the challenge FAQ; login requirement TO VERIFY | CC BY-NC-SA 4.0 (Hugging Face card, TO VERIFY at the source) |
| Text2KGBench, DBpedia-WebNLG part | `github.com/cenguix/Text2KGBench`, folder `data/dbpedia_webnlg`; Zenodo record 7916716 | release "ISWC 2023 Submission", commit `50a3d25` | open | inconsistent (CC BY 4.0 vs CC BY-SA 4.0); WebNLG-derived part is CC BY-NC-SA 4.0 |
| Text2KGBench-LettrIA | authors of the paper | not available | on request only, request pending | unknown |

Evaluation code (external tools, do not copy into this repository):
- WebNLG text-to-triples: `github.com/WebNLG/WebNLG-Text-to-triples`, commit `6a40950`, GPL-3.0.
- Text2KGBench: `src/evaluation/run_eval.py` in the Text2KGBench repository, Apache-2.0.

Rules:
- Treat all data as non-commercial, share-alike, research use only; do not redistribute it.
- Gold triples and gold facts never go into extraction inputs.
- Facts marked TO VERIFY are not confirmed at the source.
