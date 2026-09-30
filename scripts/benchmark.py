"""Score triage clusters against a small, hand-labeled JUnit fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from triage_accelerator.core import cluster_failures, parse_junit


ROOT = Path(__file__).resolve().parents[1]


def pairwise_scores(
    expected: dict[str, str], predicted: dict[str, str]
) -> tuple[float, float, float]:
    true_positive, false_positive, false_negative = pairwise_confusion(expected, predicted)
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else float(false_negative == 0)
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 1.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def pairwise_confusion(
    expected: dict[str, str], predicted: dict[str, str]
) -> tuple[int, int, int]:
    if set(expected) != set(predicted):
        raise ValueError("gold labels and parsed JUnit cases must contain the same test IDs")

    test_ids = sorted(expected)
    true_positive = false_positive = false_negative = 0
    for index, first in enumerate(test_ids):
        for second in test_ids[index + 1 :]:
            same_expected = expected[first] == expected[second]
            same_predicted = predicted[first] == predicted[second]
            if same_expected and same_predicted:
                true_positive += 1
            elif same_predicted:
                false_positive += 1
            elif same_expected:
                false_negative += 1
    return true_positive, false_positive, false_negative


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, default=ROOT / "examples" / "sample-junit.xml")
    parser.add_argument("--labels", type=Path, default=ROOT / "examples" / "sample-labels.json")
    parser.add_argument("--manual-seconds", type=float)
    parser.add_argument("--assisted-seconds", type=float)
    args = parser.parse_args()
    if (args.manual_seconds is None) != (args.assisted_seconds is None):
        parser.error("provide both --manual-seconds and --assisted-seconds")

    try:
        expected = json.loads(args.labels.read_text(encoding="utf-8"))
        started = perf_counter()
        failures = parse_junit(args.junit)
        clusters = cluster_failures(failures)
        elapsed = perf_counter() - started
        predicted = {
            f"{failure.classname}::{failure.test_name}": str(cluster_index)
            for cluster_index, cluster in enumerate(clusters)
            for failure in cluster.failures
        }
        precision, recall, f1 = pairwise_scores(expected, predicted)
        _, false_merges, missed_merges = pairwise_confusion(expected, predicted)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print("| Measure | Result |")
    print("|---|---:|")
    print(f"| Failure cases | {len(failures)} |")
    print(f"| Hand-labeled groups | {len(set(expected.values()))} |")
    print(f"| Tool clusters | {len(clusters)} |")
    print(f"| Pairwise precision / recall / F1 | {precision:.2f} / {recall:.2f} / {f1:.2f} |")
    print(f"| False-merge / missed-merge pairs | {false_merges} / {missed_merges} |")
    print(f"| Accelerator analysis time | {elapsed * 1000:.2f} ms |")
    if args.manual_seconds is None:
        print("| Manual triage / assisted review | Not measured |")
        print("| Review time saved | Not measured |")
    else:
        saved = args.manual_seconds - args.assisted_seconds
        print(f"| Manual triage time | {args.manual_seconds:.2f} s |")
        print(f"| Assisted review time | {args.assisted_seconds:.2f} s |")
        print(f"| Review time saved | {saved:.2f} s |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())