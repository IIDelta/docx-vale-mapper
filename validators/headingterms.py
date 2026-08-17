from __future__ import annotations

import json
from pathlib import Path


def load_heading_terms(config_path: Path) -> dict[str, set[str]]:
    """Load controlled heading exemptions without inferring terminology."""
    result = {"acronym_exemptions": set(), "title_case_exemptions": set()}
    if not config_path.is_file():
        return result
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise ValueError("Heading term registry must be a JSON object.")
    for key in result:
        values = payload.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Heading term registry key '{key}' must be a string list.")
        result[key] = {value.casefold() for value in values if value.strip()}
    return result
