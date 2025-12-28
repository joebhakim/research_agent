from __future__ import annotations

import argparse
from pathlib import Path

from research_agent.config import load_config
from research_agent.db.schema import apply_migrations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-agent")
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

    if args.command == "db-init":
        results = apply_migrations(Path(config.storage.sqlite_path))
        applied = [r for r in results if r.applied]
        print(f"Applied {len(applied)} migrations.")
        return

    if args.command == "run":
        from research_agent.runner import run

        output = run(args.question, config, model_override=args.model)
        print(f"Run complete: {output.run_id}")
        print(f"Report: {output.report_path}")
        return

    if args.command == "llm-test":
        from research_agent.llm.router import get_model_client

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
        print(f"Model: {routed.name}")
        print(response)
        return

    if args.command == "eval":
        from research_agent.evals.runner import run_suite

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
        print(f"Eval run complete: {run_dir}")
        return


if __name__ == "__main__":
    main()
