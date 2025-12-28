Research Agent Scaffold

This is a minimal scaffold for a claim-level research agent. It is CLI-only and uses SQLite for storage. Google PSE search is implemented; extraction and adjudication are model-assisted.

Setup (uv)

1) Create and activate a venv
   uv venv
   source .venv/bin/activate

2) Install dependencies
   uv pip install -e .

Usage

- Initialize the SQLite database:
  research-agent db-init --config agent.yaml

- Run a query:
  research-agent run --config agent.yaml "Your question here"

- Run offline with local sources:
  research-agent run --config agent.yaml --input-dir offline_sources "Your question here"

- Test model connectivity:
  research-agent llm-test --config agent.yaml --model local

- Run eval suites (probabilistic, requires model endpoint):
  research-agent eval --config agent.yaml --suite evals/suites/smoke.yaml --trials 10 --temperature 0.2

Configuration

- Copy and edit `agent.example.yaml` to `agent.yaml`.
- Secrets (e.g., model API base) are read from environment variables.
- Google PSE provider uses `GOOGLE_PSE_API_KEY` and `GOOGLE_PSE_CX` environment variables.
- Local model overrides: `MODEL_API_BASE`, `MODEL_NAME`, `MODEL_TIMEOUT_S`.
- OpenRouter auth and overrides: `OPENROUTER_API_KEY`, `OPENROUTER_APP_NAME`, `OPENROUTER_APP_URL`, `OPENROUTER_API_BASE`, `OPENROUTER_MODEL`, `OPENROUTER_TIMEOUT_S`.
- PDF extraction uses `pypdf` and may be incomplete depending on document structure.

Evaluation

- Eval suites live under `evals/suites/` and use fixtures in `evals/fixtures/` and `tests/fixtures/`.
- Eval outputs are written to `eval_runs/<suite_id>/<timestamp>/summary.json` and per-case trial artifacts.
- See `docs/evals.md` for harness details and YAML schema.

Offline MVP

- See `docs/mvp_runbook.md` for an offline-first end-to-end runbook.

Type checking (ty)

- Run `ty check src` (if installed).
