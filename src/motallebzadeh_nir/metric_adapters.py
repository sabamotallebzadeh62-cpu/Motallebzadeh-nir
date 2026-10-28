"""Thin adapters around the pinned upstream triple-quality evaluators."""

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from motallebzadeh_nir.metrics import (
    Example,
    Prediction,
    validate_alignment,
)

TEXT2KGBENCH_COMMIT = "50a3d255371b8817cdff70fd88459ac82b339cfe4"
WEBNLG_COMMIT = "6a409508885bcd7b3a5d8e42f599fe6c3c6b8564"

ONTOLOGY_SUFFIXES = {
    "ont_3_airport": "3_airport",
    "ont_4_building": "4_building",
    "ont_5_athlete": "5_athlete",
    "ont_8_celestialbody": "8_celestialbody",
    "ont_11_meanoftransportation": "11_meanoftransportation",
}

WEBNLG_CATEGORIES = {
    "ont_3_airport": "Airport",
    "ont_4_building": "Building",
    "ont_5_athlete": "Athlete",
    "ont_8_celestialbody": "CelestialBody",
    "ont_11_meanoftransportation": "MeanOfTransportation",
}


class EvaluatorError(RuntimeError):
    """Raised when an official evaluator cannot produce a valid report."""


def _run_command(command: list[str], *, cwd: Path, timeout: int) -> None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvaluatorError(f"Could not complete evaluator command: {exc}") from exc

    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "No diagnostic output"
        raise EvaluatorError(f"Evaluator exited with status {result.returncode}: {details}")


