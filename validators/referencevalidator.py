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

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)


RAW_EXTERNAL_URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[^\s<>()]+",
    flags=re.IGNORECASE,
)


def clean_url_match(
    value: str,
) -> str:
    """Remove sentence punctuation from a matched URL."""

    return value.rstrip(
        ".,;:!?"
    )


def validate_reference_text(
    paragraphs: list[ParagraphRecord],
) -> list[dict]:
    """
    Flag raw external website addresses.

    Regulatory-document references should not contain active external
    web addresses or http/www components.
    """

    findings: list[dict] = []

    for paragraph in paragraphs:
        for match in RAW_EXTERNAL_URL_PATTERN.finditer(
            paragraph.text
        ):
            url = clean_url_match(
                match.group(0)
            )

            findings.append(
                make_finding(
                    check="Clinical.RawExternalURL",
                    severity="error",
                    message=(
                        "Style guide references: Do not include "
                        "external website addresses with http, https, "
                        "or www components in document text."
                    ),
                    match=url,
                    paragraph=paragraph,
                )
            )

    return findings


def validate_active_external_link(
    paragraph: ParagraphRecord,
    display_text: str,
    address: str,
) -> dict:
    """Create a finding for one active external Word hyperlink."""

    return make_finding(
        check="Clinical.ActiveExternalLink",
        severity="error",
        message=(
            "Style guide references: Active external hyperlinks are "
            "not permitted in regulatory documents."
        ),
        match=display_text or address,
        paragraph=paragraph,
    )
