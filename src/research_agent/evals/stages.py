from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from research_agent.evidence.adjudicate import label_evidence
from research_agent.evidence.reduce import reduce_evidence
from research_agent.evidence.extract import extract_propositions
from research_agent.evidence.policy import policy_for_extent
from research_agent.llm.client import OpenAICompatClient
from research_agent.types import DocumentText, Proposition
from research_agent.evals.utils import parse_json, to_jsonable


@dataclass
class StageResult:
    payload: dict[str, Any]
    errors: list[str]


def run_extract_propositions(
    documents: list[DocumentText],
    llm_client: OpenAICompatClient,
    thinking_extent: str,
) -> StageResult:
    policy = policy_for_extent(thinking_extent)
    propositions: list[Proposition] = []
    for doc in documents:
        propositions.extend(extract_propositions(doc, llm_client, policy))
    payload = {"propositions": to_jsonable(propositions)}
    return StageResult(payload=payload, errors=[])


def run_reduce_claims(
    documents: list[DocumentText],
    llm_client: OpenAICompatClient,
    thinking_extent: str,
) -> StageResult:
    result = reduce_evidence(documents, llm_client, thinking_extent)
    payload = {
        "propositions": to_jsonable(result.propositions),
        "claim_groups": to_jsonable(result.claim_groups),
    }
    return StageResult(payload=payload, errors=[])


def run_adjudicate_evidence(
    claim_text: str,
    evidence: list[dict[str, Any]],
    llm_client: OpenAICompatClient,
    thinking_extent: str,
) -> StageResult:
    policy = policy_for_extent(thinking_extent)
    labels = label_evidence(claim_text, evidence, llm_client, policy)
    payload = {"labels": labels, "claim_text": claim_text, "evidence": evidence}
    return StageResult(payload=payload, errors=[])


def run_extract_trial_struct(
    documents: list[DocumentText],
    llm_client: OpenAICompatClient,
    temperature: float,
) -> StageResult:
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    for doc in documents:
        prompt = _trial_struct_prompt(doc.text)
        response = llm_client.chat(
            [
                {"role": "system", "content": "You extract structured trial data."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=1200,
        )
        parsed = parse_json(response)
        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]
        if isinstance(parsed, dict):
            records.append(parsed)
        else:
            errors.append(f"parse_failed:{doc.doc_id}")

    payload = {"records": records}
    return StageResult(payload=payload, errors=errors)


def run_meta_analysis(effect_sizes: list[dict[str, Any]]) -> StageResult:
    result = _fixed_effect_meta(effect_sizes)
    return StageResult(payload=result, errors=[])


def _trial_struct_prompt(text: str) -> str:
    return (
        "Extract a single clinical trial record as JSON. Use null for missing fields.\n"
        "Return JSON object only with keys:\n"
        "study_id, title, population, intervention, comparator, sample_size, "
        "analysis_population, setting, registry_id, registry_url, notes,\n"
        "design: {randomized, blinding, phase, multicenter},\n"
        "outcomes: [\n"
        "  {name, type, measure, timepoint, effect_estimates: [\n"
        "    {measure_type, estimate, ci_low, ci_high, unit, p_value, direction, n}\n"
        "  ]}\n"
        "]\n\n"
        "TEXT:\n"
        + text
    )


def _fixed_effect_meta(effect_sizes: list[dict[str, Any]]) -> dict[str, Any]:
    estimates = []
    weights = []
    measure_types = set()
    for item in effect_sizes:
        measure = item.get("measure_type")
        estimate = item.get("estimate")
        se = item.get("std_error")
        if measure:
            measure_types.add(str(measure))
        if estimate is None or se in (None, 0):
            continue
        try:
            estimate_val = float(estimate)
            se_val = float(se)
        except (TypeError, ValueError):
            continue
        weight = 1.0 / (se_val * se_val)
        estimates.append(estimate_val)
        weights.append(weight)

    if not estimates or len(measure_types) > 1:
        return {"status": "insufficient", "pooled_estimate": None}

    total_weight = sum(weights)
    pooled = sum(w * e for w, e in zip(weights, estimates)) / total_weight
    se_pooled = (1.0 / total_weight) ** 0.5
    ci_low = pooled - 1.96 * se_pooled
    ci_high = pooled + 1.96 * se_pooled
    return {
        "status": "ok",
        "pooled_estimate": pooled,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "k": len(estimates),
        "measure_type": list(measure_types)[0] if measure_types else None,
    }
