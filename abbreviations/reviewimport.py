from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abbreviations.legacyimport import (
    clean_value,
    normalize_token,
    open_database,
)
from abbreviations.reviewpromote import (
    VALID_STATUSES,
    ensure_review_schema,
    find_candidate_id,
    upsert_registry_entry,
    upsert_review_decision,
)


REQUIRED_COLUMNS = {
    "token",
    "preferred_definition",
    "replacement_token",
    "reviewer_decision",
    "reviewer_notes",
}


@dataclass(frozen=True)
class ReviewImportRow:
    """One validated reviewer decision from the CSV queue."""

    row_number: int
    token: str
    definition: str
    status: str
    replacement_token: str
    notes: str


def load_review_rows(
    input_path: Path,
) -> list[dict[str, str]]:
    """Load rows from a candidate review CSV."""

    with input_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as input_file:
        reader = csv.DictReader(input_file)

        fieldnames = set(reader.fieldnames or [])

        missing_columns = REQUIRED_COLUMNS - fieldnames

        if missing_columns:
            missing_text = ", ".join(
                sorted(missing_columns)
            )

            raise ValueError(
                "Review CSV is missing required column(s): "
                f"{missing_text}"
            )

        return list(reader)


def validate_review_rows(
    rows: list[dict[str, str]],
) -> tuple[list[ReviewImportRow], int]:
    """
    Validate reviewer decisions before writing anything to the database.

    Blank reviewer_decision values are skipped. This allows reviewers to
    leave most candidate rows unchanged.
    """

    validated_rows: list[ReviewImportRow] = []
    skipped_rows = 0
    validation_errors: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        token = clean_value(row.get("token", ""))

        status = clean_value(
            row.get("reviewer_decision", "")
        )

        definition = clean_value(
            row.get("preferred_definition", "")
        )

        replacement_token = clean_value(
            row.get("replacement_token", "")
        )

        notes = clean_value(
            row.get("reviewer_notes", "")
        )

        if not status:
            skipped_rows += 1
            continue

        if not token:
            validation_errors.append(
                f"CSV row {row_number}: token is required."
            )
            continue

        if status not in VALID_STATUSES:
            allowed_statuses = ", ".join(
                sorted(VALID_STATUSES)
            )

            validation_errors.append(
                f"CSV row {row_number}: unsupported "
                f"reviewer_decision '{status}' for token "
                f"'{token}'. Allowed values: {allowed_statuses}."
            )
            continue

        if status == "approved_expand" and not definition:
            validation_errors.append(
                f"CSV row {row_number}: token '{token}' uses "
                "approved_expand but has no preferred_definition."
            )
            continue

        if status == "deprecated" and not replacement_token:
            validation_errors.append(
                f"CSV row {row_number}: token '{token}' uses "
                "deprecated but has no replacement_token."
            )
            continue

        validated_rows.append(
            ReviewImportRow(
                row_number=row_number,
                token=token,
                definition=definition,
                status=status,
                replacement_token=replacement_token,
                notes=notes,
            )
        )

    duplicate_decisions = Counter(
        normalize_token(row.token)
        for row in validated_rows
    )

    for normalized_token, count in duplicate_decisions.items():
        if count > 1:
            validation_errors.append(
                "CSV contains multiple reviewer decisions for "
                f"the same token: '{normalized_token}'."
            )

    if validation_errors:
        joined_errors = "\n".join(validation_errors)

        raise ValueError(
            "Review CSV validation failed:\n"
            f"{joined_errors}"
        )

    return validated_rows, skipped_rows


