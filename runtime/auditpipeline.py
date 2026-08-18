"""
Purpose:
    Orchestrate the end-to-end audit lifecycle.

Inputs:
    Source DOCX path, output base path, audit mode, audit profile,
    progress/status callbacks.

Outputs:
    JSON artifacts, optional output DOCX, optional comment/auto-fix execution.

Must not:
    Construct Tkinter widgets.
    Define Style Guide rules.
    Overwrite source DOCX files.
"""

import json
import os
import subprocess
import traceback
from collections import Counter
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from validators.commentverification import (
    vale_anchor_is_verified,
)

from validators.fieldprotection import (
    protected_field_ranges,
    ranges_overlap,
)

import pythoncom
import win32com.client

from app.settings import (
    ABBREVIATION_DATABASE_PATH,
    PROJECT_ROOT,
    REGRESSION_TEST_RUNNER,
)
from abbreviations.candidatefinder import (
    TextRecord,
    discover_candidates,
    write_report as write_candidate_report,
)
from abbreviations.reportpaths import (
    candidate_report_path_for_document,
)
from runtime.auditartifacts import (
    write_audit_summary,
)
from runtime.auditmanifest import (
    build_audit_manifest,
    write_audit_manifest,
)
from runtime.auditmode import (
    comments_are_enabled,
    normalize_audit_mode,
)
from runtime.auditreport import (
    write_audit_findings_report,
)
from runtime.commentbudget import (
    apply_comment_budget,
    load_comment_budget,
    write_comment_queue,
)
from runtime.commentpolicy import (
    load_comment_policy,
    disposition,
    build_comment_plan,
    write_comment_plan,
)
from runtime.autofixpreflight import run_preflight as run_autofix_preflight
from runtime.commentpreflight import run_comment_preflight
from runtime.execution import execute_operational_audit
from runtime.regressiongate import (
    run_regression_gate,
)
from runtime.preflight import (
    format_preflight_failure,
    run_preflight,
)
from validators.findingfilter import (
    deduplicate_findings,
    filter_findings_by_context,
)
from validators.findingmerge import (
    merge_audit_findings,
)
from word.reader import (
    build_paragraph_records,
)
from word.structuralchecks import (
    add_structural_findings,
)
from word.commentwriter import (
    find_vale_match_range,
)
from validators.valespan import (
    resolve_match_offsets,
    vale_match_occurrence_index,
    vale_span_to_word_range,
)


