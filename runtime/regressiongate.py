"""
Purpose:
    Run the repository regression and unit-test gate before a document audit.

Inputs:
    Project root and regression test runner path.

Outputs:
    Returns normally when tests pass; raises RuntimeError when tests fail.

Must not:
    Open Word.
    Modify audit artifacts.
    Insert comments.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_regression_gate(
    project_root: Path,
    test_runner: Path,
) -> None:
    """Run all approved regression and unit tests."""

    command = [
        sys.executable,
        str(test_runner),
    ]

    process = subprocess.run(
        command,
        cwd=project_root,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode == 0:
        return

    output = process.stdout.strip()
    errors = process.stderr.strip()

    details = "\n\n".join(
        value
        for value in [output, errors]
        if value
    )

    raise RuntimeError(
        "The Takeda Vale regression suite failed. "
        "The live-document audit was not started.\n\n"
        f"{details}"
    )
