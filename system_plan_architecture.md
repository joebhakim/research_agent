Below is a **complete, implementation‑grade architecture and spec** for a research agent optimized for **claim‑level synthesis** and **evidence reduction** (map→reduce→adjudicate), with **heavy web search** and a **tunable thinking extent** compatible with both **FlashResearch‑4B‑Thinking (local)** and **Tongyi‑DeepResearch‑30B‑A3B (OpenRouter)**.

I anchor design choices to the Tongyi DeepResearch rollout modes (Native ReAct vs Heavy) and training/stability claims, and to the realities of search APIs in late‑2025 (Bing API retirement; practical DDG, Brave, Google PSE/JSON, Tavily/Serp APIs). Citations appear inline where a choice depends on external facts.

---

## 0) One‑screen summary

* **Agent loop:** ReAct‑style **Native** mode for fast tasks; **Heavy (IterResearch)** for long‑horizon queries with round‑by‑round workspace reconstruction, synthesis before expansion, and compute budgeting. ([Tongyi DeepResearch][1])
* **Thinking knob:** `thinking.extent ∈ {low, medium, high, heavy}` controls step budget, parallel beams, self‑critique depth, and when to escalate from 4B (local) to 30B (remote). OpenRouter’s **Tongyi‑DeepResearch‑30B‑A3B:free** exposes a **131,072‑token** context for escalations. ([OpenRouter][2])
* **Search substrate:** Pluggable broker with **Brave Search API**, **Google Programmable Search JSON API**, **Tavily**, and **SERP providers** (SerpApi/Serper/SearchAPI.io). Avoid planning around Bing’s retired API. Treat DDG’s **Instant Answer** as a free adjunct (not a full SERP). ([Brave][3])
* **Evidence core:** WARC snapshots + W3C Web Annotation selectors (TextQuote/TextPosition) to make claims **reproducibly re‑locatable** in source pages/PDFs. ([GitHub][4])
* **Evidence‑Reduce:** a typed, map‑reduce pipeline that **canonizes atomic propositions**, merges quantitative results (random‑effects if comparable), and **surfaces contradictions** with weights from source type/recency/method.
* **Clinical‑trial specialization:** optional PICO tagging, **ClinicalTrials.gov v2** connector, PubMed/PMC (NCBI E‑utilities) and Crossref metadata normalization. ([National Library of Medicine][5])
* **Chemistry/flavor specialization:** entity normalization to PubChem/ChEBI with external knowledge from **FlavorDB / FlavorDB2** and **FooDB** to build **Drink×Compound** matrices (concentration, method, source). ([OUP Academic][6])
* **Models:** default **FlashResearch‑4B‑Thinking** locally (distilled from Tongyi 30B; GGUF quants available), escalate to **Tongyi 30B** via OpenRouter as needed. (Note the **license mismatch** on the model card—track explicitly.) ([Hugging Face][7])

---

## 1) System architecture (high‑level)

```mermaid
flowchart LR
    subgraph UI["User Interfaces"]
        A1[CLI / Python SDK]
        A2[Web Notebook<br/>(Run Log + Live Plan)]
    end

    subgraph Orchestrator["Agent Orchestrator"]
        P[Planner + Critic<br/>(ReAct / Heavy)]
        T[Thinking Controller<br/>(extent, beams, budgets)]
        R[Run State + Workspace<br/>(central evolving report)]
    end

    subgraph Search["Search Broker"]
        SB[Query Expander<br/>(PICO, synonyms, facets)]
        DS[(Providers)]
        DS1[Brave API]
        DS2[Google PSE JSON]
        DS3[Tavily]
        DS4[Serp APIs<br/>(SerpApi/Serper/SearchAPI.io)]
        DS5[DDG Instant Answer<br/>(adjunct)]
    end

    subgraph Retrieval["Fetch & Parse"]
        F[Fetcher + Robots, Rate limits]
        W[WARC Snapshots]
        H[HTML Readability + De-dupe]
        PDF[PDF Parser + Tables]
    end

    subgraph Evidence["Evidence Layer"]
        E0[(Provenance DB<br/>Postgres/SQLite)]
        E1[(Evidence Graph<br/>Neo4j/PG + pgvector)]
        E2[(Embeddings cache)]
        ANNO[W3C Annotation Selectors<br/>(TextQuote/Position)]
    end

    subgraph Reduce["Evidence-Reduce Pipeline"]
        M[Map → Atomic Propositions]
        C[Canonicalize & Align<br/>(units, entities, time)]
        J[Join/Group by Claim Signatures]
        Q[Quant Merge<br/>(effects, CIs)]
        D[Disagreement Detector]
        WGT[Source Weighting]
    end

    subgraph Domain["Domain Adapters"]
        CT[Clinical Trials<br/>(PICO, CT.gov v2, PubMed/Crossref)]
        FL[Flavor Chemistry<br/>(FlavorDB/FooDB → PubChem)]
    end

    subgraph Synthesis["Synthesis & Reports"]
        CL[Claim Lens (per-claim views)]
        EM[Evidence Matrix]
        REP[Exec Brief + Full Report + Diffs]
        QA[Self-critique + Adversarial checks]
    end

    subgraph Models["Model Router"]
        L4B[FlashResearch‑4B‑Thinking (local)]
        T30B[Tongyi‑DeepResearch‑30B‑A3B via OpenRouter]
    end

    A1-->P
    A2-->P
    P<-->T
    P<-->R
    P-->SB
    SB-->DS
    DS-->F
    F-->W
    W-->H
    W-->PDF
    H-->E0
    PDF-->E0
    E0-->ANNO
    ANNO-->M
    M-->C-->J-->Q-->D-->WGT
    WGT-->CL
    WGT-->EM
    CL-->REP
    EM-->REP
    QA-->REP
    R<-->REP
    P<-->Models
    Models-->P
    CT---SB
    CT---M
    FL---M
```

