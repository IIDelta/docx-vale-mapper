from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.commentpolicy import build_comment_plan, load_comment_policy, write_comment_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an Operational Audit comment plan from findings JSON.")
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--output-base", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=PROJECT_ROOT / "config" / "commentpolicy.json")
    args = parser.parse_args()
    findings_payload = json.loads(args.findings.read_text(encoding="utf-8"))
    plan = build_comment_plan(findings_payload["findings"], load_comment_policy(args.policy))
    path = write_comment_plan(args.output_base, plan)
    print(f"COMMENT PLAN WRITTEN: {path}")
    print(f"Auto fixes: {plan['auto_fix_count']}")
    print(f"Comments: {plan['comment_count']}")
    print(f"Report only: {plan['report_only_count']}")
    print(f"Disabled: {plan['disabled_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
