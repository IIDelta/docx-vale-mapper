from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


FINDING_KEYS = (
    "Check",
    "Severity",
    "Message",
    "Match",
    "Line",
    "ParagraphIndex",
    "RangeStart",
    "RangeEnd",
    "Span",
    "Action",
)


def serialize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Return the stable, JSON-safe subset of one audit finding."""
    result: dict[str, Any] = {}
    for key in FINDING_KEYS:
        if key not in finding:
            continue
        value = finding[key]
        try:
            json.dumps(value)
            result[key] = value
        except TypeError:
            result[key] = str(value)
    return result


def write_audit_findings_report(
    output_path: Path,
    source_path: Path,
    audit_profile: str,
    audit_mode: str,
    findings: list[dict[str, Any]],
    suppressed_findings: Counter,
) -> Path:
    """Write all final findings for report-only and comment-enabled audits."""
    report_path = output_path.with_suffix(".audit_findings.json")
    payload = {
        "report_version": "1.0",
        "source_document": str(source_path.resolve()),
        "audit_profile": audit_profile,
        "audit_mode": audit_mode,
        "finding_count": len(findings),
        "rule_counts": dict(
            sorted(Counter(item.get("Check", "") for item in findings).items())
        ),
        "severity_counts": dict(
            sorted(Counter(item.get("Severity", "") for item in findings).items())
        ),
        "suppressed_rule_counts": dict(sorted(suppressed_findings.items())),
        "findings": [serialize_finding(item) for item in findings],
    }
    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    return report_path
