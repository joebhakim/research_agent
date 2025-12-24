from __future__ import annotations

from tests import path_setup  # noqa: F401

import unittest
from datetime import datetime

from research_agent.evidence.reduce import reduce_evidence
from research_agent.types import DocumentText
from tests.stubs import StubLLM


class ReduceTests(unittest.TestCase):
    def test_reduce_evidence_basic_plumbing(self) -> None:
        docs = [
            DocumentText(
                doc_id="doc1",
                url="http://example.com/1",
                title="Example 1",
                snippet="",
                text="At sea level, water boils at 100 C (212 F).",
                content_hash="hash1",
                content_type="text/html",
                retrieved_at=datetime.utcnow(),
            ),
            DocumentText(
                doc_id="doc2",
                url="http://example.com/2",
                title="Example 2",
                snippet="",
                text="Boiling point decreases as altitude increases.",
                content_hash="hash2",
                content_type="text/html",
                retrieved_at=datetime.utcnow(),
            ),
        ]
        result = reduce_evidence(docs, StubLLM(), "medium")
        self.assertGreaterEqual(len(result.claim_groups), 1)
        claim = result.claim_groups[0]
        self.assertEqual(len(claim.signature), 16)
        self.assertTrue(claim.claim_text)
        self.assertIn(claim.stance, {"supported", "mixed", "refuted", "insufficient"})
        counts = claim.merge.get("counts") if claim.merge else None
        if not counts:
            self.fail("No counts found")
        else:
            self.assertIsInstance(counts, dict)
            self.assertGreaterEqual(counts.get("support", 0), 1)


    def test_reduce_evidence_actual_results(self) -> None:
        """
        The two docs here disagree, forming a bilaterally refuting pair of claims.
        """
        docs = [
            DocumentText(
                doc_id="doc1",
                url="http://example.com/1",
                title="Example 1",
                snippet="",
                text="At sea level, water boils at 100 C (212 F).",
                content_hash="hash1",
                content_type="text/html",
                retrieved_at=datetime.utcnow(),
            ),
            DocumentText(
                doc_id="doc2",
                url="http://example.com/2",
                title="Example 2",
                snippet="",
                text="Water boils at 100 F (37.8 C) at sea level.",
                content_hash="hash2",
                content_type="text/html",
                retrieved_at=datetime.utcnow(),
            ),

        ]
        result = reduce_evidence(docs, StubLLM(), "medium")
        self.assertGreaterEqual(len(result.claim_groups), 1)
        claim = result.claim_groups[0]
        self.assertEqual(claim.stance, "refuted")

        

if __name__ == "__main__":
    unittest.main()
