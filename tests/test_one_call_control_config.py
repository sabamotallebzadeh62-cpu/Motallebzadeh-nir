from pathlib import Path

from motallebzadeh_nir.extraction import ExtractionConfig

CONFIG_PATH = Path("configs/one-call-control-dev.yaml")


def test_one_call_control_config_loads() -> None:
    cfg = ExtractionConfig.from_yaml(CONFIG_PATH)
    assert cfg.name == "one-call-control-dev"
    assert cfg.model_family == "llm-one-call-verify"
    assert cfg.max_format_repairs == 1
    assert cfg.temperature == 0.0
    assert cfg.max_tokens == 2048


def test_one_call_prompt_contains_verification_rules() -> None:
    cfg = ExtractionConfig.from_yaml(CONFIG_PATH)
    prompt = cfg.prompt
    for token in ("supported", "unsupported", "uncertain", "evidence"):
        assert token in prompt, f"missing verification rule: {token}"


def test_one_call_prompt_has_no_canonicalization_instructions() -> None:
    cfg = ExtractionConfig.from_yaml(CONFIG_PATH)
    prompt = cfg.prompt.lower()
    assert "do not rename relations" in prompt
    assert "merge entities" in prompt
