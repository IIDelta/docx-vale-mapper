import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import pythoncom
import win32com.client
import subprocess
import json
import os
import sys
from pathlib import Path
from validators.abbreviationvalidator import (
    AbbreviationEntry,
    ParagraphRecord,
    clean_text,
    find_list_heading,
    load_policy,
    validate_first_use,
)

PROJECT_ROOT = Path(__file__).resolve().parent
REGRESSION_TEST_RUNNER = PROJECT_ROOT / "tests" / "runregressiontests.py"
ABBREVIATION_POLICY_PATH = (
    PROJECT_ROOT / "config" / "abbreviationpolicy.json"
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


def extract_abbreviation_entries_from_word(
    doc,
    heading_record: ParagraphRecord | None,
) -> list[AbbreviationEntry]:
    """
    Extract a two-column List of Abbreviations table following the
    identified heading.

    The first valid two-column table after the heading is used.
    """

    if heading_record is None:
        return []

    for table_index in range(1, doc.Tables.Count + 1):
        table = doc.Tables.Item(table_index)

        if table.Range.Start <= heading_record.range_end:
            continue

        entries: list[AbbreviationEntry] = []

        for row_index in range(1, table.Rows.Count + 1):
            row = table.Rows.Item(row_index)

            try:
                if row.Cells.Count < 2:
                    continue

                abbreviation = clean_text(
                    row.Cells.Item(1).Range.Text
                )

                definition = clean_text(
                    row.Cells.Item(2).Range.Text
                )
            except Exception:
                continue

            if not abbreviation:
                continue

            entries.append(
                AbbreviationEntry(
                    abbreviation=abbreviation,
                    definition=definition,
                    source_label=(
                        f"List of Abbreviations table row {row_index}"
                    ),
                )
            )

        if len(entries) >= 2:
            return entries

    return []


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
    """Run A4.2 structural abbreviation checks for the Word document."""

    policy = load_policy(ABBREVIATION_POLICY_PATH)

    list_heading = find_list_heading(paragraph_records)

    abbreviation_entries = extract_abbreviation_entries_from_word(
        doc=doc,
        heading_record=list_heading,
    )

    has_abbreviation_list = list_heading is not None

    return validate_first_use(
        paragraphs=paragraph_records,
        policy=policy,
        has_abbreviation_list=has_abbreviation_list,
        abbreviation_entries=abbreviation_entries,
        list_heading=list_heading,
    )


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
                errors = vale_results.get("stdin.md", [])
                errors.extend(structural_findings)

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

def build_gui():
    root = tk.Tk()
    root.title("Medical Writer - Vale Auditor")
    root.geometry("600x300")
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
    
    root.mainloop()

if __name__ == "__main__":
    build_gui()