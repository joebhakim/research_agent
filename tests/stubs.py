from __future__ import annotations

from tests import path_setup  # noqa: F401

from dataclasses import dataclass
from datetime import datetime
import json
import re
from pathlib import Path

from research_agent.fetch.fetcher import FetchedDoc
from research_agent.types import SearchResult


@dataclass
class StubLLM:
    model_name: str = "stub-llm"
    api_base: str = "stub://local"

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        prompt = messages[-1].get("content", "")
        if "Extract up to" in prompt:
            text = _extract_text(prompt)
            return json.dumps(_extract_claims(text))
        if "Label each QUOTE" in prompt:
            return json.dumps(_label_quotes(prompt))
        return "[]"


def _extract_text(prompt: str) -> str:
    marker = "TEXT:\n"
    if marker in prompt:
        return prompt.split(marker, 1)[1]
    return prompt


def _extract_claims(text: str) -> list[dict[str, str]]:
    sentences = _sentences(text)
    claims: list[dict[str, str]] = []
    for sentence in sentences:
        if "boil" in sentence.lower():
            claims.append(
                {
                    "claim_text": sentence,
                    "quote": sentence,
                    "claim_type": "Fact",
                }
            )
    return claims


def _sentences(text: str) -> list[str]:
    raw = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]
    return raw


def _label_quotes(prompt: str) -> list[dict[str, object]]:
    indexes = re.findall(r"\[(\d+)\]", prompt)
    items: list[dict[str, object]] = []
    for idx in indexes:
        items.append({"index": int(idx), "label": "support"})
    return items


def stub_search_results(urls: list[str]) -> list[SearchResult]:
    now = datetime.utcnow()
    results: list[SearchResult] = []
    for idx, url in enumerate(urls, start=1):
        results.append(
            SearchResult(
                engine="google_pse",
                title=f"Fixture {idx}",
                url=url,
                snippet="fixture snippet",
                rank=idx,
                retrieved_at=now,
            )
        )
    return results


def stub_fetch_url_factory(fixtures_dir: Path, url_map: dict[str, str]):
    def _stub(url: str, timeout_s: int = 30) -> FetchedDoc:
        fixture_name = url_map[url]
        content = (fixtures_dir / fixture_name).read_bytes()
        return FetchedDoc(
            url=url,
            status_code=200,
            content=content,
            headers={"content-type": "text/html; charset=utf-8"},
            retrieved_at=datetime.utcnow(),
        )

    return _stub
