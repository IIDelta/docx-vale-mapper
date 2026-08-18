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

from collections.abc import Iterable


FIELD_MARKERS = (
    "ADDIN EN.CITE",
    "BIBLIOGRAPHY",
    "CITATION",
    "ZOTERO_ITEM",
    "CSL_CITATION",
    "MENDELEY",
    "PAGEREF",
    " REF ",
    " TOC ",
    " SEQ ",
)


def is_protected_field_code(code_text: str) -> bool:
    """Return True for citation, bibliography, and dynamic-reference fields."""
    normalized = f" {code_text.casefold()} "
    return any(marker.casefold() in normalized for marker in FIELD_MARKERS)


def ranges_overlap(
    start: int,
    end: int,
    protected_ranges: Iterable[tuple[int, int]],
) -> bool:
    """Return True when a candidate Word range overlaps a protected field."""
    return any(
        start < protected_end and end > protected_start
        for protected_start, protected_end in protected_ranges
    )


def protected_field_ranges(doc) -> list[tuple[int, int]]:
    """Extract protected Word field ranges without changing the document."""
    ranges: list[tuple[int, int]] = []
    for field_index in range(1, doc.Fields.Count + 1):
        try:
            field = doc.Fields.Item(field_index)
            if not is_protected_field_code(str(field.Code.Text)):
                continue
            start = min(int(field.Code.Start), int(field.Result.Start))
            end = max(int(field.Code.End), int(field.Result.End))
        except Exception:
            continue
        if end > start:
            ranges.append((start, end))
    return ranges
