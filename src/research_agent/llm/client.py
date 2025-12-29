from __future__ import annotations

from dataclasses import dataclass

import httpx
from loguru import logger

from research_agent.logging import trace
from research_agent.types import ChatMessage


@dataclass
class OpenAICompatClient:
    api_base: str
    model_name: str
    timeout_s: int = 60
    api_key: str | None = None
    extra_headers: dict[str, str] | None = None

    def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        url = f"{self.api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = self._build_headers()

        logger.debug(f"LLM request to {self.model_name}")
        trace("llm_request", model=self.model_name, messages=messages, max_tokens=max_tokens)

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.RequestError as exc:
            logger.error(f"LLM request failed: {exc}")
            raise RuntimeError(f"LLM endpoint unreachable: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(f"LLM HTTP error: {exc.response.status_code}")
            raise RuntimeError(f"LLM HTTP error: {exc.response.status_code}") from exc

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("vLLM response missing choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("LLM response missing content.")

        logger.debug(f"LLM response received ({len(content)} chars)")
        trace("llm_response", model=self.model_name, response=content)

        return content

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.extra_headers:
            headers.update(self.extra_headers)
        return headers


VLLMClient = OpenAICompatClient
