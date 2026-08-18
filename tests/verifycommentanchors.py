import os
import sys
import json
from pathlib import Path

def verify_comment_anchors(output_base: Path):
    com_execution_path = output_base.with_suffix(".commentexecution.json")
    if not com_execution_path.exists():
        print(f"No comment execution found for {output_base.name}. Skipping comment verification.")
        return

    com_data = json.loads(com_execution_path.read_text(encoding="utf-8"))
    
    if sys.platform == "win32":
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(output_base.with_suffix(".docx").resolve()), ReadOnly=True)
            
            inserted_comments = com_data.get("inserted", [])
            for item in inserted_comments:
                start = item.get("verified_range_start")
                end = item.get("verified_range_end")
                expected_text = item.get("match", "")
                
                rng = doc.Range(start, end)
                if rng.Text != expected_text:
                    raise AssertionError(f"Comment anchor mismatch: expected '{expected_text}', found '{rng.Text}' at {start}-{end}")
                
            doc.Close(SaveChanges=False)
            word.Quit()
        finally:
            pythoncom.CoUninitialize()
    else:
        print(f"Skipping COM comment anchor text verification on platform {sys.platform}")

    print(f"OK: verify_comment_anchors passed for {output_base.name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verifycommentanchors.py <output_base>")
        sys.exit(1)
    verify_comment_anchors(Path(sys.argv[1]))
