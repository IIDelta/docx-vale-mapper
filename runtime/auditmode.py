from __future__ import annotations


REPORTS_ONLY = "reports_only"
WORD_COMMENTS = "word_comments"
VALID_AUDIT_MODES = {REPORTS_ONLY, WORD_COMMENTS}


def normalize_audit_mode(value: str) -> str:
    """Return a supported audit output mode; default to safe reports-only."""
    normalized = str(value).strip().casefold()
    return normalized if normalized in VALID_AUDIT_MODES else REPORTS_ONLY


def comments_are_enabled(audit_mode: str) -> bool:
    """Return True only when the explicit Word-comment mode is selected."""
    return normalize_audit_mode(audit_mode) == WORD_COMMENTS
