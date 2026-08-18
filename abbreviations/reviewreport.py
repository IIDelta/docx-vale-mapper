"""
Purpose:
    Manage abbreviation discovery, registry data, candidate review,
    and policy promotion.

Inputs:
    Candidate terms, registry data, review decisions, and policy files.

Outputs:
    Review reports, registry records, and effective abbreviation policy.

Must not:
    Insert Word comments.
    Modify Word documents directly.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


BUCKET_PRIORITY = {
    "deprecated": 1,
    "ambiguous": 2,
    "likely_unknown": 3,
    "possible_unknown": 4,
    "reviewed_candidate": 5,
    "known_expand": 6,
    "known_list_only": 7,
    "protected": 8,
    "ignored": 9,
}


CSV_HEADERS = [
    "priority",
    "review_bucket",
    "confidence",
    "token",
    "count",
    "first_paragraph_index",
    "registry_status",
    "preferred_definition",
    "replacement_token",
    "enforcement_action",
    "source_reference",
    "notes",
    "contexts",
    "reviewer_decision",
    "reviewer_notes",
]


def load_candidate_report(
    report_path: Path,
) -> dict[str, Any]:
    """Load a candidate discovery JSON report."""

    with report_path.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def candidate_sort_key(
    candidate: dict[str, Any],
) -> tuple[int, str]:
    """Sort high-priority review items before known/protected terms."""

    bucket = candidate.get("review_bucket", "")

    return (
        BUCKET_PRIORITY.get(bucket, 99),
        candidate.get("token", "").casefold(),
    )


def flatten_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Convert one JSON candidate into one CSV-ready review row."""

    resolution = candidate.get("resolution") or {}

    contexts = candidate.get("contexts") or []

    return {
        "priority": BUCKET_PRIORITY.get(
            candidate.get("review_bucket", ""),
            99,
        ),
        "review_bucket": candidate.get("review_bucket", ""),
        "confidence": candidate.get("confidence", ""),
        "token": candidate.get("token", ""),
        "count": candidate.get("count", 0),
        "first_paragraph_index": candidate.get(
            "first_paragraph_index",
            "",
        ),
        "registry_status": resolution.get("status", "unknown"),
        "preferred_definition": resolution.get(
            "preferred_definition",
            "",
        ),
        "replacement_token": resolution.get(
            "replacement_token",
            "",
        ),
        "enforcement_action": resolution.get(
            "enforcement_action",
            "candidate_review",
        ),
        "source_reference": resolution.get(
            "source_reference",
            "",
        ),
        "notes": resolution.get("notes", ""),
        "contexts": " | ".join(contexts),
        "reviewer_decision": "",
        "reviewer_notes": "",
    }


def build_review_rows(
    candidate_report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create priority-sorted review rows from discovery output."""

    candidates = candidate_report.get("candidates", [])

    sorted_candidates = sorted(
        candidates,
        key=candidate_sort_key,
    )

    return [
        flatten_candidate(candidate)
        for candidate in sorted_candidates
    ]


def write_csv_report(
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write a spreadsheet-friendly candidate review queue."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=CSV_HEADERS,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)


def write_markdown_report(
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write a concise Markdown review summary."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    bucket_counts = Counter(
        row["review_bucket"]
        for row in rows
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        output_file.write("# Abbreviation Candidate Review Report\n\n")

        output_file.write(
            f"Total candidates: **{len(rows)}**\n\n"
        )

        output_file.write("## Summary by Review Bucket\n\n")
        output_file.write("| Review bucket | Count |\n")
        output_file.write("|---|---:|\n")

        for bucket, count in sorted(
            bucket_counts.items(),
            key=lambda item: (
                BUCKET_PRIORITY.get(item[0], 99),
                item[0],
            ),
        ):
            output_file.write(
                f"| `{bucket}` | {count} |\n"
            )

        output_file.write("\n## Candidate Review Queue\n\n")

        output_file.write(
            "| Priority | Bucket | Token | Count | "
            "Registry status | Recommended action |\n"
        )
        output_file.write(
            "|---:|---|---|---:|---|---|\n"
        )

        for row in rows:
            output_file.write(
                f"| {row['priority']} "
                f"| `{row['review_bucket']}` "
                f"| `{row['token']}` "
                f"| {row['count']} "
                f"| `{row['registry_status']}` "
                f"| `{row['enforcement_action']}` |\n"
            )

        output_file.write("\n## Detailed Context\n\n")

        for row in rows:
            output_file.write(
                f"### {row['token']} "
                f"— {row['review_bucket']}\n\n"
            )

            output_file.write(
                f"**Occurrences:** {row['count']}  \n"
            )

            output_file.write(
                f"**First paragraph:** "
                f"{row['first_paragraph_index']}  \n"
            )

            output_file.write(
                f"**Registry status:** "
                f"{row['registry_status']}  \n"
            )

            output_file.write(
                f"**Recommended action:** "
                f"{row['enforcement_action']}  \n"
            )

            if row["preferred_definition"]:
                output_file.write(
                    f"**Preferred definition:** "
                    f"{row['preferred_definition']}  \n"
                )

            if row["replacement_token"]:
                output_file.write(
                    f"**Replacement token:** "
                    f"{row['replacement_token']}  \n"
                )

            if row["source_reference"]:
                output_file.write(
                    f"**Source reference:** "
                    f"{row['source_reference']}  \n"
                )

            if row["notes"]:
                output_file.write(
                    f"**Notes:** {row['notes']}  \n"
                )

            if row["contexts"]:
                output_file.write(
                    f"**Contexts:** {row['contexts']}\n"
                )

            output_file.write("\n")


def parse_arguments() -> argparse.Namespace:
    """Parse review report export options."""

    parser = argparse.ArgumentParser(
        description=(
            "Export abbreviation candidate discovery JSON into "
            "CSV and Markdown review reports."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports") / "candidatefinderreport.json",
        help=(
            "Candidate discovery JSON input. "
            "Default: reports/candidatefinderreport.json"
        ),
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("reports") / "candidatereview.csv",
        help=(
            "CSV review queue output. "
            "Default: reports/candidatereview.csv"
        ),
    )

    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("reports") / "candidatereview.md",
        help=(
            "Markdown summary output. "
            "Default: reports/candidatereview.md"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Export candidate review reports."""

    arguments = parse_arguments()

    if not arguments.input.is_file():
        print(
            "REVIEW REPORT FAILED: "
            f"Candidate report not found: {arguments.input}"
        )
        return 2

    try:
        candidate_report = load_candidate_report(
            arguments.input,
        )

        rows = build_review_rows(candidate_report)

        write_csv_report(
            rows=rows,
            output_path=arguments.csv,
        )

        write_markdown_report(
            rows=rows,
            output_path=arguments.markdown,
        )

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"REVIEW REPORT FAILED: {error}")
        return 2

    print(
        f"Review rows exported: {len(rows)}"
    )

    print(
        f"CSV: {arguments.csv.resolve()}"
    )

    print(
        f"Markdown: {arguments.markdown.resolve()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
