from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3


MIGRATIONS = ["0001_init.sql", "0002_claim_text_and_run_sources.sql"]


@dataclass
class MigrationResult:
    version: int
    applied: bool


def apply_migrations(db_path: Path) -> list[MigrationResult]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row

    results: list[MigrationResult] = []
    with conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        current = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()[0]
        if current is None:
            current = 0

        migrations_dir = Path(__file__).resolve().parent / "migrations"
        for idx, filename in enumerate(MIGRATIONS, start=1):
            if idx <= current:
                results.append(MigrationResult(version=idx, applied=False))
                continue
            sql = (migrations_dir / filename).read_text()
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (idx, datetime.utcnow().isoformat()),
            )
            results.append(MigrationResult(version=idx, applied=True))

    conn.close()
    return results
