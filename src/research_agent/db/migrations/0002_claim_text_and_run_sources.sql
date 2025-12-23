ALTER TABLE claim_groups ADD COLUMN claim_text TEXT;

CREATE TABLE IF NOT EXISTS run_sources (
    run_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    url TEXT NOT NULL,
    engine TEXT,
    rank INTEGER,
    query TEXT,
    retrieved_at TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    content_type TEXT,
    content_hash TEXT,
    raw_path TEXT,
    text_path TEXT,
    PRIMARY KEY (run_id, doc_id),
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(doc_id) REFERENCES source_docs(id)
);

CREATE INDEX IF NOT EXISTS idx_run_sources_run_id ON run_sources(run_id);
