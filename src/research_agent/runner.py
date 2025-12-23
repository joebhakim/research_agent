from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib
import json
import uuid

from research_agent.config import AppConfig, SearchConfig
from research_agent.evidence.reduce import reduce_evidence
from research_agent.evidence.store import EvidenceStore
from research_agent.fetch.fetcher import fetch_url
from research_agent.llm.router import get_model_client
from research_agent.parse.html import extract_text as extract_html_text
from research_agent.parse.pdf import extract_text as extract_pdf_text
from research_agent.report.render import render_report
from research_agent.search.broker import SearchBroker
from research_agent.types import (
    ClaimGroup,
    DocumentText,
    Proposition,
    SearchQuery,
    SearchResult,
    SourceDoc,
)


@dataclass
class RunOutput:
    run_id: str
    report_path: Path
    claim_groups: list[ClaimGroup]


@dataclass
class PipelineResult:
    documents: list[DocumentText]
    propositions: list[Proposition]
    claim_groups: list[ClaimGroup]


def run(question: str, config: AppConfig, model_override: str | None = None) -> RunOutput:
    run_id = _make_run_id()
    run_dir = Path(config.storage.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    store = EvidenceStore(Path(config.storage.sqlite_path))
    store.init()

    routed = get_model_client(
        config,
        thinking_extent=config.agent.thinking.extent,
        override=model_override,
    )

    created_at = datetime.utcnow()
    run_meta = {
        "model_override": model_override,
        "model_choice": routed.name,
        "model_name": routed.client.model_name,
        "model_api_base": routed.client.api_base,
    }
    store.record_run(
        run_id=run_id,
        question=question,
        created_at=created_at,
        mode=config.agent.mode,
        thinking_extent=config.agent.thinking.extent,
        report_path=None,
        status="running",
        meta=run_meta,
    )

    try:
        if config.agent.mode == "heavy":
            pipeline = _run_heavy(question, config, store, routed.client, run_id, run_dir)
        else:
            pipeline = _run_native(question, config, store, routed.client, run_id, run_dir)

        for proposition in pipeline.propositions:
            store.upsert_proposition(proposition)
            for anchor in proposition.anchors:
                store.insert_annotation(anchor)

        for claim in pipeline.claim_groups:
            store.upsert_claim_group(claim)

        report = render_report(question, pipeline.claim_groups)
        report_path = run_dir / "report.md"
        report_path.write_text(report)

        provenance_path = _write_provenance(
            run_dir,
            run_id,
            question,
            routed,
            pipeline.documents,
            pipeline.claim_groups,
        )

        store.record_run(
            run_id=run_id,
            question=question,
            created_at=created_at,
            mode=config.agent.mode,
            thinking_extent=config.agent.thinking.extent,
            report_path=str(report_path),
            status="completed",
            meta={**run_meta, "provenance_path": str(provenance_path)},
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
            meta=run_meta,
        )
        store.close()
        raise

    store.close()
    return RunOutput(run_id=run_id, report_path=report_path, claim_groups=pipeline.claim_groups)


def _run_native(
    question: str,
    config: AppConfig,
    store: EvidenceStore,
    llm_client,
    run_id: str,
    run_dir: Path,
) -> PipelineResult:
    broker = SearchBroker.from_config(config.search)
    queries = build_queries(question, config.search)
    sources_dir = run_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    seen_urls: set[str] = set()
    documents: list[DocumentText] = []
    for query in queries:
        results = broker.search(query)
        for result in results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            doc = _fetch_and_parse(result, query.q, run_id, sources_dir, store)
            if doc and doc.text:
                documents.append(doc)

    reduce_result = reduce_evidence(documents, llm_client, config.agent.thinking.extent)
    return PipelineResult(
        documents=documents,
        propositions=reduce_result.propositions,
        claim_groups=reduce_result.claim_groups,
    )


def _run_heavy(
    question: str,
    config: AppConfig,
    store: EvidenceStore,
    llm_client,
    run_id: str,
    run_dir: Path,
) -> PipelineResult:
    # TODO: Implement iterative reconstruction and synthesis across rounds.
    return _run_native(question, config, store, llm_client, run_id, run_dir)


def build_queries(question: str, search_config: SearchConfig) -> list[SearchQuery]:
    return [
        SearchQuery(
            q=question,
            topk=search_config.topk_per_engine,
            safe_mode=search_config.safe_mode,
            freshness_days=search_config.freshness_days,
        )
    ]


def _fetch_and_parse(
    result: SearchResult,
    query_text: str,
    run_id: str,
    sources_dir: Path,
    store: EvidenceStore,
) -> DocumentText | None:
    try:
        fetched = fetch_url(result.url)
    except Exception:
        return None

    content_type = fetched.headers.get("content-type", "text/html")
    content_hash = hashlib.sha256(fetched.content).hexdigest()
    doc_id = f"src_{content_hash[:12]}"

    raw_path = sources_dir / f"{doc_id}.bin"
    raw_path.write_bytes(fetched.content)

    text = ""
    if _is_pdf(content_type, fetched.url):
        text = extract_pdf_text(fetched.content)
    else:
        text = extract_html_text(fetched.content.decode("utf-8", errors="replace"))

    text_path = sources_dir / f"{doc_id}.text.txt"
    text_path.write_text(text)

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
    store.insert_run_source(
        run_id=run_id,
        doc_id=doc_id,
        url=fetched.url,
        engine=result.engine,
        rank=result.rank,
        query=query_text,
        retrieved_at=fetched.retrieved_at,
        title=result.title,
        snippet=result.snippet,
        content_type=content_type,
        content_hash=content_hash,
        raw_path=str(raw_path),
        text_path=str(text_path),
    )

    return DocumentText(
        doc_id=doc_id,
        url=fetched.url,
        title=result.title,
        snippet=result.snippet,
        text=text,
        content_hash=content_hash,
        content_type=content_type,
        retrieved_at=fetched.retrieved_at,
        engine=result.engine,
        rank=result.rank,
    )


def _is_pdf(content_type: str, url: str) -> bool:
    if "pdf" in content_type.lower():
        return True
    return url.lower().endswith(".pdf")


def _write_provenance(
    run_dir: Path,
    run_id: str,
    question: str,
    routed,
    documents: list[DocumentText],
    claim_groups: list[ClaimGroup],
) -> Path:
    data = {
        "run_id": run_id,
        "question": question,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": {
            "choice": routed.name,
            "api_base": routed.client.api_base,
            "model_name": routed.client.model_name,
        },
        "documents": [
            {
                "doc_id": doc.doc_id,
                "url": doc.url,
                "title": doc.title,
                "snippet": doc.snippet,
                "retrieved_at": doc.retrieved_at.isoformat(),
                "content_hash": doc.content_hash,
                "content_type": doc.content_type,
                "engine": doc.engine,
                "rank": doc.rank,
                "raw_path": str(run_dir / "sources" / f"{doc.doc_id}.bin"),
                "text_path": str(run_dir / "sources" / f"{doc.doc_id}.text.txt"),
            }
            for doc in documents
        ],
        "claims": [
            {
                "signature": claim.signature,
                "claim_text": claim.claim_text,
                "stance": claim.stance,
                "rationale": claim.rationale,
                "merge": claim.merge,
            }
            for claim in claim_groups
        ],
    }
    provenance_path = run_dir / "provenance.json"
    provenance_path.write_text(json.dumps(data, indent=2))
    return provenance_path


def _make_run_id() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:6]}"
