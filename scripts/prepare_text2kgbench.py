"""Prepare deterministic dev/eval samples of Text2KGBench (DBpedia-WebNLG).

Development sentences come from the upstream train split and evaluation sentences from the
upstream test split. Evaluation items sharing a subject entity with a development item of the
same ontology are excluded. Raw data stays in the ignored data/ folder; only the manifest is
tracked by Git.
"""

import argparse
import hashlib
import json
import random
import subprocess
from pathlib import Path

RAW = Path("data/raw/Text2KGBench")
BASE = RAW / "data/dbpedia_webnlg"
OUT = Path("data/prepared/text2kgbench")
MANIFEST = Path("configs/data-manifest.json")
ONTOLOGIES = [
    "ont_3_airport",
    "ont_4_building",
    "ont_5_athlete",
    "ont_11_meanoftransportation",
    "ont_8_celestialbody",
]
DEV_PER_ONTOLOGY = 6
EVAL_PER_ONTOLOGY = 20


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subjects(row):
    return {t["sub"] for t in row["triples"]}


def by_id(rows):
    return sorted(rows, key=lambda r: r["id"])


def select(seed):
    chosen = {"dev": [], "eval": []}
    used_files = []
    for ont in ONTOLOGIES:
        train_path = BASE / "train" / f"{ont}_train.jsonl"
        gold_path = BASE / "ground_truth" / f"{ont}_ground_truth.jsonl"
        used_files += [train_path, gold_path]
        train = by_id(read_jsonl(train_path))
        gold = by_id(read_jsonl(gold_path))
        rng = random.Random(f"{seed}:{ont}")
        dev = by_id(rng.sample(train, DEV_PER_ONTOLOGY))
        dev_subjects = set().union(*(subjects(r) for r in dev))
        eligible = [r for r in gold if not subjects(r) & dev_subjects]
        if len(eligible) < EVAL_PER_ONTOLOGY:
            raise SystemExit(f"{ont}: only {len(eligible)} eligible evaluation items")
        evaluation = by_id(rng.sample(eligible, EVAL_PER_ONTOLOGY))
        chosen["dev"] += [(ont, r) for r in dev]
        chosen["eval"] += [(ont, r) for r in evaluation]
    return chosen, used_files


def split_records(chosen):
    inputs, refs, items = {}, {}, []
    for split, pairs in chosen.items():
        inputs[split] = [{"id": r["id"], "text": r["sent"], "ontology": ont} for ont, r in pairs]
        refs[split] = [{"id": r["id"], "triples": r["triples"]} for _, r in pairs]
        for ont, r in pairs:
            items.append(
                {
                    "split": split,
                    "ontology": ont,
                    "id": r["id"],
                    "group_id": f"{ont}:{min(subjects(r))}",
                }
            )
    return inputs, refs, items


def validate(chosen, inputs):
    problems = []
    expected = {
        "dev": len(ONTOLOGIES) * DEV_PER_ONTOLOGY,
        "eval": len(ONTOLOGIES) * EVAL_PER_ONTOLOGY,
    }
    all_ids = []
    for split, pairs in chosen.items():
        if len(pairs) != expected[split]:
            problems.append(f"{split}: expected {expected[split]} items, got {len(pairs)}")
        all_ids += [r["id"] for _, r in pairs]
    if len(all_ids) != len(set(all_ids)):
        problems.append("duplicate IDs across splits")
    for ont in ONTOLOGIES:
        dev_subj = set().union(*(subjects(r) for o, r in chosen["dev"] if o == ont))
        eval_subj = set().union(*(subjects(r) for o, r in chosen["eval"] if o == ont))
        if dev_subj & eval_subj:
            problems.append(f"{ont}: dev and eval share subjects")
    for split, rows in inputs.items():
        if any(set(r) != {"id", "text", "ontology"} for r in rows):
            problems.append(f"{split}: inputs contain unexpected fields (gold leak?)")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    chosen, used_files = select(args.seed)
    inputs, refs, items = split_records(chosen)
    problems = validate(chosen, inputs)
    if problems:
        print("VALIDATION FAILED:")
        for p in problems:
            print("-", p)
        return 1

    for split in inputs:
        write_jsonl(OUT / f"{split}_inputs.jsonl", inputs[split])
        write_jsonl(OUT / f"{split}_references.jsonl", refs[split])

    commit = subprocess.run(
        ["git", "-C", str(RAW), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    manifest = {
        "manifest_version": 1,
        "status": "proposal; ontology choice pending curator approval",
        "dataset": {
            "name": "Text2KGBench, DBpedia-WebNLG part",
            "source": "https://github.com/cenguix/Text2KGBench",
            "commit": commit,
            "data_license_note": (
                "Derived from WebNLG 3.0 (CC BY-NC-SA 4.0); treat as research use only."
            ),
        },
        "seed": args.seed,
        "ontologies": ONTOLOGIES,
        "selection_rule": (
            f"dev: {DEV_PER_ONTOLOGY} random train sentences per ontology; eval: "
            f"{EVAL_PER_ONTOLOGY} random test sentences per ontology, excluding those "
            "sharing a subject entity with a dev item of the same ontology."
        ),
        "group_rule": (
            "group_id approximated as ontology plus the alphabetically smallest subject "
            "entity; upstream files have no original WebNLG IDs."
        ),
        "counts": {split: len(rows) for split, rows in inputs.items()},
        "limitations": [
            "Only Text2KGBench DBpedia-WebNLG is covered; MINE and WebNLG are not included.",
            "Cross-benchmark overlap with WebNLG has not been checked.",
            "group_id is an approximation of source groups.",
            "Ontology choice is a proposal pending curator approval.",
        ],
        "file_sha256": {str(p.relative_to(RAW)): sha256(p) for p in used_files},
        "items": items,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"seed={args.seed} commit={commit}")
    print("counts:", manifest["counts"])
    print(f"wrote {MANIFEST} and files under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
