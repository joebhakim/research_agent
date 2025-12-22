from __future__ import annotations

from dataclasses import dataclass
import os

from research_agent.config import AppConfig, ModelEndpointConfig
from research_agent.llm.client import OpenAICompatClient


@dataclass
class RoutedModel:
    name: str
    client: OpenAICompatClient


def get_model_client(
    config: AppConfig,
    thinking_extent: str,
    override: str | None = None,
) -> RoutedModel:
    choice = _select_model(config, thinking_extent, override)
    if choice == "local":
        return RoutedModel(name="local", client=_build_local(config.models.local))
    if choice == "openrouter":
        return RoutedModel(name="openrouter", client=_build_openrouter(config.models.openrouter))
    raise ValueError(f"Unknown model choice: {choice}")


def _select_model(config: AppConfig, thinking_extent: str, override: str | None) -> str:
    if override:
        return override

    extent = thinking_extent.lower().strip()
    if extent in {"high", "heavy"} and config.routing.heavy_uses_openrouter:
        return "openrouter"
    return config.models.default


def _build_local(endpoint: ModelEndpointConfig) -> OpenAICompatClient:
    return OpenAICompatClient(
        api_base=endpoint.api_base,
        model_name=endpoint.model_name,
        timeout_s=endpoint.timeout_s,
    )


def _build_openrouter(endpoint: ModelEndpointConfig) -> OpenAICompatClient:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter.")

    headers: dict[str, str] = {}
    app_url = os.getenv("OPENROUTER_APP_URL")
    app_name = os.getenv("OPENROUTER_APP_NAME")
    if app_url:
        headers["HTTP-Referer"] = app_url
    if app_name:
        headers["X-Title"] = app_name

    return OpenAICompatClient(
        api_base=endpoint.api_base,
        model_name=endpoint.model_name,
        timeout_s=endpoint.timeout_s,
        api_key=api_key,
        extra_headers=headers or None,
    )
