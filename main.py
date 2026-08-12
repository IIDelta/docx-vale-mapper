from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from docx import Document


REPOSITORY_ROOT = Path(__file__).resolve().parent
VALE_CONFIG = REPOSITORY_ROOT / ".vale.ini"

CSV_HEADERS = [
    "location",
    "paragraph_index",
    "severity",
    "rule_id",
    "message",
    "match",
    "suggestion",
    "line",
    "span",
    "original_text",
]


def run_vale(text: str) -> list[dict[str, Any]]:
    """Run Vale against one extracted DOCX paragraph."""

    command = [
        "vale",
        "--no-global",
        f"--config={VALE_CONFIG}",
        "--ext=.md",
        "--output=JSON",
    ]

    process = subprocess.run(
        command,
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )

    if process.returncode == 2:
        error_message = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"Vale returned a runtime error:\n{error_message}")

    if not process.stdout.strip():
        return []

    try:
        results = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Vale returned output that could not be parsed as JSON:\n"
            f"{process.stdout}"
        ) from error

    return results.get("stdin.md", [])


def get_suggestion(alert: dict[str, Any]) -> str:
    """
    Safely extract Vale's optional replacement suggestion.

    Vale returns Action.Params as null when a rule has no configured
    replacement action, so this function always returns a string.
    """

    action = alert.get("Action") or {}

    if not isinstance(action, dict):
        return ""

    action_params = action.get("Params") or []

    if not isinstance(action_params, list):
        return ""

    return " | ".join(str(parameter) for parameter in action_params)


def scan_document(docx_path: Path) -> list[dict[str, Any]]:
    """Scan all nonempty body paragraphs in a DOCX document."""

    document = Document(docx_path)
    findings: list[dict[str, Any]] = []

    for paragraph_index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()

        if not text:
            continue

        try:
            alerts = run_vale(text)
        except RuntimeError as error:
            raise RuntimeError(
                f"Unable to scan body paragraph {paragraph_index}: {error}"
            ) from error

        for alert in alerts:
            findings.append(
                {
                    "location": f"Body paragraph {paragraph_index}",
                    "paragraph_index": paragraph_index,
                    "severity": alert.get("Severity", ""),
                    "rule_id": alert.get("Check", ""),
                    "message": alert.get("Message", ""),
                    "match": alert.get("Match", ""),
                    "suggestion": get_suggestion(alert),
                    "line": alert.get("Line", ""),
                    "span": alert.get("Span", ""),
                    "original_text": text,
                }
            )

    return findings


def export_to_csv(findings: list[dict[str, Any]], output_path: Path) -> None:
    """Write audit findings to a UTF-8 CSV file."""

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=CSV_HEADERS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(findings)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Scan DOCX body paragraphs with Takeda Vale style rules."
    )

    parser.add_argument(
        "document",
        type=Path,
        help="Path to the DOCX document to audit.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("auditreport.csv"),
        help="CSV report output path. Default: auditreport.csv",
    )

    return parser.parse_args()


def main() -> int:
    """Run the DOCX audit and export its findings."""

    arguments = parse_arguments()

    if not arguments.document.is_file():
        print(
            f"Document not found: {arguments.document}",
            file=sys.stderr,
        )
        return 2

    if arguments.document.suffix.lower() != ".docx":
        print(
            f"Expected a .docx file, received: {arguments.document.name}",
            file=sys.stderr,
        )
        return 2

    if not VALE_CONFIG.is_file():
        print(
            f"Vale configuration not found: {VALE_CONFIG}",
            file=sys.stderr,
        )
        return 2

    try:
        findings = scan_document(arguments.document)
        export_to_csv(findings, arguments.output)
    except FileNotFoundError:
        print(
            "Vale was not found. Install Vale and ensure the 'vale' command "
            "is available on PATH.",
            file=sys.stderr,
        )
        return 2
    except (OSError, RuntimeError) as error:
        print(f"Audit failed: {error}", file=sys.stderr)
        return 2

    print(f"Scan complete: {len(findings)} finding(s).")
    print(f"CSV report: {arguments.output.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
