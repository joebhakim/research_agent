Model Evaluation Harness

Overview
- Probabilistic testing harness for model behavior.
- Separate from deterministic unit tests; uses repeated trials with binomial gating.
- Suites are fixture-driven unless you point to live content.

Running
- Example:
  uv run research-agent eval --config agent.yaml --suite evals/suites/smoke.yaml --trials 10 --temperature 0.2

Outputs
- Results are written under eval_runs/<suite_id>/<timestamp>/
- summary.json contains per-case success rates and p-values
- cases/<case_id>_t<temp>/trial_<n>.json contains payloads, validation results, and raw model calls

Suite Schema (YAML)
- suite_id: string
- description: string
- trials: int (default trials per case)
- model: local|openrouter (optional)
- temperature: float (optional, used if no profile or case override)
- temperature_profile: [float, ...] (optional, runs each case at each temperature)
- thinking_extent: low|medium|high|heavy (optional)
- fixtures_dir: path (optional; defaults to ../fixtures when suites live under evals/suites/)
- scoring: {threshold, p0, alpha, min_trials}
- cases: list of case entries

Case Schema (YAML)
- case_id: string
- stage: extract_propositions | reduce_claims | adjudicate_evidence | extract_trial_struct | meta_analysis
- inputs: stage-specific payload (documents, claim_text, evidence, effect_sizes)
- validators: list of {kind, params, weight}
- scoring: {threshold, p0, alpha, min_trials} (optional override)
- trials: int (optional override)
- temperature: float (optional override)
- model: local|openrouter (optional override)
- thinking_extent: low|medium|high|heavy (optional override)

Validators
- Rule validators are keyed by kind; params follow the rule implementation.
- Examples: path_regex, path_equals, path_abs_diff, list_len_at_least, required_paths.
- LLM-as-judge: set kind: llm_judge with params.criteria (or params.description).
- LLM-as-judge validators are skipped unless you pass --enable-llm-judge.

Scoring
- Per-trial score is the weighted fraction of validators that pass.
- Trial passes when score >= threshold.
- Case pass is decided by a binomial tail p-value over non-skipped trials.

Fixtures
- text_fixture paths are resolved relative to fixtures_dir (default: evals/fixtures/ for suites in evals/suites/).
- HTML fixtures are parsed via the HTML extractor; PDF fixtures use the PDF extractor.
