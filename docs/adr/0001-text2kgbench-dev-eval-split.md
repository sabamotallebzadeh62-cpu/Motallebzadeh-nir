---
status: proposed
date: 2026-10-15
decision-makers: Saba
consulted: curator (not yet consulted)
---
# Text2KGBench development/evaluation split: train for development, test for evaluation, five proposed ontologies

## Context and problem statement

Issue #7 requires versioned development and evaluation data with no leakage between them. The
upstream Text2KGBench (DBpedia-WebNLG part, commit `50a3d255371b8817cdff70fd88459ac82b339cfe`)
has 19 ontologies, 2,846 train and 2,014 test sentences. Its files carry no original WebNLG IDs,
so source groups (paraphrases of one triple set) cannot be read from the data.

Measurements on the local copy:

- Identical triple sets: every sentence has its own (groups = sentences), so this rule merges nothing.
- Any shared entity: merges almost everything (for example `ont_16_city` becomes one group).
- Shared subject entity: groups are few and large (for example `ont_1_university` has 2 groups,
  the largest with 63 of 71 sentences).
- No exact normalized sentence overlap between train and test in any ontology.
- Shared subjects between train and test per ontology: 0 for airport, meanoftransportation,
  university, company, astronaut; 1 for building, athlete, celestialbody, artist, scientist,
  sportsteam; higher for city (20), musicalwork (12), writtenwork (7), politician (6).
- Three repeated test sentences, all in `ont_16_city` (see `docs/data-quality-text2kgbench.md`).

## Considered options

1. Draw development and evaluation both from `test`, split by an approximate group.
2. Draw development from `train` and evaluation from `test`, excluding evaluation items that
   share a subject entity with a development item of the same ontology.
3. Wait for original WebNLG IDs before preparing any sample.

## Decision outcome

Chosen option: 2.

- Development: 6 random `train` sentences per ontology (30 in total).
- Evaluation: 20 random `test` sentences per ontology (100 in total), excluding items whose
  subject entities overlap a development item of the same ontology.
- Seed 42, deterministic per ontology; `scripts/prepare_text2kgbench.py` rebuilds the same
  130 IDs and writes `configs/data-manifest.json`. Re-running it left the manifest unchanged.
- Ontologies (proposal, pending curator approval): airport, building, athlete,
  meanoftransportation, celestialbody. They were chosen because they have at least 72 test
  sentences, at most 1 shared train/test subject and several subject groups. This is a proposal
  from local measurements, not an approved choice.
- `group_id` in the manifest is an approximation (ontology plus the alphabetically smallest
  subject). It is not an original source-group ID.

### Consequences

- Leakage is prevented at sentence and subject level only. Source-group independence is not
  proven, and a bootstrap over these groups would have few groups per ontology.
- Cross-benchmark overlap with WebNLG is not checked: MINE and WebNLG are not prepared yet.
- The three repeated `ont_16_city` sentences are outside the chosen ontologies; raw records
  were not modified.
- If the curator picks other ontologies, only the `ONTOLOGIES` list in the script changes and
  the manifest must be regenerated.
- The data is derived from WebNLG 3.0 (CC BY-NC-SA 4.0): research use only, no redistribution.
- No MLflow run: this is data preparation, not an experiment.

## Pros and cons of the options

Option 1: keeps one source file but has no upstream split, so development and evaluation would
rely entirely on an approximate grouping that merges too much or too little.

Option 2: uses the upstream train/test split as the first barrier and adds a subject-level
exclusion; costs a small loss of eligible evaluation items.

Option 3: avoids approximate groups but blocks the issue's deadline (2026-10-18) on data that
may not exist in these files.
