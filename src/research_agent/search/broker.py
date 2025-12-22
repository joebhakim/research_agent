from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from research_agent.config import SearchConfig
from research_agent.types import SearchQuery, SearchResult
from research_agent.search.providers import brave, google_pse, serper, tavily


class SearchProvider(Protocol):
    name: str

    def search(self, query: SearchQuery) -> list[SearchResult]:
        ...


@dataclass
class SearchBroker:
    providers: list[SearchProvider]

    @classmethod
    def from_config(cls, config: SearchConfig) -> "SearchBroker":
        providers: list[SearchProvider] = []
        for name in config.providers:
            if name == "brave":
                providers.append(brave.BraveProvider())
            elif name == "google_pse":
                providers.append(google_pse.GooglePSEProvider())
            elif name == "tavily":
                providers.append(tavily.TavilyProvider())
            elif name == "serper":
                providers.append(serper.SerperProvider())
            else:
                continue
        return cls(providers=providers)

    def search(self, query: SearchQuery) -> list[SearchResult]:
        results: list[SearchResult] = []
        for provider in self.providers:
            try:
                results.extend(provider.search(query))
            except Exception:
                continue
        return rrf_rank(results)


def rrf_rank(results: list[SearchResult], k: int = 60) -> list[SearchResult]:
    if not results:
        return []
    scores: dict[str, float] = {}
    best: dict[str, SearchResult] = {}
    for result in results:
        scores[result.url] = scores.get(result.url, 0.0) + 1.0 / (k + result.rank)
        if result.url not in best:
            best[result.url] = result

    ranked = sorted(best.values(), key=lambda item: scores[item.url], reverse=True)
    now = datetime.utcnow()
    for idx, item in enumerate(ranked, start=1):
        item.rank = idx
        item.retrieved_at = now
    return ranked
