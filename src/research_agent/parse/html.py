from __future__ import annotations

from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def extract_text(html: str) -> str:
    # TODO: Replace with readability and anchored selector extraction.
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()
