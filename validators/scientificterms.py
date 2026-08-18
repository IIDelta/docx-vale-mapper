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

import json
import re
from pathlib import Path
from typing import Any

from validators.abbreviationvalidator import ParagraphRecord, make_finding


def load_scientific_terms(config_path: Path) -> dict[str, list[str]]:
    """Load controlled scientific typography terms without guessing context."""
    empty = {"italic_required": [], "roman_required": []}
    if not config_path.is_file():
        return empty
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise ValueError("Scientific term registry must be a JSON object.")
    result: dict[str, list[str]] = {}
    for key in empty:
        values = payload.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Scientific term registry key '{key}' must be a string list.")
        result[key] = sorted({value.strip() for value in values if value.strip()}, key=str.casefold)
    return result


def validate_scientific_terms(
    paragraph: ParagraphRecord,
    text: str,
    get_format,
    registry: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Check only registry-approved terms for italic or roman formatting."""
    findings: list[dict[str, Any]] = []
    for term in registry["italic_required"]:
        for match in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text):
            if not get_format(match.start(), match.end()).get("italic", False):
                findings.append(make_finding(
                    "Clinical.ConfiguredItalicRequired",
                    "warning",
                    "Scientific typography: Italicize this configured scientific term.",
                    match.group(0),
                    paragraph,
                ))
    for term in registry["roman_required"]:
        for match in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE):
            if get_format(match.start(), match.end()).get("italic", False):
                findings.append(make_finding(
                    "Clinical.ConfiguredRomanRequired",
                    "warning",
                    "Scientific typography: Do not italicize this configured term.",
                    match.group(0),
                    paragraph,
                ))
    return findings
