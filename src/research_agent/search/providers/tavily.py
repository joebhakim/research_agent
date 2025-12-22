from __future__ import annotations

from dataclasses import dataclass

from research_agent.types import SearchQuery, SearchResult


@dataclass
class TavilyProvider:
    name: str = "tavily"
    api_key: str | None = None

    def search(self, query: SearchQuery) -> list[SearchResult]:
        # TODO: Implement Tavily Search API.
        return []
