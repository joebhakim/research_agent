TODO

Where we are right now
- Offline-first pipeline works end-to-end with local HTML/PDF/TXT sources.
- Evidence reduce pipeline runs (extract -> canonicalize -> adjudicate) and writes reports + provenance.
- Eval harness runs and captures raw LLM calls; extraction quality depends on model formatting.
- Search is minimal (Google PSE only); no question-aware filtering or relevance ranking yet.
- PDF/HTML parsing is basic; boilerplate and unrelated claims still appear.

Plan (near-term)
- Make extraction question-aware or add a relevance filter for claims.
- Add boilerplate trimming for PDFs/HTML to reduce noisy claims.
- Stabilize JSON output (either model choice or enforced decoding).
- Add targeted source sets for offline runs and a repeatable smoke run.

Main TODO: Information Retrieval (modern LLM search agent)
- Define a retrieval loop (plan -> search -> fetch -> synthesize -> refine queries).
- Implement query expansion + iterative search across multiple providers.
- Add relevance ranking and dedup (URL + content hash + semantic clustering).
- Build a small browsing cache with source snapshots and citations.
- Add a query-to-claim alignment pass before adjudication.
- Add retrieval-focused evals (coverage, diversity, freshness, and accuracy).
