from __future__ import annotations
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from runtime.execution import execute_operational_audit

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--manifest", type=Path, required=True)
p.add_argument("--autofix-preflight", type=Path, required=True)
p.add_argument("--comment-preflight", type=Path, required=True)
p.add_argument("--output-base", type=Path, required=True)
a = p.parse_args()

print("OPERATIONAL EXECUTION WRITTEN:", execute_operational_audit(a.source, a.output, a.manifest, a.autofix_preflight, a.comment_preflight, a.output_base))
