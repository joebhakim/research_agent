from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_trial(output_dir: Path, case_id: str, trial_index: int, payload: dict[str, Any]) -> Path:
    case_dir = output_dir / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    path = case_dir / f"trial_{trial_index:03d}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_summary(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "summary.json"
    path.write_text(json.dumps(payload, indent=2))
    return path
