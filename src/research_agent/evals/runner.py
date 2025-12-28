from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from research_agent.config import AppConfig
from research_agent.evals.artifacts import write_summary, write_trial
from research_agent.evals.cases import EvalCase, EvalSuite, load_suite
from research_agent.evals.judges.llm import LLMJudge
from research_agent.evals.judges.rule import ValidationResult, validate
from research_agent.evals.stages import (
    run_adjudicate_evidence,
    run_extract_propositions,
    run_extract_trial_struct,
    run_meta_analysis,
    run_reduce_claims,
)
from research_agent.evals.stats import binomial_tail_p_value
from research_agent.evals.utils import load_document_text
from research_agent.llm.router import get_model_client


@dataclass
class CaseSummary:
    case_id: str
    stage: str
    temperature: float
    passed: bool
    p_value: float | None
    pass_rate: float
    k: int
    n: int
    skipped: int
    score_threshold: float
    p0: float
    alpha: float
    min_trials: int
    model_choice: str
    model_name: str
    details: list[dict[str, Any]]


def run_suite(
    suite_path: Path,
    config: AppConfig,
    trials_override: int | None = None,
    model_override: str | None = None,
    output_dir: Path | None = None,
    temperature_override: float | None = None,
    enable_llm_judge: bool = False,
) -> Path:
    suite = load_suite(suite_path)
    fixtures_dir = _resolve_fixtures_dir(suite_path, suite.fixtures_dir)

    output_root = output_dir or Path("eval_runs")
    run_dir = output_root / suite.suite_id / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[CaseSummary] = []
    for case in suite.cases:
        temperatures = _resolve_temperatures(suite, case, temperature_override)
        for temperature in temperatures:
            summary = _run_case(
                case=case,
                suite=suite,
                config=config,
                trials_override=trials_override,
                model_override=model_override,
                run_dir=run_dir,
                fixtures_dir=fixtures_dir,
                temperature=temperature,
                enable_llm_judge=enable_llm_judge,
            )
            summaries.append(summary)

    summary_payload = {
        "suite_id": suite.suite_id,
        "description": suite.description,
        "suite_trials": suite.trials,
        "trials_override": trials_override,
        "temperature_override": temperature_override,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cases": [asdict(item) for item in summaries],
    }
    write_summary(run_dir, summary_payload)
    return run_dir


def _run_case(
    case: EvalCase,
    suite: EvalSuite,
    config: AppConfig,
    trials_override: int | None,
    model_override: str | None,
    run_dir: Path,
    fixtures_dir: Path,
    temperature: float,
    enable_llm_judge: bool,
) -> CaseSummary:
    trials = trials_override or case.trials or suite.trials
    thinking_extent = case.thinking_extent or suite.thinking_extent or config.agent.thinking.extent
    case_model = case.model or suite.model
    routed = get_model_client(
        config,
        thinking_extent=thinking_extent,
        override=model_override or case_model,
    )

    successes = 0
    failures = 0
    skipped = 0
    trial_details: list[dict[str, Any]] = []
    case_key = f"{case.case_id}_t{temperature:g}"
    for trial_index in range(1, trials + 1):
        recording_client = RecordingClient(routed.client, override_temperature=temperature)
        stage_result = _run_stage(case, recording_client, fixtures_dir, thinking_extent, temperature)
        trial_judge = LLMJudge(
            enabled=enable_llm_judge,
            llm_client=recording_client if enable_llm_judge else None,
        )
        validation = _validate_case(case, stage_result.payload, trial_judge)
        score = _score_validation(validation)
        if score is None:
            skipped += 1
            passed = False
        else:
            passed = score >= case.scoring.threshold
            if passed:
                successes += 1
            else:
                failures += 1

        trial_payload = {
            "case_id": case.case_id,
            "trial": trial_index,
            "stage": case.stage,
            "temperature": temperature,
            "payload": stage_result.payload,
            "errors": stage_result.errors,
            "validation": [asdict(item) for item in validation],
            "score": score,
            "passed": passed,
            "skipped": score is None,
            "raw_calls": recording_client.calls,
        }
        write_trial(run_dir, case_key, trial_index, trial_payload)
        trial_details.append(
            {
                "trial": trial_index,
                "score": score,
                "passed": passed,
                "skipped": score is None,
            }
        )

    total = successes + failures
    p_value = None
    passed = False
    if total >= case.scoring.min_trials:
        p_value = binomial_tail_p_value(total, successes, case.scoring.p0)
        passed = p_value < case.scoring.alpha

    pass_rate = successes / total if total else 0.0

    return CaseSummary(
        case_id=case.case_id,
        stage=case.stage,
        temperature=temperature,
        passed=passed,
        p_value=p_value,
        pass_rate=pass_rate,
        k=successes,
        n=total,
        skipped=skipped,
        score_threshold=case.scoring.threshold,
        p0=case.scoring.p0,
        alpha=case.scoring.alpha,
        min_trials=case.scoring.min_trials,
        model_choice=routed.name,
        model_name=routed.client.model_name,
        details=trial_details,
    )


