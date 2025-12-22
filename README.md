Research Agent Scaffold

This is a minimal scaffold for a claim-level research agent. It is CLI-only and uses SQLite for storage. Search providers and parsing are stubbed with TODOs.

Setup (uv)

1) Create and activate a venv
   uv venv
   source .venv/bin/activate

2) Install dependencies
   uv pip install -e .

Usage

- Initialize the SQLite database:
  research-agent db-init --config agent.yaml

- Run a query (stubbed search/providers):
  research-agent run --config agent.yaml "Your question here"

Configuration

- Copy and edit `agent.example.yaml` to `agent.yaml`.
- Secrets (e.g., model API base) are read from environment variables.

Type checking (ty)

- Run `ty check src` (if installed).
