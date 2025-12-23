from __future__ import annotations

import hashlib
import re

from research_agent.types import Proposition


def canonicalize_propositions(propositions: list[Proposition]) -> list[Proposition]:
    for prop in propositions:
        claim_text = str(prop.payload.get("claim_text", "")).strip()
        canonical = normalize_claim_text(claim_text)
        signature = signature_for_text(canonical)
        prop.payload["canonical_text"] = canonical
        prop.payload["claim_signature"] = signature
    return propositions


def normalize_claim_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def signature_for_text(text: str) -> str:
    normalized = normalize_claim_text(text).lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return digest
