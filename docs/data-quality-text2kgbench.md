# Text2KGBench data quality review

**Date:** 2026-10-14
**Status:** Preliminary findings; upstream review required
**Dataset area:** `data/raw/Text2KGBench/data/dbpedia_webnlg`

## Scope

This note records structural validation findings for the local DBpedia-WebNLG
data, focusing on repeated test sentences and their gold annotations. It does
not authorize changes to, or redistribution of, the raw dataset.

## Validation summary

- Test data covers 19 ontology files and 2,014 records.
- Test IDs are unique across the inspected test files.
- No exact normalized sentence overlap was found between test and train
  within the inspected ontology files.
- Three repeated normalized test-sentence groups were found; all are in
  `ont_16_city_test.jsonl`.
- Sentence overlap checks alone do not establish source-group independence.

## Repeated test sentences requiring review

### 1. Atlanta / DeKalb County

IDs: `ont_16_city_test_81`, `ont_16_city_test_203`

Both records use:

> Most of Atlanta is part of DeKalb County in Georgia, United States.

The gold annotations differ in the subject of the `country` triple:
one uses `DeKalb_County,_Georgia`, while the other uses `Atlanta`.

### 2. Auburn / Lee County — wording variant

IDs: `ont_16_city_test_97`, `ont_16_city_test_204`

Both records use:

> Auburn is part of Lee County, Alabama in the United States.

The gold annotations differ in the subject of the `country` triple:
one uses `Alabama`, while the other uses `Auburn,_Alabama`.

### 3. Auburn / Lee County — identical sentence

IDs: `ont_16_city_test_98`, `ont_16_city_test_99`

Both records use:

> Auburn is part of Lee County in Alabama, United States.

The final triple differs:
- ID `ont_16_city_test_98` uses `Auburn,_Alabama` as subject,
  `isPartOf` as relation, and `Alabama` as object.
- ID `ont_16_city_test_99` uses `Lee_County,_Alabama` as subject,
  `state` as relation, and `Alabama` as object.

## Interpretation and limitations

Repeated sentence text does not necessarily imply duplicate gold annotations.
The observed differences may reflect distinct annotation choices or data
quality issues; this local inspection alone cannot establish which annotation
is correct.

The current findings do not establish whether records share an upstream
source group, nor whether they overlap with other benchmarks.

## Recommended follow-up

1. Preserve the raw records unchanged.
2. Compare these records with the authoritative upstream source and its
   documented version, if available.
3. Resolve the dataset policy with the supervisor before excluding,
   deduplicating, or otherwise changing evaluation records.
4. Keep any eventual filtering or selection deterministic and documented.

No records were removed or modified as part of this review.
