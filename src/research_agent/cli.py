from __future__ import annotations

import argparse
from pathlib import Path

from research_agent.config import load_config
from research_agent.db.schema import apply_migrations
from research_agent.runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a research query")
    run_parser.add_argument("question", help="User question to research")
    run_parser.add_argument("--config", required=True, help="Path to YAML config")

    db_parser = subparsers.add_parser("db-init", help="Initialize the SQLite database")
    db_parser.add_argument("--config", required=True, help="Path to YAML config")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(Path(args.config))

    if args.command == "db-init":
        results = apply_migrations(Path(config.storage.sqlite_path))
        applied = [r for r in results if r.applied]
        print(f"Applied {len(applied)} migrations.")
        return

    if args.command == "run":
        output = run(args.question, config)
        print(f"Run complete: {output.run_id}")
        print(f"Report: {output.report_path}")
        return


if __name__ == "__main__":
    main()
