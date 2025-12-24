MVP Expectations (Illustrative)

This document describes expected behavior for a typical run. It is illustrative,
not a strict contract, because live search and LLM outputs are nondeterministic.
Tests use fixtures and stubs to validate deterministic behavior.

Example Question
- "water boils at what temperature"

Search Expectations (Qualitative)
- Should surface at least one credible source.
- Should include a statement about 100 C / 212 F at sea level.
- Should mention that boiling point changes with altitude/pressure when present.

Example Input Snippets (Fixture-Based)
- "At sea level, water boils at 100 C (212 F)."
- "Boiling point decreases as altitude increases."

Example Extracted Propositions (JSON)
[
  {
    "claim_text": "At sea level, water boils at 100 C (212 F).",
    "quote": "At sea level, water boils at 100 C (212 F).",
    "claim_type": "Fact"
  },
  {
    "claim_text": "Boiling point decreases as altitude increases.",
    "quote": "Boiling point decreases as altitude increases.",
    "claim_type": "Fact"
  }
]

Example Reduced / Adjudicated Claims
- Claim: "At sea level, water boils at 100 C (212 F)."
  - Stance: supported
  - Evidence counts: support=2, refute=0, neutral=0
- Claim: "Boiling point decreases as altitude increases."
  - Stance: supported
  - Evidence counts: support=1, refute=0, neutral=0

Notes
- Real sources may use different phrasing and units.
- The agent groups claims by a hashed signature of canonicalized claim text.
- Adjudication is model-assisted and should be treated as a heuristic.
