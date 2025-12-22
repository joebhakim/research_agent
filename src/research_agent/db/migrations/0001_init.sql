CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_docs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    warc_path TEXT,
    mime TEXT NOT NULL,
    publish_date TEXT,
    source_type TEXT,
    engine TEXT,
    license_hint TEXT,
    meta_json TEXT
);

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    selector_json TEXT NOT NULL,
    quote TEXT NOT NULL,
    context TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES source_docs(id)
);

CREATE TABLE IF NOT EXISTS propositions (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    anchors_json TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    quality_json TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES source_docs(id)
);

CREATE TABLE IF NOT EXISTS claim_groups (
    signature TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    propositions_json TEXT NOT NULL,
    merge_json TEXT,
    stance TEXT NOT NULL,
    rationale TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    thinking_extent TEXT NOT NULL,
    report_path TEXT,
    status TEXT NOT NULL,
    meta_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_source_docs_url ON source_docs(url);
CREATE INDEX IF NOT EXISTS idx_annotations_doc_id ON annotations(doc_id);
CREATE INDEX IF NOT EXISTS idx_propositions_doc_id ON propositions(doc_id);
