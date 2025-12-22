from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
import json
import sqlite3

from research_agent.db.schema import apply_migrations
from research_agent.types import Annotation, ClaimGroup, Proposition, SourceDoc


class EvidenceStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def init(self) -> None:
        apply_migrations(self.db_path)

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def upsert_source(self, source: SourceDoc) -> None:
        conn = self.connect()
        with conn:
            conn.execute(
                """
                INSERT INTO source_docs (id, url, retrieved_at, content_hash, warc_path, mime, publish_date, source_type, engine, license_hint, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    url=excluded.url,
                    retrieved_at=excluded.retrieved_at,
                    content_hash=excluded.content_hash,
                    warc_path=excluded.warc_path,
                    mime=excluded.mime,
                    publish_date=excluded.publish_date,
                    source_type=excluded.source_type,
                    engine=excluded.engine,
                    license_hint=excluded.license_hint,
                    meta_json=excluded.meta_json
                """,
                (
                    source.id,
                    source.url,
                    source.retrieved_at.isoformat(),
                    source.content_hash,
                    source.warc_path,
                    source.mime,
                    source.publish_date,
                    source.source_type,
                    source.engine,
                    source.license_hint,
                    _json_dumps(source.meta),
                ),
            )

    def insert_annotation(self, annotation: Annotation) -> None:
        conn = self.connect()
        with conn:
            conn.execute(
                """
                INSERT INTO annotations (doc_id, selector_json, quote, context)
                VALUES (?, ?, ?, ?)
                """,
                (
                    annotation.doc_id,
                    _json_dumps(annotation.selector),
                    annotation.quote,
                    annotation.context,
                ),
            )

    def upsert_proposition(self, proposition: Proposition) -> None:
        conn = self.connect()
        with conn:
            conn.execute(
                """
                INSERT INTO propositions (id, type, payload_json, anchors_json, doc_id, quality_json, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    payload_json=excluded.payload_json,
                    anchors_json=excluded.anchors_json,
                    doc_id=excluded.doc_id,
                    quality_json=excluded.quality_json,
                    extracted_at=excluded.extracted_at
                """,
                (
                    proposition.id,
                    proposition.type,
                    _json_dumps(proposition.payload),
                    _json_dumps(proposition.anchors),
                    proposition.doc_id,
                    _json_dumps(proposition.quality),
                    proposition.extracted_at.isoformat(),
                ),
            )

    def upsert_claim_group(self, claim: ClaimGroup) -> None:
        conn = self.connect()
        with conn:
            conn.execute(
                """
                INSERT INTO claim_groups (signature, domain, propositions_json, merge_json, stance, rationale)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(signature) DO UPDATE SET
                    domain=excluded.domain,
                    propositions_json=excluded.propositions_json,
                    merge_json=excluded.merge_json,
                    stance=excluded.stance,
                    rationale=excluded.rationale
                """,
                (
                    claim.signature,
                    claim.domain,
                    _json_dumps(claim.propositions),
                    _json_dumps(claim.merge) if claim.merge else None,
                    claim.stance,
                    claim.rationale,
                ),
            )

    def record_run(
        self,
        run_id: str,
        question: str,
        created_at: datetime,
        mode: str,
        thinking_extent: str,
        report_path: str | None,
        status: str,
        meta: dict[str, object] | None = None,
    ) -> None:
        conn = self.connect()
        with conn:
            conn.execute(
                """
                INSERT INTO runs (id, question, created_at, mode, thinking_extent, report_path, status, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    question=excluded.question,
                    created_at=excluded.created_at,
                    mode=excluded.mode,
                    thinking_extent=excluded.thinking_extent,
                    report_path=excluded.report_path,
                    status=excluded.status,
                    meta_json=excluded.meta_json
                """,
                (
                    run_id,
                    question,
                    created_at.isoformat(),
                    mode,
                    thinking_extent,
                    report_path,
                    status,
                    _json_dumps(meta or {}),
                ),
            )


def _json_dumps(value: object) -> str:
    return json.dumps(value, default=_json_default)


def _json_default(value: object) -> str:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
