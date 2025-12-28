from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from research_agent.evals.utils import as_strings, expand_path, to_float


@dataclass
class ValidationResult:
    kind: str
    passed: bool
    weight: float
    message: str
    skipped: bool = False


def validate(payload: dict[str, Any], kind: str, params: dict[str, Any], weight: float) -> ValidationResult:
    if kind == "path_exists":
        return _path_exists(payload, params, weight)
    if kind == "path_regex":
        return _path_regex(payload, params, weight)
    if kind == "path_equals":
        return _path_equals(payload, params, weight)
    if kind == "path_in":
        return _path_in(payload, params, weight)
    if kind == "path_numeric_range":
        return _path_numeric_range(payload, params, weight)
    if kind == "path_abs_diff":
        return _path_abs_diff(payload, params, weight)
    if kind == "list_len_at_least":
        return _list_len_at_least(payload, params, weight)
    if kind == "required_paths":
        return _required_paths(payload, params, weight)

    return ValidationResult(kind=kind, passed=False, weight=weight, message="unknown validator")


def _path_exists(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    values = expand_path(payload, path)
    passed = any(_has_value(value) for value in values)
    return ValidationResult(kind="path_exists", passed=passed, weight=weight, message=f"path={path}")


def _path_regex(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    pattern = str(params.get("pattern", ""))
    min_matches = int(params.get("min_matches", 1))
    flags = re.IGNORECASE if bool(params.get("case_insensitive", True)) else 0

    values = as_strings(expand_path(payload, path))
    matches = 0
    for value in values:
        if re.search(pattern, value, flags=flags):
            matches += 1
    passed = matches >= min_matches
    return ValidationResult(
        kind="path_regex",
        passed=passed,
        weight=weight,
        message=f"path={path} pattern={pattern} matches={matches}",
    )


def _path_equals(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    expected = params.get("value")
    values = expand_path(payload, path)
    passed = any(value == expected for value in values)
    return ValidationResult(
        kind="path_equals",
        passed=passed,
        weight=weight,
        message=f"path={path} expected={expected}",
    )


def _path_in(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    expected = params.get("values", [])
    if not isinstance(expected, list):
        expected = [expected]
    values = expand_path(payload, path)
    passed = any(value in expected for value in values)
    return ValidationResult(kind="path_in", passed=passed, weight=weight, message=f"path={path}")


def _path_numeric_range(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    min_val = params.get("min")
    max_val = params.get("max")
    values = [to_float(value) for value in expand_path(payload, path)]
    values = [value for value in values if value is not None]
    passed = False
    for value in values:
        if min_val is not None and value < float(min_val):
            continue
        if max_val is not None and value > float(max_val):
            continue
        passed = True
        break
    return ValidationResult(kind="path_numeric_range", passed=passed, weight=weight, message=f"path={path}")


def _path_abs_diff(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    target = to_float(params.get("target"))
    tolerance = to_float(params.get("tolerance"))
    if target is None or tolerance is None:
        return ValidationResult(kind="path_abs_diff", passed=False, weight=weight, message="missing target/tolerance")
    values = [to_float(value) for value in expand_path(payload, path)]
    values = [value for value in values if value is not None]
    passed = any(abs(value - target) <= tolerance for value in values)
    return ValidationResult(kind="path_abs_diff", passed=passed, weight=weight, message=f"path={path}")


def _list_len_at_least(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    path = str(params.get("path", ""))
    minimum = int(params.get("min_len", 1))
    values = expand_path(payload, path)
    length = len(values[0]) if values and isinstance(values[0], list) else 0
    passed = length >= minimum
    return ValidationResult(kind="list_len_at_least", passed=passed, weight=weight, message=f"path={path}")


def _required_paths(payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
    paths = params.get("paths", [])
    if not isinstance(paths, list):
        return ValidationResult(kind="required_paths", passed=False, weight=weight, message="paths must be list")
    missing = []
    for path in paths:
        values = expand_path(payload, str(path))
        if not any(_has_value(value) for value in values):
            missing.append(path)
    passed = not missing
    return ValidationResult(
        kind="required_paths",
        passed=passed,
        weight=weight,
        message=f"missing={missing}",
    )


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list) or isinstance(value, dict):
        return bool(value)
    return True
