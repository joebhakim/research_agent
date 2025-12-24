from __future__ import annotations

from tests import path_setup  # noqa: F401

import unittest
from datetime import datetime

from research_agent.evidence.extract import chunk_text, extract_propositions
from research_agent.evidence.policy import policy_for_extent
from research_agent.types import DocumentText
from tests.stubs import StubLLM


class ExtractTests(unittest.TestCase):
    def test_chunk_text_overlap(self) -> None:
        text = "0123456789" * 5
        chunks = chunk_text(text, chunk_chars=20, overlap=5)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0][-5:], chunks[1][:5])

    def test_extract_propositions(self) -> None:
        doc = DocumentText(
            doc_id="doc1",
            url="http://example.com",
            title="Example",
            snippet="",
            text="Water boils at 100 C.",
            content_hash="hash",
            content_type="text/html",
            retrieved_at=datetime.utcnow(),
        )
        policy = policy_for_extent("medium")
        props = extract_propositions(doc, StubLLM(), policy)
        self.assertGreaterEqual(len(props), 1)
        prop = props[0]
        self.assertEqual(prop.payload.get("claim_text"), "Water boils at 100 C.")
        self.assertEqual(prop.payload.get("quote"), "Water boils at 100 C.")
        self.assertTrue(prop.anchors)
        selector = prop.anchors[0].selector
        self.assertIn("start", selector)
        self.assertIn("end", selector)


if __name__ == "__main__":
    unittest.main()
