from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from research_agent.evidence.adjudicate import label_evidence
from research_agent.evidence.canonicalize import canonicalize_propositions
from research_agent.evidence.extract import extract_propositions
from research_agent.evidence.policy import EvidencePolicy, policy_for_extent
from research_agent.llm.client import OpenAICompatClient
from research_agent.types import ClaimGroup, DocumentText, Proposition


@dataclass
class ReduceResult:
    propositions: list[Proposition]
    claim_groups: list[ClaimGroup]

def reduce_evidence(
    docs: Iterable[DocumentText],
    llm_client: OpenAICompatClient,
    thinking_extent: str,
) -> ReduceResult:
    policy = policy_for_extent(thinking_extent)
    propositions = map_to_propositions(docs, llm_client, policy)
    canonical = canonicalize_propositions(propositions)
    groups = group_claims(canonical, policy)
    merged = merge_claims(groups, docs, policy)
    adjudicated = adjudicate(merged, llm_client, policy)
    return ReduceResult(propositions=canonical, claim_groups=adjudicated)


def map_to_propositions(
    docs: Iterable[DocumentText],
    llm_client: OpenAICompatClient,
    policy: EvidencePolicy,
) -> list[Proposition]:
    propositions: list[Proposition] = []
    for doc in docs:
        propositions.extend(extract_propositions(doc, llm_client, policy))
    return propositions


@dataclass
class GroupSummary:
    signature: str
    claim_text: str
    propositions: list[Proposition]


@dataclass
class MergedGroup:
    signature: str
    claim_text: str
    propositions: list[Proposition]
    evidence: list[dict[str, object]]


def group_claims(propositions: Iterable[Proposition], policy: EvidencePolicy) -> list[GroupSummary]:
    grouped: dict[str, list[Proposition]] = {}
    claim_texts: dict[str, str] = {}
    for prop in propositions:
        signature = str(prop.payload.get("claim_signature", ""))
        if not signature:
            continue
        grouped.setdefault(signature, []).append(prop)
        if signature not in claim_texts:
            claim_texts[signature] = str(prop.payload.get("claim_text", "")).strip()

    summaries = [
        GroupSummary(signature=sig, claim_text=claim_texts.get(sig, ""), propositions=props)
        for sig, props in grouped.items()
    ]
    summaries.sort(key=lambda item: len(item.propositions), reverse=True)
    return summaries[: policy.max_claims]


def merge_claims(
    groups: Iterable[GroupSummary],
    docs: Iterable[DocumentText],
    policy: EvidencePolicy,
) -> list[MergedGroup]:
    doc_index = {doc.doc_id: doc for doc in docs}
    merged: list[MergedGroup] = []
    for group in groups:
        evidence = build_evidence(group.propositions, doc_index)
        merged.append(
            MergedGroup(
                signature=group.signature,
                claim_text=group.claim_text,
                propositions=group.propositions,
                evidence=evidence[: policy.max_evidence_per_claim],
            )
        )
    return merged


def build_evidence(
    propositions: Iterable[Proposition],
    doc_index: dict[str, DocumentText],
) -> list[dict[str, object]]:
    seen: set[tuple[str, str]] = set()
    evidence: list[dict[str, object]] = []
    for prop in propositions:
        quote = str(prop.payload.get("quote", "")).strip()
        key = (prop.doc_id, quote)
        if key in seen or not quote:
            continue
        seen.add(key)
        doc = doc_index.get(prop.doc_id)
        evidence.append(
            {
                "doc_id": prop.doc_id,
                "url": doc.url if doc else "",
                "title": doc.title if doc else "",
                "quote": quote,
            }
        )
    return evidence


def adjudicate(
    groups: Iterable[MergedGroup],
    llm_client: OpenAICompatClient,
    policy: EvidencePolicy,
) -> list[ClaimGroup]:
    adjudicated: list[ClaimGroup] = []
    for group in groups:
        labels = label_evidence(group.claim_text, group.evidence, llm_client, policy)
        counts = {"support": 0, "refute": 0, "neutral": 0}
        labeled_evidence: list[dict[str, object]] = []
        for idx, entry in enumerate(group.evidence):
            label = labels[idx] if idx < len(labels) else "neutral"
            counts[label] = counts.get(label, 0) + 1
            entry_with_label = dict(entry)
            entry_with_label["label"] = label
            labeled_evidence.append(entry_with_label)

        stance = derive_stance(counts)
        rationale = (
            f"support={counts['support']}, refute={counts['refute']}, neutral={counts['neutral']} "
            f"across {len(labeled_evidence)} evidence items."
        )
        merge_payload = {
            "counts": counts,
            "evidence": labeled_evidence,
            "canonical_text": _canonical_from_props(group.propositions),
        }
        adjudicated.append(
            ClaimGroup(
                signature=group.signature,
                claim_text=group.claim_text,
                domain="general",
                propositions=[prop.id for prop in group.propositions],
                merge=merge_payload,
                stance=stance,
                rationale=rationale,
            )
        )
    return adjudicated


def derive_stance(counts: dict[str, int]) -> str:
    support = counts.get("support", 0)
    refute = counts.get("refute", 0)
    if support and refute:
        return "mixed"
    if support and not refute:
        return "supported"
    if refute and not support:
        return "refuted"
    return "insufficient"


def _canonical_from_props(propositions: Iterable[Proposition]) -> str:
    for prop in propositions:
        canonical = prop.payload.get("canonical_text")
        if isinstance(canonical, str) and canonical:
            return canonical
    return ""
