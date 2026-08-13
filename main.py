import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from typing import Any
import threading
import pythoncom
import win32com.client
import subprocess
import json
import os
import sys
import re
from pathlib import Path
from validators.abbreviationvalidator import (
    AbbreviationEntry,
    ParagraphRecord,
    clean_text,
    find_list_heading,
    normalize_abbreviation,
    validate_deprecated_terms,
    validate_first_use,
)
from abbreviations.auditbridge import build_effective_policy
from validators.findingmerge import merge_audit_findings
from abbreviations.candidatefinder import (
    TextRecord,
    discover_candidates,
    write_report as write_candidate_report,
)
from abbreviations.reviewwindow import open_review_window
from abbreviations.reportpaths import (
    candidate_report_path_for_document,
)


PROJECT_ROOT = Path(__file__).resolve().parent

REGRESSION_TEST_RUNNER = PROJECT_ROOT / "tests" / "runregressiontests.py"

ABBREVIATION_POLICY_PATH = (
    PROJECT_ROOT / "config" / "abbreviationpolicy.json"
)

ABBREVIATION_DATABASE_PATH = (
    PROJECT_ROOT / "data" / "abbreviations.sqlite"
)


def run_regression_gate() -> None:
    """Run all approved Vale fixtures before auditing a live document."""

    command = [
        sys.executable,
        str(REGRESSION_TEST_RUNNER),
    ]

    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode != 0:
        output = process.stdout.strip()
        errors = process.stderr.strip()

        details = "\n\n".join(
            value
            for value in [output, errors]
            if value
        )

        raise RuntimeError(
            "The Takeda Vale regression suite failed. "
            "The live-document audit was not started.\n\n"
            f"{details}"
        )


ABBREVIATION_CELL_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9+*'’:/.\-]{0,24}$"
)


def extract_entries_from_table(
    table,
    table_index: int,
) -> list[AbbreviationEntry]:
    """
    Extract potential abbreviation-definition pairs from a Word table.

    The first nonempty cell is treated as the abbreviation, and the
    second nonempty cell is treated as its definition. This handles
    ordinary two-column tables and many merged-cell layouts.
    """

    entries: list[AbbreviationEntry] = []

    for row_index in range(1, table.Rows.Count + 1):
        row = table.Rows.Item(row_index)
        cell_values: list[str] = []

        try:
            cell_count = row.Cells.Count
        except Exception:
            continue

        for cell_index in range(1, cell_count + 1):
            try:
                cell_value = clean_text(
                    row.Cells.Item(cell_index).Range.Text
                )
            except Exception:
                cell_value = ""

            # Preserve blank cells. A blank second cell is meaningful because
            # it represents a missing abbreviation definition.
            cell_values.append(cell_value)

        if len(cell_values) < 2:
            continue

        abbreviation = cell_values[0].strip()
        definition = cell_values[1].strip()

        # Ignore rows that have no abbreviation in the first column.
        if not abbreviation:
            continue

        abbreviation_upper = abbreviation.upper()

        if (
            normalize_abbreviation(abbreviation) in {
                "abbreviation",
                "abbreviations",
                "term",
                "terms",
            }
            or "LIST OF ABBREVIATIONS" in abbreviation_upper
        ):
            continue

        entries.append(
            AbbreviationEntry(
                abbreviation=abbreviation,
                definition=definition,
                source_label=(
                    f"List of Abbreviations table {table_index}, "
                    f"row {row_index}"
                ),
            )
        )

    return entries


def score_abbreviation_table(
    entries: list[AbbreviationEntry],
    tracked_abbreviations: set[str],
) -> int:
    """
    Score a candidate Word table.

    High scores indicate that a table resembles a List of Abbreviations:
    - multiple short abbreviation-like first-column values;
    - populated definition cells;
    - matches to tracked abbreviations such as AE, DLT, LFT, or MedDRA.
    """

    if len(entries) < 2:
        return 0

    abbreviation_like_count = sum(
        bool(
            ABBREVIATION_CELL_PATTERN.fullmatch(
                entry.abbreviation.strip()
            )
        )
        for entry in entries
    )

    definition_count = sum(
        bool(entry.definition.strip())
        for entry in entries
    )

    tracked_match_count = sum(
        normalize_abbreviation(entry.abbreviation)
        in tracked_abbreviations
        for entry in entries
    )

    return (
        abbreviation_like_count * 10
        + definition_count * 2
        + tracked_match_count * 100
    )