def _run_stage(
    case: EvalCase,
    llm_client,
    fixtures_dir: Path,
    thinking_extent: str,
    temperature: float,
) -> Any:
    stage = case.stage
    inputs = case.inputs
    documents = []
    if "documents" in inputs:
        for doc in inputs.get("documents", []):
            if isinstance(doc, dict):
                documents.append(load_document_text(doc, fixtures_dir))

    if stage == "extract_propositions":
        return run_extract_propositions(
            documents,
            llm_client,
            thinking_extent,
        )
    if stage == "reduce_claims":
        return run_reduce_claims(
            documents,
            llm_client,
            thinking_extent,
        )
    if stage == "adjudicate_evidence":
        claim_text = str(inputs.get("claim_text", ""))
        evidence = inputs.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
        return run_adjudicate_evidence(
            claim_text,
            evidence,
            llm_client,
            thinking_extent,
        )
    if stage == "extract_trial_struct":
        return run_extract_trial_struct(documents, llm_client, temperature)
    if stage == "meta_analysis":
        effect_sizes = inputs.get("effect_sizes", [])
        if not isinstance(effect_sizes, list):
            effect_sizes = []
        return run_meta_analysis(effect_sizes)

    raise ValueError(f"Unknown stage: {stage}")


def _validate_case(
    case: EvalCase,
    payload: dict[str, Any],
    llm_judge: LLMJudge,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for validator in case.validators:
        if validator.kind == "llm_judge":
            results.append(llm_judge.validate(payload, validator.params, validator.weight))
            continue
        results.append(validate(payload, validator.kind, validator.params, validator.weight))
    return results


def _score_validation(results: list[ValidationResult]) -> float | None:
    total = 0.0
    earned = 0.0
    for result in results:
        if result.skipped:
            continue
        total += result.weight
        if result.passed:
            earned += result.weight
    if total == 0:
        return None
    return earned / total


def _resolve_fixtures_dir(suite_path: Path, fixtures_dir: Path | None) -> Path:
    if fixtures_dir is None:
        if suite_path.parent.name == "suites":
            return (suite_path.parent.parent / "fixtures").resolve()
        return (suite_path.parent / "fixtures").resolve()
    if fixtures_dir.is_absolute():
        return fixtures_dir
    return (suite_path.parent / fixtures_dir).resolve()


def _resolve_temperatures(
    suite: EvalSuite,
    case: EvalCase,
    override: float | None,
) -> list[float]:
    if override is not None:
        return [float(override)]
    if case.temperature is not None:
        return [case.temperature]
    if suite.temperature_profile:
        return suite.temperature_profile
    if suite.temperature is not None:
        return [suite.temperature]
    return [0.1]


class RecordingClient:
    def __init__(self, client, override_temperature: float | None = None) -> None:
        self._client = client
        self.calls: list[dict[str, Any]] = []
        self.override_temperature = override_temperature
        self.model_name = client.model_name
        self.api_base = client.api_base

    def chat(self, messages, temperature: float = 0.2, max_tokens: int = 512) -> str:
        if self.override_temperature is not None:
            temperature = self.override_temperature
        response = self._client.chat(messages, temperature=temperature, max_tokens=max_tokens)
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response": response,
            }
        )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
