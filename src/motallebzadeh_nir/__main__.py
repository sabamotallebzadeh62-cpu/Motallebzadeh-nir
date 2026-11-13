"""Run one experiment: `uv run python -m motallebzadeh_nir --config configs/smoke.yaml`."""

import argparse
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from motallebzadeh_nir.config import load_settings
from motallebzadeh_nir.pipeline import ExperimentConfig, run_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="motallebzadeh_nir", description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="experiment config, YAML")
    args = parser.parse_args(argv)

    load_dotenv()  # MLflow and boto read the S3 keys from the environment, not from Settings
    settings = load_settings()
    with args.config.open(encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)
    if raw.pop("kind", None) == "extraction":
        from motallebzadeh_nir.extraction import ExtractionConfig
        from motallebzadeh_nir.extraction_run import run_extraction

        extraction = run_extraction(
            ExtractionConfig.from_yaml(args.config), settings, config_path=args.config
        )
        print(
            f"run_id={extraction.run_id} chunks={extraction.n_chunks} ok={extraction.n_ok} "
            f"empty={extraction.n_empty} failed={extraction.n_failed}"
        )
        return 0
    cfg = ExperimentConfig.from_yaml(args.config)
    result = run_experiment(cfg, settings, config_path=args.config)
    print(f"run_id={result.run_id} mse={result.mse:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
