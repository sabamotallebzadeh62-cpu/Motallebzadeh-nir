import pytest
from pydantic import ValidationError

from motallebzadeh_nir.extraction_types import (
    ExtractionResult,
    Status,
    Triple,
    Usage,
    make_triple_id,
)


def test_empty_graph_is_valid_success() -> None:
    result = ExtractionResult(
        document_id="d1", chunk_id="c1", model_id="m", status=Status.OK, triples=[]
    )
    assert result.status is Status.OK
    assert result.triples == []
    assert result.error is None


def test_failed_result_needs_error() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(document_id="d1", chunk_id="c1", model_id="m", status=Status.FAILED)


def test_failed_result_with_error_is_valid() -> None:
    result = ExtractionResult(
        document_id="d1",
        chunk_id="c1",
        model_id="m",
        status=Status.FAILED,
        error="timeout",
    )
    assert result.status is Status.FAILED
    assert result.triples == []


def test_ok_result_must_not_have_error() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(document_id="d1", chunk_id="c1", model_id="m", status=Status.OK, error="x")


def test_triple_id_is_stable() -> None:
    a = make_triple_id("d1", "Paris", "capital_of", "France")
    b = make_triple_id("d1", " paris ", "Capital_Of", "france")
    assert a == b
    assert a != make_triple_id("d2", "Paris", "capital_of", "France")


def test_unknown_usage_stays_none() -> None:
    assert Usage().input_tokens is None
    assert Usage().output_tokens is None


def test_ok_result_with_triple() -> None:
    triple = Triple(
        triple_id=make_triple_id("d1", "Paris", "capital_of", "France"),
        document_id="d1",
        subject="Paris",
        predicate="capital_of",
        object="France",
        evidence="Paris is the capital of France.",
    )
    result = ExtractionResult(
        document_id="d1",
        chunk_id="c1",
        model_id="m",
        status=Status.OK,
        triples=[triple],
        usage=Usage(input_tokens=10, output_tokens=5),
    )
    assert len(result.triples) == 1


def test_triple_id_distinguishes_delimiter_collisions() -> None:
    first = make_triple_id("d1", "a|b", "c", "d")
    second = make_triple_id("d1", "a", "b|c", "d")

    assert first != second


def test_result_rejects_triple_from_different_document() -> None:
    triple = Triple(
        triple_id=make_triple_id("d2", "Alice", "knows", "Bob"),
        document_id="d2",
        subject="Alice",
        predicate="knows",
        object="Bob",
    )

    with pytest.raises(ValidationError):
        ExtractionResult(
            document_id="d1",
            chunk_id="c1",
            model_id="m",
            status=Status.OK,
            triples=[triple],
        )