**Why this shape?** It mirrors Tongyi’s **Heavy/IterResearch**: each round reconstructs a slim workspace, writes into a central report, then decides next actions—rather than accumulating an unbounded scratchpad. That matches your “evidence reduce” north star. ([Tongyi DeepResearch][1])

---

## 2) Key behaviors and knobs

### 2.1 Thinking extent (global)

```yaml
thinking:
  extent: low | medium | high | heavy
  max_react_steps: 4 | 8 | 16 | 32
  beams: 1 | 2 | 3 | 4
  critique_passes: 0 | 1 | 2 | 3
  escalate_policy:
    to_tongyi_30b_if:
      coverage < 0.8 OR contradictions > 1 OR uncertainty_high
  summarization_ratio: 0.1..0.5  # how aggressively to compress workspace per round
```

* **Native** = `low/medium`; **Heavy** = `high/heavy` + workspace reconstruction. Heavy mirrors Tongyi’s test‑time scaling and “synthesis→reconstruction” cadence. ([Tongyi DeepResearch][1])
* **Escalation** uses OpenRouter’s free Tongyi 30B (131k context). ([OpenRouter][2])

### 2.2 Search profile (per task)

```yaml
search:
  engines: [brave, google_pse, tavily, serper]
  topk_per_engine: 8
  freshness_days: 365
  safe_mode: standard
  api_budget_usd: 0.50
  allow_ddg_instant_answer: true  # not a full SERP, adjunct only
```

* **Bing**: don’t depend on it (API retired Aug 11, 2025). ([The Verge][8])
* **DDG**: the **Instant Answer** endpoint is free but not full results—treat as auxiliary; use SERP providers if you want DDG‑like listings. ([Postman][9])
* **Alternatives**: Brave’s official API; Google **Programmable Search JSON** ($5/1k queries, 10k/day); **Tavily** (basic vs advanced credits); commercial SERPs (SerpApi/Serper/SearchAPI.io). ([Brave][3])

---

## 3) Evidence layer & “Evidence‑Reduce”

### 3.1 Source capture & traceability

* **Snapshots:** Store raw responses as **WARC**; persist both HTML and PDF bytes with content SHA‑256 and HTTP headers. ([GitHub][4])
* **Anchors:** For every quoted span or table cell used, emit a **W3C Web Annotation** selector (TextQuote + TextPosition) so citations remain resolvable even after minor DOM changes. ([W3C][10])

**`SourceDoc` schema (selected):**

```json
{
  "id": "src_...",
  "url": "https://...",
  "retrieved_at": "2025-11-04T15:12:00Z",
  "content_hash": "sha256:...",
  "warc_path": "warc/2025/11/04/...",
  "mime": "text/html|application/pdf",
  "publish_date": "2024-08-21",
  "source_type": "peer_review|preprint|registry|news|blog|database",
  "engine": "brave|google_pse|tavily|serper|direct",
  "license_hint": "open|paywalled|unknown",
  "meta": {"doi":"10.xxxx/...", "nct_id":"NCT01234567"}
}
```

