from __future__ import annotations

from dataclasses import dataclass

from research_agent.types import SearchQuery, SearchResult


@dataclass
class GooglePSEProvider:
    name: str = "google_pse"
    api_key: str | None = None
    cx: str | None = None

    def search(self, query: SearchQuery) -> list[SearchResult]:
        # TODO: Implement Google Programmable Search JSON API.
        return []
