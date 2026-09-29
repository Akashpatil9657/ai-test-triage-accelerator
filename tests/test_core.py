from pathlib import Path

from triage_accelerator.core import (
    attach_ownership,
    cluster_failures,
    parse_changed_files,
    parse_junit,
    render_markdown,
)


ROOT = Path(__file__).parent.parent


def test_junit_failures_are_grouped_and_normalized():
    failures = parse_junit(ROOT / "examples" / "sample-junit.xml")
    changed_files = parse_changed_files((ROOT / "examples" / "sample.diff").read_text())
    attach_ownership(failures, changed_files)
    clusters = cluster_failures(failures)
    assert len(failures) == 4
    assert len(clusters) == 3
    assert clusters[0].count == 2
    assert clusters[0].priority == "P1"
    assert "<n>" in clusters[0].signature


def test_changed_files_attach_to_matching_test_context():
    failures = parse_junit(ROOT / "examples" / "sample-junit.xml")
    changed = parse_changed_files((ROOT / "examples" / "sample.diff").read_text())
    attach_ownership(failures, changed)
    assert changed == ["src/payments.py", "tests/test_payments.py"]
    assert any(f.changed_files for f in failures)


def test_report_only_shows_empty_changed_file_fallback_when_needed():
    assert "- None supplied" in render_markdown([], [])
    assert "- None supplied" not in render_markdown([], ["src/payments.py"])
