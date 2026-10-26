# Role-based knowledge graph extraction: does verification pay for its tokens?

[Русская версия](README.ru.md)

Semester research project (NIR) started from the [lab template](https://github.com/Industrial-AI-Research-Lab/motallebzadeh-nir-template).

## Research question

Does separating knowledge-graph extraction from verification improve graph quality enough to justify the extra tokens? A later question is whether a small model can benefit more, and more cheaply, from this separation than from switching to a larger model.

A knowledge graph here is a set of triples. A triple is a fact written as subject – relation – object, for example (Marie Curie, born_in, Warsaw).

The first month is a **pilot**: it prepares data, metrics and a single-prompt baseline, then runs a small controlled comparison of extraction methods with token costs logged separately. The pilot cannot settle the full hypotheses. That is later semester work (see below).

## Project status

| Area | Status |
|---|---|
| Python package `motallebzadeh_nir` (renamed from the template), `make check`, `make run`, MLflow logging | Implemented (template scaffold) |
| MLflow example run on synthetic regression data (`configs/smoke.yaml`) | Template example only, not a research result |
| Data preparation, extraction baseline, verifier, triple-quality metrics, cost logging | Planned, not implemented yet |
| Literature review and comparison of methods | In progress, see [reading log](docs/reading-log.md) |
| Work outside GitHub | None confirmed. |

No research results have been obtained yet.

## Milestones

1. [Prepare the data, metrics and single-prompt baseline](https://github.com/sabamotallebzadeh62-cpu/Motallebzadeh-nir/milestone/1)
2. Compare extraction methods in a controlled pilot: see the [milestones list](https://github.com/sabamotallebzadeh62-cpu/Motallebzadeh-nir/milestones)

Later semester work (not part of the pilot): additional baselines (EDC, LLMGraphTransformer, REBEL), canonicalization and the full role-based pipeline, several rounds and cross-size verifier/extractor pairs, full samples with several seeds, and the final report.

## Quick start

```bash
cp .env.example .env          # fill in the keys; .env is ignored
uv sync                       # installs the package and the dev tools from uv.lock
uvx pre-commit install        # gitleaks, large files, make check before every commit
make check                    # ruff, mypy, pytest
make run                      # one experiment: configs/smoke.yaml -> an MLflow run
make mlflow                   # MLflow UI over the local mlflow.db
```

The package is already renamed to `motallebzadeh_nir`.

## Layout

```
src/motallebzadeh_nir/   code that is imported and tested: config.py, pipeline.py, __main__.py
tests/                   smoke test: the pipeline on a tiny input
configs/                 experiment configs (YAML)
notebooks/               exploration; outputs may stay as a report of a result
docs/adr/                decision log, one file per decision
docs/meetings/           meeting records
docs/reading-log.md      papers read
data/                    ignored; how to fetch the data is described below
results/                 tables and figures exported from code
.github/                 PR template, issue form for experiments, CODEOWNERS, CI
```

## Data

Planned benchmarks (candidates, final choice pending): MINE (from kg-gen), WebNLG 2020, Text2KGBench. Raw data is never committed; `data/` is git-ignored. Fetch and preparation commands will be added with the data-preparation task; until then there is nothing to fetch.

## Experiments

Every run is recorded in MLflow (`MLFLOW_TRACKING_URI` in `.env`, the local `mlflow.db` by default). A results row is commit, config path, seed, run id, metrics.

The table below is the template format. It has no real results yet.

| commit | config | seed | run id | mse |
|---|---|---|---|---|

Planned next: a single-prompt extraction baseline, a one-call control with verifier instructions, a batched verifier, and a KGGen adapter, all evaluated with the same metrics and token accounting.

## Checks

`make check` runs from three places: pre-commit on your machine, CI on every PR, the agent hook. Branch `<type>/<short-description>`, PR title `<type>: ...`; the types are feat, fix, refactor, docs, test, chore, exp.

## LLM assistants

I use Claude (chat) to explain tasks, draft documentation and debug; I review and understand everything I commit. Their instructions: [AGENTS.md](AGENTS.md); the shared lab rules are connected by `make overlay` ([nir-agent-overlay](https://github.com/Industrial-AI-Research-Lab/nir-agent-overlay)). You are responsible for code written with an agent.

## Guides

[Practice guides](https://github.com/Industrial-AI-Research-Lab/project-implementation-manual/blob/master/nir-requirements/recommendations/README.md) of the lab manual: papers, repository and code, task tracking, agent artifacts.

## Licence

The template is MIT. Choose the licence of your own code and replace LICENSE if needed.
