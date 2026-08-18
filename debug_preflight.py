import json
from pathlib import Path
import sys

def debug():
    reports = Path(r"C:\Users\xjc0417\Documents\docx-vale-mapper\reports")
    preflight_path = reports / "KER050-MD-201 Protocol Amend 8 2026-07-29_AUDITED.autofixpreflight.json"
    if not preflight_path.exists():
        print("Preflight not found at", preflight_path)
        return
        
    data = json.loads(preflight_path.read_text(encoding="utf-8"))
    
    unverified = data.get("unverified_auto_fixes", [])
    print(f"Total unverified: {len(unverified)}")
    for i, item in enumerate(unverified[:5]):
        print(f"\nItem {i+1}:")
        print(f"Reason: {item.get('reason')}")
        print(f"Rule: {item.get('plan', {}).get('rule')}")
        print(f"Match: {item.get('plan', {}).get('match')}")

if __name__ == "__main__":
    debug()
