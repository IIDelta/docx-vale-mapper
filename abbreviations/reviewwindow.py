from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any


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


class AbbreviationReviewWindow(tk.Toplevel):
    """Read-only candidate review window."""

    def __init__(
        self,
        parent: tk.Misc,
        report_path: Path,
    ) -> None:
        super().__init__(parent)

        self.report_path = report_path
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

    def clear_details(self) -> None:
        """Clear the selected-candidate detail panel."""

        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.configure(state=tk.DISABLED)

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


def open_review_window(
    parent: tk.Misc,
    report_path: Path,
) -> AbbreviationReviewWindow:
    """Open the read-only review window."""

    return AbbreviationReviewWindow(
        parent=parent,
        report_path=report_path,
    )
