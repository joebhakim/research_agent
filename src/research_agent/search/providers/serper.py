from __future__ import annotations

from dataclasses import dataclass

from research_agent.types import SearchQuery, SearchResult


@dataclass
class SerperProvider:
    name: str = "serper"
    api_key: str | None = None
    engine: str | None = None

    def search(self, query: SearchQuery) -> list[SearchResult]:
        # TODO: Implement Serper (or other SERP API) integration.
        return []