### 3.2 Map → Canonicalize → Group → Merge → Adjudicate

**Map (extraction)**

* Turn passages/tables into **atomic propositions** of form:

  * **Clinical:** `Effect(intervention, comparator, outcome, population, estimate, ci, unit, timepoint, study_type)`
  * **Composition:** `Presence(drink, compound, amount, unit, method, context)`
* Each proposition carries **anchors** (selectors), **doc_id**, and **method notes** (e.g., GC‑MS). For tables, extract with PDF table parser, attach cell selectors.

**Canonicalize**

* Normalize **entities** (UMLS/MeSH for P/I/O; PubChem CID/ChEBI for compounds). Unit normalization (e.g., mg/L ↔ ppm).
* Date alignment (trial start date vs publication date).
* Join with **Crossref** + **PubMed** metadata to fill DOI, journal, article type. ([crossref.org][11])

**Group (claim signatures)**

* Hash on **signature** fields that define *the same claim*:

  * Clinical: `(population ~ fuzzy), intervention, comparator, outcome, timepoint`
  * Composition: `drink (style/origin), compound, context (brew temp, roast, etc.)`

**Merge (quantitative synthesis)**

* If comparable (units, endpoints match): compute **random‑effects** pooled estimate; otherwise present stratified distributions and ranges. (Framework hook; MVP can report weighted mean ± IQR and flag heterogeneity.)

**Adjudicate (disagreement‑aware)**

* Score each proposition with a **source weight**:
  `w = f(source_type, peer_review, sample_size, method, recency, registry_link)` with caps for preprints/blogs; **RCT/SR > cohort > preprint > blog/news**; **registry link (NCT)** boosts.
* **Contradiction detector** flags claim groups with non‑overlapping CIs or mutually exclusive statements; **Critic** forces a final stance: *supported / mixed / refuted / insufficient*.

**Why this approach?** It operationalizes “evidence reduce” into deterministic steps with pluggable stats, while preserving verifiable anchors. It’s also consistent with Heavy mode’s discipline of **synthesis before expansion**. ([Tongyi DeepResearch][1])

---

## 4) Domain adapters

### 4.1 Clinical trials (PICO‑first)

* **Connectors:** ClinicalTrials.gov **v2 API** (modernized), PubMed/PMC via NCBI **E‑utilities**, Crossref for DOI metadata. ([National Library of Medicine][5])
* **PICO tagging:** start with rule‑assisted prompts; add model‑based extractors drawing on recent PICO extraction literature for RCT abstracts to reduce screening time. ([OUP Academic][12])
* **Extra fields:** trial phase, enrollment, randomization/blinding flags, registry IDs, analysis population (ITT/PP), primary endpoint definitions, timepoints.

**Clinical `Effect` example (JSONL):**

```json
{"claim_id":"clm_x", "type":"Effect",
 "I":"metformin 500 mg bid", "C":"placebo", "O":"HbA1c change",
 "P":"T2DM adults", "estimate":-0.9, "unit":"% HbA1c", "ci":[-1.2,-0.6],
 "timepoint":"12w", "study_type":"RCT", "n":220, "anchors":[...], "doc_id":"src_..."}
```

### 4.2 Flavor chemistry (Drink×Compound matrix)

* **Databases:** **FlavorDB/FlavorDB2** (flavor molecules & food sources), **FooDB** (food chemical constituents), optionally **FSBI‑DB/PhytoHub**; normalize to **PubChem CID**. ([OUP Academic][6])
* **Extraction:** look for **tables & method sections** (GC‑MS/LC‑MS) and build `Presence()` propositions with concentration and analytic method; allow ranges and detection limits.
* **Matrix builder:** pivot **aggregated propositions** into **drinks × compounds**, cells storing `{est, range, n, method, sources[]}` for immediate export.

---

## 5) Models & routing

* **Default**: run **FlashResearch‑4B‑Thinking** locally (Qwen‑4B base, distilled from Tongyi 30B; GGUF quants exist; single 12–16 GB GPU is fine). **Note**: model card shows **MIT** on top, **Apache‑2.0** in metadata—lock license at commit time. ([Hugging Face][7])
* **Escalation**: **Tongyi‑DeepResearch‑30B‑A3B** via OpenRouter (131k context; free variant exists for testing). This model explicitly supports **ReAct** and an **IterResearch “Heavy”** rollout, which matches our loop. ([OpenRouter][2])

---

## 6) Module‑level specifications

### 6.1 Planner + Critic

