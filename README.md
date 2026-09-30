# AI Test Triage Accelerator

[Public source repository](https://github.com/Akashpatil9657/ai-test-triage-accelerator)

## Problem statement

Release engineers and QA analysts often receive long pytest/JUnit failure reports. One regression can produce repeated failures, while urgent issues are buried in noisy stack traces. Before this tool, reviewers manually removed changing values, counted duplicates, and guessed ownership from a diff, delaying triage and making handoffs inconsistent.

The accelerator parses JUnit XML and an optional unified Git diff, groups normalized failures, and writes a prioritized Markdown brief. Its default path is deterministic and offline. An optional local Ollama model adds a tentative root-cause hypothesis; the model cannot set priorities or change the deterministic clusters.

## Run in under 10 minutes

Requires Python 3.10+. The default workflow has no model or network requirement.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m triage_accelerator.cli examples/sample-junit.xml --diff examples/sample.diff --output sample-output.md
Get-Content sample-output.md
python -m scripts.benchmark
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

### Optional local AI explanation

Install Ollama, pull a local model, and keep its localhost service running:

```text
ollama pull llama3.2:3b
python -m triage_accelerator.cli examples/sample-junit.xml --diff examples/sample.diff --explain
```

The feature uses only Python's standard library and sends the prompt only to a localhost Ollama endpoint. It redacts common email, account ID, payment-card, and credential patterns first. Redaction is heuristic and cannot guarantee removal of every sensitive value. The CLI allows 120 seconds per response for cold or slower local models; adjust this with `--ollama-timeout`. If Ollama is unavailable or returns invalid output, the CLI warns and still writes the deterministic report.

## Sample output

The synthetic JUnit sample has four failing cases. Two share the normalized HTTP 500 assertion and explicit changed-file paths, so they form one P1 cluster. The other two failures form separate clusters.

```text
**4 failing tests** grouped into **3 actionable clusters**.

### 1. P1 - assertionerror: expected <n>, got <n>
- **Tests:** 2 (`test_card_declined`, `test_card_declined_retry`)
- **Likely changed ownership:** `src/payments.py`, `tests/test_payments.py`
```

The full report is written to `sample-output.md` by the command above. The hand labels for the fixture are in `examples/sample-labels.json`.

## Evaluation

The bundled synthetic example has four cases and three hand-labeled groups. Running `python -m scripts.benchmark` compares the pairwise grouping decisions against those labels:

| Measure | Bundled fixture result |
|---|---:|
| Failure cases | 4 |
| Hand-labeled groups | 3 |
| Tool clusters | 3 |
| Pairwise precision / recall / F1 | 1.00 / 1.00 / 1.00 |
| False-merge / missed-merge pairs | 0 / 0 |
| Tool analysis time | 1.05 ms (one Python 3.12.10 venv run) |

These scores describe one small synthetic fixture, not production accuracy. The processing time is tool computation only, not a triage-time comparison. The benchmark supports `--manual-seconds` plus `--assisted-seconds` to report an actual timed comparison. Those human timings have not yet been collected, so no time saving is claimed. For a credible evaluation, replay at least 30 sanitized historical reports, agree on labels before running the tool, and compare time, pairwise grouping scores, false merges, missed merges, and ownership hits.

## Limits, risks, and bank readiness

- Signature normalization is heuristic; similar messages can merge unrelated defects, and formatting changes can split one defect.
- Ownership requires the changed relative path to appear in failure details. This avoids filename-only coincidences, but reports without relevant trace paths will have no ownership match.
- P0/P1/P2 are simple triage hints, not business or operational risk scores.
- Redaction only covers common patterns. Review and redact reports before use; stack traces can include identifiers or regulated data the tool does not recognize.
- A local model can be wrong, follow malicious text inside reports despite the untrusted-data prompt, or invent explanations. Its output is marked unverified and must not replace reproducing the failure and reviewing the code.
- The CLI does not send prompts to remote endpoints; it rejects non-local Ollama URLs. Production use still needs approved redaction, audit and retention controls, access controls, a versioned evaluation set, human approval, and model-risk review.