def extract_abbreviation_entries_from_word(
    doc,
    heading_record: ParagraphRecord | None,
    policy: dict,
) -> list[AbbreviationEntry]:
    """
    Locate and extract the most likely List of Abbreviations table.

    Rather than using the first table after the heading, this function
    evaluates every later table and chooses the nearest high-confidence
    abbreviation-definition table.
    """

    if heading_record is None:
        return []

    tracked_abbreviations = {
        normalize_abbreviation(abbreviation)
        for abbreviation in policy.get(
            "tracked_abbreviations",
            {},
        )
    }

    candidates: list[
        tuple[int, int, int, list[AbbreviationEntry]]
    ] = []


    for table_index in range(1, doc.Tables.Count + 1):
        table = doc.Tables.Item(table_index)

        # Skip only tables that end before the List of Abbreviations heading.
        #
        # Important: a List of Abbreviations heading may be inside the same
        # Word table as its abbreviation rows. In that case, table.Range.Start
        # occurs before the heading, but table.Range.End occurs after it.
        if table.Range.End <= heading_record.range_end:
            continue


        entries = extract_entries_from_table(
            table=table,
            table_index=table_index,
        )

        score = score_abbreviation_table(
            entries=entries,
            tracked_abbreviations=tracked_abbreviations,
        )

        if score == 0:
            continue

        if (
            table.Range.Start
            <= heading_record.range_start
            <= table.Range.End
        ):
            # The heading is inside this table.
            distance_from_heading = 0
        else:
            # The table follows the heading in the document body.
            distance_from_heading = max(
                0,
                table.Range.Start - heading_record.range_end,
            )

        preview = ", ".join(
            entry.abbreviation
            for entry in entries[:10]
        )

        print(
            f"A4.2 candidate table {table_index}; "
            f"start={table.Range.Start}; "
            f"end={table.Range.End}; "
            f"score={score}; "
            f"entries={len(entries)}; "
            f"preview=[{preview}]"
        )

        candidates.append(
            (
                score,
                distance_from_heading,
                table_index,
                entries,
            )
        )

    if not candidates:
        print(
            "A4.2: List of Abbreviations heading found, "
            "but no candidate abbreviation table was extracted."
        )
        return []

    # Highest structural score wins. If scores tie, choose the table
    # nearest to the List of Abbreviations heading.
    candidates.sort(
        key=lambda candidate: (
            -candidate[0],
            candidate[1],
        )
    )

    best_score, best_distance, best_table_index, best_entries = (
        candidates[0]
    )

    preview = ", ".join(
        entry.abbreviation
        for entry in best_entries[:10]
    )

    print(
        "A4.2: Selected List of Abbreviations "
        f"table {best_table_index}; "
        f"score={best_score}; "
        f"distance={best_distance}; "
        f"entries={len(best_entries)}; "
        f"preview=[{preview}]"
    )

    return best_entries


def build_paragraph_records(doc):
    """
    Extract body paragraphs, retain Word location metadata, and build
    the Vale batch payload and line-to-paragraph map.
    """

    batch_parts: list[str] = []
    line_to_paragraph: dict[int, Any] = {}
    paragraph_records: list[ParagraphRecord] = []

    current_line = 1
    total_paragraphs = doc.Paragraphs.Count

    for index, paragraph in enumerate(doc.Paragraphs, start=1):
        raw_text = paragraph.Range.Text
        normalized_text = clean_text(raw_text)

        if not normalized_text:
            continue

        try:
            style_name = paragraph.Style.NameLocal
        except Exception:
            style_name = ""

        record = ParagraphRecord(
            index=index,
            line=current_line,
            text=normalized_text,
            style_name=style_name,
            range_start=paragraph.Range.Start,
            range_end=paragraph.Range.End,
        )

        paragraph_records.append(record)
        line_to_paragraph[current_line] = paragraph
        batch_parts.append(normalized_text)

        current_line += 2

    batch_payload = "\n\n".join(batch_parts)

    return (
        batch_payload,
        line_to_paragraph,
        paragraph_records,
        total_paragraphs,
    )