* **Inputs:** question, prior report state, `thinking.extent`, budgets.
* **Outputs:** next‑step plan (search → visit → extract → reduce → synthesize), **stop**/continue decision, and **critic notes** (what would falsify current top claim).
* **Constraints:** Disallow exposing internal chain‑of‑thought in user‑facing text; only publish artifacts (claims, evidence, reasoning summaries).

### 6.2 Search Broker

* **Interface:**

```python
SearchQuery{q, site_filters[], time_range, region, engine, topk}
SearchResult{engine, title, url, snippet, rank, retrieved_at}
```

* **Providers & notes:**

  * **Brave Search API** (official, privacy‑forward). ([Brave][3])
  * **Google Programmable Search JSON** ($5/1k queries; 10k/day). ([Google for Developers][13])
  * **Tavily** (basic vs advanced credits). ([docs.tavily.com][14])
  * **SERP providers** (SerpApi/Serper/SearchAPI.io) with DDG/Google/News endpoints. ([SerpApi][15])
  * **DDG Instant Answer**: free summaries (no full SERP). ([Postman][9])
* **Ranking:** Reciprocal‑rank fusion + freshness bias; dedupe by normalized URL + content hash.

### 6.3 Fetch & Parse

* Respect robots, rate limits; capture **WARC**; extract HTML via **readability**; **PDF tables** via pdfminer/pymupdf + table detectors. Store **anchors** (selectors) for every quote/table cell. ([GitHub][4])

### 6.4 Evidence Store

* **Relational (Postgres/SQLite):** sources, annotations, propositions, claim groups, merges, weights.
* **Vector layer (pgvector):** passage embeddings for quick re‑finding.
* **Graph (Neo4j or Postgres adjacency):** `SourceDoc -> supports|contradicts -> Claim`.

### 6.5 Evidence‑Reduce Engine

* **Map:** LLM‑aided extraction with templates per domain; strict **quote+selector** requirement on any nontrivial claim.
* **Canonicalize:** unit/entity/date normalization; DOI/pubmed lookup. ([crossref.org][11])
* **Group:** signature hash; **heterogeneity checks** to gate merging.
* **Merge:** numeric merges (pooled means, CIs; random‑effects hook); textual merges create **stance distributions**.
* **Adjudicate:** choose **supported/mixed/refuted/insufficient** with rationale; push unresolved contradictions to **Critic** loop.

### 6.6 Synthesis & Reports

* **Claim Lens:** per‑claim page: stance, merged numbers, **supporting** and **contradicting** sources (with anchors).
* **Evidence Matrix:** `sources × assertions` with color coding for stance.
* **Exec Brief:** bottom‑line + what would change the conclusion.
* **Diffs:** when re‑run later, show **per‑claim changes** (new evidence, altered merge).

### 6.7 Telemetry & Governance

* **Provenance JSON** per run (model versions, prompts, tool calls, URLs, hashes).
* **Budget ledger** (tokens, API dollars).
* **Safety rails:** medical/financial not legal advice.
* **Licensing:** surface model/data licenses; snapshot only what ToS permits.

---

## 7) External connectors (initial)

* **Clinical:** ClinicalTrials.gov **v2** (modernized endpoints), **NCBI E‑utilities** (PubMed/PMC), **Crossref REST**. ([National Library of Medicine][5])
* **Chemistry/Food:** **FlavorDB/FlavorDB2**, **FooDB** (plus link‑outs to **PubChem**/ChEBI). ([OUP Academic][6])
* **General web:** **Brave API**, **Google PSE JSON**, **Tavily**, **Serp APIs**; **DDG Instant Answer** adjunct. ([Brave][3])

---

## 8) Data schemas (selected, Pydantic‑style)

```python
class Annotation(BaseModel):
    doc_id: str
    selector: Dict[str, Any]  # W3C TextQuote/TextPosition
    quote: str
    context: str

class Proposition(BaseModel):
    id: str
    type: Literal["Effect","Presence","Fact"]
    payload: Dict[str, Any]    # typed fields per proposition type
    anchors: List[Annotation]
    doc_id: str
    quality: Dict[str, Any]    # method flags, n, peer_reviewed, etc.
    extracted_at: datetime

class ClaimGroup(BaseModel):
    signature: str
    domain: Literal["clinical","flavor","general"]
    propositions: List[str]    # ids
    merge: Optional[Dict[str, Any]]
    stance: Literal["supported","mixed","refuted","insufficient"]
    rationale: str
```

