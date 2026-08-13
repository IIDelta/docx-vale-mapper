from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any
from abbreviations.legacyimport import normalize_token
from abbreviations.reviewactions import apply_local_decision
from abbreviations.listgenerator import (
    build_generation_plan,
    generate_list_document,
    load_candidate_report as load_generation_candidate_report,
    write_generation_report,
)


BUCKET_ORDER = [
    "deprecated",
    "ambiguous",
    "likely_unknown",
    "possible_unknown",
    "reviewed_candidate",
    "known_expand",
    "known_list_only",
    "protected",
    "ignored",
]


TREE_COLUMNS = (
    "bucket",
    "token",
    "count",
    "first_paragraph",
    "registry_status",
    "action",
    "definition",
)


def load_candidates(
    report_path: Path,
) -> list[dict[str, Any]]:
    """Load candidates from a candidate discovery JSON report."""

    with report_path.open(
        encoding="utf-8",
    ) as input_file:
        payload = json.load(input_file)

    candidates = payload.get("candidates", [])

    if not isinstance(candidates, list):
        raise ValueError(
            "Candidate report contains an invalid candidates value."
        )

    return candidates


def candidate_sort_key(
    candidate: dict[str, Any],
) -> tuple[int, str]:
    """Sort candidate records by review priority, then token."""

    bucket = candidate.get("review_bucket", "")

    try:
        priority = BUCKET_ORDER.index(bucket)
    except ValueError:
        priority = len(BUCKET_ORDER)

    return (
        priority,
        candidate.get("token", "").casefold(),
    )


def filter_candidates(
    candidates: list[dict[str, Any]],
    selected_bucket: str,
    search_text: str,
) -> list[dict[str, Any]]:
    """Filter candidates by review bucket and token/definition search."""

    normalized_search = search_text.strip().casefold()

    filtered_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        bucket = candidate.get("review_bucket", "")

        if (
            selected_bucket != "All"
            and bucket != selected_bucket
        ):
            continue

        resolution = candidate.get("resolution") or {}

        searchable_text = " ".join(
            [
                candidate.get("token", ""),
                candidate.get("review_bucket", ""),
                resolution.get("status", ""),
                resolution.get("preferred_definition", ""),
                resolution.get("replacement_token", ""),
                resolution.get("notes", ""),
            ]
        ).casefold()

        if (
            normalized_search
            and normalized_search not in searchable_text
        ):
            continue

        filtered_candidates.append(candidate)

    return sorted(
        filtered_candidates,
        key=candidate_sort_key,
    )


def review_bucket_for_resolution(
    resolution: dict[str, Any],
    occurrence_count: int,
    inline_definition_count: int,
) -> str:
    """Return the display bucket for an updated registry resolution."""

    if not resolution.get("found", False):
        if inline_definition_count > 0 or occurrence_count >= 2:
            return "likely_unknown"

        return "possible_unknown"

    status = resolution.get("status", "")

    if status == "approved_expand":
        return "known_expand"

    if status == "approved_no_expand":
        return "protected"

    if status == "approved_list_only":
        return "known_list_only"

    if status == "deprecated":
        return "deprecated"

    if status == "ambiguous":
        return "ambiguous"

    if status == "reviewed_candidate":
        return "reviewed_candidate"

    if status == "ignored":
        return "ignored"

    return "possible_unknown"


def confidence_for_resolution(
    resolution: dict[str, Any],
    occurrence_count: int,
    inline_definition_count: int,
) -> str:
    """Return display confidence for an updated registry resolution."""

    if resolution.get("found", False):
        return "high"

    if inline_definition_count > 0 or occurrence_count >= 2:
        return "likely"

    return "possible"


def update_candidate_payload(
    payload: dict[str, Any],
    token: str,
    resolution: dict[str, Any],
) -> bool:
    """
    Update one candidate in an in-memory candidate report payload.

    Returns True when the candidate was found and updated.
    """

    normalized_token = normalize_token(token)

    for candidate in payload.get("candidates", []):
        if (
            normalize_token(
                candidate.get("token", "")
            )
            != normalized_token
        ):
            continue

        occurrence_count = int(
            candidate.get("count", 0)
        )

        inline_definition_count = int(
            candidate.get(
                "inline_definition_count",
                0,
            )
        )

        candidate["resolution"] = resolution

        candidate["review_bucket"] = (
            review_bucket_for_resolution(
                resolution=resolution,
                occurrence_count=occurrence_count,
                inline_definition_count=inline_definition_count,
            )
        )

        candidate["confidence"] = confidence_for_resolution(
            resolution=resolution,
            occurrence_count=occurrence_count,
            inline_definition_count=inline_definition_count,
        )

        return True

    return False


