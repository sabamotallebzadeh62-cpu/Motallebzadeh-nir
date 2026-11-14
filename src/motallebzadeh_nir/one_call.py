"""One-call control (issue #15): data adapter and the strict evidence contract.

The one-call method puts extraction and verification rules in a single prompt. To keep the
comparison with the two-step method controlled, it must accept answers by the same rules as
the paired verifier (PR #35): a kept triple needs a nonempty evidence quote that is present
in the source text after the same whitespace normalisation. The baseline's optional-evidence
contract is not changed.
"""

from __future__ import annotations

import json
from pathlib import Path

from motallebzadeh_nir.extraction import FailureKind, ParseError, parse_triples
from motallebzadeh_nir.extraction_types import Chunk, Triple


def normalise(text: str) -> str:
    """Collapse whitespace; identical to the verifier's normalisation (PR #35)."""
    return " ".join(text.split())


def parse_one_call(document_id: str, raw: str, source_text: str) -> list[Triple]:
    """Parse a one-call answer and require a quote of the source for every triple."""
    triples = parse_triples(document_id, raw)
    source = normalise(source_text)
    for triple in triples:
        if not triple.evidence or normalise(triple.evidence) not in source:
            raise ParseError(
                FailureKind.INVALID_SCHEMA,
                f"triple {triple.triple_id}: evidence is missing or not a quote of the source",
            )
    return triples


def read_prepared_inputs(path: Path) -> list[Chunk]:
    """Read the data-preparation output (`id`, `text`, `ontology`) as chunks.

    The original ID is kept as both document_id and chunk_id: one sentence is one document
    and one chunk. Any other key (for example a gold field) is rejected, not ignored, so that
    gold triples cannot reach a prompt by accident.
    """
    chunks: list[Chunk] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict) or set(row) != {"id", "text", "ontology"}:
                raise ValueError(f"{path}:{number}: expected exactly id, text and ontology")
            if row["id"] in seen:
                raise ValueError(f"{path}:{number}: duplicate id {row['id']!r}")
            seen.add(row["id"])
            try:
                chunks.append(Chunk(document_id=row["id"], chunk_id=row["id"], text=row["text"]))
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: invalid chunk: {exc}") from exc
    if not chunks:
        raise ValueError(f"{path}: no chunks found")
    return chunks