def run_text2kgbench(
    examples: list[Example],
    predictions: list[Prediction],
    upstream_root: Path,
    *,
    timeout: int = 300,
) -> dict[str, Any]:
    """Run the official Text2KGBench evaluator on the supplied examples."""
    validate_alignment(examples, predictions)
    if not examples:
        raise ValueError("Text2KGBench requires at least one example.")

    upstream_root = upstream_root.resolve()
    script = upstream_root / "src/evaluation/run_eval.py"
    ontology_dir = upstream_root / "data/dbpedia_webnlg/ontologies"

    if not script.is_file():
        raise FileNotFoundError(f"Text2KGBench evaluator not found: {script}")

    prediction_by_id = {item.id: item for item in predictions}
    unknown_ontologies = sorted({item.ontology for item in examples} - ONTOLOGY_SUFFIXES.keys())
    if unknown_ontologies:
        raise ValueError(f"Unsupported Text2KGBench ontologies: {unknown_ontologies}")

    with tempfile.TemporaryDirectory(prefix="text2kgbench-") as temporary:
        work_dir = Path(temporary)
        path_patterns = {
            "sys": str(work_dir / "sys_$$onto$$.jsonl"),
            "gt": str(work_dir / "gt_$$onto$$.jsonl"),
            "onto": str(ontology_dir / "$$onto$$_ontology.json"),
            "output": str(work_dir / "case_results_$$onto$$.jsonl"),
        }
        suffixes = sorted({ONTOLOGY_SUFFIXES[item.ontology] for item in examples})

        for suffix in suffixes:
            ontology_id = next(key for key, value in ONTOLOGY_SUFFIXES.items() if value == suffix)
            ontology_examples = [item for item in examples if item.ontology == ontology_id]
            gt_path = work_dir / f"gt_{suffix}.jsonl"
            sys_path = work_dir / f"sys_{suffix}.jsonl"

            with (
                gt_path.open("w", encoding="utf-8") as gt_stream,
                sys_path.open("w", encoding="utf-8") as sys_stream,
            ):
                for example in ontology_examples:
                    gt_record = {
                        "id": example.id,
                        "sent": example.text,
                        "triples": [triple.as_text2kgbench() for triple in example.triples],
                    }
                    system_record = {
                        "id": example.id,
                        "triples": [
                            [triple.sub, triple.rel, triple.obj]
                            for triple in prediction_by_id[example.id].triples
                        ],
                    }
                    gt_stream.write(json.dumps(gt_record) + "\n")
                    sys_stream.write(json.dumps(system_record) + "\n")

        config_path = work_dir / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "onto_list": suffixes,
                    "path_patterns": path_patterns,
                    "avg_out_file": str(work_dir / "averages.jsonl"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        _run_command(
            [sys.executable, str(script), "--eval_config_path", str(config_path)],
            cwd=upstream_root,
            timeout=timeout,
        )

        averages_path = work_dir / "averages.jsonl"
        if not averages_path.is_file():
            raise EvaluatorError("Text2KGBench did not create its aggregate report.")

        try:
            rows = [
                json.loads(line)
                for line in averages_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except json.JSONDecodeError as exc:
            raise EvaluatorError("Text2KGBench aggregate report is invalid JSONL.") from exc

        global_rows = [
            row for row in rows if row.get("id") == "global" and row.get("type") == "global"
        ]
        if len(global_rows) != 1:
            raise EvaluatorError("Text2KGBench report must contain exactly one global aggregate.")

        global_report = {key: value for key, value in global_rows[0].items() if key != "onto_list"}

        return {
            "status": "success",
            "evaluator": "Text2KGBench",
            "upstream_commit": TEXT2KGBENCH_COMMIT,
            "example_count": len(examples),
            "global": global_report,
            "ontology_averages": [row for row in rows if row.get("type") == "all_test_cases"],
        }


def _build_webnlg_xml(
    examples: list[Example],
    prediction_by_id: dict[str, Prediction],
) -> bytes:
    """Build the minimal XML structure consumed by the official WebNLG script."""
    benchmark = ET.Element("benchmark")
    entries = ET.SubElement(benchmark, "entries")

    for example in examples:
        category = WEBNLG_CATEGORIES.get(example.ontology)
        if category is None:
            raise ValueError(f"Unsupported WebNLG ontology: {example.ontology}")

        entry = ET.SubElement(
            entries,
            "entry",
            {"category": category, "eid": example.id},
        )
        reference_set = ET.SubElement(entry, "modifiedtripleset")
        for triple in example.triples:
            ET.SubElement(reference_set, "mtriple").text = triple.as_webnlg()

        candidate_set = ET.SubElement(entry, "generatedtripleset")
        for triple in prediction_by_id[example.id].triples:
            ET.SubElement(candidate_set, "gtriple").text = triple.as_webnlg()

    return bytes(ET.tostring(benchmark, encoding="utf-8", xml_declaration=True))


def run_webnlg(
    examples: list[Example],
    predictions: list[Prediction],
    upstream_root: Path,
    *,
    timeout: int = 300,
) -> dict[str, Any]:
    """Run the official WebNLG evaluator and return its unmodified score payload."""
    validate_alignment(examples, predictions)
    if not examples:
        raise ValueError("WebNLG requires at least one example.")

    empty_ids = sorted(item.id for item in predictions if not item.triples)
    if empty_ids:
        raise EvaluatorError(
            "WebNLG's official scorer does not reliably support empty candidate "
            f"triple sets; evaluation aborted for IDs: {empty_ids}"
        )

    upstream_root = upstream_root.resolve()
    script = upstream_root / "Evaluation_script_json.py"
    if not script.is_file():
        raise FileNotFoundError(f"WebNLG evaluator not found: {script}")

    prediction_by_id = {item.id: item for item in predictions}

    with tempfile.TemporaryDirectory(prefix="webnlg-") as temporary:
        work_dir = Path(temporary)
        references_path = work_dir / "references.xml"
        candidates_path = work_dir / "candidates.xml"
        output_path = work_dir / "results.json"

        reference_xml = _build_webnlg_xml(examples, prediction_by_id)
        candidates_xml = _build_webnlg_xml(
            [Example(item.id, item.text, item.ontology, ()) for item in examples],
            prediction_by_id,
        )
        references_path.write_bytes(reference_xml)
        candidates_path.write_bytes(candidates_xml)

        _run_command(
            [
                sys.executable,
                str(script),
                str(references_path),
                str(candidates_path),
                str(output_path),
            ],
            cwd=upstream_root,
            timeout=timeout,
        )

        if not output_path.is_file():
            raise EvaluatorError("WebNLG did not create its result JSON.")

        try:
            scores = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise EvaluatorError("WebNLG result is invalid JSON.") from exc

        if not isinstance(scores, dict) or not {
            "Total_scores",
            "Exact_match",
        }.issubset(scores):
            raise EvaluatorError("WebNLG result is missing expected score sections.")

        return {
            "status": "success",
            "evaluator": "WebNLG",
            "upstream_commit": WEBNLG_COMMIT,
            "example_count": len(examples),
            "scores": scores,
        }
