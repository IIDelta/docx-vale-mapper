from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreflightCheck:
    """One runtime environment check."""

    name: str
    passed: bool
    details: str


def check_file(
    name: str,
    file_path: Path,
) -> PreflightCheck:
    """Check whether a required file exists."""

    if file_path.is_file():
        return PreflightCheck(
            name=name,
            passed=True,
            details=str(file_path),
        )

    return PreflightCheck(
        name=name,
        passed=False,
        details=f"Missing file: {file_path}",
    )


def check_directory(
    name: str,
    directory_path: Path,
) -> PreflightCheck:
    """Check whether a required directory exists."""

    if directory_path.is_dir():
        return PreflightCheck(
            name=name,
            passed=True,
            details=str(directory_path),
        )

    return PreflightCheck(
        name=name,
        passed=False,
        details=f"Missing directory: {directory_path}",
    )


def check_python_module(
    name: str,
    module_name: str,
) -> PreflightCheck:
    """Check whether a Python module is installed."""

    available = importlib.util.find_spec(
        module_name
    ) is not None

    if available:
        return PreflightCheck(
            name=name,
            passed=True,
            details=f"Python module available: {module_name}",
        )

    return PreflightCheck(
        name=name,
        passed=False,
        details=f"Python module not available: {module_name}",
    )


def check_vale() -> PreflightCheck:
    """Check whether Vale is available and return its version."""

    vale_path = shutil.which("vale")

    if not vale_path:
        return PreflightCheck(
            name="Vale CLI",
            passed=False,
            details="Vale executable was not found on PATH.",
        )

    try:
        process = subprocess.run(
            ["vale", "--version"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        return PreflightCheck(
            name="Vale CLI",
            passed=False,
            details=f"Unable to execute Vale: {error}",
        )

    if process.returncode != 0:
        details = (
            process.stderr.strip()
            or process.stdout.strip()
            or "Vale returned a nonzero exit code."
        )

        return PreflightCheck(
            name="Vale CLI",
            passed=False,
            details=details,
        )

    return PreflightCheck(
        name="Vale CLI",
        passed=True,
        details=process.stdout.strip(),
    )


def check_output_directory(
    output_path: Path,
) -> PreflightCheck:
    """
    Verify that the output directory exists and is writable.

    The directory is created when possible.
    """

    output_directory = output_path.parent

    try:
        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as error:
        return PreflightCheck(
            name="Output directory",
            passed=False,
            details=(
                f"Unable to create output directory "
                f"{output_directory}: {error}"
            ),
        )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=output_directory,
            prefix="audit_preflight_",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name
            )

        temporary_path.unlink()

    except OSError as error:
        return PreflightCheck(
            name="Output directory",
            passed=False,
            details=(
                f"Output directory is not writable "
                f"({output_directory}): {error}"
            ),
        )

    return PreflightCheck(
        name="Output directory",
        passed=True,
        details=str(output_directory),
    )


def run_preflight(
    project_root: Path,
    output_path: Path,
) -> dict:
    """
    Run environment checks required before a Word audit begins.
    """

    checks = [
        check_file(
            "Vale configuration",
            project_root / ".vale.ini",
        ),
        check_directory(
            "Styles directory",
            project_root / "Styles",
        ),
        check_file(
            "Abbreviation policy",
            project_root
            / "config"
            / "abbreviationpolicy.json",
        ),
        check_python_module(
            "python-docx",
            "docx",
        ),
        check_python_module(
            "pywin32",
            "win32com",
        ),
        check_vale(),
        check_output_directory(
            output_path,
        ),
    ]

    passed = all(
        check.passed
        for check in checks
    )

    return {
        "passed": passed,
        "checks": [
            asdict(check)
            for check in checks
        ],
    }


def format_preflight_failure(
    preflight_result: dict,
) -> str:
    """Format failed checks into a user-facing error message."""

    failed_checks = [
        check
        for check in preflight_result["checks"]
        if not check["passed"]
    ]

    if not failed_checks:
        return ""

    lines = [
        "Audit preflight failed:",
        "",
    ]

    for check in failed_checks:
        lines.append(
            f"- {check['name']}: {check['details']}"
        )

    return "\n".join(lines)
