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


SUMMARY_HEADINGS = {
    "summary of changes",
    "summary of change",
    "amendment summary",
    "summary of protocol changes",
    "summary of amendments",
}


PROTOCOL_SUMMARY_HEADINGS = {
    "protocol summary",
    "protocol synopsis",
    "synopsis",
}


REFERENCE_HEADINGS = {
    "references",
    "reference list",
    "bibliography",
}


TITLE_PAGE_LABEL_PATTERN = re.compile(
    r"^(?:"
    r"title of study|"
    r"protocol full title|"
    r"protocol number|"
    r"original protocol|"
    r"amendment number|"
    r"sponsor confidentiality statement|"
    r"sponsor|"
    r"investigational product|"
    r"compound|"
    r"study phase|"
    r"indication"
    r")\s*:",
    flags=re.IGNORECASE,
)


CAPTION_PATTERN = re.compile(
    r"^(?:Table|Figure)\s+",
    flags=re.IGNORECASE,
)


def heading_level_from_style(
    style_name: str,
) -> int:
    """Return Word heading level from a style name."""

    match = re.search(
        r"heading\s+(\d+)",
        style_name,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return 0


def is_title_style(
    style_name: str,
) -> bool:
    """Return True for Word title/subtitle styles."""

    normalized = style_name.casefold()

    return (
        normalized == "title"
        or normalized == "subtitle"
        or "document title" in normalized
    )


def is_summary_heading(
    text: str,
) -> bool:
    """Return True for Summary of Changes headings."""

    return text.strip().casefold() in SUMMARY_HEADINGS


def is_protocol_summary_heading(
    text: str,
) -> bool:
    """Return True for protocol summary headings."""

    return text.strip().casefold() in PROTOCOL_SUMMARY_HEADINGS


def is_reference_heading(
    text: str,
) -> bool:
    """Return True for reference-section headings."""

    return text.strip().casefold() in REFERENCE_HEADINGS


def is_title_page_label(
    text: str,
) -> bool:
    """Return True for common title-page metadata labels."""

    return bool(
        TITLE_PAGE_LABEL_PATTERN.match(
            text.strip()
        )
    )


def classify_content_zone(
    text: str,
    style_name: str,
    is_in_table: bool,
    list_marker: str,
    title_page_active: bool,
    summary_active: bool,
    protocol_summary_active: bool,
    reference_active: bool,
) -> str:
    """
    Assign one document-content zone to a paragraph.

    The order is deliberate: table/title/summary metadata must never
    be treated as ordinary prose or editorial list items.
    """

    if summary_active:
        return "summary_of_changes"

    if protocol_summary_active:
        return "protocol_summary"

    if is_title_style(style_name):
        return "title_page"

    if title_page_active and (
        is_in_table
        or is_title_page_label(text)
    ):
        return "title_page"

    heading_level = heading_level_from_style(
        style_name
    )

    if heading_level > 0:
        return "heading"

    if CAPTION_PATTERN.match(text.strip()):
        return "caption"

    if is_in_table:
        return "table_cell"

    if list_marker.strip():
        return "list_item"

    if reference_active:
        return "reference"

    return "body_narrative"
