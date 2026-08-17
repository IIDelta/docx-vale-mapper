from __future__ import annotations

import json
from pathlib import Path


def load_unit_style_exemptions(config_path: Path) -> set[str]:
    """Load exact Word style names exempt from unit-spacing suggestions."""
    if not config_path.is_file():
        return set()
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    values = payload.get("excluded_style_names", [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("excluded_style_names must be a list of strings.")
    return {value.strip().casefold() for value in values if value.strip()}
