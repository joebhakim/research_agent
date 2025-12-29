# Research Agent - Development Guide

## Project Overview

This is a claim-level research agent with LLM-assisted evidence extraction, canonicalization, grouping, and adjudication. It supports both live search (Google PSE, Brave, Tavily, Serper) and offline operation with local HTML/PDF sources.

**Core pipeline**: Search → Fetch/Parse → Extract Propositions → Canonicalize → Group Claims → Adjudicate Evidence → Reduce & Report

## Type Checking

We use strict type checking with `ty`:

```bash
# Check core modules
uv run ty check src/research_agent/

# Check tests
uv run ty check tests/
```

**Requirements**:
- All new code must include type annotations
- All modules must pass `ty check` before committing
- Use `from typing import ...` for proper type hints
- Add `ty` to `[project.optional-dependencies]` dev section in pyproject.toml

## Testing Strategy

We use **fixture-based offline testing** to avoid live API dependencies:

```bash
# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_extract.py -v
```

**Test approach**:
- Use local HTML/PDF fixtures in `tests/fixtures/` and `evals/fixtures/`
- Mock external API calls (search providers, model endpoints)
- Focus on deterministic unit tests for core logic
- Use the eval harness (`evals/`) for probabilistic LLM behavior testing

**Eval harness** (separate from unit tests):
```bash
uv run research-agent eval --config agent.yaml --suite evals/suites/smoke.yaml --trials 10
```

## Documentation Maintenance

**Keep these documents current and concise**:

### 1. README.md
- Project overview and purpose
- Installation (uv)
- Basic usage examples (db-init, run, eval, llm-test)
- Configuration overview
- Key features (online/offline modes)

**Target**: 50-100 lines. Link to `docs/` for details.

### 2. system_plan_architecture.md
- High-level mermaid diagram showing system components and data flow
- Brief descriptions of each major subsystem (Agent Orchestrator, Search Broker, Evidence Layer, etc.)
- Key design decisions and rationale
- Use the current mermaid flowchart as the template - keep it at that level of detail

**Target**: 200-400 lines including diagram. Update when adding new subsystems or changing pipeline structure.

### 3. docs/*.md
- `evals.md`: Eval harness schema and usage
- `mvp_runbook.md`: Offline operation guide
- Keep focused on specific workflows, not implementation details

**Update cadence**:
- README: Update on any user-facing CLI changes or new features
- system_plan_architecture.md: Update when adding/removing major components or changing pipeline flow
- docs/*.md: Update when changing eval schema or offline workflows

## Development Workflow

```bash
# Setup
uv venv
uv pip install -e .
uv pip install ty pytest

# Before committing
uv run ty check src/research_agent/
uv run pytest tests/

# Run the agent
uv run research-agent db-init --config agent.yaml
uv run research-agent run --config agent.yaml "Your query"

# Offline mode (no search APIs)
uv run research-agent run --config agent.yaml --input-dir offline_sources "Your query"

# Test model connectivity
uv run research-agent llm-test --config agent.yaml --model local
```

## Project-Specific Conventions

### LLM Code (Pragmatic Approach)
- **Prompts**: LLM prompts in `llm/` and `evidence/` are experimental. Iterate quickly based on eval results.
- **Model routing**: Use local (FlashResearch-4B) by default, escalate to OpenRouter (Tongyi-30B) for heavy tasks.
- **Prompt engineering**: Track prompt changes in git but don't over-engineer. Let eval results drive improvements.

### Evidence Pipeline (Pragmatic Iteration)
- **Core modules**: `evidence/extract.py`, `evidence/canonicalize.py`, `evidence/adjudicate.py`, `evidence/reduce.py`
- **Iteration**: Move fast on pipeline logic improvements. Use offline fixtures to validate changes.
- **Provenance**: W3C annotation selectors and WARC snapshots are best-effort. Don't block on perfect provenance.

### Configuration
- Use `agent.yaml` for all runtime config (search providers, model endpoints, thinking extent)
- Read secrets from environment variables (GOOGLE_PSE_API_KEY, MODEL_API_BASE, OPENROUTER_API_KEY)
- Keep `agent.example.yaml` updated as a template

### Output Organization
```
runs/<run_id>/          # Per-run outputs
  report.md             # Final synthesis report
  provenance.json       # Evidence provenance artifacts

eval_runs/<suite>/<ts>/ # Eval harness outputs
  summary.json          # Success rates, p-values
  cases/                # Per-case trial artifacts

data/agent.db           # SQLite persistence (sources, propositions, claims, annotations)
```

## Key Commands Reference

```bash
# Initialize database
uv run research-agent db-init --config agent.yaml

# Run with live search
uv run research-agent run --config agent.yaml "What are the health effects of coffee?"

# Run offline with local sources
uv run research-agent run --config agent.yaml --input-dir offline_sources "Your query"

# Test LLM connectivity
uv run research-agent llm-test --config agent.yaml --model local
uv run research-agent llm-test --config agent.yaml --model openrouter

# Run eval suite
uv run research-agent eval --config agent.yaml --suite evals/suites/smoke.yaml --trials 10 --temperature 0.2

# Type check
uv run ty check src/research_agent/

# Test
uv run pytest tests/ -v
```

## When Making Changes

1. **Adding new features**: Update README with user-facing changes, update system_plan_architecture.md if adding new subsystems
2. **Modifying pipeline**: Add fixture-based tests, run `ty check`, validate with offline run
3. **Changing LLM prompts**: Run eval suite to measure impact, iterate based on results
4. **Configuration changes**: Update `agent.example.yaml` template
5. **Before committing**: `uv run ty check src/research_agent/ && uv run pytest tests/`
