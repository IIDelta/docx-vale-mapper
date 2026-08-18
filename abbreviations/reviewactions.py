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

import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from abbreviations.legacyimport import clean_value
from abbreviations.registryapi import (
    RegistryResolution,
    resolve_token,
)
from abbreviations.reviewimport import (
    apply_review_import,
    validate_review_rows,
)


def build_gui_decision_set() -> str:
    """
    Create a unique decision-set identifier.

    Unique identifiers preserve review history instead of overwriting
    prior GUI decisions for the same token.
    """

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    return f"gui_review_{timestamp}"


def apply_local_decision(
    database_path: Path,
    token: str,
    status: str,
    definition: str = "",
    replacement_token: str = "",
    notes: str = "",
    reviewer: str | None = None,
) -> tuple[RegistryResolution, dict[str, Any]]:
    """
    Validate and apply one local GUI decision.

    Returns:
        1. Updated registry resolution.
        2. Import/audit report for the decision.
    """

    reviewer_name = clean_value(
        reviewer or getpass.getuser()
    )

    if not reviewer_name:
        reviewer_name = "local_editor"

    raw_row = {
        "token": clean_value(token),
        "preferred_definition": clean_value(definition),
        "replacement_token": clean_value(
            replacement_token
        ),
        "reviewer_decision": clean_value(status),
        "reviewer_notes": clean_value(notes),
    }

    validated_rows, skipped_rows = validate_review_rows(
        [raw_row]
    )

    if skipped_rows != 0 or len(validated_rows) != 1:
        raise ValueError(
            "A nonblank reviewer decision is required."
        )

    decision_set = build_gui_decision_set()

    report = apply_review_import(
        database_path=database_path,
        review_rows=validated_rows,
        reviewer=reviewer_name,
        decision_set=decision_set,
        source_prefix="gui_review",
    )

    report["review_rows_skipped"] = skipped_rows
    report["decision_origin"] = "gui_review"

    resolution = resolve_token(
        database_path=database_path,
        token=raw_row["token"],
    )

    return resolution, report
