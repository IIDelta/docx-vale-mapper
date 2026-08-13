from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from abbreviations.legacyimport import (
    clean_value,
    initialize_database,
    normalize_token,
    open_database,
)
from abbreviations.reviewpromote import ensure_review_schema


@dataclass(frozen=True)
class RegistryResolution:
    """Resolved registry information for one abbreviation token."""

    requested_token: str
    found: bool
    token: str
    normalized_token: str
    preferred_definition: str
    status: str
    source_reference: str
    replacement_token: str
    notes: str

    @property
    def enforcement_action(self) -> str:
        """Return the intended future document-audit behavior."""

        if not self.found:
            return "candidate_review"

        if self.status == "approved_expand":
            return "require_definition_or_list_entry"

        if self.status == "approved_no_expand":
            return "do_not_require_expansion"

        if self.status == "approved_list_only":
            return "require_list_entry"

        if self.status == "deprecated":
            return "warn_and_suggest_replacement"

        if self.status == "ambiguous":
            return "manual_definition_review"

        if self.status == "reviewed_candidate":
            return "candidate_review"

        if self.status == "ignored":
            return "ignore"

        return "candidate_review"

    def to_dict(self) -> dict:
        """Convert resolution data into JSON-safe output."""

        result = asdict(self)
        result["enforcement_action"] = self.enforcement_action

        return result


def resolve_token(
    database_path: Path,
    token: str,
) -> RegistryResolution:
    """Resolve one token against the reviewed registry."""

    requested_token = clean_value(token)

    if not requested_token:
        raise ValueError("A token is required for registry resolution.")

    initialize_database(database_path)

    with open_database(database_path) as connection:
        ensure_review_schema(connection)

        row = connection.execute(
            """
            SELECT
                token,
                normalized_token,
                preferred_definition,
                status,
                source_reference,
                replacement_token,
                notes
            FROM registry_entries
            WHERE normalized_token = ?
            """,
            (normalize_token(requested_token),),
        ).fetchone()

    if row is None:
        return RegistryResolution(
            requested_token=requested_token,
            found=False,
            token="",
            normalized_token=normalize_token(requested_token),
            preferred_definition="",
            status="unknown",
            source_reference="",
            replacement_token="",
            notes="No reviewed registry entry exists for this token.",
        )

    return RegistryResolution(
        requested_token=requested_token,
        found=True,
        token=row[0],
        normalized_token=row[1],
        preferred_definition=row[2],
        status=row[3],
        source_reference=row[4],
        replacement_token=row[5] or "",
        notes=row[6],
    )


def resolve_tokens(
    database_path: Path,
    tokens: list[str],
) -> list[RegistryResolution]:
    """Resolve multiple tokens in their supplied order."""

    return [
        resolve_token(
            database_path=database_path,
            token=token,
        )
        for token in tokens
    ]


def list_registry_tokens(
    database_path: Path,
) -> list[str]:
    """Return reviewed registry tokens ordered longest-first."""

    initialize_database(database_path)

    with open_database(database_path) as connection:
        ensure_review_schema(connection)

        rows = connection.execute(
            """
            SELECT token
            FROM registry_entries
            ORDER BY LENGTH(token) DESC, token COLLATE NOCASE
            """
        ).fetchall()

    return [
        row[0]
        for row in rows
    ]


def parse_arguments() -> argparse.Namespace:
    """Parse command-line query options."""

    parser = argparse.ArgumentParser(
        description=(
            "Query reviewed abbreviation registry entries."
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
        "--token",
        action="append",
        required=True,
        help=(
            "Token to resolve. Repeat --token for multiple values."
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Run registry resolution from the command line."""

    arguments = parse_arguments()

    try:
        resolutions = resolve_tokens(
            database_path=arguments.database,
            tokens=arguments.token,
        )
    except (OSError, ValueError) as error:
        print(f"REGISTRY QUERY FAILED: {error}")
        return 2

    print(
        json.dumps(
            [
                resolution.to_dict()
                for resolution in resolutions
            ],
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
