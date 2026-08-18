"""
Purpose:
    Resolve verified Word ranges and support controlled comment insertion.

Inputs:
    Verified findings, Word COM ranges, line/range maps, and protected fields.

Outputs:
    Resolved ranges and Word comments.

Must not:
    Guess an unverified anchor.
    Modify source documents.
    Apply auto-fixes.
    Decide rule disposition.
"""

from typing import Any

from validators.commentverification import (
    vale_anchor_is_verified,
)
from validators.fieldprotection import (
    protected_field_ranges,
    ranges_overlap,
)
from validators.valespan import (
    resolve_match_offsets,
    vale_match_occurrence_index,
    vale_span_to_word_range,
)


def find_vale_match_range(
    doc,
    paragraph_start: int,
    paragraph_end: int,
    match_text: str,
    occurrence_index: int = 0,
) -> Any:
    """
    Use Word Find to locate the exact Vale match.

    Supports repeated text by selecting the requested occurrence index.
    Long match strings are not sent to Word Find because Word has a
    string-parameter length limit.
    """

    if not match_text.strip():
        return None

    if len(match_text) > 200:
        return None

    try:
        search_start = paragraph_start
        search_end = paragraph_end
        current_occurrence = 0

        while search_start < search_end:
            search_range = doc.Range(
                search_start,
                search_end,
            )

            find = search_range.Find

            find.ClearFormatting()
            find.Replacement.ClearFormatting()

            find.Text = match_text
            find.Forward = True
            find.Wrap = 0
            find.Format = False
            find.MatchCase = False
            find.MatchWholeWord = False
            find.MatchWildcards = False

            found = find.Execute()

            if not found:
                return None

            if current_occurrence == occurrence_index:
                return search_range.Duplicate

            current_occurrence += 1
            search_start = search_range.End

    except Exception as find_error:
        print(
            "Word Find fallback unavailable for "
            f"'{match_text}': {find_error}"
        )

    return None

