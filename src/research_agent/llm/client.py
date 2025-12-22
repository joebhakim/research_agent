from __future__ import annotations

from dataclasses import dataclass

import httpx

from research_agent.types import ChatMessage


@dataclass
class VLLMClient:
    api_base: str
    model_name: str
    timeout_s: int = 60

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
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
        except httpx.RequestError as exc:
            raise RuntimeError(f"vLLM endpoint unreachable: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"vLLM HTTP error: {exc.response.status_code}") from exc

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("vLLM response missing choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("vLLM response missing content.")
        return content
