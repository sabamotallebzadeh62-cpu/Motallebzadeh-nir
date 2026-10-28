# Triple-quality metrics

## Purpose and scope

This document describes the project's adapters for the official Text2KGBench
and WebNLG Text-to-triples evaluators. The adapters share a project-level
representation of examples, references, and predictions, but they do not
replace the upstream scoring definitions.

Integration checks use the prepared development split only. The evaluation
split must not be used to debug, tune, or validate adapter behavior.

## Reproducibility

The adapters identify the upstream evaluator revisions in their result
summaries:

| Evaluator | Upstream commit |
|---|---|
| Text2KGBench | `50a3d255371b8817cdff70fd88459ac82b339cfe` |
| WebNLG Text-to-triples | `6a409508885bcd7b3a5d8e42f599fe6c3c6b8564` |

The `metrics` optional dependency group pins the evaluator-related packages
used by this integration. The upstream WebNLG requirements include older
dependency versions that are not compatible with the project's Python 3.12
runtime. The project therefore uses compatible pinned versions without
modifying upstream evaluator code. See `pyproject.toml` and `uv.lock` for the
exact versions.

Raw upstream repositories and prepared data are local inputs to the evaluation
workflow and must not be committed as project data.

## Input contract

The shared representation contains:

- An example ID, source text, ontology ID, and reference triples.
- A prediction ID and a list of predicted triples.
- Each triple has a subject (`sub`), relation (`rel`), and object (`obj`).

Inputs and predictions are aligned by ID, not by file order. Duplicate IDs,
malformed records, missing predictions, extra predictions, and invalid triple
fields are rejected during loading or alignment validation.

An empty triple list is syntactically valid in the shared representation.
Whether an evaluator can score an empty prediction is evaluator-specific:
the WebNLG adapter rejects empty candidates because the upstream evaluator
cannot reliably process that case. Invalid input and evaluator failures must
remain visible errors; they must not be replaced with an empty graph or a
perfect score.

## Evaluator behavior and metric interpretation

### Text2KGBench

The adapter translates project triples to the record format expected by the
official Text2KGBench script and maps project ontology IDs to the upstream
ontology identifiers.

The upstream evaluator normalizes triples for its precision, recall, and F1
calculation by lowercasing and removing spaces and underscores. Its
triple-matching calculation uses sets, so duplicate triples do not necessarily
increase the exact-match counts. Its precision/recall/F1 calculation filters
predictions by reference relation labels before comparing triples. Therefore,
these scores must not be interpreted as a complete measure of every possible
relation error.

Ontology conformance and subject, relation, and object hallucination measures
are separate upstream metrics. In particular, the hallucination measures use
upstream heuristics, including checks against the source text and ontology
labels. A non-zero hallucination score can occur even when the predicted
triples are identical to the references. Interpret these measures according
to their own definitions rather than treating them as ordinary triple
precision or recall.

The upstream report includes a `global` aggregate and per-ontology rows.
The global `onto_list` field is omitted from the adapter's returned report
because it contains temporary and local filesystem paths. Per-ontology
averages remain available in `ontology_averages`.

### WebNLG Text-to-triples

The adapter converts examples to the XML structure expected by the official
WebNLG evaluator. XML is generated with an XML library so special characters
are escaped correctly.

The returned `Total_scores` sections include `Ent_type`, `Partial`, `Strict`,
and `Exact`. These are distinct scoring modes and must retain their upstream
names. The separate `Exact_match` section is also retained; it must not be
renamed to or confused with `Total_scores.Exact`.

WebNLG normalizes fields using its own rules, including case normalization,
camel-case splitting, underscore-to-space conversion, whitespace
normalization, and handling of parenthetical suffixes. Its entity-level and
triple-level scoring modes can treat a match differently. Do not assume its
normalization, duplicate handling, denominators, or aggregate scores are
interchangeable with Text2KGBench.

## Hand-calculated examples

The following examples illustrate ordinary set-based exact triple matching.
They are explanatory examples, not substitutes for either official
evaluator's implementation.

