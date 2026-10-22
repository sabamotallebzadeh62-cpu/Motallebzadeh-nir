"""Tests for the shared triple-metrics input contract."""

import json
from pathlib import Path

import pytest

from motallebzadeh_nir.metrics import (
    Example,
    Prediction,
    Triple,
    load_examples,
    load_predictions,
    validate_alignment,
)


def write_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def test_load_examples_joins_inputs_and_references_by_id(tmp_path: Path) -> None:
    inputs = write_jsonl(
        tmp_path / "inputs.jsonl",
        [{"id": "a", "text": "A sentence.", "ontology": "airport"}],
    )
    references = write_jsonl(
        tmp_path / "references.jsonl",
        [{"id": "a", "triples": [{"sub": "A", "rel": "locatedIn", "obj": "B"}]}],
    )

    examples = load_examples(inputs, references)

    assert examples == [
        Example(
            id="a",
            text="A sentence.",
            ontology="airport",
            triples=(Triple("A", "locatedIn", "B"),),
        )
    ]


def test_duplicate_triples_are_preserved_by_loader(tmp_path: Path) -> None:
    predictions_path = write_jsonl(
        tmp_path / "predictions.jsonl",
        [
            {
                "id": "a",
                "triples": [
                    {"sub": "A", "rel": "r", "obj": "B"},
                    {"sub": "A", "rel": "r", "obj": "B"},
                ],
            }
        ],
    )

    predictions = load_predictions(predictions_path)

    assert len(predictions[0].triples) == 2


def test_empty_prediction_is_valid_and_has_no_triples(tmp_path: Path) -> None:
    predictions_path = write_jsonl(
        tmp_path / "predictions.jsonl",
        [{"id": "a", "triples": []}],
    )

    predictions = load_predictions(predictions_path)

    assert predictions == [Prediction(id="a", triples=())]


def test_invalid_triple_is_rejected(tmp_path: Path) -> None:
    predictions_path = write_jsonl(
        tmp_path / "predictions.jsonl",
        [{"id": "a", "triples": [{"sub": "A", "rel": "", "obj": "B"}]}],
    )

    with pytest.raises(ValueError, match="rel"):
        load_predictions(predictions_path)


def test_input_reference_id_mismatch_is_rejected(tmp_path: Path) -> None:
    inputs = write_jsonl(
        tmp_path / "inputs.jsonl",
        [{"id": "a", "text": "Sentence.", "ontology": "airport"}],
    )
    references = write_jsonl(
        tmp_path / "references.jsonl",
        [{"id": "b", "triples": []}],
    )

    with pytest.raises(ValueError, match="ID mismatch"):
        load_examples(inputs, references)


def test_missing_and_unknown_prediction_ids_are_reported() -> None:
    examples = [
        Example("a", "Sentence A.", "airport", ()),
        Example("b", "Sentence B.", "airport", ()),
    ]
    predictions = [Prediction("unexpected", ())]

    with pytest.raises(ValueError, match="missing prediction IDs.*unknown prediction IDs"):
        validate_alignment(examples, predictions)