**Evidence Matrix row:** `{"doc_id": "...", "url": "...", "claims": [{"signature":"...", "stance":"support|contradict|neutral", "anchors":[...]}]}`

---

## 9) Run loop (Native vs Heavy)

**Native (fast):**

1. Expand queries → search (k≈8 per engine).
2. Fetch top results → map to propositions.
3. Reduce once → produce brief + claims table.
4. If `coverage<τ or contradictions>0`, **either** loop once more **or** escalate.

**Heavy (test‑time scaled):**
Repeat rounds:

* **Reconstruct** minimal workspace from prior round (central report + unresolved claims), **synthesize first**, then expand queries specifically for unresolved edges; compress notes each round. This follows Tongyi’s Heavy/IterResearch recipe. ([Tongyi DeepResearch][1])

---

## 10) Implementation skeleton & priorities

**Sprint 1 (MVP):**

* Local 4B model router + OpenRouter Tongyi 30B fallback. ([OpenRouter][2])
* Search broker: Brave + Google PSE JSON + Tavily + Serper; DDG Instant Answer adjunct. ([Brave][3])
* Fetch/WARC + HTML/PDF parsing; W3C selectors; Postgres+pgvector schema. ([GitHub][4])
* Evidence‑Reduce (generic propositions, numeric merge v0, contradiction flags).
* Report/Claim Lens UI (CLI + simple web).

**Sprint 2 (Clinical adapter):**

* CT.gov v2 and PubMed/Crossref connectors; basic **PICO** extraction; RCT flags in `Effect()` payload. ([National Library of Medicine][5])

**Sprint 3 (Flavor adapter):**

* FlavorDB/FooDB ingestion; PubChem normalization; **Drink×Compound** matrix builder with export. ([OUP Academic][6])

---

## 11) Configuration surface (YAML)

```yaml
agent:
  mode: native|heavy
  thinking:
    extent: medium
    max_react_steps: 8
    beams: 2
    critique_passes: 1
    escalate_policy: {coverage: 0.8, contradictions: 1}

search:
  providers:
    brave: {api_key: "...", region: "us"}
    google_pse: {cx: "...", key: "..."}    # $5/1k queries
    tavily: {api_key: "...", depth: "advanced"}  # credits
    serper: {api_key: "...", engine: "google"}   # paid SERP
    ddg_ia: {enabled: true}  # adjunct only

storage:
  warc_dir: "./warc"
  db_url: "postgresql://..."
  cache_ttl_days: 14

domains:
  clinical: {ctgov_v2: {...}, pubmed: {...}, crossref: {...}}
  flavor: {flavordb: {...}, foodb: {...}, pubchem: {...}}
```

---

## 12) Output guarantees (contract)

Every final answer must include:

* **Key Claims Table** (each claim → stance + **anchored citations**).
* **Evidence Matrix** (source vs assertion).
* **Assumptions/Uncertainties** + “what would change the conclusion.”
* **Provenance JSON** and **WARC snapshot list** for audit.

---

## 13) Why these choices (selective evidence)

* **Heavy vs Native** and the round‑based **synthesis→reconstruction** cadence are explicitly described in Tongyi’s release; we replicate behaviorally (not weights). ([Tongyi DeepResearch][1])
* **OpenRouter Tongyi 30B** offers **131k tokens** and is available with a free variant—good for escalations; local 4B handles the common case. ([OpenRouter][2])
* **Search reality 2025:** Bing API retired; **DDG** does not expose a full SERP API (Instant Answer only), so **Brave**, **Google PSE JSON**, **Tavily**, and **SERP providers** are the pragmatic backbone. ([The Verge][8])
* **Traceability:** WARC + Web Annotation selectors give durable, verifiable citations. ([GitHub][4])
* **Clinical adapters** and **PICO** extraction are well‑studied and supported by public APIs. ([National Library of Medicine][5])
* **Flavor chemistry** has curated open databases (**FlavorDB**, **FooDB**) that we can normalize to PubChem CIDs for cross‑source joins. ([OUP Academic][6])

---

## 14) Potential refutations (and counters)

1. **“DDG is free; why not just use that?”**
   *Refutation:* The **Instant Answer** endpoint is not a full SERP and won’t return the ranked web links needed for evidence‑first research. Use it as an adjunct, not the backbone. **Counter:** Build atop Brave/Google PSE/Tavily/SERP providers, optionally enrich with DDG IA. ([Postman][9])

