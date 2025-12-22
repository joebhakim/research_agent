from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, TypedDict


class AnnotationSelector(TypedDict, total=False):
    type: str
    exact: str
    prefix: str
    suffix: str
    start: int
    end: int


@dataclass
class Annotation:
    doc_id: str
    selector: AnnotationSelector
    quote: str
    context: str


@dataclass
class SourceDoc:
    id: str
    url: str
    retrieved_at: datetime
    content_hash: str
    warc_path: str | None
    mime: str
    publish_date: str | None = None
    source_type: str | None = None
    engine: str | None = None
    license_hint: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposition:
    id: str
    type: Literal["Effect", "Presence", "Fact"]
    payload: dict[str, Any]
    anchors: list[Annotation]
    doc_id: str
    quality: dict[str, Any]
    extracted_at: datetime


@dataclass
class ClaimGroup:
    signature: str
    domain: Literal["clinical", "flavor", "general"]
    propositions: list[str]
    merge: dict[str, Any] | None
    stance: Literal["supported", "mixed", "refuted", "insufficient"]
    rationale: str


@dataclass
class SearchQuery:
    q: str
    site_filters: list[str] = field(default_factory=list)
    time_range: str | None = None
    region: str | None = None
    engine: str | None = None
    topk: int | None = None


@dataclass
class SearchResult:
    engine: str
    title: str
    url: str
    snippet: str
    rank: int
    retrieved_at: datetime


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class RunState:
    run_id: str
    question: str
    created_at: datetime
    mode: str
    thinking_extent: str
    report_path: str | None = None
    status: str = "pending"
