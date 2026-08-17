from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.commentpreflight import run_comment_preflight


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate unresolved comment anchors."
    )

    parser.add_argument(
        "--source",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--plan",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-base",
        required=True,
        type=Path,
    )

    arguments = parser.parse_args()

    report_path = run_comment_preflight(
        source_path=arguments.source,
        plan_path=arguments.plan,
        manifest_path=arguments.manifest,
        output_base=arguments.output_base,
    )

    print(
        f"COMMENT PREFLIGHT WRITTEN: {report_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
