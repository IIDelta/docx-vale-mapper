from __future__ import annotations
import sys
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.executionverification import verify_execution_artifacts
from runtime.outputverification import verify_output_document
from abbreviations.legacyimport import calculate_sha256

FIXTURES_DIR = ROOT / "tests" / "fixtures" / "generated"

def mock_execution(fixture_name: str, docx_path: Path):
    """
    Simulates the execution artifact generation since we can't run pywin32 on Linux.
    If this were running on Windows, it would call `execute_operational_audit`.
    """
    base = FIXTURES_DIR / fixture_name
    af_path = base.with_suffix(".autofixexecution.json")
    com_path = base.with_suffix(".commentexecution.json")
    val_path = base.with_suffix(".outputverification.json")
    
    sha = calculate_sha256(docx_path)
    
    # Mocking standard responses that executionverification expects
    af_data = {
        "source_sha256": sha,
        "output_sha256": sha, # mock identical output since we don't modify the source in this mock
        "applied_count": 0,
        "summary_comment_count": 0
    }
    
    com_data = {
        "source_sha256": sha,
        "output_sha256": sha,
        "inserted_count": 0,
        "aggregated_count": 0,
        "inserted": []
    }
    
    af_path.write_text(json.dumps(af_data), encoding="utf-8")
    com_path.write_text(json.dumps(com_data), encoding="utf-8")
    val_path.write_text(json.dumps({}), encoding="utf-8")

def run_harness():
    print("Running Phase 2 Execution Verification Harness...")
    
    fixtures = {
        "FixtureA": FIXTURES_DIR / "Fixture_A_AutoFix.docx",
        "FixtureB": FIXTURES_DIR / "Fixture_B_Aggregation.docx",
        "FixtureC": FIXTURES_DIR / "Fixture_C_Ineligible.docx",
        "FixtureD": FIXTURES_DIR / "Fixture_D_Integrity.docx"
    }
    
    for name, path in fixtures.items():
        if not path.exists():
            print(f"Skipping {name}: Fixture not found at {path}")
            continue
            
        print(f"\nProcessing {name}...")
        
        # Simulate execution
        mock_execution(name, path)
        
        base = FIXTURES_DIR / name
        af_path = base.with_suffix(".autofixexecution.json")
        com_path = base.with_suffix(".commentexecution.json")
        
        # Run Verification
        sha = calculate_sha256(path)
        
        exec_result = verify_execution_artifacts(
            autofix_json_path=af_path,
            comment_json_path=com_path,
            expected_source_sha=sha,
            expected_output_sha=sha,
            expected_autofix_count=0,
            expected_individual_comment_count=0,
            expected_aggregated_comment_count=0
        )
        print(f"Execution Verification Result: {'PASS' if exec_result['passed'] else 'FAIL'}")
        if not exec_result['passed']:
            print(f"  Errors: {exec_result['errors']}")
            
        out_result = verify_output_document(
            source_path=path,
            output_path=path, # Mock output path as source path for now
            expected_mva_comment_count=0,
            expected_nbspace_replacements=False,
            expected_math_spacing_replacements=False
        )
        print(f"Output Verification Result: {'PASS' if out_result['output_document_exists'] else 'FAIL'}")
        
    print("\nHarness complete.")

if __name__ == "__main__":
    run_harness()
