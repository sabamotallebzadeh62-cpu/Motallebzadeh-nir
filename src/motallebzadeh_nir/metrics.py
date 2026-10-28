"""Shared data contracts for official triple-quality evaluators."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Triple:
    """One subject-relation-object triple in the project representation."""

    sub: str
    rel: str
    obj: str

    def as_text2kgbench(self) -> dict[str, str]:
        """Return the official Text2KGBench reference representation."""
        return {"sub": self.sub, "rel": self.rel, "obj": self.obj}

    def as_webnlg(self) -> str:
        """Return the pipe-delimited triple expected by WebNLG."""
        return f"{self.sub} | {self.rel} | {self.obj}"


@dataclass(frozen=True, slots=True)
class Example:
    """One source sentence and its gold triples."""

    id: str
    text: str
    ontology: str
    triples: tuple[Triple, ...]


@dataclass(frozen=True, slots=True)
class Prediction:
    """Predicted triples for one example."""

    id: str
    triples: tuple[Triple, ...]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"{path}: line {line_number}: blank JSONL line")
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}: line {line_number}: record must be an object")
            records.append(record)
    return records


def _required_string(record: dict[str, Any], key: str, line_number: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Line {line_number}: {key!r} must be a non-empty string")
    return value


def _parse_triples(value: Any, line_number: int) -> tuple[Triple, ...]:
    if not isinstance(value, list):
        raise ValueError(f"Line {line_number}: 'triples' must be a list")

    triples: list[Triple] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"Line {line_number}: triple {index} must be an object")
        triples.append(
            Triple(
                sub=_required_string(item, "sub", line_number),
                rel=_required_string(item, "rel", line_number),
                obj=_required_string(item, "obj", line_number),
            )
        )
    return tuple(triples)


def _index_by_id(records: list[dict[str, Any]], source: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for line_number, record in enumerate(records, start=1):
        record_id = _required_string(record, "id", line_number)
        if record_id in indexed:
            raise ValueError(f"{source}: duplicate id {record_id!r}")
        indexed[record_id] = record
    return indexed


def load_examples(input_path: Path, reference_path: Path) -> list[Example]:
    """Join prepared inputs and references by ID, rejecting missing or extra IDs."""
    inputs = _index_by_id(_read_jsonl(input_path), str(input_path))
    references = _index_by_id(_read_jsonl(reference_path), str(reference_path))

    missing_references = sorted(inputs.keys() - references.keys())
    missing_inputs = sorted(references.keys() - inputs.keys())
    if missing_references or missing_inputs:
        raise ValueError(
            "Input/reference ID mismatch: "
            f"missing references={missing_references}; "
            f"missing inputs={missing_inputs}"
        )

    examples: list[Example] = []
    for line_number, (example_id, record) in enumerate(inputs.items(), start=1):
        reference = references[example_id]
        examples.append(
            Example(
                id=example_id,
                text=_required_string(record, "text", line_number),
                ontology=_required_string(record, "ontology", line_number),
                triples=_parse_triples(reference.get("triples"), line_number),
            )
        )

    if not examples:
        raise ValueError(f"No examples found in {input_path}")
    return examples


def load_predictions(path: Path) -> list[Prediction]:
    """Load predictions using the shared project triple representation."""
    predictions: list[Prediction] = []
    seen_ids: set[str] = set()

    for line_number, record in enumerate(_read_jsonl(path), start=1):
        prediction_id = _required_string(record, "id", line_number)
        if prediction_id in seen_ids:
            raise ValueError(f"Line {line_number}: duplicate id {prediction_id!r}")
        seen_ids.add(prediction_id)
        predictions.append(
            Prediction(
                id=prediction_id,
                triples=_parse_triples(record.get("triples"), line_number),
            )
        )
    return predictions


def validate_alignment(examples: list[Example], predictions: list[Prediction]) -> None:
    """Reject unknown and missing prediction IDs explicitly."""
    expected = {example.id for example in examples}
    actual = {prediction.id for prediction in predictions}

    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)

    if unknown or missing:
        details = []
        if missing:
            details.append(f"missing prediction IDs ({len(missing)}): {missing}")
        if unknown:
            details.append(f"unknown prediction IDs ({len(unknown)}): {unknown}")
        raise ValueError("Prediction/reference ID mismatch: " + "; ".join(details))
