from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ValidatorSpec:
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class ScoringSpec:
    threshold: float
    p0: float
    alpha: float
    min_trials: int


@dataclass
class EvalCase:
    case_id: str
    stage: str
    inputs: dict[str, Any]
    validators: list[ValidatorSpec]
    scoring: ScoringSpec
    model: str | None = None
    thinking_extent: str | None = None
    temperature: float | None = None
    trials: int | None = None


@dataclass
class EvalSuite:
    suite_id: str
    description: str
    trials: int
    model: str | None
    temperature: float | None
    temperature_profile: list[float] | None
    thinking_extent: str | None
    fixtures_dir: Path | None
    scoring_defaults: ScoringSpec
    cases: list[EvalCase]


def load_suite(path: Path) -> EvalSuite:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Suite YAML must be a mapping.")

    suite_id = str(data.get("suite_id", path.stem))
    description = str(data.get("description", ""))
    trials = int(data.get("trials", 10))
    model = _as_optional_str(data.get("model"))
    temperature = _as_optional_float(data.get("temperature"))
    temperature_profile = _load_temperature_profile(data.get("temperature_profile"))
    thinking_extent = _as_optional_str(data.get("thinking_extent"))
    fixtures_dir = _as_optional_path(data.get("fixtures_dir"))

    scoring_defaults = _load_scoring(data.get("scoring", {}))
    cases_data = data.get("cases", [])
    if not isinstance(cases_data, list):
        raise ValueError("Suite cases must be a list.")

    cases: list[EvalCase] = []
    for raw_case in cases_data:
        if not isinstance(raw_case, dict):
            continue
        cases.append(_load_case(raw_case, scoring_defaults))

    return EvalSuite(
        suite_id=suite_id,
        description=description,
        trials=trials,
        model=model,
        temperature=temperature,
        temperature_profile=temperature_profile,
        thinking_extent=thinking_extent,
        fixtures_dir=fixtures_dir,
        scoring_defaults=scoring_defaults,
        cases=cases,
    )


def _load_case(raw: dict[str, Any], scoring_defaults: ScoringSpec) -> EvalCase:
    case_id = str(raw.get("case_id", "case"))
    stage = str(raw.get("stage", "extract_propositions"))
    inputs = raw.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    validators = _load_validators(raw.get("validators", []))
    scoring = _load_scoring(raw.get("scoring", {}), defaults=scoring_defaults)
    return EvalCase(
        case_id=case_id,
        stage=stage,
        inputs=inputs,
        validators=validators,
        scoring=scoring,
        model=_as_optional_str(raw.get("model")),
        thinking_extent=_as_optional_str(raw.get("thinking_extent")),
        temperature=_as_optional_float(raw.get("temperature")),
        trials=_as_optional_int(raw.get("trials")),
    )


def _load_validators(raw: Any) -> list[ValidatorSpec]:
    validators: list[ValidatorSpec] = []
    if not isinstance(raw, list):
        return validators
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", ""))
        params = item.get("params", {})
        if not isinstance(params, dict):
            params = {}
        weight = float(item.get("weight", 1.0))
        validators.append(ValidatorSpec(kind=kind, params=params, weight=weight))
    return validators


def _load_scoring(raw: Any, defaults: ScoringSpec | None = None) -> ScoringSpec:
    if defaults is None:
        defaults = ScoringSpec(threshold=1.0, p0=0.8, alpha=0.05, min_trials=10)
    if not isinstance(raw, dict):
        return defaults
    return ScoringSpec(
        threshold=float(raw.get("threshold", defaults.threshold)),
        p0=float(raw.get("p0", defaults.p0)),
        alpha=float(raw.get("alpha", defaults.alpha)),
        min_trials=int(raw.get("min_trials", defaults.min_trials)),
    )


def _load_temperature_profile(raw: Any) -> list[float] | None:
    if not isinstance(raw, list):
        return None
    values: list[float] = []
    for item in raw:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            continue
    return values or None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_path(value: Any) -> Path | None:
    text = _as_optional_str(value)
    if text is None:
        return None
    return Path(text)