For a reference set containing one triple, `(A, locatedIn, B)`:

| Prediction | Exact matches | Predicted triples | Reference triples | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| `(A, locatedIn, B)` | 1 | 1 | 1 | 1.00 | 1.00 | 1.00 |
| `(A, bornIn, B)` | 0 | 1 | 1 | 0.00 | 0.00 | 0.00 |
| `(A, locatedIn, C)` | 0 | 1 | 1 | 0.00 | 0.00 | 0.00 |
| Empty prediction | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |

For this illustration, precision is `TP / predicted_count`, recall is
`TP / reference_count`, and F1 is the harmonic mean of precision and recall.
The empty-prediction example assumes a non-empty reference set and defines
precision as zero when there are no predictions. This convention is for the
illustration only; adapter-level rejection or upstream behavior takes
precedence in actual evaluation.

### Duplicates

Suppose the reference contains one `(A, locatedIn, B)` triple and the
prediction contains that triple twice. A set-based exact comparison has one
unique match, not two. The shared input loader preserves duplicate triples
rather than silently removing them; the official evaluator determines how
duplicates affect its scores. Consult that evaluator's result sections rather
than applying the illustrative set calculation to every official metric.

### Partial matches

Suppose the reference contains `(A, locatedIn, B)` and the prediction
contains `(A, locatedIn, C)`. Under strict triple equality, this is not an
exact match. A partial-matching evaluator may award credit under its own
entity or field matching rules. Such partial credit must be reported using
the evaluator's corresponding metric, not presented as an exact match.

### Invalid output

A malformed JSONL record, missing required triple field, duplicate example
ID, missing prediction ID, or unexpected prediction ID is an input error,
not an incorrect-but-scoreable triple. The loader or alignment validation
raises an error. Likewise, a non-zero evaluator exit, missing output file, or
invalid evaluator result is an evaluation failure. These conditions must not
be converted into an empty prediction or a score of 1.00.

## Aggregation and denominators

Use the official output as the source of truth for each evaluator's
denominators and aggregation:

- Text2KGBench reports global aggregates and per-ontology averages. Its
  upstream implementation averages case-level values within ontology and
  then computes the global ontology-level aggregate; displayed values are
  rounded by the upstream script.
- WebNLG reports separate score sections and counts such as `Correct`,
  `Incorrect`, `Partial`, `Missed`, `Spurious`, `Possible`, and `Actual`.
  Their interpretation depends on the selected scoring mode. Retain these
  fields when reporting scores and do not derive one score section from
  another.

Always report the evaluator name, upstream commit, example count, and the
specific score section being discussed.

## Development integration smoke test

An identity-prediction smoke test was run on 30 prepared development examples,
six per ontology. The predictions copied the reference triples exactly. This
checks data conversion and evaluator invocation; it is not a model benchmark.

Text2KGBench returned:

| Global metric | Result |
|---|---:|
| Average precision | 1.00 |
| Average recall | 1.00 |
| Average F1 | 1.00 |
| Average ontology conformance | 1.00 |
| Average subject hallucination | 0.31 |
| Average relation hallucination | 0.00 |
| Average object hallucination | 0.45 |

The non-zero subject and object hallucination values reflect the upstream
heuristics described above and should not be read as evidence that the
identity predictions differed from the references.

WebNLG returned the following F1 values:

| Score section | F1 |
|---|---:|
| `Total_scores.Ent_type` | 0.988636 |
| `Total_scores.Partial` | 0.982955 |
| `Total_scores.Strict` | 0.977273 |
| `Total_scores.Exact` | 0.977273 |
| `Exact_match` | 1.000000 |

The different WebNLG score sections are not interchangeable. The discrepancy
between `Exact_match` and the other sections is recorded as observed
upstream behavior and is not silently corrected by the adapter.

These smoke-test results should be regenerated after adapter or dependency
changes. They must not be presented as model quality results.

## Running checks

Run the project checks with:

```bash
make check

```
