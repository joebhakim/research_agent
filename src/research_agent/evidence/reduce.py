from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from research_agent.types import ClaimGroup, Proposition


@dataclass
class ReduceResult:
    propositions: list[Proposition]
    claim_groups: list[ClaimGroup]


def reduce_evidence(docs: Iterable[str]) -> ReduceResult:
    propositions = map_to_propositions(docs)
    canonical = canonicalize(propositions)
    groups = group_claims(canonical)
    merged = merge_claims(groups)
    adjudicated = adjudicate(merged)
    return ReduceResult(propositions=canonical, claim_groups=adjudicated)


def map_to_propositions(docs: Iterable[str]) -> list[Proposition]:
    # TODO: Implement LLM-assisted extraction with anchored citations.
    _ = docs
    return []


def canonicalize(propositions: Iterable[Proposition]) -> list[Proposition]:
    # TODO: Normalize entities, units, and dates.
    return list(propositions)


def group_claims(propositions: Iterable[Proposition]) -> list[ClaimGroup]:
    # TODO: Hash claim signatures and group propositions.
    _ = propositions
    return []


def merge_claims(groups: Iterable[ClaimGroup]) -> list[ClaimGroup]:
    # TODO: Merge numeric claims and compute heterogeneity.
    return list(groups)


def adjudicate(groups: Iterable[ClaimGroup]) -> list[ClaimGroup]:
    # TODO: Apply source weighting and contradiction detection.
    return list(groups)