def apply_review_import(
    database_path: Path,
    review_rows: list[ReviewImportRow],
    reviewer: str,
    decision_set: str,
) -> dict[str, Any]:
    """Apply validated reviewer decisions to the reviewed registry."""

    reviewer_name = clean_value(reviewer)
    decision_set_name = clean_value(decision_set)

    if not reviewer_name:
        raise ValueError("A reviewer value is required.")

    if not decision_set_name:
        raise ValueError("A decision_set value is required.")

    with open_database(database_path) as connection:
        ensure_review_schema(connection)

        status_counts: Counter[str] = Counter()
        applied_tokens: list[str] = []

        for review_row in review_rows:
            source_reference = (
                f"csv_review:{reviewer_name}"
            )

            registry_id = upsert_registry_entry(
                connection=connection,
                token=review_row.token,
                definition=review_row.definition,
                status=review_row.status,
                source_reference=source_reference,
                replacement_token=review_row.replacement_token,
                notes=review_row.notes,
            )

            candidate_id = find_candidate_id(
                connection=connection,
                normalized_token=normalize_token(
                    review_row.token
                ),
            )

            upsert_review_decision(
                connection=connection,
                registry_id=registry_id,
                candidate_id=candidate_id,
                decision_set=decision_set_name,
                token=review_row.token,
                status=review_row.status,
                source_reference=source_reference,
                notes=review_row.notes,
            )

            status_counts[review_row.status] += 1
            applied_tokens.append(review_row.token)

        registry_rows = connection.execute(
            """
            SELECT status, COUNT(*)
            FROM registry_entries
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()

    return {
        "reviewer": reviewer_name,
        "decision_set": decision_set_name,
        "review_rows_applied": len(review_rows),
        "applied_status_counts": dict(
            sorted(status_counts.items())
        ),
        "applied_tokens": sorted(
            applied_tokens,
            key=str.casefold,
        ),
        "registry_status_counts": {
            row[0]: row[1]
            for row in registry_rows
        },
    }


def write_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Write an import audit report as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")


def parse_arguments() -> argparse.Namespace:
    """Parse CSV review import options."""

    parser = argparse.ArgumentParser(
        description=(
            "Import validated reviewer decisions from a candidate "
            "review CSV into the reviewed abbreviation registry."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports") / "candidatereview.csv",
        help=(
            "Candidate review CSV path. "
            "Default: reports/candidatereview.csv"
        ),
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data") / "abbreviations.sqlite",
        help=(
            "SQLite database path. "
            "Default: data/abbreviations.sqlite"
        ),
    )

    parser.add_argument(
        "--reviewer",
        required=True,
        help=(
            "Reviewer identifier recorded in source_reference."
        ),
    )

    parser.add_argument(
        "--decision-set",
        default="csv_candidate_review",
        help=(
            "Traceable name for this decision batch. "
            "Default: csv_candidate_review"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports") / "reviewimportreport.json",
        help=(
            "JSON audit report path. "
            "Default: reports/reviewimportreport.json"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Run reviewer-decision import."""

    arguments = parse_arguments()

    if not arguments.input.is_file():
        print(
            "REVIEW IMPORT FAILED: "
            f"CSV file not found: {arguments.input}"
        )
        return 2

    try:
        raw_rows = load_review_rows(
            arguments.input
        )

        review_rows, skipped_rows = validate_review_rows(
            raw_rows
        )

        report = apply_review_import(
            database_path=arguments.database,
            review_rows=review_rows,
            reviewer=arguments.reviewer,
            decision_set=arguments.decision_set,
        )

        report["review_rows_skipped"] = skipped_rows
        report["input_path"] = str(
            arguments.input.resolve()
        )

        write_report(
            report=report,
            output_path=arguments.report,
        )

    except (
        OSError,
        ValueError,
        csv.Error,
        json.JSONDecodeError,
    ) as error:
        print(f"REVIEW IMPORT FAILED: {error}")
        return 2

    print(
        f"Review rows applied: "
        f"{report['review_rows_applied']}"
    )

    print(
        f"Review rows skipped: "
        f"{report['review_rows_skipped']}"
    )

    print(
        f"Applied status counts: "
        f"{report['applied_status_counts']}"
    )

    print(
        f"Report: {arguments.report.resolve()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
