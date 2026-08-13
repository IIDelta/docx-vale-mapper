from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIRECTORY = PROJECT_ROOT / "tests"
VALE_CONFIG = PROJECT_ROOT / ".vale.ini"
EXPECTED_RESULTS_FILE = TESTS_DIRECTORY / "expectedresults.json"

VALE_EXECUTABLE = os.environ.get("VALE_EXE", "vale")


def load_expected_results() -> dict[str, dict[str, Any]]:
    """Load the expected fixture totals and rule-count contracts."""

    with EXPECTED_RESULTS_FILE.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def run_vale_fixture(fixture_path: Path) -> list[dict[str, Any]]:
    """Run Vale against one fixture and return its alert list."""

    command = [
        VALE_EXECUTABLE,
        "--no-global",
        f"--config={VALE_CONFIG}",
        "--output=JSON",
        str(fixture_path),
    ]

    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode == 2:
        details = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(
            f"Vale runtime failure for {fixture_path.name}:\n{details}"
        )

    if not process.stdout.strip():
        raise RuntimeError(
            f"Vale returned no JSON output for {fixture_path.name}."
        )

    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Vale returned invalid JSON for {fixture_path.name}:\n"
            f"{process.stdout}"
        ) from error

    if len(payload) != 1:
        raise RuntimeError(
            f"Expected one Vale result object for {fixture_path.name}; "
            f"received {len(payload)}."
        )

    return next(iter(payload.values()))


def validate_fixture(
    fixture_name: str,
    expected: dict[str, Any],
) -> list[str]:
    """Return a list of failures for one regression fixture."""

    fixture_path = TESTS_DIRECTORY / "fixtures" / fixture_name
    failures: list[str] = []

    if not fixture_path.is_file():
        return [f"{fixture_name}: fixture file was not found."]

    try:
        alerts = run_vale_fixture(fixture_path)
    except RuntimeError as error:
        return [str(error)]

    expected_total = expected["expected_total"]
    observed_total = len(alerts)

    if observed_total != expected_total:
        failures.append(
            f"{fixture_name}: expected {expected_total} total finding(s), "
            f"observed {observed_total}."
        )

    observed_checks = Counter(alert.get("Check", "") for alert in alerts)
    expected_checks = Counter(expected["expected_checks"])

    if observed_checks != expected_checks:
        failures.append(
            f"{fixture_name}: rule-count mismatch.\n"
            f"  Expected: {dict(sorted(expected_checks.items()))}\n"
            f"  Observed: {dict(sorted(observed_checks.items()))}"
        )

    if not failures:
        print(
            f"PASS  {fixture_name:<38} "
            f"{observed_total:>3} finding(s)"
        )

    return failures


def run_structural_unit_tests() -> list[str]:
    """Run pure-Python structural validator tests."""

    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test*.py",
    ]

    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode == 0:
        print(
            "PASS  abbreviation structural, import, and registry unit tests"
        )
        return []

    details = "\n".join(
        value
        for value in [
            process.stdout.strip(),
            process.stderr.strip(),
        ]
        if value
    )

    return [
        "A4.2 structural abbreviation validator tests failed.\n"
        f"{details}"
    ]


def parse_arguments() -> argparse.Namespace:
    """Parse optional fixture-selection arguments."""

    parser = argparse.ArgumentParser(
        description="Run Vale regression tests for approved Takeda style rules."
    )

    parser.add_argument(
        "--fixture",
        action="append",
        dest="fixtures",
        help=(
            "Run only one fixture. Repeat --fixture to run multiple fixtures. "
            "Example: --fixture a1coreclinicalterminology.md"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Execute the selected regression tests."""

    if not VALE_CONFIG.is_file():
        print(f"FAIL  Vale configuration not found: {VALE_CONFIG}")
        return 2

    if not EXPECTED_RESULTS_FILE.is_file():
        print(f"FAIL  Expected-results file not found: {EXPECTED_RESULTS_FILE}")
        return 2

    try:
        expected_results = load_expected_results()
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL  Unable to load expected results: {error}")
        return 2

    arguments = parse_arguments()

    selected_fixtures = arguments.fixtures or list(expected_results)

    unknown_fixtures = [
        fixture
        for fixture in selected_fixtures
        if fixture not in expected_results
    ]

    if unknown_fixtures:
        print(
            "FAIL  Unknown fixture name(s): "
            + ", ".join(unknown_fixtures)
        )
        return 2

    print("Running Vale regression suite...")
    print()

    all_failures: list[str] = []

    for fixture_name in selected_fixtures:
        failures = validate_fixture(
            fixture_name,
            expected_results[fixture_name],
        )
        all_failures.extend(failures)

    if arguments.fixtures is None:
        all_failures.extend(run_structural_unit_tests())

    print()

    if all_failures:
        print("REGRESSION TESTS FAILED")
        print()

        for failure in all_failures:
            print(f"FAIL  {failure}")

        return 1

    if arguments.fixtures is None:
        print(
            f"REGRESSION TESTS PASSED "
            f"({len(selected_fixtures)} Vale fixture file(s) "
            "and structural validator tests)"
        )
    else:
        print(
            f"REGRESSION TESTS PASSED "
            f"({len(selected_fixtures)} fixture file(s))"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