2. **“Heavy mode adds latency; why not just stuff more into context?”**
   *Refutation:* Bigger context ≠ better synthesis; Tongyi’s **Heavy** emphasizes *reconstruction before expansion* to maintain cognitive focus. **Counter:** Gate Heavy by coverage/contradiction signals and escalate model size only when needed. ([Tongyi DeepResearch][1])

3. **“Bing is the best web index; we should use it.”**
   *Refutation:* The **Bing Search API** was retired Aug 11, 2025—don’t build on sand. **Counter:** Use Brave/Google PSE/Tavily; keep the broker pluggable for future engines. ([The Verge][8])

4. **“FlashResearch licensing is unclear.”**
   *Refutation:* The HF card shows **MIT** top‑level and **Apache‑2.0** in metadata—this ambiguity can block adoption. **Counter:** Pin an exact model commit and stash the license artifact in our repo; require a pre‑flight license check in CI. ([Hugging Face][7])

---

## 15) Review checklist (decisions for you)

* ✅ Claim signatures for **clinical**: accept `(P,I,C,O,timepoint)` as the grouping key?
* ✅ Numerical merge policy defaults: pooled mean with heterogeneity gates; random‑effects optional behind a flag.
* ✅ Source weighting priors for **stance adjudication** (e.g., RCT/SR > cohort > preprint > news/blog; registry link bonus).
* ✅ Flavor adapter: prioritize **FlavorDB2 + FooDB** and PubChem CID normalization for matrix export (CSV/Parquet)? ([ift.onlinelibrary.wiley.com][16])
* ✅ Search budget defaults and providers to enable by default (my suggestion above).
* ✅ Accept OpenRouter Tongyi 30B escalation thresholds (`coverage<0.8` or contradictions>1) to start? ([OpenRouter][2])

If this matches your intent, I’ll turn it into a concrete **repo scaffold** (Python package + CLI + minimal web UI), including DB migrations, provider adapters, the Evidence‑Reduce engine skeleton, and a couple of **end‑to‑end example tasks** (one RCT question; one **Drink×Compound** matrix build).

[1]: https://tongyi-agent.github.io/blog/introducing-tongyi-deep-research/ "Tongyi DeepResearch: A New Era of Open-Source AI Researchers | Tongyi DeepResearch"
[2]: https://openrouter.ai/alibaba/tongyi-deepresearch-30b-a3b%3Afree "Tongyi DeepResearch 30B A3B (free) - API, Providers, Stats | OpenRouter"
[3]: https://brave.com/search/api/?utm_source=chatgpt.com "Brave Search API"
[4]: https://github.com/webrecorder/warcio?utm_source=chatgpt.com "webrecorder/warcio: Streaming WARC/ARC library for fast ..."
[5]: https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html?utm_source=chatgpt.com "ClinicalTrials.gov API Version 2.0 Now Available. 2024 Mar-Apr"
[6]: https://academic.oup.com/nar/article/46/D1/D1210/4559748?utm_source=chatgpt.com "FlavorDB: a database of flavor molecules - Oxford Academic"
[7]: https://huggingface.co/flashresearch/FlashResearch-4B-Thinking "flashresearch/FlashResearch-4B-Thinking · Hugging Face"
[8]: https://www.theverge.com/news/667517/microsoft-bing-search-api-end-of-support-ai-replacement?utm_source=chatgpt.com "Microsoft shuts off Bing Search APIs and recommends switching to AI"
[9]: https://www.postman.com/api-evangelist/search/documentation/bdkqiym/duckduckgo-instant-answer-api?utm_source=chatgpt.com "DuckDuckGo Instant Answer API | Documentation"
[10]: https://www.w3.org/TR/annotation-model/?utm_source=chatgpt.com "Web Annotation Data Model"
[11]: https://www.crossref.org/documentation/retrieve-metadata/rest-api/?utm_source=chatgpt.com "REST API"
[12]: https://academic.oup.com/bioinformatics/article/39/9/btad542/7260503?utm_source=chatgpt.com "Towards precise PICO extraction from abstracts of randomized ..."
[13]: https://developers.google.com/custom-search/docs/overview?utm_source=chatgpt.com "Overview | Programmable Search Engine"
[14]: https://docs.tavily.com/documentation/api-reference/endpoint/search?utm_source=chatgpt.com "Tavily Search"
[15]: https://serpapi.com/?utm_source=chatgpt.com "SerpApi: Google Search API"
[16]: https://ift.onlinelibrary.wiley.com/doi/10.1111/1750-3841.17298?utm_source=chatgpt.com "FlavorDB2: An updated database of flavor molecules"
