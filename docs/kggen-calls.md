# KGGen: pinned version and internal model calls

Preparation for Issue #14. Checked on 2026-10-26 by reading the published wheel;
nothing was installed and no model was called.

## Pin

- Package: `kg-gen` 0.4.0 (latest on PyPI at the time of checking).
- Wheel SHA-256: `4f5ed6b840dd81e60fc4d85d60bfef06b75f39feec77e02681ef9bd7423bd62f`
- Python: `>=3.10,<4.0`.
- Declared dependencies include `dspy>=2.6.27`, `openai>=1.108.1`,
  `sentence-transformers>=5.1.0`, `datasets>=4.1.1`, `pyvis`, `nltk`, `tqdm`,
  `pydantic>=2.0.0`, and also `pre-commit` and `ty`.
- Proposed, not applied: keep it out of the main dependencies (heavy install, and it
  declares dev tools as runtime requirements) and add it as an optional extra.

## Model calls (observed in the source)

All calls go through `dspy.LM` (`kg_gen.py`), not through the project's OpenAI client.

| Step | Entry point | Model calls |
|---|---|---|
| Extraction, entities | `generate` -> `get_entities` | `dspy.Predict` (`TextEntities` or `ConversationEntities`), one per text or chunk |
| Extraction, relations | `generate` -> `get_relations` | `dspy.Predict` (`ExtractRelations`), one per text or chunk |
| Relations, fallback | `get_relations`, only if the first attempt raises | a second `dspy.Predict`, then `dspy.ChainOfThought(FixedRelations)`; the failed first attempt may already have used tokens |
| Clustering | `cluster` -> `cluster_graph`, for entities and again for edges | signatures present: `ExtractCluster`, `ValidateCluster`, `CheckExistingClusters` (ChainOfThought), `ChooseRepresentative` |
| Aggregation | `aggregate` | none: a plain set union of entities, relations and edges |

With `chunk_size` set, chunks run in parallel in a `ThreadPoolExecutor`, so call
logging must be thread-safe. The number of clustering calls depends on the data.

## Not verified yet

- How many calls `cluster_items` makes per run, and in what order (not read).
- Whether dspy caches calls, which would make a repeated call report zero tokens.
- Whether `init_model` passes a seed to `dspy.LM` (not read; `generate` has no seed argument).
- Temperature: `generate` and `cluster` use `temperature or self.temperature`, so an
  explicit `0.0` is falsy and falls back to the constructor value. Set the temperature
  in the `KGGen(...)` constructor rather than per call, and check the default.
- Where to hook call logging: `CallLogger` wraps a callable, but KGGen calls the model
  inside dspy, so the hook point still has to be chosen.
