from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_SUFFIXES = (
    ".audit_findings.json",
    ".audit_summary.json",
    ".audit_manifest.json",
)


def report_path(output_base: Path, suffix: str) -> Path:
    """Return one report sidecar path from an audit DOCX-style base path."""
    return output_base.with_suffix(suffix)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path.name}.")
    return payload


def validate_reports_only_artifacts(
    source_path: Path,
    output_base: Path,
) -> list[str]:
    """Return acceptance failures for one completed reports-only audit."""
    failures: list[str] = []
    if not source_path.is_file():
        return [f"Source fixture was not found: {source_path}"]
    if output_base.exists():
        failures.append(
            "Reports-only mode created an audited DOCX: "
            f"{output_base}"
        )

    paths = {
        suffix: report_path(output_base, suffix)
        for suffix in REQUIRED_SUFFIXES
    }
    for suffix, path in paths.items():
        if not path.is_file():
            failures.append(f"Missing reports-only artifact {suffix}: {path}")
    if failures:
        return failures

    findings = load_json(paths[".audit_findings.json"])
    summary = load_json(paths[".audit_summary.json"])
    manifest = load_json(paths[".audit_manifest.json"])

    if findings.get("audit_mode") != "reports_only":
        failures.append("Findings report audit_mode is not reports_only.")
    if manifest.get("audit_mode") != "reports_only":
        failures.append("Manifest audit_mode is not reports_only.")
    if manifest.get("output_document_created") is not False:
        failures.append("Manifest must set output_document_created to false.")
    if summary.get("inserted_comment_count") != 0:
        failures.append("Reports-only mode inserted Word comments.")

    finding_count = findings.get("finding_count")
    if not isinstance(finding_count, int):
        failures.append("Findings report has no integer finding_count.")
        return failures
    if len(findings.get("findings", [])) != finding_count:
        failures.append("Findings array count does not match finding_count.")
    if summary.get("final_finding_count") != finding_count:
        failures.append("Summary finding count does not match findings report.")

    skipped = summary.get("skipped_comment_reasons", {})
    if skipped.get("comment_insertion_disabled") != finding_count:
        failures.append(
            "Reports-only summary must record every finding as "
            "comment_insertion_disabled."
        )
    return failures
