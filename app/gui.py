"""
Purpose:
    Build and manage the Tkinter user interface.

Inputs:
    User-selected document paths, audit mode, and audit options.

Outputs:
    Starts application workflow and displays progress/status.

Must not:
    Resolve Word ranges.
    Apply auto-fixes.
    Insert Word comments.
    Implement Style Guide rules.
"""

import os
import tkinter as tk
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)

from abbreviations.reportpaths import (
    candidate_report_path_for_document,
)
from abbreviations.reviewwindow import (
    open_review_window,
)
from app.settings import (
    ABBREVIATION_DATABASE_PATH,
)
from app.workflow import (
    start_process,
)


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
    """
    Build and display the main audit application window.
    """

    root = tk.Tk()

    root.title("Medical Writer - Vale Auditor")
    root.geometry("650x470")
    root.resizable(False, False)

    frame = ttk.Frame(
        root,
        padding="20",
    )

    frame.pack(
        fill=tk.BOTH,
        expand=True,
    )

    frame.columnconfigure(
        1,
        weight=1,
    )

    # ------------------------------------------------------------
    # Input document
    # ------------------------------------------------------------
    ttk.Label(
        frame,
        text="Target Protocol (.docx):",
    ).grid(
        row=0,
        column=0,
        sticky=tk.W,
        pady=(0, 5),
    )

    input_entry = ttk.Entry(
        frame,
        width=55,
    )

    input_entry.grid(
        row=0,
        column=1,
        sticky=tk.EW,
        padx=10,
        pady=(0, 5),
    )

    ttk.Button(
        frame,
        text="Browse",
        command=lambda: select_input(
            input_entry,
            output_entry,
        ),
    ).grid(
        row=0,
        column=2,
        pady=(0, 5),
    )

    # ------------------------------------------------------------
    # Output document
    # ------------------------------------------------------------
    ttk.Label(
        frame,
        text="Report Base / Audited DOCX:",
    ).grid(
        row=1,
        column=0,
        sticky=tk.W,
        pady=10,
    )

    output_entry = ttk.Entry(
        frame,
        width=55,
    )

    output_entry.grid(
        row=1,
        column=1,
        sticky=tk.EW,
        padx=10,
        pady=10,
    )

    ttk.Button(
        frame,
        text="Browse",
        command=lambda: select_output(
            output_entry
        ),
    ).grid(
        row=1,
        column=2,
        pady=10,
    )

    # ------------------------------------------------------------
    # Audit profile (Hardcoded for Operational Audit)
    # ------------------------------------------------------------
    audit_profile_var = tk.StringVar(
        value="Operational Audit"
    )
    insert_comments_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        frame,
        text="Create audited DOCX with Word comments (slow)",
        variable=insert_comments_var,
    ).grid(
        row=4,
        column=1,
        sticky=tk.W,
        padx=10,
        pady=(0, 5),
    )
    ttk.Label(
        frame,
        text="Unchecked: writes JSON reports only; does not save a DOCX.",
        wraplength=440,
    ).grid(
        row=5,
        column=1,
        sticky=tk.W,
        padx=10,
        pady=(0, 8),
    )

    # ------------------------------------------------------------
    # Status and progress
    # ------------------------------------------------------------
    status_var = tk.StringVar()
    status_var.set("Ready.")

    ttk.Label(
        frame,
        textvariable=status_var,
    ).grid(
        row=6,
        column=0,
        columnspan=3,
        sticky=tk.W,
        pady=(15, 5),
    )

    progress_var = tk.DoubleVar()

    progress_bar = ttk.Progressbar(
        frame,
        variable=progress_var,
        maximum=100,
    )

    progress_bar.grid(
        row=7,
        column=0,
        columnspan=3,
        sticky=(tk.W, tk.E),
        pady=5,
    )

    # ------------------------------------------------------------
    # Audit action
    # ------------------------------------------------------------
    start_btn = ttk.Button(
        frame,
        text="Run Audit",
        command=lambda: start_process(
            input_entry,
            output_entry,
            status_var,
            progress_var,
            start_btn,
            audit_profile_var,
            insert_comments_var,
        ),
    )

    start_btn.grid(
        row=8,
        column=0,
        columnspan=3,
        pady=(20, 10),
    )

    # ------------------------------------------------------------
    # Abbreviation review
    # ------------------------------------------------------------
    review_btn = ttk.Button(
        frame,
        text="Review Abbreviations",
        command=lambda: open_review_for_selected_output(
            parent=root,
            output_entry=output_entry,
        ),
    )

    review_btn.grid(
        row=9,
        column=0,
        columnspan=3,
        pady=(0, 10),
    )

    root.mainloop()