def add_structural_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """Run structural abbreviation checks for the Word document."""

    policy = build_effective_policy(
        base_policy_path=ABBREVIATION_POLICY_PATH,
        database_path=ABBREVIATION_DATABASE_PATH,
    )

    list_heading = find_list_heading(paragraph_records)

    abbreviation_entries = extract_abbreviation_entries_from_word(
        doc=doc,
        heading_record=list_heading,
        policy=policy,
    )

    has_abbreviation_list = list_heading is not None

    findings = validate_first_use(
        paragraphs=paragraph_records,
        policy=policy,
        has_abbreviation_list=has_abbreviation_list,
        abbreviation_entries=abbreviation_entries,
        list_heading=list_heading,
    )

    findings.extend(
        validate_deprecated_terms(
            paragraphs=paragraph_records,
            deprecated_terms=policy.get(
                "deprecated_terms",
                {},
            ),
        )
    )

    return findings


# --- THE CORE ENGINE ---
def run_scan_thread(docx_path, output_path, status_var, progress_var, start_btn):
    """This runs in the background so the GUI doesn't freeze."""
    # 1. We MUST initialize COM for this specific background thread
    pythoncom.CoInitialize() 

    word = None
    doc = None
    
    try:
        status_var.set("Running approved rule regression tests...")
        progress_var.set(0)

        run_regression_gate()

        status_var.set("Regression tests passed. Launching Word...")
        progress_var.set(5)

        abs_input = os.path.abspath(docx_path)
        abs_output = os.path.abspath(output_path)
        
        status_var.set("Launching Word in the background...")
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        try:
            doc = word.Documents.Open(abs_input)
            (
                batch_payload,
                line_to_para_object,
                paragraph_records,
                total_paragraphs,
            ) = build_paragraph_records(doc)

            status_var.set(
                f"Step 1/3: Extracting {total_paragraphs} paragraphs..."
            )
            progress_var.set(33)

            structural_findings = add_structural_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            )

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
                        Path(abs_output)
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

                # Candidate reporting is useful but must not block the primary
                # Word audit if a noncritical reporting error occurs.
                print(
                    "Candidate review report was not generated: "
                    f"{candidate_error}"
                )

            status_var.set("Step 2/3: Executing Vale style scan...")
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
                encoding='utf-8'
            )
            progress_var.set(66) # Scan complete, bump bar to 66%
            
            if process.stdout.strip():
                vale_results = json.loads(process.stdout)
                vale_errors = vale_results.get("stdin.md", [])
                
                errors = merge_audit_findings(
                    vale_findings=vale_errors,
                    structural_findings=structural_findings,
                )


                status_var.set(
                    f"Step 3/3: Injecting {len(errors)} comments..."
                )

                total_errors = len(errors)
                
                if total_errors > 0:
                    for idx, error in enumerate(errors, start=1):
                        vale_line = error.get('Line')
                        target_paragraph = line_to_para_object.get(vale_line)
                        
                        if target_paragraph:
                            severity = error.get('Severity', 'suggestion').upper()
                            match_text = error.get('Match', '')
                            message = error.get('Message', '')
                            rule_id = error.get("Check", "Clinical.UnknownRule")

                            comment_text = (
                                f"{rule_id} {severity} -> "
                                f"'{match_text}': {message}"
)
                            
                            doc.Comments.Add(Range=target_paragraph.Range, Text=comment_text)
                            
                        # Update progress for the final 33% of the bar
                        progress_var.set(66 + ((idx / total_errors) * 34))
                        
            status_var.set("Saving audited document...")
            doc.SaveAs2(abs_output)
            status_var.set("Complete! Document is ready.")
            progress_var.set(100)
            messagebox.showinfo("Success", f"Scan complete.\nSaved to:\n{abs_output}")
            
        finally:
            doc.Close(SaveChanges=False)
            word.Quit()
            
    except Exception as e:
        status_var.set("Error occurred during scan.")
        messagebox.showerror("Error", str(e))
    finally:
        # 2. We MUST uninitialize COM before the thread dies
        pythoncom.CoUninitialize()
        # Re-enable the start button
        start_btn.config(state=tk.NORMAL)

