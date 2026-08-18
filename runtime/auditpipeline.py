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

        errors = deduplicate_findings(
            context_filtered_errors
        )

        comment_metrics[
            "candidate_comment_count"
        ] = len(errors)

        if suppressed_findings:
            print(
                "Context-suppressed findings: "
                f"{sum(suppressed_findings.values())}"
            )

            for reason, count in sorted(
                suppressed_findings.items()
            ):
                print(
                    f"  {count} suppressed: {reason}"
                )

        deduplicated_count = (
            len(context_filtered_errors)
            - len(errors)
        )

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
        print(
            f"Audit findings report written: {findings_report_path}"
        )

        if not comments_are_enabled(audit_mode):
            comment_metrics["skipped_comment_reasons"][
                "comment_insertion_disabled"
            ] += len(errors)

            audit_stage = "Writing reports-only audit summary"
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

            vale_version = ""
            for check in preflight_result["checks"]:
                if check["name"] == "Vale CLI":
                    vale_version = check["details"]
                    break
            content_zone_counts = Counter(
                record.content_zone
                for record in paragraph_records
            )
            manifest = build_audit_manifest(
                source_path=source_path,
                output_path=audited_output_path,
                audit_profile=audit_profile,
                audit_mode=audit_mode,
                output_document_created=False,
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

            status_var.set(
                "Complete: JSON reports written; Word comments disabled."
            )
            progress_var.set(100)
            messagebox.showinfo(
                "Audit Complete",
                (
                    "Audit complete. No Word comments or audited DOCX "
                    "were created."
                    f"Findings report:{findings_report_path}"
                    f"Findings: {len(errors)}"
                ),
            )
            return

        # ------------------------------------------------------------
        # Phase 9: Resolve ranges and insert comments
        # ------------------------------------------------------------
        audit_stage = "Inserting Word comments"

        status_var.set(
            f"Step 3/3: Injecting {len(errors)} comments..."
        )

        total_errors = len(errors)

        def finding_start_position(
            finding: dict,
        ) -> int:
            """Return a stable location for reverse-order comments."""

            range_start = finding.get("RangeStart")

            if isinstance(range_start, int):
                return range_start

            line_number = finding.get("Line")

            paragraph_range = line_to_range.get(
                line_number
            )

            if paragraph_range:
                return paragraph_range[0]

            return 0

        ordered_errors = sorted(
            errors,
            key=finding_start_position,
            reverse=True,
        )

        # Final deduplication guard.
        #
        # Pre-range deduplication cannot catch findings that differ
        # in Vale span or source metadata but resolve to the same
        # exact Word range.
        inserted_comment_range_keys: set[
            tuple[str, int, int]
        ] = set()

        comment_budget = load_comment_budget(
            PROJECT_ROOT / "config" / "commentbudget.json"
        )
        selected_errors, deferred_findings = apply_comment_budget(
            findings=errors,
            budget=comment_budget,
        )
        for deferred_finding in deferred_findings:
            deferred_reason = deferred_finding.get(
                "DeferredReason", "comment_budget_unknown"
            )
            comment_metrics["skipped_comment_reasons"][
                deferred_reason
            ] += 1
        if comment_budget["write_full_review_queue"]:
            queue_path = write_comment_queue(
                output_path=audited_output_path,
                all_findings=errors,
                selected_findings=selected_errors,
                deferred_findings=deferred_findings,
                budget=comment_budget,
            )
            print(f"Comment review queue written: {queue_path}")
        ordered_errors = sorted(
            selected_errors,
            key=finding_start_position,
            reverse=True,
        )
        total_errors = len(ordered_errors)
        print(
            f"Comment budget: {len(errors)} candidates; "
            f"{total_errors} selected; "
            f"{len(deferred_findings)} deferred."
        )

        status_var.set(
            f"Step 3/3: Injecting {total_errors} prioritized comments "
            f"from {len(errors)} findings..."
        )
        progress_var.set(66)

        for idx, error in enumerate(
            ordered_errors,
            start=1,
        ):
            range_start = error.get("RangeStart")
            range_end = error.get("RangeEnd")

            target_range = None

            # --------------------------------------------------------
            # Exact structural ranges
            # --------------------------------------------------------
            if (
                isinstance(range_start, int)
                and isinstance(range_end, int)
                and range_end > range_start
            ):
                document_end = doc.Content.End

                safe_start = max(
                    0,
                    min(
                        range_start,
                        document_end - 1,
                    ),
                )

                safe_end = max(
                    safe_start + 1,
                    min(
                        range_end,
                        document_end,
                    ),
                )

                target_range = doc.Range(
                    safe_start,
                    safe_end,
                )

            # --------------------------------------------------------
            # Vale and paragraph-level findings
            # --------------------------------------------------------
            else:
                line_number = error.get("Line")

                paragraph_range = line_to_range.get(
                    line_number
                )

                if paragraph_range:
                    (
                        paragraph_start,
                        paragraph_end,
                    ) = paragraph_range

                    vale_text = line_to_vale_text.get(
                        line_number,
                        "",
                    )

                    match_text = str(
                        error.get("Match", "")
                    )

                    occurrence_index = (
                        vale_match_occurrence_index(
                            vale_text=vale_text,
                            match_text=match_text,
                            span=error.get("Span"),
                        )
                    )

                    word_find_range = find_vale_match_range(
                        doc=doc,
                        paragraph_start=paragraph_start,
                        paragraph_end=paragraph_end,
                        match_text=match_text,
                        occurrence_index=occurrence_index,
                    )

                    if word_find_range is not None:
                        target_range = word_find_range

                    else:
                        match_offsets = resolve_match_offsets(
                            vale_text=vale_text,
                            match_text=match_text,
                            span=error.get("Span"),
                        )

                        if match_offsets is not None:
                            (
                                match_start,
                                match_end,
                            ) = match_offsets

                            safe_start = (
                                paragraph_start
                                + match_start
                            )

                            safe_end = (
                                paragraph_start
                                + match_end
                            )

                        else:
                            vale_span_range = (
                                vale_span_to_word_range(
                                    paragraph_start=paragraph_start,
                                    paragraph_end=paragraph_end,
                                    span=error.get("Span"),
                                )
                            )

                            if vale_span_range is not None:
                                (
                                    safe_start,
                                    safe_end,
                                ) = vale_span_range

                            else:
                                document_end = doc.Content.End

                                safe_start = max(
                                    0,
                                    min(
                                        paragraph_start,
                                        document_end - 1,
                                    ),
                                )

                                safe_end = max(
                                    safe_start + 1,
                                    min(
                                        paragraph_end,
                                        document_end,
                                    ),
                                )

                        target_range = doc.Range(
                            safe_start,
                            safe_end,
                        )

            if target_range is None:
                comment_metrics[
                    "skipped_comment_reasons"
                ]["no_target_range"] += 1

                continue

            protected_ranges = protected_field_ranges(doc)
            if ranges_overlap(
                int(target_range.Start),
                int(target_range.End),
                protected_ranges,
            ):
                comment_metrics[
                    "skipped_comment_reasons"
                ]["protected_word_field"] += 1
                print(
                    "Skipping comment inside protected Word field."
                )
                continue

            severity = error.get(
                "Severity",
                "suggestion",
            ).upper()

            match_text = str(
                error.get("Match", "")
            )

            message = error.get(
                "Message",
                "",
            )

            rule_id = error.get(
                "Check",
                "Clinical.UnknownRule",
            )

            # --------------------------------------------------------
            # Final same-run resolved-range deduplication
            # --------------------------------------------------------
            resolved_range_key = (
                rule_id,
                int(target_range.Start),
                int(target_range.End),
            )

            if (
                resolved_range_key
                in inserted_comment_range_keys
            ):
                print(
                    "Skipping duplicate resolved comment: "
                    f"{rule_id} -> '{match_text}'"
                )

                comment_metrics[
                    "skipped_comment_reasons"
                ]["duplicate_resolved_range"] += 1

                continue

            # --------------------------------------------------------
            # Verified Vale anchors only
            # --------------------------------------------------------
            if (
                isinstance(error.get("Span"), list)
                and match_text
            ):
                if not vale_anchor_is_verified(
                    word_range_text=target_range.Text,
                    vale_match_text=match_text,
                ):
                    print(
                        "Skipping unverified Vale anchor: "
                        f"{rule_id} -> '{match_text}' "
                        f"(Word range: '{target_range.Text}')"
                    )

                    comment_metrics[
                        "skipped_comment_reasons"
                    ]["unverified_vale_anchor"] += 1

                    continue

            comment_text = (
                f"{rule_id} {severity} -> "
                f"'{match_text}': {message}"
            )

            try:
                new_comment = doc.Comments.Add(
                    Range=target_range,
                    Text=comment_text,
                )

                try:
                    new_comment.Author = "MVA"
                    new_comment.Initial = "MVA"
                except Exception:
                    pass

                inserted_comment_range_keys.add(
                    resolved_range_key
                )

                comment_metrics[
                    "inserted_comment_count"
                ] += 1

            except Exception as comment_error:
                print(
                    "Comment insertion skipped for "
                    f"{rule_id}: {comment_error}"
                )

                comment_metrics[
                    "skipped_comment_reasons"
                ]["word_comment_insertion_error"] += 1

            progress_var.set(
                66 + ((idx / max(1, total_errors)) * 34)
            )

        # ------------------------------------------------------------
        # Phase 10: Audit summary and output save
        # ------------------------------------------------------------
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

        audit_stage = "Saving audited document"

        status_var.set(
            "Saving audited document..."
        )

        doc.SaveAs2(abs_output)

        # ------------------------------------------------------------
        # Phase 11: Audit manifest
        # ------------------------------------------------------------
        audit_stage = "Writing audit manifest"

        vale_version = ""

        for check in preflight_result["checks"]:
            if check["name"] == "Vale CLI":
                vale_version = check["details"]
                break

        content_zone_counts = Counter(
            record.content_zone
            for record in paragraph_records
        )

        manifest = build_audit_manifest(
            source_path=source_path,
            output_path=audited_output_path,
            audit_profile=audit_profile,
            audit_mode=audit_mode,
            output_document_created=True,
            vale_version=vale_version,
            final_findings=errors,
            suppressed_findings=suppressed_findings,
            comment_metrics=comment_metrics,
            content_zone_counts=dict(
                content_zone_counts
            ),
            preflight_result=preflight_result,
        )

        manifest_path = write_audit_manifest(
            manifest=manifest,
            output_path=audited_output_path,
        )

        print(
            f"Audit manifest written: {manifest_path}"
        )

        status_var.set(
            "Complete! Document is ready."
        )

        progress_var.set(100)

        messagebox.showinfo(
            "Success",
            (
                "Scan complete.\n\n"
                f"Saved to:\n{abs_output}\n\n"
                f"Inserted comments: "
                f"{comment_metrics['inserted_comment_count']}\n"
                f"Skipped comments: "
                f"{sum(comment_metrics['skipped_comment_reasons'].values())}"
            ),
        )

    except Exception as error:
        status_var.set(
            f"Error occurred during: {audit_stage}"
        )

        error_details = traceback.format_exc()

        print(
            f"AUDIT ERROR DURING {audit_stage}:"
        )

        print(error_details)

        messagebox.showerror(
            "Audit Error",
            (
                f"Audit failed during:\n"
                f"{audit_stage}\n\n"
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
            start_btn.config(
                state=tk.NORMAL
            )
        except Exception as button_error:
            print(
                "GUI cleanup warning: "
                f"{button_error}"
            )

