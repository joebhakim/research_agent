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
class ModelEndpointConfig:
    api_base: str
    model_name: str
    timeout_s: int


@dataclass
class ModelsConfig:
    default: str
    local: ModelEndpointConfig
    openrouter: ModelEndpointConfig


@dataclass
class RoutingConfig:
    heavy_uses_openrouter: bool


@dataclass
class AppConfig:
    agent: AgentConfig
    search: SearchConfig
    storage: StorageConfig
    models: ModelsConfig
    routing: RoutingConfig


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
    models_data = _get_map(data, "models")
    model_data = _get_map(data, "model")
    routing_data = _get_map(data, "routing")

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

    models = _load_models_config(models_data, model_data)
    routing = RoutingConfig(
        heavy_uses_openrouter=_to_bool(routing_data.get("heavy_uses_openrouter"), default=True),
    )

    return AppConfig(agent=agent, search=search, storage=storage, models=models, routing=routing)


def _apply_env_overrides(config: AppConfig) -> None:
    api_base = os.getenv("MODEL_API_BASE")
    model_name = os.getenv("MODEL_NAME")
    timeout_s = os.getenv("MODEL_TIMEOUT_S")
    openrouter_base = os.getenv("OPENROUTER_API_BASE")
    openrouter_model = os.getenv("OPENROUTER_MODEL")
    openrouter_timeout = os.getenv("OPENROUTER_TIMEOUT_S")

    if api_base:
        config.models.local.api_base = api_base
    if model_name:
        config.models.local.model_name = model_name
    if timeout_s:
        try:
            config.models.local.timeout_s = int(timeout_s)
        except ValueError:
            raise ValueError("MODEL_TIMEOUT_S must be an integer.")
    if openrouter_base:
        config.models.openrouter.api_base = openrouter_base
    if openrouter_model:
        config.models.openrouter.model_name = openrouter_model
    if openrouter_timeout:
        try:
            config.models.openrouter.timeout_s = int(openrouter_timeout)
        except ValueError:
            raise ValueError("OPENROUTER_TIMEOUT_S must be an integer.")


def _load_models_config(models_data: dict[str, Any], model_data: dict[str, Any]) -> ModelsConfig:
    if models_data:
        local_data = _get_map(models_data, "local")
        openrouter_data = _get_map(models_data, "openrouter")
        default = str(models_data.get("default", "local"))
        return ModelsConfig(
            default=default,
            local=_endpoint_from(
                local_data,
                default_base="http://localhost:8000/v1",
                default_name="flashresearch-4b-thinking",
            ),
            openrouter=_endpoint_from(
                openrouter_data,
                default_base="https://openrouter.ai/api/v1",
                default_name="alibaba/tongyi-deepresearch-30b-a3b:free",
            ),
        )

    local = _endpoint_from(
        model_data,
        default_base="http://localhost:8000/v1",
        default_name="flashresearch-4b-thinking",
    )
    openrouter = ModelEndpointConfig(
        api_base="https://openrouter.ai/api/v1",
        model_name="alibaba/tongyi-deepresearch-30b-a3b:free",
        timeout_s=60,
    )
    return ModelsConfig(default="local", local=local, openrouter=openrouter)


def _endpoint_from(
    data: dict[str, Any],
    default_base: str,
    default_name: str,
    default_timeout: int = 60,
) -> ModelEndpointConfig:
    return ModelEndpointConfig(
        api_base=str(data.get("api_base", default_base)),
        model_name=str(data.get("model_name", default_name)),
        timeout_s=int(data.get("timeout_s", default_timeout)),
    )


def _get_map(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    return {}


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default
