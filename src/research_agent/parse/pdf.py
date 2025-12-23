from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_text(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        return ""

    for page in reader.pages:
        try:
            page_text = page.extract_text()
        except Exception:
            page_text = ""
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)
