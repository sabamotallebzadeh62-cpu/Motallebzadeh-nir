import json
from collections import Counter
from pathlib import Path

BASE = Path("data/raw/Text2KGBench/data/dbpedia_webnlg")


def read_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def normalize(text):
    return " ".join(text.casefold().split())


def main():
    errors = []
    test_dir = BASE / "test"
    train_dir = BASE / "train"
    gold_dir = BASE / "ground_truth"
    test_files = sorted(test_dir.glob("*_test.jsonl"))

    if not test_files:
        print(f"ERROR: no test files found under {test_dir}")
        return 1

    all_test_ids = []
    all_test_texts = []
    total = 0

    print(f"Dataset: {BASE}")
    print(f"Test files: {len(test_files)}")

    for test_path in test_files:
        ontology = test_path.name.removesuffix("_test.jsonl")
        train_path = train_dir / f"{ontology}_train.jsonl"
        gold_path = gold_dir / f"{ontology}_ground_truth.jsonl"

        if not train_path.exists() or not gold_path.exists():
            errors.append(f"{ontology}: train or ground-truth file missing")
            continue

        try:
            test = read_jsonl(test_path)
            train = read_jsonl(train_path)
            gold = read_jsonl(gold_path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue

        test_ids = [r.get("id") for r in test]
        gold_ids = [r.get("id") for r in gold]
        train_ids = [r.get("id") for r in train]

        if any(not isinstance(r.get("id"), str) or not r.get("id") for r in test):
            errors.append(f"{ontology}: missing or invalid test ID")
        if any(not isinstance(r.get("sent"), str) for r in test):
            errors.append(f"{ontology}: missing or invalid test sentence")
        if any(set(r) != {"id", "sent"} for r in test):
            errors.append(f"{ontology}: test records contain unexpected fields")
        if len(test_ids) != len(set(test_ids)):
            errors.append(f"{ontology}: duplicate test IDs")
        if len(train_ids) != len(set(train_ids)):
            errors.append(f"{ontology}: duplicate train IDs")
        if len(gold_ids) != len(set(gold_ids)):
            errors.append(f"{ontology}: duplicate gold IDs")
        if set(test_ids) != set(gold_ids):
            errors.append(f"{ontology}: test/gold IDs do not match")
        if any("triples" not in r for r in gold):
            errors.append(f"{ontology}: gold record missing triples")

        train_texts = {normalize(r["sent"]) for r in train if isinstance(r.get("sent"), str)}
        overlap = sum(
            1
            for r in test
            if isinstance(r.get("sent"), str) and normalize(r["sent"]) in train_texts
        )
        if overlap:
            errors.append(f"{ontology}: {overlap} test sentences exactly overlap train")

        def subjects(rows):
            return {
                triple.get("sub")
                for row in rows
                for triple in row.get("triples", [])
                if isinstance(triple, dict) and isinstance(triple.get("sub"), str)
            }

        shared_subjects = subjects(gold) & subjects(train)

        all_test_ids.extend(test_ids)
        all_test_texts.extend(normalize(r["sent"]) for r in test if isinstance(r.get("sent"), str))
        total += len(test)

        print(
            f"{ontology}: test={len(test)}, train={len(train)}, "
            f"gold={len(gold)}, shared_subjects={len(shared_subjects)}, "
            f"exact_text_overlap={overlap}"
        )

    duplicate_ids = len(all_test_ids) - len(set(all_test_ids))
    duplicate_texts = len(all_test_texts) - len(set(all_test_texts))
    print(f"\nTotal test records: {total}")
    print(f"Duplicate test IDs across files: {duplicate_ids}")
    print(f"Repeated normalized test texts: {duplicate_texts}")

    if duplicate_ids:
        errors.append("duplicate test IDs across ontology files")

    counts = Counter(all_test_texts)
    repeated = [text for text, count in counts.items() if count > 1]
    if repeated:
        print("Note: repeated test sentences require review; not automatically leakage.")

    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} issue(s)):")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nStructural validation passed.")
    print("Note: subject overlap is diagnostic, not proof of source-group independence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
