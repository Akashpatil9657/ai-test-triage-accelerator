from pathlib import Path

import pytest

from triage_accelerator.core import (
    Failure,
    attach_ownership,
    cluster_failures,
    parse_changed_files,
    parse_junit,
    render_markdown,
)


ROOT = Path(__file__).parent.parent


def test_junit_failures_are_grouped_and_normalized():
    failures = parse_junit(ROOT / "examples" / "sample-junit.xml")
    changed_files = parse_changed_files(
        (ROOT / "examples" / "sample.diff").read_text(encoding="utf-8")
    )
    attach_ownership(failures, changed_files)
    clusters = cluster_failures(failures)
    assert len(failures) == 4
    assert len(clusters) == 3
    assert clusters[0].count == 2
    assert clusters[0].priority == "P1"
    assert "<n>" in clusters[0].signature


def test_changed_files_attach_to_matching_test_context():
    failures = parse_junit(ROOT / "examples" / "sample-junit.xml")
    changed = parse_changed_files(
        (ROOT / "examples" / "sample.diff").read_text(encoding="utf-8")
    )
    attach_ownership(failures, changed)
    assert changed == ["src/payments.py", "tests/test_payments.py"]
    assert [failure.test_name for failure in failures if failure.changed_files] == [
        "test_card_declined",
        "test_card_declined_retry",
    ]


def test_report_only_shows_empty_changed_file_fallback_when_needed():
    assert "- None supplied" in render_markdown([], [])
    assert "- None supplied" not in render_markdown([], ["src/payments.py"])


def test_windows_paths_are_normalized_before_numbers():
    failure = Failure("test", "suite", "Error at C:\\build\\job123\\foo42.py code 500", "", 0)
    assert failure.signature == "error at <path> code <n>"


def test_ownership_requires_changed_path_in_failure_details():
    failure = Failure("test_utils", "tests.TestUtils", "AssertionError", "failed", 0)
    attach_ownership([failure], ["src/utils.py"])
    assert failure.changed_files == []

    failure.details = 'File "C:/repo/src/utils.py", line 12, in helper'
    attach_ownership([failure], ["src/utils.py"])
    assert failure.changed_files == ["src/utils.py"]


def test_parse_junit_supports_testsuites_empty_and_skipped_cases(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuites><testsuite><testcase name="skipped"><skipped /></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert parse_junit(report) == []


@pytest.mark.parametrize("contents", [None, "<testsuite>"])
def test_cli_reports_missing_or_malformed_xml_without_traceback(
    tmp_path, monkeypatch, capsys, contents
):
    from triage_accelerator.cli import main

    report = tmp_path / "report.xml"
    if contents is not None:
        report.write_text(contents, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["triage", str(report)])
    with pytest.raises(SystemExit) as error:
        main()
    captured = capsys.readouterr()
    assert error.value.code == 2
    assert "could not read valid JUnit XML" in captured.err
    assert "Traceback" not in captured.err
