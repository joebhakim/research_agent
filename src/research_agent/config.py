from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass
class ThinkingConfig:
    extent: str
    max_react_steps: int
    beams: int
    critique_passes: int
    summarization_ratio: float


@dataclass
class AgentConfig:
    mode: str
    thinking: ThinkingConfig


@dataclass
class SearchConfig:
    providers: list[str]
    topk_per_engine: int
    freshness_days: int
    safe_mode: str
    api_budget_usd: float


@dataclass
class StorageConfig:
    sqlite_path: Path
    warc_dir: Path
    runs_dir: Path


@dataclass
class ModelConfig:
    api_base: str
    model_name: str
    timeout_s: int


@dataclass
class AppConfig:
    agent: AgentConfig
    search: SearchConfig
    storage: StorageConfig
    model: ModelConfig


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping.")
    config = _from_dict(data)
    _apply_env_overrides(config)
    return config


def _from_dict(data: dict[str, Any]) -> AppConfig:
    agent_data = _get_map(data, "agent")
    thinking_data = _get_map(agent_data, "thinking")
    search_data = _get_map(data, "search")
    storage_data = _get_map(data, "storage")
    model_data = _get_map(data, "model")

    thinking = ThinkingConfig(
        extent=str(thinking_data.get("extent", "medium")),
        max_react_steps=int(thinking_data.get("max_react_steps", 8)),
        beams=int(thinking_data.get("beams", 2)),
        critique_passes=int(thinking_data.get("critique_passes", 1)),
        summarization_ratio=float(thinking_data.get("summarization_ratio", 0.2)),
    )

    agent = AgentConfig(
        mode=str(agent_data.get("mode", "native")),
        thinking=thinking,
    )

    providers_raw = search_data.get("providers", ["brave", "google_pse", "tavily", "serper"])
    providers = [str(p) for p in providers_raw] if isinstance(providers_raw, list) else []
    search = SearchConfig(
        providers=providers,
        topk_per_engine=int(search_data.get("topk_per_engine", 8)),
        freshness_days=int(search_data.get("freshness_days", 365)),
        safe_mode=str(search_data.get("safe_mode", "standard")),
        api_budget_usd=float(search_data.get("api_budget_usd", 0.5)),
    )

    storage = StorageConfig(
        sqlite_path=Path(storage_data.get("sqlite_path", "./data/agent.db")),
        warc_dir=Path(storage_data.get("warc_dir", "./warc")),
        runs_dir=Path(storage_data.get("runs_dir", "./runs")),
    )

    model = ModelConfig(
        api_base=str(model_data.get("api_base", "http://localhost:8000/v1")),
        model_name=str(model_data.get("model_name", "flashresearch-4b-thinking")),
        timeout_s=int(model_data.get("timeout_s", 60)),
    )

    return AppConfig(agent=agent, search=search, storage=storage, model=model)


def _apply_env_overrides(config: AppConfig) -> None:
    api_base = os.getenv("MODEL_API_BASE")
    model_name = os.getenv("MODEL_NAME")
    timeout_s = os.getenv("MODEL_TIMEOUT_S")

    if api_base:
        config.model.api_base = api_base
    if model_name:
        config.model.model_name = model_name
    if timeout_s:
        try:
            config.model.timeout_s = int(timeout_s)
        except ValueError:
            raise ValueError("MODEL_TIMEOUT_S must be an integer.")


def _get_map(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    return {}
