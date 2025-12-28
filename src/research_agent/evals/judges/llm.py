from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from research_agent.evals.judges.rule import ValidationResult
from research_agent.llm.client import OpenAICompatClient
from research_agent.evals.utils import parse_json


@dataclass
class LLMJudge:
    enabled: bool
    llm_client: OpenAICompatClient | None

    def validate(self, payload: dict[str, Any], params: dict[str, Any], weight: float) -> ValidationResult:
        if not self.enabled or self.llm_client is None:
            return ValidationResult(
                kind="llm_judge",
                passed=False,
                weight=weight,
                message="llm judge disabled",
                skipped=True,
            )

        prompt = _build_prompt(payload, params)
        response = self.llm_client.chat(
            [
                {"role": "system", "content": "You are a strict evaluator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        parsed = parse_json(response)
        if not isinstance(parsed, dict):
            return ValidationResult(
                kind="llm_judge",
                passed=False,
                weight=weight,
                message="llm judge parse failed",
            )
        verdict = bool(parsed.get("pass", False))
        message = str(parsed.get("rationale", ""))
        return ValidationResult(kind="llm_judge", passed=verdict, weight=weight, message=message)


def _build_prompt(payload: dict[str, Any], params: dict[str, Any]) -> str:
    criteria = params.get("criteria") or params.get("description", "")
    return (
        "Evaluate the payload against the criteria.\n"
        "Return JSON only: {\"pass\": true|false, \"rationale\": \"...\"}.\n\n"
        f"CRITERIA:\n{criteria}\n\n"
        f"PAYLOAD:\n{json.dumps(payload, indent=2)}"
    )
