from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.reportscontract import validate_reports_only_artifacts

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate reports-only audit artifacts."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-base", required=True, type=Path)
    arguments = parser.parse_args()

    failures = validate_reports_only_artifacts(
        arguments.source,
        arguments.output_base,
    )
    if failures:
        print("REPORTS-ONLY ACCEPTANCE FAILED")
        for failure in failures:
            print(f"FAIL  {failure}")
        return 1
    print("REPORTS-ONLY ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
