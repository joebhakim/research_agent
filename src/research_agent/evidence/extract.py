from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from loguru import logger

from research_agent.evidence.policy import EvidencePolicy
from research_agent.llm.client import OpenAICompatClient
from research_agent.logging import trace
from research_agent.types import Annotation, AnnotationSelector, DocumentText, Proposition


@dataclass
class ExtractResult:
    propositions: list[Proposition]


def extract_propositions(
    document: DocumentText,
    llm_client: OpenAICompatClient,
    policy: EvidencePolicy,
) -> list[Proposition]:
    if not document.text.strip():
        return []

    propositions: list[Proposition] = []
    chunks = chunk_text(document.text, policy.chunk_chars, policy.chunk_overlap)
    total_chunks = min(len(chunks), policy.max_chunks_per_doc)
    for i, chunk in enumerate(chunks[: policy.max_chunks_per_doc], start=1):
        if len(propositions) >= policy.max_props_per_doc:
            break
        logger.debug(f"Processing chunk {i}/{total_chunks} for {document.doc_id}")
        items = _extract_from_chunk(document, chunk, llm_client, policy.max_props_per_chunk)
        for item in items:
            if len(propositions) >= policy.max_props_per_doc:
                break
            prop = _build_proposition(document, item, llm_client)
            if prop:
                propositions.append(prop)

    # Trace extracted propositions
    trace(
        "propositions_extracted",
        doc_id=document.doc_id,
        propositions=[p.payload for p in propositions],
    )
    return propositions


def _extract_from_chunk(
    document: DocumentText,
    chunk: str,
    llm_client: OpenAICompatClient,
    max_props: int,
) -> list[dict[str, Any]]:
    prompt = _build_prompt(document, chunk, max_props)
    response = llm_client.chat(
        [
            {"role": "system", "content": "You extract atomic, text-grounded claims."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=900,
    )
    parsed = _parse_json_list(response)
    if not parsed:
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _build_prompt(document: DocumentText, chunk: str, max_props: int) -> str:
    return (
        "Extract up to "
        + str(max_props)
        + " atomic propositions directly supported by the TEXT.\n"
        "Return JSON array only. Each item must include:\n"
        "- claim_text: short sentence\n"
        "- quote: exact substring from TEXT supporting the claim\n"
        "- claim_type: Effect | Presence | Fact\n"
        "If nothing is supported, return [].\n\n"
        "TEXT:\n"
        + chunk
    )


def _build_proposition(
    document: DocumentText,
    item: dict[str, Any],
    llm_client: OpenAICompatClient,
) -> Proposition | None:
    claim_text = _as_str(item.get("claim_text"))
    quote = _as_str(item.get("quote"))
    claim_type = _normalize_claim_type(_as_str(item.get("claim_type")))
    if not claim_text or not quote:
        return None

    anchor = _make_anchor(document.text, quote, document.doc_id)
    anchors = [anchor] if anchor else []
    prop_id = _make_prop_id(document.doc_id, claim_text, quote)
    payload = {
        "claim_text": claim_text,
        "quote": quote,
        "claim_type": claim_type,
    }
    return Proposition(
        id=prop_id,
        type=claim_type,
        payload=payload,
        anchors=anchors,
        doc_id=document.doc_id,
        quality={
            "model": llm_client.model_name,
            "chunk_chars": len(document.text),
        },
        extracted_at=datetime.utcnow(),
    )


def chunk_text(text: str, chunk_chars: int, overlap: int) -> list[str]:
    if chunk_chars <= 0:
        return [text]
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + chunk_chars)
        chunks.append(text[start:end])
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def _make_anchor(text: str, quote: str, doc_id: str) -> Annotation | None:
    if not quote:
        return None
    start = text.find(quote)
    if start < 0:
        start = text.lower().find(quote.lower())
    if start < 0:
        selector: AnnotationSelector = {
            "type": "TextQuoteSelector",
            "exact": quote,
        }
        return Annotation(doc_id=doc_id, selector=selector, quote=quote, context="")

    end = start + len(quote)
    prefix = text[max(0, start - 80) : start]
    suffix = text[end : min(len(text), end + 80)]
    selector = {
        "type": "TextQuoteSelector",
        "exact": quote,
        "prefix": prefix,
        "suffix": suffix,
        "start": start,
        "end": end,
    }
    context = prefix + quote + suffix
    return Annotation(doc_id=doc_id, selector=selector, quote=quote, context=context)


def _make_prop_id(doc_id: str, claim_text: str, quote: str) -> str:
    raw = f"{doc_id}:{claim_text}:{quote}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"prop_{digest}"


def _parse_json_list(text: str) -> list[Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        logger.warning("Failed to parse LLM response as JSON: no array found")
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        return []
    if isinstance(parsed, list):
        return parsed
    return []


def _normalize_claim_type(value: str) -> str:
    cleaned = value.strip().capitalize()
    if cleaned in {"Effect", "Presence", "Fact"}:
        return cleaned
    return "Fact"


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()
