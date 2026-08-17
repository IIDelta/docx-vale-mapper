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


def enrich_finding(finding: dict[str, Any], record) -> dict[str, Any]:
    result = serialize_finding(finding)
    if record is not None:
        if result.get("ParagraphIndex") is None:
            result["ParagraphIndex"] = record.index
        if result.get("Line") is None:
            result["Line"] = record.line
        result["Context"] = {
            "content_zone": record.content_zone,
            "section_context": record.section_context,
            "style_name": record.style_name,
            "heading_level": record.heading_level,
            "is_in_table": record.is_in_table,
            "list_marker": record.list_marker,
            "has_protected_field": record.has_protected_field,
            "paragraph_text": record.text,
        }
    return result


def write_audit_findings_report(
    output_path: Path,
    source_path: Path,
    audit_profile: str,
    audit_mode: str,
    findings: list[dict[str, Any]],
    suppressed_findings: Counter,
    paragraph_records=(),
) -> Path:
    """Write all final findings for report-only and comment-enabled audits."""
    report_path = output_path.with_suffix(".audit_findings.json")
    record_by_line = {record.line: record for record in paragraph_records}
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
        "findings": [enrich_finding(item, record_by_line.get(item.get("Line"))) for item in findings],
    }
    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    return report_path
