from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from research_agent.evidence.policy import EvidencePolicy
from research_agent.llm.client import OpenAICompatClient


@dataclass
class LabeledEvidence:
    index: int
    label: str


def label_evidence(
    claim_text: str,
    evidence: list[dict[str, Any]],
    llm_client: OpenAICompatClient,
    policy: EvidencePolicy,
) -> list[str]:
    if not evidence:
        return []

    limited = evidence[: policy.max_evidence_per_claim]
    prompt = _build_prompt(claim_text, limited)
    response = llm_client.chat(
        [
            {"role": "system", "content": "You label evidence as support, refute, or neutral."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
    )
    labels = _parse_labels(response, len(limited))
    if not labels:
        labels = ["neutral"] * len(limited)
    return labels


def _build_prompt(claim_text: str, evidence: list[dict[str, Any]]) -> str:
    lines = [
        "Label each QUOTE as support, refute, or neutral for the CLAIM.",
        "Return JSON array only: [{\"index\":0,\"label\":\"support\"}, ...]",
        "CLAIM:",
        claim_text,
        "",
        "QUOTES:",
    ]
    for idx, item in enumerate(evidence):
        quote = str(item.get("quote", ""))
        title = str(item.get("title", ""))
        url = str(item.get("url", ""))
        lines.append(f"[{idx}] {quote}")
        if title:
            lines.append(f"Source: {title}")
        if url:
            lines.append(f"URL: {url}")
        lines.append("")
    return "\n".join(lines)


def _parse_labels(text: str, expected: int) -> list[str]:
    data = _parse_json_list(text)
    if not data:
        return []
    labels = ["neutral"] * expected
    for item in data:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        label = str(item.get("label", "")).strip().lower()
        if not isinstance(index, int):
            continue
        if index < 0 or index >= expected:
            continue
        if label not in {"support", "refute", "neutral"}:
            label = "neutral"
        labels[index] = label
    return labels


def _parse_json_list(text: str) -> list[Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return parsed
    return []
