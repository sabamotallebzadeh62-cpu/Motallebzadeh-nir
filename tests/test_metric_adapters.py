"""Tests for the official triple-evaluator adapters."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from motallebzadeh_nir.metric_adapters import (
    EvaluatorError,
    _build_webnlg_xml,
    run_webnlg,
)
from motallebzadeh_nir.metrics import Example, Prediction, Triple


def test_webnlg_xml_contains_reference_and_candidate_triples() -> None:
    example = Example(
        id="sample-1",
        text="A is located in B.",
        ontology="ont_3_airport",
        triples=(Triple("A", "locatedIn", "B"),),
    )
    prediction = Prediction(
        id="sample-1",
        triples=(Triple("A", "locatedIn", "B"),),
    )

    root = ET.fromstring(_build_webnlg_xml([example], {"sample-1": prediction}))
    entry = root.find("./entries/entry")

    assert entry is not None
    assert entry.attrib["eid"] == "sample-1"
    assert entry.findtext("./modifiedtripleset/mtriple") == "A | locatedIn | B"
    assert entry.findtext("./generatedtripleset/gtriple") == "A | locatedIn | B"


def test_webnlg_xml_escapes_xml_special_characters() -> None:
    example = Example(
        id="sample-2",
        text="A & B.",
        ontology="ont_3_airport",
        triples=(Triple("A & B", "locatedIn", "C"),),
    )
    prediction = Prediction(
        id="sample-2",
        triples=(Triple("A & B", "locatedIn", "C"),),
    )

    xml_bytes = _build_webnlg_xml([example], {"sample-2": prediction})
    root = ET.fromstring(xml_bytes)

    assert root.findtext("./entries/entry/modifiedtripleset/mtriple") == ("A & B | locatedIn | C")


def test_webnlg_rejects_empty_predictions_before_invoking_evaluator(
    tmp_path: Path,
) -> None:
    example = Example("sample-3", "A sentence.", "ont_3_airport", ())
    prediction = Prediction("sample-3", ())

    with pytest.raises(EvaluatorError, match="empty candidate"):
        run_webnlg([example], [prediction], tmp_path)


def test_webnlg_rejects_unsupported_ontology() -> None:
    example = Example("sample-4", "A sentence.", "unsupported", ())
    prediction = Prediction(
        "sample-4",
        (Triple("A", "relatedTo", "B"),),
    )

    with pytest.raises(ValueError, match="Unsupported WebNLG ontology"):
        _build_webnlg_xml([example], {"sample-4": prediction})
