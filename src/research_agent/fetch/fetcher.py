from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class FetchedDoc:
    url: str
    status_code: int
    content: bytes
    headers: dict[str, str]
    retrieved_at: datetime


def fetch_url(url: str, timeout_s: int = 30) -> FetchedDoc:
    # TODO: Add robots.txt checks, rate limiting, and WARC capture.
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return FetchedDoc(
            url=str(response.url),
            status_code=response.status_code,
            content=response.content,
            headers={k: v for k, v in response.headers.items()},
            retrieved_at=datetime.utcnow(),
        )
