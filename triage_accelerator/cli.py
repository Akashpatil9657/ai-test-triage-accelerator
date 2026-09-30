"""Command-line entry point for the triage accelerator."""

from argparse import ArgumentParser
from pathlib import Path
import sys

from .core import attach_ownership, cluster_failures, parse_changed_files, parse_junit, render_markdown
from .explain import explain_clusters, ollama_generate


def main() -> int:
    parser = ArgumentParser(description="Group and prioritize pytest failures offline.")
    parser.add_argument("junit", type=Path, help="pytest JUnit XML report")
    parser.add_argument("--diff", type=Path, help="optional unified git diff")
    parser.add_argument("--output", type=Path, help="write Markdown brief to this file")
    parser.add_argument("--explain", action="store_true", help="add local Ollama hypotheses")
    parser.add_argument("--ollama-model", default="llama3.2:3b", help="local Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434/api/generate",
        help="localhost Ollama generate endpoint",
    )
    parser.add_argument(
        "--ollama-timeout",
        type=float,
        default=120,
        help="seconds to wait for each local model response",
    )
    args = parser.parse_args()

    try:
        failures = parse_junit(args.junit)
        changed_files = (
            parse_changed_files(args.diff.read_text(encoding="utf-8")) if args.diff else []
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    attach_ownership(failures, changed_files)
    clusters = cluster_failures(failures)
    explanations = None
    if args.explain:
        try:
            explanations = explain_clusters(
                clusters,
                lambda prompt: ollama_generate(
                    prompt,
                    model=args.ollama_model,
                    endpoint=args.ollama_url,
                    timeout=args.ollama_timeout,
                ),
            )
        except Exception as exc:
            print(
                f"Warning: local model explanation unavailable ({type(exc).__name__}); "
                "deterministic report generated.",
                file=sys.stderr,
            )
    report = render_markdown(clusters, changed_files, explanations)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
