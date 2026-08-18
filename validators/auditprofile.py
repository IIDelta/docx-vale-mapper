"""
Purpose:
    Apply verified safe auto-fixes to copied Word documents.

Inputs:
    Source/output paths, verified auto-fix plan, protected field ranges.

Outputs:
    Modified output DOCX and auto-fix execution artifact.

Must not:
    Modify source DOCX.
    Apply unverified fixes.
    Apply report-only or disabled rules.
    Replace broad Word ranges without exact verification.
"""

from __future__ import annotations


OPERATIONAL_AUDIT = "operational"


def normalize_audit_profile(
    value: str,
) -> str:
    """Convert display/user text into an internal audit profile."""

    return OPERATIONAL_AUDIT
