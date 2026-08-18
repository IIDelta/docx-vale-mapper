"""
Purpose:
    Write audit summary artifacts.

Inputs:
    Findings, suppression metrics, comment metrics, and paragraph metadata.

Outputs:
    audit_summary.json.

Must not:
    Open Word.
    Insert comments.
    Modify source or output DOCX files.
"""

import json
from collections import Counter
from pathlib import Path

from validators.abbreviationvalidator import (
    ParagraphRecord,
)


def write_audit_summary(
    output_path: Path,
    audit_profile: str,
    vale_findings: list[dict],
    structural_findings: list[dict],
    final_findings: list[dict],
    suppressed_findings,
    comment_metrics: dict,
    paragraph_records: list[ParagraphRecord],
) -> None:
    """
    Write a local audit summary sidecar for review and diagnostics.
    """

    summary_path = output_path.with_suffix(
        ".audit_summary.json"
    )

    content_zone_counts = Counter(
        record.content_zone
        for record in paragraph_records
    )

    summary = {
        "audit_profile": audit_profile,
        "vale_finding_count": len(vale_findings),
        "structural_finding_count": len(
            structural_findings
        ),
        "final_finding_count": len(final_findings),
        "candidate_comment_count": comment_metrics[
            "candidate_comment_count"
        ],
        "inserted_comment_count": comment_metrics[
            "inserted_comment_count"
        ],
        "skipped_comment_count": sum(
            comment_metrics[
                "skipped_comment_reasons"
            ].values()
        ),
        "skipped_comment_reasons": dict(
            sorted(
                comment_metrics[
                    "skipped_comment_reasons"
                ].items()
            )
        ),
        "final_rule_counts": dict(
            sorted(
                Counter(
                    finding.get("Check", "")
                    for finding in final_findings
                ).items()
            )
        ),
        "suppressed_finding_count": sum(
            suppressed_findings.values()
        ),
        "suppressed_rule_counts": dict(
            sorted(suppressed_findings.items())
        ),
        "content_zone_counts": dict(
            sorted(content_zone_counts.items())
        ),
    }

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            summary,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")

    print(
        f"Audit summary written: {summary_path}"
    )


