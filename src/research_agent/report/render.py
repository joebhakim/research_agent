from __future__ import annotations

from datetime import datetime

from research_agent.types import ClaimGroup


def render_report(question: str, claim_groups: list[ClaimGroup]) -> str:
    lines: list[str] = []
    lines.append("# Research Report")
    lines.append("")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append("## Question")
    lines.append(question)
    lines.append("")
    lines.append("## Key Claims")
    if not claim_groups:
        lines.append("- No claims extracted (providers and parsers are stubbed).")
    else:
        for claim in claim_groups:
            lines.append(f"- {claim.signature} [{claim.stance}] {claim.rationale}")
    lines.append("")
    lines.append("## Evidence Matrix")
    lines.append(render_evidence_matrix(claim_groups))
    lines.append("")
    lines.append("## Assumptions / Uncertainties")
    lines.append("- Search providers, fetching, and extraction are TODOs.")
    lines.append("")
    lines.append("## Provenance")
    lines.append("- TODO: write provenance JSON and WARC snapshot list.")
    return "\n".join(lines)


def render_evidence_matrix(claim_groups: list[ClaimGroup]) -> str:
    if not claim_groups:
        return "- No evidence captured yet."
    lines = ["| Claim | Stance |", "| --- | --- |"]
    for claim in claim_groups:
        lines.append(f"| {claim.signature} | {claim.stance} |")
    return "\n".join(lines)
