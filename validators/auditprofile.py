from __future__ import annotations


STANDARD_AUDIT = "standard"
ADVANCED_AUDIT = "advanced"


def normalize_audit_profile(
    value: str,
) -> str:
    """Convert display/user text into an internal audit profile."""

    normalized = value.strip().casefold()

    if normalized in {
        "advanced",
        "advanced structural review",
        "structural",
    }:
        return ADVANCED_AUDIT

    return STANDARD_AUDIT


def is_advanced_profile(
    profile: str,
) -> bool:
    """Return True only for Advanced Structural Review."""

    return normalize_audit_profile(
        profile
    ) == ADVANCED_AUDIT
