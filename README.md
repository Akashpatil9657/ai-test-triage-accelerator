# AI Test Triage Accelerator

## Problem statement

Release engineers and QA analysts often receive a long pytest/JUnit failure report after a change. The same underlying defect can appear in many tests, while the most urgent regression may be buried among noisy, repeated stack traces. Before this tool, a human copied failures into a spreadsheet or chat, manually removed changing values such as IDs and line numbers, counted duplicates, and guessed which changed file was most likely responsible. That work delayed triage and made handoff inconsistent, especially when several teams owned adjacent services.

This accelerator turns a JUnit XML report and an optional unified Git diff into a short, prioritized Markdown brief. It normalizes volatile values, groups likely duplicate failures, highlights changed-file matches, and explicitly leaves final diagnosis to a human. It is intentionally offline-first, so the sample run needs no LLM key. An LLM can be added later as an explanation layer after redaction, but the deterministic evidence stays visible.

## Run in under 10 minutes

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m triage_accelerator.cli examples/sample-junit.xml --diff examples/sample.diff --output sample-output.md
Get-Content sample-output.md
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

## Sample output

The included sample contains four failures. The accelerator produces three clusters. The repeated HTTP 500 assertion is ranked P1 because it affects two tests and matches changed files; P0 is reserved for clusters affecting at least three tests.

```text
4 failing tests grouped into 3 actionable clusters.

1. P1 - assertionerror: expected <n>, got <n>
   Tests: 2 (test_card_declined, test_card_declined_retry)
   Likely changed ownership: src/payments.py, tests/test_payments.py
```

The full generated report is written to `sample-output.md` by the command above.

## Evaluation metrics

On Python 3.12.10, the bundled sample command produced the following functional results. The project test suite passes 3/3 tests. This is a small fixture demonstration, not a timing or accuracy benchmark:

| Measure | Bundled fixture result | How to evaluate |
|---|---:|---|
| Failure cases processed | 4 | Count parsed JUnit failure elements |
| Failure clusters produced | 3 | Compare normalized signatures |
| Repeated cases grouped | 2 | Check the first cluster contains both card-decline tests |
| Project tests passing | 3 / 3 | Run `python -m pytest` |
| External services / API keys | 0 | Run with network access disabled |

No end-to-end timing or defect-detection accuracy is claimed yet. To measure improvement over manual triage, replay at least 30 historical CI reports, have two blinded reviewers label root-cause groups, ownership, and severity, then compare review time, pairwise agreement, missed defects, and false merges against the accelerator output.

## Limits, risks, and bank-readiness changes

- Normalization is heuristic. Two different defects can be merged when their messages look alike, or one defect can split across formatting differences.
- Ownership matching only uses changed-file names and test context; it does not understand architecture or service dependencies.
- Priority is a triage hint, not risk scoring. It ignores customer impact, control criticality, data sensitivity, and deployment exposure.
- XML reports and stack traces may contain credentials, account identifiers, or regulated data. A human must redact and approve what enters the tool.
- A reviewer must reproduce the failure, inspect the complete stack trace, verify the changed code, and decide whether a defect is real.

Before bank use, I would add approved redaction rules, immutable audit logs, role-based access, retention controls, encrypted storage, a versioned evaluation set, confidence scores, and a human approval gate. Any hosted LLM explanation layer would require model-risk review, prompt-injection tests, data-processing approval, and a deterministic fallback.
