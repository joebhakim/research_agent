from __future__ import annotations

from tests import path_setup  # noqa: F401

import sqlite3
import tempfile
import unittest
from pathlib import Path

from research_agent.db.schema import apply_migrations


class SchemaTests(unittest.TestCase):
    def test_migrations_create_claim_text_and_run_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            apply_migrations(db_path)
            conn = sqlite3.connect(db_path)
            try:
                columns = conn.execute("PRAGMA table_info(claim_groups)").fetchall()
                column_names = {row[1] for row in columns}
                self.assertIn("claim_text", column_names)

                run_sources = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='run_sources'"
                ).fetchone()
                self.assertIsNotNone(run_sources)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
