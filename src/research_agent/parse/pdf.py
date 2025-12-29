from __future__ import annotations

from io import BytesIO

from loguru import logger
from pypdf import PdfReader


def extract_text(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""

    for page in reader.pages:
        try:
            page_text = page.extract_text()
        except Exception:
            page_text = ""
        if page_text:
            text_parts.append(page_text)

    result = "\n".join(text_parts)
    logger.debug(f"Extracted {len(result)} chars from PDF")
    return result
