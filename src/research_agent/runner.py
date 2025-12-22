from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib
import uuid

from research_agent.config import AppConfig
from research_agent.evidence.reduce import reduce_evidence
from research_agent.evidence.store import EvidenceStore
from research_agent.fetch.fetcher import fetch_url
from research_agent.parse.html import extract_text as extract_html_text
from research_agent.parse.pdf import extract_text as extract_pdf_text
from research_agent.report.render import render_report
from research_agent.search.broker import SearchBroker
from research_agent.types import ClaimGroup, SearchQuery, SearchResult, SourceDoc


@dataclass
class RunOutput:
    run_id: str
    report_path: Path
    claim_groups: list[ClaimGroup]


def run(question: str, config: AppConfig) -> RunOutput:
    run_id = _make_run_id()
    run_dir = Path(config.storage.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    store = EvidenceStore(Path(config.storage.sqlite_path))
    store.init()

    created_at = datetime.utcnow()
    store.record_run(
        run_id=run_id,
        question=question,
        created_at=created_at,
        mode=config.agent.mode,
        thinking_extent=config.agent.thinking.extent,
        report_path=None,
        status="running",
    )

    try:
        if config.agent.mode == "heavy":
            claim_groups = _run_heavy(question, config, store)
        else:
            claim_groups = _run_native(question, config, store)

        report = render_report(question, claim_groups)
        report_path = run_dir / "report.md"
        report_path.write_text(report)

        store.record_run(
            run_id=run_id,
            question=question,
            created_at=created_at,
            mode=config.agent.mode,
            thinking_extent=config.agent.thinking.extent,
            report_path=str(report_path),
            status="completed",
        )
    except Exception:
        store.record_run(
            run_id=run_id,
            question=question,
            created_at=created_at,
            mode=config.agent.mode,
            thinking_extent=config.agent.thinking.extent,
            report_path=None,
            status="failed",
        )
        store.close()
        raise

    store.close()
    return RunOutput(run_id=run_id, report_path=report_path, claim_groups=claim_groups)


def _run_native(question: str, config: AppConfig, store: EvidenceStore) -> list[ClaimGroup]:
    broker = SearchBroker.from_config(config.search)
    queries = build_queries(question, config.search.topk_per_engine)
    results: list[SearchResult] = []
    for query in queries:
        results.extend(broker.search(query))

    docs: list[str] = []
    for result in results:
        doc_text = _fetch_and_parse(result, store)
        if doc_text:
            docs.append(doc_text)

    reduce_result = reduce_evidence(docs)
    for claim in reduce_result.claim_groups:
        store.upsert_claim_group(claim)
    for proposition in reduce_result.propositions:
        store.upsert_proposition(proposition)

    return reduce_result.claim_groups


def _run_heavy(question: str, config: AppConfig, store: EvidenceStore) -> list[ClaimGroup]:
    # TODO: Implement iterative reconstruction and synthesis across rounds.
    return _run_native(question, config, store)


def build_queries(question: str, topk: int) -> list[SearchQuery]:
    return [SearchQuery(q=question, topk=topk)]


def _fetch_and_parse(result: SearchResult, store: EvidenceStore) -> str:
    fetched = fetch_url(result.url)
    content_type = fetched.headers.get("content-type", "text/html")
    content_hash = hashlib.sha256(fetched.content).hexdigest()
    doc_id = f"src_{content_hash[:12]}"

    source_doc = SourceDoc(
        id=doc_id,
        url=fetched.url,
        retrieved_at=fetched.retrieved_at,
        content_hash=f"sha256:{content_hash}",
        warc_path=None,
        mime=content_type.split(";")[0],
        engine=result.engine,
        meta={"title": result.title, "snippet": result.snippet},
    )
    store.upsert_source(source_doc)

    if _is_pdf(content_type, fetched.url):
        return extract_pdf_text(fetched.content)
    return extract_html_text(fetched.content.decode("utf-8", errors="replace"))


def _is_pdf(content_type: str, url: str) -> bool:
    if "pdf" in content_type.lower():
        return True
    return url.lower().endswith(".pdf")


def _make_run_id() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:6]}"
