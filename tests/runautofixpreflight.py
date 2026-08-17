from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from runtime.autofixpreflight import run_preflight
p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--plan",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output-base",type=Path,required=True);a=p.parse_args()
path=run_preflight(a.source,a.plan,a.manifest,a.output_base)
print(f"AUTOFIX PREFLIGHT WRITTEN: {path}")
