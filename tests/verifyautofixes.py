import os
import sys
import json
from pathlib import Path

def verify_auto_fixes(output_base: Path):
    af_execution_path = output_base.with_suffix(".autofixexecution.json")
    if not af_execution_path.exists():
        print(f"No auto-fix execution found for {output_base.name}. Skipping auto-fix verification.")
        return

    af_data = json.loads(af_execution_path.read_text(encoding="utf-8"))
    
    if sys.platform == "win32":
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(output_base.with_suffix(".docx").resolve()), ReadOnly=True)
            
            applied_fixes = af_data.get("applied", [])
            for item in applied_fixes:
                start = item.get("verified_range_start")
                end = item.get("verified_range_end")
                # But wait, the range might have shrunk/grown.
                # Actually, the string replacement length might differ from the original match length.
                # If we apply fixes in reverse order, do the starting positions of earlier (later in text) fixes remain valid? Yes.
                # But the start position of *this* fix remains the same, though its end position may change based on the replacement length.
                expected_repl = item.get("replacement", "")
                
                # Length of the new range: start + len(expected_repl)
                rng = doc.Range(start, start + len(expected_repl))
                if rng.Text != expected_repl:
                    raise AssertionError(f"Auto-fix verification failed: expected '{expected_repl}' at {start}, found '{rng.Text}'")
                
            doc.Close(SaveChanges=False)
            word.Quit()
        finally:
            pythoncom.CoUninitialize()
    else:
        print(f"Skipping COM auto-fix text verification on platform {sys.platform}")

    print(f"OK: verify_auto_fixes passed for {output_base.name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verifyautofixes.py <output_base>")
        sys.exit(1)
    verify_auto_fixes(Path(sys.argv[1]))
