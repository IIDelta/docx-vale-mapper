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

import re


def normalize_comment_text(
    value: str,
) -> str:
    """
    Normalize Word and Vale text for safe comparison.

    This preserves the meaning of normal prose while removing Word
    paragraph/cell markers and harmonizing nonbreaking spaces.
    """

    normalized = (
        value.replace("\r", "")
        .replace("\x07", "")
        .replace("\x0b", "")
        .replace("\n", " ")
        .replace("\xa0", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip().casefold()


def vale_anchor_is_verified(
    word_range_text: str,
    vale_match_text: str,
) -> bool:
    """
    Return True only when the selected Word range equals the Vale match.

    This is used for Vale findings that include a Span. Structural
    findings are not verified here because they use their own ranges.
    """

    expected = normalize_comment_text(
        vale_match_text
    )

    actual = normalize_comment_text(
        word_range_text
    )

    if not expected:
        return False

    return actual == expected
