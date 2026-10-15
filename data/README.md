# data/

Ignored by Git except this file. Raw data, weights and large files live in MLflow, MinIO or the
cluster storage; the project README says how to fetch them. At most a tiny labelled sample may be
committed here, by agreement with the supervisor.

## Text2KGBench (DBpedia-WebNLG part)

Raw data is not committed. Fetch it into `data/raw/` (ignored by Git). The upstream repository
uses Git LFS (only `tekgen.zip`), so install `git-lfs` before cloning.

    git lfs install
    git clone https://github.com/cenguix/Text2KGBench.git data/raw/Text2KGBench
    git -C data/raw/Text2KGBench checkout 50a3d255371b8817cdff70fd88459ac82b339cfe

Pinned version: commit `50a3d255371b8817cdff70fd88459ac82b339cfe` (upstream `main`, 2024-05-05).

Validate the raw files, then build the proposed samples:

    uv run python scripts/validate_benchmark_data.py
    uv run python scripts/prepare_text2kgbench.py

The second command writes `configs/data-manifest.json` (tracked) and input/reference files
under `data/prepared/text2kgbench/` (ignored). With seed 42 it selects 30 development items
(from upstream `train`) and 100 evaluation items (from upstream `test`) over five proposed
ontologies. Re-running it must leave the manifest unchanged.

Extraction inputs contain only `id`, `text` and `ontology`; gold triples are written to
separate reference files and must never be passed to an extractor.

Known limitations:

- Only this part of Text2KGBench is prepared; MINE and WebNLG are not covered yet.
- The five ontologies are a proposal pending curator approval.
- Upstream files have no original WebNLG IDs, so `group_id` in the manifest is an approximation.
- Cross-benchmark overlap with WebNLG has not been checked.
- Three repeated test sentences exist in `ont_16_city`; see `docs/data-quality-text2kgbench.md`.
- Licence: the upstream README states that the data is derived from WebNLG 3.0 (CC BY-NC-SA 4.0)
  and also declares CC BY 4.0 for the benchmark. Treat the data as non-commercial research
  use only and do not redistribute it.