# --- THE GUI BUILDER ---
def select_input(entry_widget, output_entry_widget):
    filepath = filedialog.askopenfilename(filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)
        
        # Auto-generate the output filepath
        directory, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        out_filepath = os.path.join(directory, f"{name}_AUDITED{ext}")
        
        output_entry_widget.delete(0, tk.END)
        output_entry_widget.insert(0, out_filepath)

def select_output(entry_widget):
    filepath = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)

def start_process(input_entry, output_entry, status_var, progress_var, start_btn):
    in_path = input_entry.get()
    out_path = output_entry.get()
    
    if not in_path or not out_path:
        messagebox.showwarning("Missing Files", "Please select both input and output files.")
        return
        
    if not os.path.exists(in_path):
        messagebox.showerror("File Not Found", "The selected input file does not exist.")
        return

    # Disable button to prevent multiple clicks
    start_btn.config(state=tk.DISABLED)
    status_var.set("Starting...")
    progress_var.set(0)
    
    # Launch the background thread
    thread = threading.Thread(
        target=run_scan_thread, 
        args=(in_path, out_path, status_var, progress_var, start_btn),
        daemon=True
    )
    thread.start()


def open_review_for_selected_output(
    parent: tk.Misc,
    output_entry,
) -> None:
    """
    Open the candidate review window only for the selected audit output.

    The review window must never silently display a stale report from
    a different document.
    """

    output_value = output_entry.get().strip()

    if not output_value:
        messagebox.showinfo(
            "Abbreviation Review",
            (
                "Select a document and run an audit before opening "
                "the abbreviation review window."
            ),
            parent=parent,
        )
        return

    output_path = Path(output_value)

    report_path = candidate_report_path_for_document(
        output_path
    )

    if not report_path.is_file():
        messagebox.showinfo(
            "Abbreviation Review",
            (
                "No abbreviation candidate report exists for this "
                "audit output yet.\n\n"
                "Run the audit first, then open the review window."
            ),
            parent=parent,
        )
        return

    open_review_window(
        parent=parent,
        report_path=report_path,
        database_path=ABBREVIATION_DATABASE_PATH,
    )



def build_gui():
    root = tk.Tk()
    root.title("Medical Writer - Vale Auditor")
    root.geometry("600x350")
    root.resizable(False, False)
    
    # Padding and layout configuration
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Input Row
    ttk.Label(frame, text="Target Protocol (.docx):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    input_entry = ttk.Entry(frame, width=50)
    input_entry.grid(row=0, column=1, padx=10, pady=(0, 5))
    ttk.Button(frame, text="Browse", command=lambda: select_input(input_entry, output_entry)).grid(row=0, column=2, pady=(0, 5))
    
    # Output Row
    ttk.Label(frame, text="Output Audited File:").grid(row=1, column=0, sticky=tk.W, pady=10)
    output_entry = ttk.Entry(frame, width=50)
    output_entry.grid(row=1, column=1, padx=10, pady=10)
    ttk.Button(frame, text="Browse", command=lambda: select_output(output_entry)).grid(row=1, column=2, pady=10)
    
    # Progress and Status
    status_var = tk.StringVar()
    status_var.set("Ready.")
    ttk.Label(frame, textvariable=status_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
    
    # Action Button
    start_btn = ttk.Button(
        frame, 
        text="Run Audit", 
        command=lambda: start_process(input_entry, output_entry, status_var, progress_var, start_btn)
    )
    start_btn.grid(row=4, column=0, columnspan=3, pady=20)

    review_btn = ttk.Button(
        frame,
        text="Review Abbreviations",
        command=lambda: open_review_for_selected_output(
            parent=root,
            output_entry=output_entry,
        ),
    )

    review_btn.grid(
        row=5,
        column=0,
        columnspan=3,
        pady=(0, 10),
    )

    root.mainloop()

if __name__ == "__main__":
    build_gui()