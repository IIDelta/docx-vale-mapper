import threading
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

from app.settings import (
    PROJECT_ROOT,
)
from runtime.auditmode import (
    REPORTS_ONLY,
    WORD_COMMENTS,
)
from runtime.auditpipeline import (
    run_scan_thread,
)
from validators.auditprofile import (
    normalize_audit_profile,
)



def start_process(
    input_entry,
    output_entry,
    status_var,
    progress_var,
    start_btn,
    audit_profile_var,
    insert_comments_var,
):
    """
    Validate user input and launch the audit worker.

    This function prevents source overwrite, validates DOCX paths,
    prompts before overwriting an existing output, and passes the
    selected audit profile to the worker thread.
    """

    in_path = input_entry.get().strip()
    out_path = output_entry.get().strip()

    if not in_path or not out_path:
        messagebox.showwarning(
            "Missing Files",
            "Please select both input and output files.",
        )
        return

    source_path = Path(in_path)
    output_path = Path(out_path)

    if not source_path.is_file():
        messagebox.showerror(
            "File Not Found",
            (
                "The selected input file does not exist:\n\n"
                f"{source_path}"
            ),
        )
        return

    if source_path.suffix.casefold() != ".docx":
        messagebox.showerror(
            "Invalid Input",
            (
                "The input file must be a DOCX document.\n\n"
                f"Selected file: {source_path.name}"
            ),
        )
        return

    if output_path.suffix.casefold() != ".docx":
        messagebox.showerror(
            "Invalid Output",
            (
                "The output file must use the .docx extension.\n\n"
                f"Selected file: {output_path.name}"
            ),
        )
        return

    normalized_source_path = str(
        source_path.resolve()
    ).casefold()

    normalized_output_path = str(
        output_path.resolve()
    ).casefold()

    if normalized_source_path == normalized_output_path:
        messagebox.showerror(
            "Invalid Output",
            (
                "The output file must be different from the "
                "source document.\n\n"
                "The source document will never be overwritten."
            ),
        )
        return

    if insert_comments_var.get() and output_path.exists():
        overwrite_confirmed = messagebox.askyesno(
            "Overwrite Existing Output?",
            (
                "An output file already exists:\n\n"
                f"{output_path}\n\n"
                "The existing output file will be replaced. "
                "The source document will not be changed.\n\n"
                "Continue?"
            ),
        )

        if not overwrite_confirmed:
            status_var.set(
                "Audit cancelled. Existing output was not overwritten."
            )
            return

    audit_profile = normalize_audit_profile(
        audit_profile_var.get()
    )
    audit_mode = (
        WORD_COMMENTS
        if insert_comments_var.get()
        else REPORTS_ONLY
    )

    start_btn.config(state=tk.DISABLED)

    status_var.set(
        f"Starting {audit_profile} audit..."
    )

    progress_var.set(0)

    thread = threading.Thread(
        target=run_scan_thread,
        args=(
            str(source_path),
            str(output_path),
            status_var,
            progress_var,
            start_btn,
            audit_profile,
            audit_mode,
        ),
        daemon=True,
    )

    thread.start()
