from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from abbreviations.legacyimport import (
    clean_value,
    initialize_database,
    normalize_token,
    open_database,
)


REVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS registry_entries (
    registry_id INTEGER PRIMARY KEY,
    token TEXT NOT NULL,
    normalized_token TEXT NOT NULL UNIQUE,
    preferred_definition TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    replacement_token TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id INTEGER PRIMARY KEY,
    decision_key TEXT NOT NULL UNIQUE,
    registry_id INTEGER NOT NULL,
    candidate_id INTEGER,
    decision_set TEXT NOT NULL,
    token TEXT NOT NULL,
    normalized_token TEXT NOT NULL,
    status TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    reviewed_at_utc TEXT NOT NULL,
    FOREIGN KEY (registry_id)
        REFERENCES registry_entries(registry_id)
        ON DELETE CASCADE,
    FOREIGN KEY (candidate_id)
        REFERENCES candidate_terms(candidate_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_registry_entries_status
    ON registry_entries(status);

CREATE INDEX IF NOT EXISTS idx_review_decisions_set
    ON review_decisions(decision_set);
"""


VALID_STATUSES = {
    "approved_expand",
    "approved_no_expand",
    "approved_list_only",
    "reviewed_candidate",
    "deprecated",
    "ambiguous",
    "ignored",
}


def ensure_review_schema(
    connection: sqlite3.Connection,
) -> None:
    """Create B2 registry and review tables."""

    connection.executescript(REVIEW_SCHEMA)


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load a JSON configuration file."""

    with file_path.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def find_candidate_id(
    connection: sqlite3.Connection,
    normalized_token: str,
) -> int | None:
    """Return the earliest legacy candidate ID for a token, if present."""

    row = connection.execute(
        """
        SELECT candidate_id
        FROM candidate_terms
        WHERE normalized_token = ?
        ORDER BY candidate_id
        LIMIT 1
        """,
        (normalized_token,),
    ).fetchone()

    return int(row[0]) if row else None


def upsert_registry_entry(
    connection: sqlite3.Connection,
    token: str,
    definition: str,
    status: str,
    source_reference: str,
    replacement_token: str,
    notes: str,
) -> int:
    """Create or update one canonical reviewed registry entry."""

    timestamp = datetime.now(timezone.utc).isoformat()
    normalized_token = normalize_token(token)

    connection.execute(
        """
        INSERT INTO registry_entries (
            token,
            normalized_token,
            preferred_definition,
            status,
            source_reference,
            replacement_token,
            notes,
            created_at_utc,
            updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(normalized_token)
        DO UPDATE SET
            token = excluded.token,
            preferred_definition = excluded.preferred_definition,
            status = excluded.status,
            source_reference = excluded.source_reference,
            replacement_token = excluded.replacement_token,
            notes = excluded.notes,
            updated_at_utc = excluded.updated_at_utc
        """,
        (
            token,
            normalized_token,
            definition,
            status,
            source_reference,
            replacement_token,
            notes,
            timestamp,
            timestamp,
        ),
    )

    row = connection.execute(
        """
        SELECT registry_id
        FROM registry_entries
        WHERE normalized_token = ?
        """,
        (normalized_token,),
    ).fetchone()

    return int(row[0])


def upsert_review_decision(
    connection: sqlite3.Connection,
    registry_id: int,
    candidate_id: int | None,
    decision_set: str,
    token: str,
    status: str,
    source_reference: str,
    notes: str,
) -> None:
    """Create or update a traceable review-decision record."""

    normalized_token = normalize_token(token)
    decision_key = f"{decision_set}:{normalized_token}"
    timestamp = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        INSERT INTO review_decisions (
            decision_key,
            registry_id,
            candidate_id,
            decision_set,
            token,
            normalized_token,
            status,
            source_reference,
            notes,
            reviewed_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(decision_key)
        DO UPDATE SET
            registry_id = excluded.registry_id,
            candidate_id = excluded.candidate_id,
            status = excluded.status,
            source_reference = excluded.source_reference,
            notes = excluded.notes,
            reviewed_at_utc = excluded.reviewed_at_utc
        """,
        (
            decision_key,
            registry_id,
            candidate_id,
            decision_set,
            token,
            normalized_token,
            status,
            source_reference,
            notes,
            timestamp,
        ),
    )


def apply_protected_terms(
    connection: sqlite3.Connection,
    policy: dict[str, Any],
    decision_set: str,
) -> int:
    """
    Add policy-protected terms to the reviewed registry.

    These records are not imported from the legacy source. They are
    created as approved_no_expand entries based on the local policy.
    """

    protected_count = 0

    for token in policy.get("never_expand", []):
        cleaned_token = clean_value(token)

        if not cleaned_token:
            continue

        registry_id = upsert_registry_entry(
            connection=connection,
            token=cleaned_token,
            definition="",
            status="approved_no_expand",
            source_reference="policy_protected_terms",
            replacement_token="",
            notes=(
                "Protected term. Do not require first-use expansion."
            ),
        )

        upsert_review_decision(
            connection=connection,
            registry_id=registry_id,
            candidate_id=find_candidate_id(
                connection,
                normalize_token(cleaned_token),
            ),
            decision_set=decision_set,
            token=cleaned_token,
            status="approved_no_expand",
            source_reference="policy_protected_terms",
            notes=(
                "Protected term synchronized from local policy."
            ),
        )

        protected_count += 1

    return protected_count


def apply_review_seed(
    database_path: Path,
    seed_path: Path,
    policy_path: Path,
) -> dict[str, Any]:
    """Apply a reviewed seed file and protected-term policy."""

    if not seed_path.is_file():
        raise FileNotFoundError(
            f"Review seed file was not found: {seed_path}"
        )

    if not policy_path.is_file():
        raise FileNotFoundError(
            f"Policy file was not found: {policy_path}"
        )

    initialize_database(database_path)

    seed = load_json_file(seed_path)
    policy = load_json_file(policy_path)

    decision_set = clean_value(
        str(seed.get("decision_set", "default_review"))
    )

    decisions = seed.get("decisions", [])

    if not isinstance(decisions, list):
        raise ValueError(
            "The review seed requires a 'decisions' array."
        )

    with open_database(database_path) as connection:
        ensure_review_schema(connection)

        applied_statuses: Counter[str] = Counter()
        applied_tokens: list[str] = []

        for decision in decisions:
            token = clean_value(str(decision.get("token", "")))
            definition = clean_value(
                str(decision.get("definition", ""))
            )
            status = clean_value(
                str(decision.get("status", ""))
            )
            source_reference = clean_value(
                str(decision.get("source_reference", ""))
            )
            replacement_token = clean_value(
                str(decision.get("replacement_token", ""))
            )
            notes = clean_value(
                str(decision.get("notes", ""))
            )

            if not token:
                raise ValueError(
                    "Every review decision requires a token."
                )

            if status not in VALID_STATUSES:
                raise ValueError(
                    f"Unsupported review status '{status}' "
                    f"for token '{token}'."
                )

            if not source_reference:
                raise ValueError(
                    f"Token '{token}' requires source_reference."
                )

            registry_id = upsert_registry_entry(
                connection=connection,
                token=token,
                definition=definition,
                status=status,
                source_reference=source_reference,
                replacement_token=replacement_token,
                notes=notes,
            )

            candidate_id = find_candidate_id(
                connection,
                normalize_token(token),
            )

            upsert_review_decision(
                connection=connection,
                registry_id=registry_id,
                candidate_id=candidate_id,
                decision_set=decision_set,
                token=token,
                status=status,
                source_reference=source_reference,
                notes=notes,
            )

            applied_statuses[status] += 1
            applied_tokens.append(token)

        protected_count = apply_protected_terms(
            connection=connection,
            policy=policy,
            decision_set=decision_set,
        )

        connection.commit()

        registry_rows = connection.execute(
            """
            SELECT status, COUNT(*)
            FROM registry_entries
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()

        return {
            "decision_set": decision_set,
            "seed_path": str(seed_path.resolve()),
            "database_path": str(database_path.resolve()),
            "seed_decisions_applied": len(applied_tokens),
            "seed_status_counts": dict(
                sorted(applied_statuses.items())
            ),
            "protected_terms_synchronized": protected_count,
            "registry_status_counts": {
                row[0]: row[1]
                for row in registry_rows
            },
            "applied_tokens": sorted(
                applied_tokens,
                key=str.casefold,
            ),
        }


def write_report(
    report: dict[str, Any],
    report_path: Path,
) -> None:
    """Write a formatted JSON B2 report."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")


def parse_arguments() -> argparse.Namespace:
    """Parse B2 command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Apply reviewed abbreviation decisions to the SQLite registry."
        )
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
        "--seed",
        type=Path,
        default=Path("config") / "abbreviationreviewseed.json",
        help=(
            "Reviewed decision seed path. "
            "Default: config/abbreviationreviewseed.json"
        ),
    )

    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("config") / "abbreviationpolicy.json",
        help=(
            "Protected-term policy path. "
            "Default: config/abbreviationpolicy.json"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports") / "reviewpromotionreport.json",
        help=(
            "JSON report path. "
            "Default: reports/reviewpromotionreport.json"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Run B2 registry review promotion."""

    arguments = parse_arguments()

    try:
        report = apply_review_seed(
            database_path=arguments.database,
            seed_path=arguments.seed,
            policy_path=arguments.policy,
        )

        write_report(
            report=report,
            report_path=arguments.report,
        )

    except (
        FileNotFoundError,
        OSError,
        ValueError,
        sqlite3.Error,
        json.JSONDecodeError,
    ) as error:
        print(f"REVIEW PROMOTION FAILED: {error}")
        return 2

    print(
        f"Review decisions applied: "
        f"{report['seed_decisions_applied']}"
    )

    print(
        f"Protected terms synchronized: "
        f"{report['protected_terms_synchronized']}"
    )

    print(
        f"Registry statuses: "
        f"{report['registry_status_counts']}"
    )

    print(
        f"Report: {arguments.report.resolve()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
