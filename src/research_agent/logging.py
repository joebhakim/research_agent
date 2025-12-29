"""Logging configuration for research-agent.

Provides two log outputs:
- run.log: Human-readable, scannable stage progress (colored terminal + file)
- trace.jsonl: Detailed content (claim text, LLM prompts/responses, propositions)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

# Module-level trace file handle
_trace_file: Any = None
_trace_path: Path | None = None


def setup_logging(
    level: str = "INFO",
    run_dir: Path | None = None,
) -> None:
    """Configure loguru sinks for console and optional file outputs.

    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR)
        run_dir: If provided, creates run.log and trace.jsonl in this directory
    """
    global _trace_file, _trace_path

    # Remove default handler
    logger.remove()

    # Compact format for human-readable logs
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan> | "
        "<level>{message}</level>"
    )

    # Console sink (stderr, colored)
    logger.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=True,
    )

    # File sinks (if run_dir provided)
    if run_dir:
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        # run.log - human-readable, same format without colors
        log_path = run_dir / "run.log"
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name} | "
            "{message}"
        )
        logger.add(
            log_path,
            format=file_format,
            level=level,
            colorize=False,
        )

        # trace.jsonl - detailed content
        _trace_path = run_dir / "trace.jsonl"
        _trace_file = open(_trace_path, "a", encoding="utf-8")


def close_logging() -> None:
    """Close trace file if open."""
    global _trace_file, _trace_path
    if _trace_file:
        _trace_file.close()
        _trace_file = None
        _trace_path = None


def trace(event: str, **payload: Any) -> None:
    """Write a trace event to trace.jsonl.

    Args:
        event: Event type (e.g., "llm_request", "propositions_extracted")
        **payload: Event-specific data
    """
    if _trace_file is None:
        return

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    _trace_file.write(json.dumps(record, default=str) + "\n")
    _trace_file.flush()


def get_log_level(verbose: bool = False, debug: bool = False, quiet: bool = False) -> str:
    """Determine log level from CLI flags.

    Precedence: debug > verbose > default > quiet
    """
    if debug:
        return "TRACE"
    if verbose:
        return "DEBUG"
    if quiet:
        return "WARNING"
    return "INFO"