# --- THE CORE ENGINE ---
def run_scan_thread(
    docx_path,
    output_path,
    status_var,
    progress_var,
    start_btn,
    audit_profile,
    audit_mode,
):
    """
    Run the Word audit in a background thread.

    The audit uses a production-safe Standard profile by default and
    prevents duplicate comments on the same resolved Word range.
    """

    pythoncom.CoInitialize()
    audit_mode = normalize_audit_mode(audit_mode)

    word = None
    doc = None

    audit_stage = "1ing audit"

    preflight_result = {
        "passed": False,
        "checks": [],
    }

    vale_errors: list[dict] = []
    structural_findings: list[dict] = []
    errors: list[dict] = []

    suppressed_findings = Counter()

    comment_metrics = {
        "candidate_comment_count": 0,
        "inserted_comment_count": 0,
        "skipped_comment_reasons": Counter(),
    }

    try:
        abs_input = os.path.abspath(docx_path)
        abs_output = os.path.abspath(output_path)

        source_path = Path(abs_input)
        audited_output_path = Path(abs_output)

        # ------------------------------------------------------------
        # Phase 1: Environment preflight
        # ------------------------------------------------------------
        audit_stage = "Running environment preflight"

        status_var.set(
            "Running environment preflight..."
        )

        progress_var.set(0)

        preflight_result = run_preflight(
            project_root=PROJECT_ROOT,
            output_path=audited_output_path,
        )

        if not preflight_result["passed"]:
            raise RuntimeError(
                format_preflight_failure(
                    preflight_result
                )
            )

        # ------------------------------------------------------------
        # Phase 2: Regression gate
        # ------------------------------------------------------------
        audit_stage = "Running regression tests"

        status_var.set(
            "Running approved rule regression tests..."
        )

        run_regression_gate(
            project_root=PROJECT_ROOT,
            test_runner=REGRESSION_TEST_RUNNER,
        )


        # ------------------------------------------------------------
        # Phase 3: Launch Word
        # ------------------------------------------------------------
        audit_stage = "Launching Microsoft Word"

        status_var.set(
            "Regression tests passed. Launching Word..."
        )

        progress_var.set(5)

        word = win32com.client.Dispatch(
            "Word.Application"
        )

        word.Visible = False

        # ------------------------------------------------------------
        # Phase 4: Open and extract document
        # ------------------------------------------------------------
        audit_stage = "Opening source document"

        doc = word.Documents.Open(abs_input)

        audit_stage = "Extracting document paragraphs"

        (
            batch_payload,
            line_to_range,
            line_to_vale_text,
            paragraph_records,
            total_paragraphs,
        ) = build_paragraph_records(doc)

        status_var.set(
            f"Step 1/3: Extracting "
            f"{total_paragraphs} paragraphs..."
        )

        progress_var.set(33)

        # ------------------------------------------------------------
        # Phase 5: Structural validation
        # ------------------------------------------------------------
        audit_stage = "Running structural validators"

        structural_findings = add_structural_findings(
            doc=doc,
            paragraph_records=paragraph_records,
            audit_profile=audit_profile,
        )

        # ------------------------------------------------------------
        # Retaining Word COM locks for later phases
        # ------------------------------------------------------------

        # ------------------------------------------------------------
        # Phase 6: Candidate report
        # ------------------------------------------------------------
        try:
            candidate_records = [
                TextRecord(
                    index=record.index,
                    text=record.text,
                )
                for record in paragraph_records
            ]

            candidate_summaries = discover_candidates(
                database_path=ABBREVIATION_DATABASE_PATH,
                records=candidate_records,
            )

            candidate_report_path = (
                candidate_report_path_for_document(
                    audited_output_path
                )
            )

            write_candidate_report(
                summaries=candidate_summaries,
                report_path=candidate_report_path,
            )

            print(
                "Candidate review report updated: "
                f"{candidate_report_path}"
            )

        except Exception as candidate_error:
            print(
                "Candidate review report was not generated: "
                f"{candidate_error}"
            )

        # ------------------------------------------------------------
        # Phase 7: Vale execution
        # ------------------------------------------------------------
        audit_stage = "Running Vale"

        status_var.set(
            "Step 2/3: Executing Vale style scan..."
        )

        process = subprocess.run(
            [
                "vale",
                "--no-global",
                f"--config={PROJECT_ROOT / '.vale.ini'}",
                "--ext=.md",
                "--output=JSON",
            ],
            input=batch_payload,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
        )

        if process.returncode == 2:
            details = (
                process.stderr.strip()
                or process.stdout.strip()
                or "Vale returned a runtime error."
            )

            raise RuntimeError(
                f"Vale execution failed:\n{details}"
            )

        progress_var.set(66)

        if process.stdout.strip():
            vale_results = json.loads(
                process.stdout
            )

            vale_errors = vale_results.get(
                "stdin.md",
                [],
            )

        # ------------------------------------------------------------
        # Phase 8: Merge, filter, and deduplicate findings
        # ------------------------------------------------------------
        merged_errors = merge_audit_findings(
            vale_findings=vale_errors,
            structural_findings=structural_findings,
        )

        (
            context_filtered_errors,
            suppressed_findings,
        ) = filter_findings_by_context(
            findings=merged_errors,
            paragraph_records=paragraph_records,
        )

        context_filtered_errors = deduplicate_findings(
            context_filtered_errors
        )

        comment_policy = load_comment_policy(
            PROJECT_ROOT / "config" / "commentpolicy.json"
        )

        comment_plan_data = build_comment_plan(
            findings=context_filtered_errors,
            policy=comment_policy,
        )

        plan_path = write_comment_plan(
            output_base=audited_output_path,
            plan=comment_plan_data,
        )
        print(f"Comment plan written: {plan_path}")

        for disp, count in comment_plan_data["rule_dispositions"].items():
            if disp == "disabled":
                for finding in comment_plan_data["disabled_findings"]:
                    suppressed_findings[f"{finding.get('Check', 'Unknown')}:disabled_by_policy"] += 1

        errors = []
        for finding in context_filtered_errors:
            if disposition(finding, comment_policy) != "disabled":
                errors.append(finding)

        comment_metrics["candidate_comment_count"] = len(errors)

        if suppressed_findings:
            print(
                "Context-suppressed findings: "
                f"{sum(suppressed_findings.values())}"
            )
            for reason, count in sorted(suppressed_findings.items()):
                print(f"  {count} suppressed: {reason}")

        deduplicated_count = len(context_filtered_errors) - len(errors)
        if deduplicated_count > 0:
            print(
                "Duplicate findings removed before "
                f"range resolution: {deduplicated_count}"
            )

        findings_report_path = write_audit_findings_report(
            output_path=audited_output_path,
            source_path=source_path,
            audit_profile=audit_profile,
            audit_mode=audit_mode,
            findings=errors,
            suppressed_findings=suppressed_findings,
            paragraph_records=paragraph_records,
        )
        print(f"Audit findings report written: {findings_report_path}")

        audit_stage = "Writing audit summary"
        write_audit_summary(
            output_path=audited_output_path,
            audit_profile=audit_profile,
            vale_findings=vale_errors,
            structural_findings=structural_findings,
            final_findings=errors,
            suppressed_findings=suppressed_findings,
            comment_metrics=comment_metrics,
            paragraph_records=paragraph_records,
        )

        audit_stage = "Writing audit manifest"
        vale_version = ""
        for check in preflight_result["checks"]:
            if check["name"] == "Vale CLI":
                vale_version = check["details"]
                break

        content_zone_counts = Counter(
            record.content_zone for record in paragraph_records
        )

        manifest = build_audit_manifest(
            source_path=source_path,
            output_path=audited_output_path,
            audit_profile=audit_profile,
            audit_mode=audit_mode,
            output_document_created=comments_are_enabled(audit_mode),
            vale_version=vale_version,
            final_findings=errors,
            suppressed_findings=suppressed_findings,
            comment_metrics=comment_metrics,
            content_zone_counts=dict(content_zone_counts),
            preflight_result=preflight_result,
        )
        manifest_path = write_audit_manifest(
            manifest=manifest,
            output_path=audited_output_path,
        )
        print(f"Audit manifest written: {manifest_path}")

        if not comments_are_enabled(audit_mode):
            comment_metrics["skipped_comment_reasons"]["comment_insertion_disabled"] += len(errors)
            status_var.set("Complete: JSON reports written; Word comments disabled.")
            progress_var.set(100)
            messagebox.showinfo(
                "Audit Complete",
                (
                    "Audit complete. No Word comments or audited DOCX "
                    "were created.\n"
                    f"Findings report: {findings_report_path}\n"
                    f"Findings: {len(errors)}"
                ),
            )
            return

        # ------------------------------------------------------------
        # Phase 9: Preflight and Word Execution
        # ------------------------------------------------------------
        audit_stage = "Running Word execution preflights"
        status_var.set("Step 3/3: Running preflights and Word execution...")
        progress_var.set(70)

        autofix_preflight_path = run_autofix_preflight(
            source_path=source_path,
            plan_path=plan_path,
            manifest_path=manifest_path,
            output_base=audited_output_path,
            doc=doc,
        )
        print(f"Auto-fix preflight written: {autofix_preflight_path}")

        comment_preflight_path = run_comment_preflight(
            source_path=source_path,
            plan_path=plan_path,
            manifest_path=manifest_path,
            output_base=audited_output_path,
            doc=doc,
        )
        print(f"Comment preflight written: {comment_preflight_path}")

        if doc is not None:
            try:
                doc.Close(SaveChanges=False)
            except Exception:
                pass
            doc = None

        audit_stage = "Executing Operational Audit"
        progress_var.set(80)

        execution_results = execute_operational_audit(
            source_path=source_path,
            output_path=audited_output_path,
            manifest_path=manifest_path,
            autofix_preflight_path=autofix_preflight_path,
            comment_preflight_path=comment_preflight_path,
            output_base=audited_output_path,
            word_app=word,
        )

        status_var.set("Complete! Document is ready.")
        progress_var.set(100)

        val_result = json.loads(execution_results["outputverification"].read_text(encoding="utf-8"))

        messagebox.showinfo(
            "Success",
            (
                "Scan complete.\n\n"
                f"Saved to:\n{abs_output}\n\n"
                f"Auto-fixes applied: {val_result['applied_auto_fix_count']}\n"
                f"Comments inserted: {val_result['inserted_comment_count']}\n"
                f"Aggregated comments: {val_result['aggregated_comment_count']}"
            ),
        )

    except Exception as error:
        status_var.set(f"Error occurred during: {audit_stage}")
        error_details = traceback.format_exc()
        print(f"AUDIT ERROR DURING {audit_stage}:")
        print(error_details)

        messagebox.showerror(
            "Audit Error",
            (
                f"Audit failed during:\n{audit_stage}\n\n"
                f"{error}\n\n"
                "Detailed traceback was printed to the PowerShell window."
            ),
        )

    finally:
        if doc is not None:
            try:
                doc.Close(
                    SaveChanges=False
                )
            except Exception as cleanup_error:
                print(
                    "Word document cleanup warning: "
                    f"{cleanup_error}"
                )

        if word is not None:
            try:
                word.Quit()
            except Exception as cleanup_error:
                print(
                    "Word application cleanup warning: "
                    f"{cleanup_error}"
                )

        pythoncom.CoUninitialize()

        try:
            start_btn.config(state=tk.NORMAL)
        except Exception as button_error:
            print(f"GUI cleanup warning: {button_error}")