def update_candidate_report_resolution(
    report_path: Path,
    token: str,
    resolution: dict[str, Any],
) -> bool:
    """
    Update one candidate report entry after a local GUI decision.

    The candidate report remains tied to the audited document, but its
    resolution metadata is refreshed immediately after the decision.
    """

    with report_path.open(
        encoding="utf-8",
    ) as input_file:
        payload = json.load(input_file)

    updated = update_candidate_payload(
        payload=payload,
        token=token,
        resolution=resolution,
    )

    if not updated:
        return False

    temporary_path = report_path.with_suffix(
        report_path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            payload,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")

    temporary_path.replace(report_path)

    return True


def format_generation_blockers(
    blockers,
) -> str:
    """Format list-generation blockers for a user-facing dialog."""

    if not blockers:
        return ""

    return "\n".join(
        f"• {blocker.token}: {blocker.message}"
        for blocker in blockers
    )


class AbbreviationReviewWindow(tk.Toplevel):
    """Read-only candidate review window."""

    def __init__(
        self,
        parent: tk.Misc,
        report_path: Path,
        database_path: Path,
    ) -> None:
        super().__init__(parent)

        self.report_path = report_path
        self.database_path = database_path
        self.candidates: list[dict[str, Any]] = []
        self.visible_candidates: dict[str, dict[str, Any]] = {}

        self.title("Abbreviation Review")
        self.geometry("1150x680")
        self.minsize(900, 560)

        self.bucket_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar(value="")
        self.summary_var = tk.StringVar(
            value="No candidate report loaded."
        )
        self.decision_var = tk.StringVar(value="")
        self.definition_var = tk.StringVar(value="")
        self.replacement_var = tk.StringVar(value="")
        self.action_status_var = tk.StringVar(
            value="Select a candidate to create a local decision."
        )
        self.build_window()
        self.load_report()

    def build_window(self) -> None:
        """Build the review-window controls."""

        outer_frame = ttk.Frame(
            self,
            padding="12",
        )
        outer_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        control_frame = ttk.Frame(outer_frame)
        control_frame.pack(
            fill=tk.X,
            pady=(0, 8),
        )

        ttk.Label(
            control_frame,
            text="Review bucket:",
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        bucket_values = [
            "All",
            *BUCKET_ORDER,
        ]

        self.bucket_filter = ttk.Combobox(
            control_frame,
            textvariable=self.bucket_var,
            values=bucket_values,
            state="readonly",
            width=22,
        )

        self.bucket_filter.pack(
            side=tk.LEFT,
            padx=(0, 16),
        )

        self.bucket_filter.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_tree(),
        )

        ttk.Label(
            control_frame,
            text="Search:",
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        search_entry = ttk.Entry(
            control_frame,
            textvariable=self.search_var,
            width=36,
        )

        search_entry.pack(
            side=tk.LEFT,
            padx=(0, 8),
        )

        search_entry.bind(
            "<KeyRelease>",
            lambda _event: self.refresh_tree(),
        )

        ttk.Button(
            control_frame,
            text="Reload Report",
            command=self.load_report,
        ).pack(
            side=tk.RIGHT,
        )

        ttk.Label(
            outer_frame,
            textvariable=self.summary_var,
        ).pack(
            fill=tk.X,
            pady=(0, 8),
        )

        table_frame = ttk.Frame(outer_frame)
        table_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=TREE_COLUMNS,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "bucket": "Review Bucket",
            "token": "Candidate",
            "count": "Count",
            "first_paragraph": "First Paragraph",
            "registry_status": "Registry Status",
            "action": "Recommended Action",
            "definition": "Preferred Definition",
        }

        widths = {
            "bucket": 150,
            "token": 110,
            "count": 55,
            "first_paragraph": 105,
            "registry_status": 145,
            "action": 220,
            "definition": 310,
        }

        for column in TREE_COLUMNS:
            self.tree.heading(
                column,
                text=headings[column],
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=50,
                stretch=True,
            )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.HORIZONTAL,
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.show_selected_details,
        )

        details_frame = ttk.LabelFrame(
            outer_frame,
            text="Candidate Details",
            padding="8",
        )

        details_frame.pack(
            fill=tk.BOTH,
            expand=False,
            pady=(10, 0),
        )

        self.details_text = tk.Text(
            details_frame,
            height=10,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )

        details_scrollbar = ttk.Scrollbar(
            details_frame,
            orient=tk.VERTICAL,
            command=self.details_text.yview,
        )

        self.details_text.configure(
            yscrollcommand=details_scrollbar.set,
        )

        self.details_text.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        details_scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )
        action_frame = ttk.LabelFrame(
            outer_frame,
            text="Local Registry Decision",
            padding="8",
        )

        action_frame.pack(
            fill=tk.X,
            pady=(10, 0),
        )

        decision_values = [
            "",
            "approved_expand",
            "approved_no_expand",
            "approved_list_only",
            "reviewed_candidate",
            "deprecated",
            "ambiguous",
            "ignored",
        ]

        ttk.Label(
            action_frame,
            text="Decision:",
        ).grid(
            row=0,
            column=0,
            sticky=tk.W,
            padx=(0, 6),
            pady=(0, 6),
        )

        self.decision_combo = ttk.Combobox(
            action_frame,
            textvariable=self.decision_var,
            values=decision_values,
            state="readonly",
            width=24,
        )

        self.decision_combo.grid(
            row=0,
            column=1,
            sticky=tk.W,
            padx=(0, 16),
            pady=(0, 6),
        )

        ttk.Label(
            action_frame,
            text="Definition:",
        ).grid(
            row=0,
            column=2,
            sticky=tk.W,
            padx=(0, 6),
            pady=(0, 6),
        )

        self.definition_entry = ttk.Entry(
            action_frame,
            textvariable=self.definition_var,
            width=48,
        )

        self.definition_entry.grid(
            row=0,
            column=3,
            sticky=tk.EW,
            pady=(0, 6),
        )

        ttk.Label(
            action_frame,
            text="Replacement:",
        ).grid(
            row=1,
            column=0,
            sticky=tk.W,
            padx=(0, 6),
        )

        self.replacement_entry = ttk.Entry(
            action_frame,
            textvariable=self.replacement_var,
            width=24,
        )

        self.replacement_entry.grid(
            row=1,
            column=1,
            sticky=tk.W,
            padx=(0, 16),
        )

        ttk.Label(
            action_frame,
            text="Notes:",
        ).grid(
            row=1,
            column=2,
            sticky=tk.NW,
            padx=(0, 6),
        )

        self.decision_notes_text = tk.Text(
            action_frame,
            height=3,
            wrap=tk.WORD,
        )

        self.decision_notes_text.grid(
            row=1,
            column=3,
            sticky=tk.EW,
        )

        self.apply_decision_button = ttk.Button(
            action_frame,
            text="Apply Local Decision",
            command=self.apply_selected_decision,
        )

        self.apply_decision_button.grid(
            row=2,
            column=0,
            sticky=tk.W,
            pady=(8, 0),
        )

        self.generate_list_button = ttk.Button(
            action_frame,
            text="Generate List",
            command=self.generate_list,
        )

        self.generate_list_button.grid(
            row=2,
            column=1,
            sticky=tk.W,
            padx=(8, 0),
            pady=(8, 0),
        )

        action_frame.columnconfigure(
            3,
            weight=1,
        )


    def load_report(self) -> None:
        """Load the latest candidate report from disk."""

        if not self.report_path.is_file():
            self.candidates = []
            self.refresh_tree()

            self.summary_var.set(
                "No candidate report found. Run an audit first."
            )

            return

        try:
            self.candidates = load_candidates(
                self.report_path
            )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            self.candidates = []
            self.refresh_tree()

            messagebox.showerror(
                "Candidate Report Error",
                str(error),
                parent=self,
            )

            return

        self.refresh_tree()

    def refresh_tree(self) -> None:
        """Apply current filters and repopulate the candidate table."""

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        self.visible_candidates = {}

        filtered_candidates = filter_candidates(
            candidates=self.candidates,
            selected_bucket=self.bucket_var.get(),
            search_text=self.search_var.get(),
        )

        total_count = len(self.candidates)
        visible_count = len(filtered_candidates)

        self.summary_var.set(
            f"Showing {visible_count} of {total_count} candidate(s). "
            f"Report: {self.report_path.name}"
        )

        for candidate in filtered_candidates:
            resolution = candidate.get("resolution") or {}

            item_id = self.tree.insert(
                "",
                tk.END,
                values=(
                    candidate.get("review_bucket", ""),
                    candidate.get("token", ""),
                    candidate.get("count", 0),
                    candidate.get(
                        "first_paragraph_index",
                        "",
                    ),
                    resolution.get("status", "unknown"),
                    resolution.get(
                        "enforcement_action",
                        "candidate_review",
                    ),
                    resolution.get(
                        "preferred_definition",
                        "",
                    ),
                ),
            )

            self.visible_candidates[item_id] = candidate

        self.clear_details()

    def clear_decision_form(self) -> None:
        """Clear editable local-decision controls."""

        self.decision_var.set("")
        self.definition_var.set("")
        self.replacement_var.set("")

        self.decision_notes_text.delete(
            "1.0",
            tk.END,
        )

        self.action_status_var.set(
            "Select a candidate to create a local decision."
        )

    def populate_decision_form(
        self,
        candidate: dict[str, Any],
    ) -> None:
        """Prepopulate decision controls from current registry data."""

        resolution = candidate.get("resolution") or {}

        status = resolution.get("status", "")

        if status == "unknown":
            status = ""

        self.decision_var.set(status)

        self.definition_var.set(
            resolution.get(
                "preferred_definition",
                "",
            )
        )

        self.replacement_var.set(
            resolution.get(
                "replacement_token",
                "",
            )
        )

        self.decision_notes_text.delete(
            "1.0",
            tk.END,
        )

        self.decision_notes_text.insert(
            "1.0",
            resolution.get("notes", ""),
        )

        self.action_status_var.set(
            "Edit the decision fields, then apply the local decision."
        )

    def apply_selected_decision(self) -> None:
        """Validate and apply a decision for the selected candidate."""

        selected_items = self.tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "No Candidate Selected",
                "Select a candidate before applying a decision.",
                parent=self,
            )
            return

        item_id = selected_items[0]

        candidate = self.visible_candidates.get(item_id)

        if candidate is None:
            messagebox.showerror(
                "Candidate Error",
                "The selected candidate could not be loaded.",
                parent=self,
            )
            return

        decision = self.decision_var.get().strip()

        if not decision:
            messagebox.showwarning(
                "Decision Required",
                "Choose a decision before applying changes.",
                parent=self,
            )
            return

        try:
            resolution, report = apply_local_decision(
                database_path=self.database_path,
                token=candidate.get("token", ""),
                status=decision,
                definition=self.definition_var.get(),
                replacement_token=self.replacement_var.get(),
                notes=self.decision_notes_text.get(
                    "1.0",
                    tk.END,
                ),
            )

            updated = update_candidate_report_resolution(
                report_path=self.report_path,
                token=candidate.get("token", ""),
                resolution=resolution.to_dict(),
            )

        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Decision Error",
                str(error),
                parent=self,
            )
            return

        if not updated:
            messagebox.showwarning(
                "Report Refresh Warning",
                (
                    "The local decision was saved, but the "
                    "candidate report could not be updated."
                ),
                parent=self,
            )

        self.action_status_var.set(
            f"Saved {decision} decision for "
            f"{candidate.get('token', '')}."
        )

        self.load_report()

        messagebox.showinfo(
            "Decision Saved",
            (
                f"Local decision saved for "
                f"{candidate.get('token', '')}.\n\n"
                f"Applied status: {resolution.status}\n"
                f"Decision set: {report['decision_set']}"
            ),
            parent=self,
        )


    def generate_list(self) -> None:
        """Build and save a standalone abbreviation-list DOCX."""

        try:
            candidate_report = load_generation_candidate_report(
                self.report_path
            )

            plan = build_generation_plan(
                database_path=self.database_path,
                candidate_report=candidate_report,
            )

        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror(
                "List Generation Error",
                str(error),
                parent=self,
            )
            return

        if not plan.can_generate:
            blocker_text = format_generation_blockers(
                plan.blockers
            )

            messagebox.showwarning(
                "List Generation Blocked",
                (
                    "The list cannot be generated until the "
                    "following candidates are resolved:\n\n"
                    f"{blocker_text}"
                ),
                parent=self,
            )

            self.action_status_var.set(
                f"List generation blocked by "
                f"{len(plan.blockers)} candidate(s)."
            )

            return

        report_name = self.report_path.name

        base_name = report_name.replace(
            ".abbreviationreview.json",
            "",
        )

        default_output = (
            self.report_path.parent
            / f"{base_name}_abbreviations.docx"
        )

        selected_output = filedialog.asksaveasfilename(
            parent=self,
            title="Save List of Abbreviations",
            initialfile=default_output.name,
            initialdir=str(default_output.parent),
            defaultextension=".docx",
            filetypes=[
                (
                    "Word Documents",
                    "*.docx",
                )
            ],
        )

        if not selected_output:
            self.action_status_var.set(
                "List generation cancelled."
            )
            return

        output_path = Path(selected_output)

        generation_report_path = output_path.with_suffix(
            ".listgeneration.json"
        )

        try:
            generate_list_document(
                plan=plan,
                output_path=output_path,
            )

            write_generation_report(
                plan=plan,
                output_path=generation_report_path,
            )

        except (OSError, ValueError) as error:
            messagebox.showerror(
                "List Generation Error",
                str(error),
                parent=self,
            )
            return

        self.action_status_var.set(
            f"Generated {len(plan.entries)} list entry/entries."
        )

        messagebox.showinfo(
            "List Generated",
            (
                "List of Abbreviations created successfully.\n\n"
                f"Entries: {len(plan.entries)}\n"
                f"Excluded protected or ignored terms: "
                f"{len(plan.excluded_tokens)}\n\n"
                f"DOCX:\n{output_path}\n\n"
                f"Plan report:\n{generation_report_path}"
            ),
            parent=self,
        )


    def clear_details(self) -> None:
        """Clear selected-candidate details and decision controls."""

        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.configure(state=tk.DISABLED)

        self.clear_decision_form()


    def show_selected_details(
        self,
        _event: tk.Event | None = None,
    ) -> None:
        """Show full registry and context details for selected candidate."""

        selected_items = self.tree.selection()

        if not selected_items:
            self.clear_details()
            return

        item_id = selected_items[0]

        candidate = self.visible_candidates.get(item_id)

        if candidate is None:
            self.clear_details()
            return

        resolution = candidate.get("resolution") or {}

        lines = [
            f"Candidate: {candidate.get('token', '')}",
            f"Review bucket: {candidate.get('review_bucket', '')}",
            f"Confidence: {candidate.get('confidence', '')}",
            f"Occurrences: {candidate.get('count', 0)}",
            (
                "First paragraph: "
                f"{candidate.get('first_paragraph_index', '')}"
            ),
            (
                "Inline definition occurrences: "
                f"{candidate.get('inline_definition_count', 0)}"
            ),
            "",
            f"Registry status: {resolution.get('status', 'unknown')}",
            (
                "Recommended action: "
                f"{resolution.get('enforcement_action', '')}"
            ),
            (
                "Preferred definition: "
                f"{resolution.get('preferred_definition', '')}"
            ),
            (
                "Replacement token: "
                f"{resolution.get('replacement_token', '')}"
            ),
            (
                "Source reference: "
                f"{resolution.get('source_reference', '')}"
            ),
            f"Notes: {resolution.get('notes', '')}",
            "",
            "Contexts:",
        ]

        contexts = candidate.get("contexts") or []

        if contexts:
            for context_index, context in enumerate(
                contexts,
                start=1,
            ):
                lines.append(
                    f"{context_index}. {context}"
                )
        else:
            lines.append("No context sample available.")

        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(
            "1.0",
            "\n".join(lines),
        )
        self.details_text.configure(state=tk.DISABLED)
        self.populate_decision_form(candidate)


def open_review_window(
    parent: tk.Misc,
    report_path: Path,
    database_path: Path,
) -> AbbreviationReviewWindow:
    """Open the read-only review window."""

    return AbbreviationReviewWindow(
        parent=parent,
        report_path=report_path,
        database_path=database_path,
    )

