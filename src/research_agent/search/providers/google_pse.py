from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os

import httpx

from research_agent.types import SearchQuery, SearchResult

DEFAULT_API_BASE = "https://customsearch.googleapis.com/customsearch/v1"


@dataclass
class GooglePSEProvider:
    name: str = "google_pse"
    api_key: str | None = None
    cx: str | None = None
    api_base: str = DEFAULT_API_BASE
    timeout_s: int = 20

    def search(self, query: SearchQuery) -> list[SearchResult]:
        api_key = self.api_key or os.getenv("GOOGLE_PSE_API_KEY")
        cx = self.cx or os.getenv("GOOGLE_PSE_CX")
        if not api_key or not cx:
            return []

        params = {
            "key": api_key,
            "cx": cx,
            "q": _apply_site_filters(query.q, query.site_filters),
        }

        if query.topk:
            params["num"] = _clamp(query.topk, 1, 10)
        if query.time_range:
            params["dateRestrict"] = query.time_range
        elif query.freshness_days:
            params["dateRestrict"] = f"d{query.freshness_days}"
        if query.safe_mode:
            params["safe"] = _map_safe_mode(query.safe_mode)
        if query.region:
            params["gl"] = query.region

        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.get(self.api_base, params=params)
            response.raise_for_status()

        data = response.json()
        items = data.get("items", [])
        now = datetime.utcnow()
        results: list[SearchResult] = []
        for idx, item in enumerate(items, start=1):
            link = item.get("link")
            if not link:
                continue
            results.append(
                SearchResult(
                    engine=self.name,
                    title=item.get("title", ""),
                    url=link,
                    snippet=item.get("snippet", ""),
                    rank=idx,
                    retrieved_at=now,
                )
            )
        return results


def _apply_site_filters(query: str, sites: list[str]) -> str:
    if not sites:
        return query
    if len(sites) == 1:
        return f"{query} site:{sites[0]}"
    site_expr = " OR ".join(f"site:{site}" for site in sites)
    return f"{query} ({site_expr})"


def _map_safe_mode(value: str) -> str:
    val = value.lower().strip()
    if val in {"active", "on", "strict", "true", "yes"}:
        return "active"
    if val in {"off", "disabled", "none"}:
        return "off"
    return "off"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
