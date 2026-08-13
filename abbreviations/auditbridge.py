from __future__ import annotations

import copy
import sqlite3
from pathlib import Path
from typing import Any

from abbreviations.legacyimport import (
    open_database,
)
from abbreviations.reviewpromote import ensure_review_schema
from validators.abbreviationvalidator import (
    load_policy,
)


def load_registry_policy(
    database_path: Path,
) -> dict[str, Any]:
    """
    Load reviewed registry decisions relevant to document auditing.

    If no local database exists yet, return an empty registry policy.
    """

    empty_policy = {
        "tracked_abbreviations": {},
        "never_expand": [],
        "deprecated_terms": {},
    }

    if not database_path.is_file():
        return empty_policy

    try:
        with open_database(database_path) as connection:
            ensure_review_schema(connection)

            rows = connection.execute(
                """
                SELECT
                    token,
                    preferred_definition,
                    status,
                    replacement_token
                FROM registry_entries
                """
            ).fetchall()

    except sqlite3.Error:
        return empty_policy

    registry_policy = {
        "tracked_abbreviations": {},
        "never_expand": [],
        "deprecated_terms": {},
    }

    for (
        token,
        definition,
        status,
        replacement_token,
    ) in rows:
        if status == "approved_expand" and definition:
            registry_policy["tracked_abbreviations"][token] = {
                "expansion": definition
            }

        elif status == "approved_no_expand":
            registry_policy["never_expand"].append(token)

        elif status == "deprecated" and replacement_token:
            registry_policy["deprecated_terms"][token] = (
                replacement_token
            )

    return registry_policy


def build_effective_policy(
    base_policy_path: Path,
    database_path: Path,
) -> dict[str, Any]:
    """
    Merge the static local policy with reviewed registry decisions.

    Registry decisions override static policy behavior when the same
    token exists in both places.
    """

    base_policy = load_policy(base_policy_path)
    registry_policy = load_registry_policy(database_path)

    effective_policy = copy.deepcopy(base_policy)

    effective_policy.setdefault(
        "tracked_abbreviations",
        {},
    )

    effective_policy.setdefault(
        "never_expand",
        [],
    )

    protected_display_values: dict[str, str] = {}

    for token in effective_policy["never_expand"]:
        cleaned_token = token.strip()

        if cleaned_token:
            protected_display_values.setdefault(
                cleaned_token.casefold(),
                cleaned_token,
            )

    for token in registry_policy["never_expand"]:
        cleaned_token = token.strip()

        if cleaned_token:
            protected_display_values.setdefault(
                cleaned_token.casefold(),
                cleaned_token,
            )

    effective_policy["never_expand"] = sorted(
        protected_display_values.values(),
        key=str.casefold,
    )

    protected_lookup = {
        token.casefold()
        for token in effective_policy["never_expand"]
    }

    for token, metadata in registry_policy[
        "tracked_abbreviations"
    ].items():
        if token.casefold() in protected_lookup:
            continue

        effective_policy["tracked_abbreviations"][token] = metadata

    effective_policy["tracked_abbreviations"] = {
        token: metadata
        for token, metadata in effective_policy[
            "tracked_abbreviations"
        ].items()
        if token.casefold() not in protected_lookup
    }

    effective_policy["deprecated_terms"] = (
        registry_policy["deprecated_terms"]
    )

    return effective_policy
