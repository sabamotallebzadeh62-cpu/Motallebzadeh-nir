---
status: proposed
date: 2026-10-22
decision-makers: <student>
consulted: <supervisor>
---

# Integrate official triple-quality evaluators

## Context and problem statement

The project needs reproducible triple-extraction quality metrics on development
fixtures. The metrics must include exact and partial matching, precision,
recall, F1, ontology conformance, and subject, relation, and object
hallucination measures.

The evaluation must use the official WebNLG Text-to-triples and
Text2KGBench implementations rather than silently substituting locally
implemented scores. Upstream evaluators have different input formats,
normalization rules, aggregation strategies, and edge-case behavior.

Only the prepared development split may be used while developing and testing
the integration. The evaluation split must not be used to tune or validate
implementation choices.

## Considered options

1. Implement all metrics locally.
2. Invoke both official evaluators directly from ad hoc scripts.
3. Provide a common project-level input interface with thin adapters for each
   official evaluator.

## Decision outcome

Propose option 3.

Use a shared project representation for examples and triples, with separate
adapters that translate inputs into the formats required by each official
evaluator. Preserve the official metric definitions and report the evaluators'
outputs without relabeling one metric as another.

Pin the upstream evaluator revisions and relevant runtime dependencies.
Document normalization, matching, denominators, aggregation, and known
upstream limitations in `docs/metrics.md`.

Tests will use hand-calculated fixtures covering correct triples, incorrect
relations, partial matches, duplicates, empty predictions, and invalid
outputs. Evaluator failures and missing prediction IDs must be visible in
the run summary; failures must not be converted into perfect scores.

Development fixtures only will be used for integration checks. Reports must
identify the upstream revisions and distinguish synthetic adapter smoke tests
from actual model evaluation.

### Consequences

- The project depends on two upstream evaluation implementations with
  different interfaces and dependency requirements.
- Thin adapters add maintenance work but keep upstream behavior explicit.
- Some upstream edge cases may require clear failure reporting or documented
  compatibility handling rather than changes to official scoring behavior.
- Official scores from the two evaluators are not assumed to be directly
  interchangeable.

## Pros and cons of the options

### Option 1: Implement all metrics locally

- Pros: One uniform implementation and fewer upstream runtime dependencies.
- Cons: Risks diverging from official metric definitions and makes comparisons
  with published results less defensible.

### Option 2: Invoke official evaluators from ad hoc scripts

- Pros: Minimal initial integration effort.
- Cons: Repeated conversion logic, weak automated testing, and less reliable
  error reporting and reproducibility.

### Option 3: Common interface with official-evaluator adapters

- Pros: Reusable inputs, testable conversions, explicit official scoring,
  and consistent run summaries.
- Cons: Requires adapters, dependency pinning, and documentation of upstream
  differences and limitations.
