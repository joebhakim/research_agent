from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
import json
import re
from typing import Any, Iterable

from research_agent.parse.html import extract_text as extract_html_text
from research_agent.parse.pdf import extract_text as extract_pdf_text
from research_agent.types import DocumentText


def load_document_text(doc_input: dict[str, Any], fixtures_dir: Path | None) -> DocumentText:
    doc_id = str(doc_input.get("doc_id", "doc"))
    title = str(doc_input.get("title", ""))
    url = str(doc_input.get("url", ""))
    snippet = str(doc_input.get("snippet", ""))
    fixture = doc_input.get("text_fixture")
    content_type = str(doc_input.get("content_type", "text/plain"))
    text = str(doc_input.get("text", ""))
    format_hint = str(doc_input.get("format", "")).lower()

    if fixture:
        fixture_path = Path(fixture)
        if not fixture_path.is_absolute():
            base = fixtures_dir or Path.cwd()
            fixture_path = (base / fixture).resolve()
        suffix = fixture_path.suffix.lower()
        if format_hint == "pdf" or suffix == ".pdf":
            text = extract_pdf_text(fixture_path.read_bytes())
            content_type = "application/pdf"
        else:
            raw_text = fixture_path.read_text()
            if format_hint == "html" or suffix in {".html", ".htm"}:
                text = extract_html_text(raw_text)
                content_type = "text/html"
            else:
                text = raw_text
                content_type = "text/plain"

    return DocumentText(
        doc_id=doc_id,
        url=url,
        title=title,
        snippet=snippet,
        text=text,
        content_hash="",
        content_type=content_type,
        retrieved_at=datetime.utcnow(),
        engine=None,
        rank=None,
    )


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def parse_json(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    blob = _extract_json_blob(text)
    if not blob:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def _extract_json_blob(text: str) -> str | None:
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        return obj_match.group(0)
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        return arr_match.group(0)
    return None


def expand_path(data: Any, path: str) -> list[Any]:
    if path == "" or path is None:
        return [data]
    tokens = path.split(".")
    nodes = [data]
    for token in tokens:
        if not token:
            continue
        name, index = _parse_token(token)
        next_nodes: list[Any] = []
        for node in nodes:
            if isinstance(node, dict):
                value = node.get(name)
            else:
                value = None
            if index is None:
                if value is not None:
                    next_nodes.append(value)
                continue
            if not isinstance(value, list):
                continue
            if index == "*":
                next_nodes.extend(value)
            else:
                idx = int(index)
                if 0 <= idx < len(value):
                    next_nodes.append(value[idx])
        nodes = next_nodes
    return nodes


def _parse_token(token: str) -> tuple[str, str | None]:
    match = re.match(r"^([A-Za-z0-9_]+)(?:\[(\*|\d+)\])?$", token)
    if not match:
        return token, None
    return match.group(1), match.group(2)


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            result.append(value)
        else:
            result.append(str(value))
    return result
