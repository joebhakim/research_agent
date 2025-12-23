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
        lines.append("- No claims extracted.")
    else:
        for claim in claim_groups:
            lines.append(f"- {claim.claim_text} [{claim.stance}] {claim.rationale}")
    lines.append("")
    lines.append("## Evidence Matrix")
    lines.append(render_evidence_matrix(claim_groups))
    lines.append("")
    lines.append("## Evidence Snippets")
    lines.append(render_evidence_snippets(claim_groups))
    lines.append("")
    lines.append("## Assumptions / Uncertainties")
    lines.append("- Extraction and adjudication are model-assisted and can miss claims or mislabel evidence.")
    lines.append("- PDF extraction quality depends on the parser and document structure.")
    lines.append("")
    lines.append("## Provenance")
    lines.append("- See provenance.json in the run directory.")
    return "\n".join(lines)


def render_evidence_matrix(claim_groups: list[ClaimGroup]) -> str:
    if not claim_groups:
        return "- No evidence captured yet."
    lines = ["| Claim | Support | Refute | Neutral |", "| --- | --- | --- | --- |"]
    for claim in claim_groups:
        counts = _counts_from_claim(claim)
        lines.append(
            f"| {claim.claim_text} | {counts['support']} | {counts['refute']} | {counts['neutral']} |"
        )
    return "\n".join(lines)


def render_evidence_snippets(claim_groups: list[ClaimGroup]) -> str:
    lines: list[str] = []
    for claim in claim_groups:
        lines.append(f"Claim: {claim.claim_text}")
        evidence = _evidence_from_claim(claim)
        if not evidence:
            lines.append("- No evidence snippets captured.")
            continue
        for item in evidence[:5]:
            label = str(item.get("label", "neutral"))
            quote = str(item.get("quote", ""))
            url = str(item.get("url", ""))
            title = str(item.get("title", ""))
            prefix = f"[{label}]" if label else ""
            source = title or url
            if source:
                lines.append(f"- {prefix} {quote} ({source})")
            else:
                lines.append(f"- {prefix} {quote}")
    return "\n".join(lines) if lines else "- No evidence snippets captured."


def _counts_from_claim(claim: ClaimGroup) -> dict[str, int]:
    if not claim.merge:
        return {"support": 0, "refute": 0, "neutral": 0}
    counts = claim.merge.get("counts")
    if not isinstance(counts, dict):
        return {"support": 0, "refute": 0, "neutral": 0}
    return {
        "support": int(counts.get("support", 0)),
        "refute": int(counts.get("refute", 0)),
        "neutral": int(counts.get("neutral", 0)),
    }


def _evidence_from_claim(claim: ClaimGroup) -> list[dict[str, object]]:
    if not claim.merge:
        return []
    evidence = claim.merge.get("evidence")
    if isinstance(evidence, list):
        return [item for item in evidence if isinstance(item, dict)]
    return []
