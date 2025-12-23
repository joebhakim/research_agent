from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvidencePolicy:
    chunk_chars: int
    chunk_overlap: int
    max_chunks_per_doc: int
    max_props_per_chunk: int
    max_props_per_doc: int
    max_claims: int
    max_evidence_per_claim: int


def policy_for_extent(extent: str) -> EvidencePolicy:
    normalized = extent.strip().lower()
    if normalized == "low":
        return EvidencePolicy(
            chunk_chars=2000,
            chunk_overlap=200,
            max_chunks_per_doc=2,
            max_props_per_chunk=3,
            max_props_per_doc=6,
            max_claims=10,
            max_evidence_per_claim=6,
        )
    if normalized == "high":
        return EvidencePolicy(
            chunk_chars=3000,
            chunk_overlap=240,
            max_chunks_per_doc=4,
            max_props_per_chunk=5,
            max_props_per_doc=12,
            max_claims=30,
            max_evidence_per_claim=12,
        )
    if normalized == "heavy":
        return EvidencePolicy(
            chunk_chars=3500,
            chunk_overlap=280,
            max_chunks_per_doc=5,
            max_props_per_chunk=6,
            max_props_per_doc=16,
            max_claims=40,
            max_evidence_per_claim=14,
        )
    return EvidencePolicy(
        chunk_chars=2500,
        chunk_overlap=200,
        max_chunks_per_doc=3,
        max_props_per_chunk=4,
        max_props_per_doc=8,
        max_claims=20,
        max_evidence_per_claim=10,
    )
