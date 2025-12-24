from __future__ import annotations

from tests import path_setup  # noqa: F401

import unittest

from research_agent.parse.html import extract_text as extract_html_text
from research_agent.parse.pdf import extract_text as extract_pdf_text


class ParseTests(unittest.TestCase):
    def test_extract_html_text(self) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        text = extract_html_text(html)
        self.assertIn("Hello", text)

    def test_extract_pdf_text_invalid(self) -> None:
        text = extract_pdf_text(b"not a pdf")
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
