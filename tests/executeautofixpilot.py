from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from runtime.autofixexecutor import execute_autofix_pilot
p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--preflight",type=Path,required=True);a=p.parse_args()
print("AUTOFIX EXECUTION WRITTEN:",execute_autofix_pilot(a.source,a.output,a.manifest,a.preflight))
