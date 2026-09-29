"""Command-line entry point for the triage accelerator."""

from argparse import ArgumentParser
from pathlib import Path

from .core import attach_ownership, cluster_failures, parse_changed_files, parse_junit, render_markdown


def main() -> int:
    parser = ArgumentParser(description="Group and prioritize pytest failures offline.")
    parser.add_argument("junit", type=Path, help="pytest JUnit XML report")
    parser.add_argument("--diff", type=Path, help="optional unified git diff")
    parser.add_argument("--output", type=Path, help="write Markdown brief to this file")
    args = parser.parse_args()

    failures = parse_junit(args.junit)
    changed_files = parse_changed_files(args.diff.read_text(encoding="utf-8")) if args.diff else []
    attach_ownership(failures, changed_files)
    report = render_markdown(cluster_failures(failures), changed_files)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
