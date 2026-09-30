"""Core parsing, grouping, ranking, and Markdown rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET


@dataclass
class Failure:
    test_name: str
    classname: str
    message: str
    details: str
    duration: float
    changed_files: list[str] = field(default_factory=list)

    @property
    def signature(self) -> str:
        text = self.message
        if not text or text.lower() == "failure":
            text = self.details
        text = re.sub(r"(?i)\b[A-Z]:\\[^\s]+|/[^\s]+", "<path>", text)
        text = re.sub(r"0x[0-9a-f]+|\b\d+(?:\.\d+)?\b", "<n>", text.lower())
        text = re.sub(r"\s+", " ", text).strip()
        return text[:180]


@dataclass
class Cluster:
    signature: str
    failures: list[Failure]

    @property
    def count(self) -> int:
        return len(self.failures)

    @property
    def priority(self) -> str:
        if self.count >= 3:
            return "P0"
        if any(f.changed_files for f in self.failures):
            return "P1"
        return "P2"

    @property
    def likely_files(self) -> list[str]:
        files: list[str] = []
        for failure in self.failures:
            for path in failure.changed_files:
                if path not in files:
                    files.append(path)
        return files


def parse_junit(path: Path) -> list[Failure]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"could not read valid JUnit XML '{path}': {exc}") from exc
    failures: list[Failure] = []
    for case in root.iter("testcase"):
        node = case.find("failure")
        if node is None:
            node = case.find("error")
        if node is None:
            continue
        try:
            duration = float(case.attrib.get("time", "0") or 0)
        except ValueError as exc:
            raise ValueError(
                f"invalid test duration in JUnit XML '{path}' for "
                f"{case.attrib.get('name', 'unknown')}"
            ) from exc
        failures.append(
            Failure(
                test_name=case.attrib.get("name", "unknown"),
                classname=case.attrib.get("classname", "unknown"),
                message=node.attrib.get("message", "failure"),
                details=(node.text or "").strip(),
                duration=duration,
            )
        )
    return failures


def parse_changed_files(diff: str) -> list[str]:
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path != "/dev/null" and path not in files:
                files.append(path)
    return files


def attach_ownership(failures: list[Failure], changed_files: list[str]) -> None:
    for failure in failures:
        trace = re.sub(r"[\\]+", "/", failure.details).lower()
        failure.changed_files.extend(
            path
            for path in changed_files
            if path.replace("\\", "/").lower().lstrip("./") in trace
        )


def cluster_failures(failures: list[Failure]) -> list[Cluster]:
    grouped: dict[str, list[Failure]] = {}
    for failure in failures:
        grouped.setdefault(failure.signature, []).append(failure)
    clusters = [Cluster(signature, items) for signature, items in grouped.items()]
    return sorted(clusters, key=lambda cluster: (-cluster.count, cluster.signature))


def render_markdown(
    clusters: list[Cluster],
    changed_files: list[str],
    explanations: list[str] | None = None,
) -> str:
    total = sum(cluster.count for cluster in clusters)
    lines = [
        "# AI Test Triage Brief",
        "",
        "> Offline analysis: signatures are normalized from JUnit XML; no source or test data leaves the machine.",
        "",
        f"**{total} failing tests** grouped into **{len(clusters)} actionable clusters**.",
        "",
        "## Changed Files",
        "",
    ]
    if changed_files:
        lines.extend(f"- `{path}`" for path in changed_files)
    else:
        lines.append("- None supplied")
    lines.extend(["", "## Prioritized Clusters", ""])
    if not clusters:
        lines.append("No failures found.")
    for index, cluster in enumerate(clusters, 1):
        examples = ", ".join(f"`{item.test_name}`" for item in cluster.failures[:3])
        owners = ", ".join(f"`{path}`" for path in cluster.likely_files) or "No changed-file match"
        lines.extend(
            [
                f"### {index}. {cluster.priority} - {cluster.signature}",
                "",
                f"- **Tests:** {cluster.count} ({examples})",
                f"- **Likely changed ownership:** {owners}",
                "- **Suggested next check:** inspect the first failing assertion and reproduce this signature locally.",
                "",
            ]
        )
        if explanations and index <= len(explanations):
            lines.append(f"> **Unverified local-model hypothesis:** {explanations[index - 1]}")
            lines.append("")
    lines.extend(
        [
            "## Human Review Required",
            "",
            "- Confirm the normalized failures represent the same root cause.",
            "- Validate ownership and business impact before changing production code.",
            "- Treat stack traces and test names as potentially sensitive data.",
            "",
        ]
    )
    return "\n".join(lines)
