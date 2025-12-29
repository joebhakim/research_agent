from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from research_agent.config import load_config
from research_agent.db.schema import apply_migrations
from research_agent.logging import close_logging, get_log_level, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show debug logs")
    parser.add_argument("--debug", action="store_true", help="Show trace-level logs")
    parser.add_argument("--quiet", "-q", action="store_true", help="Show only warnings and errors")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a research query")
    run_parser.add_argument("question", help="User question to research")
    run_parser.add_argument("--config", required=True, help="Path to YAML config")
    run_parser.add_argument(
        "--model",
        choices=["local", "openrouter"],
        default=None,
        help="Override model routing selection",
    )
    run_parser.add_argument(
        "--sources",
        default=None,
        help="Path to a newline-delimited list of local files (offline mode).",
    )
    run_parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory of local HTML/PDF/TXT files to ingest (offline mode).",
    )

    db_parser = subparsers.add_parser("db-init", help="Initialize the SQLite database")
    db_parser.add_argument("--config", required=True, help="Path to YAML config")

    llm_parser = subparsers.add_parser("llm-test", help="Test LLM connectivity")
    llm_parser.add_argument("--config", required=True, help="Path to YAML config")
    llm_parser.add_argument(
        "--model",
        choices=["local", "openrouter"],
        default=None,
        help="Select which model to test",
    )
    llm_parser.add_argument(
        "--prompt",
        default="Respond with the word OK.",
        help="Prompt to send to the model",
    )

    eval_parser = subparsers.add_parser("eval", help="Run an evaluation suite")
    eval_parser.add_argument("--config", required=True, help="Path to YAML config")
    eval_parser.add_argument("--suite", required=True, help="Path to suite YAML")
    eval_parser.add_argument("--trials", type=int, default=None, help="Override trial count")
    eval_parser.add_argument(
        "--model",
        choices=["local", "openrouter"],
        default=None,
        help="Override model routing selection",
    )
    eval_parser.add_argument("--temperature", type=float, default=None, help="Override temperature")
    eval_parser.add_argument("--output-dir", default=None, help="Output directory for eval runs")
    eval_parser.add_argument(
        "--enable-llm-judge",
        action="store_true",
        help="Enable optional LLM-as-judge validators",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(Path(args.config))

    # Determine log level from CLI flags
    log_level = get_log_level(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
    )

    if args.command == "db-init":
        setup_logging(level=log_level)
        results = apply_migrations(Path(config.storage.sqlite_path))
        applied = [r for r in results if r.applied]
        logger.info(f"Applied {len(applied)} migrations.")
        return

    if args.command == "run":
        from research_agent.runner import run

        # Console-only logging initially; runner sets up file logging after creating run_dir
        setup_logging(level=log_level)

        sources_path = Path(args.sources) if args.sources else None
        input_dir = Path(args.input_dir) if args.input_dir else None
        try:
            output = run(
                args.question,
                config,
                model_override=args.model,
                sources_path=sources_path,
                input_dir=input_dir,
                log_level=log_level,
            )
            logger.success(f"Run complete: {output.run_id}")
            logger.info(f"Report: {output.report_path}")
        finally:
            close_logging()
        return

    if args.command == "llm-test":
        from research_agent.llm.router import get_model_client

        setup_logging(level=log_level)
        routed = get_model_client(
            config,
            thinking_extent=config.agent.thinking.extent,
            override=args.model,
        )
        response = routed.client.chat(
            [
                {
                    "role": "user",
                    "content": args.prompt,
                }
            ],
            max_tokens=32,
        )
        logger.info(f"Model: {routed.name}")
        logger.info(response)
        return

    if args.command == "eval":
        from research_agent.evals.runner import run_suite

        setup_logging(level=log_level)
        output_dir = Path(args.output_dir) if args.output_dir else None
        run_dir = run_suite(
            Path(args.suite),
            config,
            trials_override=args.trials,
            model_override=args.model,
            output_dir=output_dir,
            temperature_override=args.temperature,
            enable_llm_judge=args.enable_llm_judge,
        )
        logger.success(f"Eval run complete: {run_dir}")
        return


if __name__ == "__main__":
    main()
