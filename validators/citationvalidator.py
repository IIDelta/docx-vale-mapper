from __future__ import annotations

import re
from dataclasses import dataclass


CITATION_FIELD_PREFIXES = (
    "ADDIN EN.CITE",
    "CITATION",
    "ADDIN ZOTERO_ITEM",
    "ADDIN MENDELEY",
)


BIBLIOGRAPHY_FIELD_PREFIXES = (
    "BIBLIOGRAPHY",
    "ADDIN EN.REFLIST",
    "ADDIN ZOTERO_BIBL",
    "ADDIN MENDELEY_BIBLIOGRAPHY",
)


@dataclass(frozen=True)
class CitationFieldRecord:
    """One detected Word citation or bibliography field."""

    field_type: str
    code_text: str
    result_start: int
    result_end: int


def normalize_field_code(
    value: str,
) -> str:
    """Normalize Word field code text for matching."""

    return re.sub(
        r"\s+",
        " ",
        value.replace("\r", " ").strip(),
    ).upper()


def classify_field_code(
    code_text: str,
) -> str:
    """
    Classify a Word field code.

    Returns:
        citation
        bibliography
        other
    """

    normalized_code = normalize_field_code(
        code_text
    )

    if normalized_code.startswith(
        CITATION_FIELD_PREFIXES
    ):
        return "citation"

    if normalized_code.startswith(
        BIBLIOGRAPHY_FIELD_PREFIXES
    ):
        return "bibliography"

    return "other"


def is_protected_citation_field(
    code_text: str,
) -> bool:
    """Return True for citation or bibliography field codes."""

    return classify_field_code(
        code_text
    ) in {
        "citation",
        "bibliography",
    }


def ranges_overlap(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> bool:
    """
    Return True when two Word character ranges overlap.
    """

    return (
        first_start < second_end
        and second_start < first_end
    )


def target_overlaps_citation_field(
    target_start: int,
    target_end: int,
    citation_fields: list[CitationFieldRecord],
) -> bool:
    """
    Return True when a comment target overlaps a protected field result.
    """

    return any(
        ranges_overlap(
            target_start,
            target_end,
            field.result_start,
            field.result_end,
        )
        for field in citation_fields
    )
