import os
import sys
import json
from pathlib import Path
from abbreviations.legacyimport import calculate_sha256

def verify_output_docx(source_path: Path, output_base: Path):
    output_docx = output_base.with_suffix('.docx')
    if not output_docx.exists():
        raise AssertionError(f"Output document missing: {output_docx}")

    if not source_path.exists():
        raise AssertionError(f"Source document missing: {source_path}")

    # Verify JSON manifests
    manifest_path = output_base.with_suffix(".auditmanifest.json")
    if not manifest_path.exists():
        raise AssertionError(f"Audit manifest missing: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise AssertionError(f"Audit manifest is invalid JSON: {manifest_path}")

    source_sha = calculate_sha256(source_path)
    if manifest.get("source_sha256") != source_sha:
        raise AssertionError("Source document SHA changed or mismatch in manifest!")

    if sys.platform == "win32":
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(output_docx.resolve()), ReadOnly=True)
            doc.Close(SaveChanges=False)
            word.Quit()
        except Exception as e:
            raise AssertionError(f"Failed to open output DOCX via Word COM: {e}")
        finally:
            pythoncom.CoUninitialize()
    else:
        print(f"Skipping COM output DOCX open test on platform {sys.platform}")

    print(f"OK: verify_output_docx passed for {output_docx.name}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verifyoutputdocx.py <source_path> <output_base>")
        sys.exit(1)
    verify_output_docx(Path(sys.argv[1]), Path(sys.argv[2]))
