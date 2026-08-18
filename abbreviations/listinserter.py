"""
Purpose:
    Manage abbreviation discovery, registry data, candidate review,
    and policy promotion.

Inputs:
    Candidate terms, registry data, review decisions, and policy files.

Outputs:
    Review reports, registry records, and effective abbreviation policy.

Must not:
    Insert Word comments.
    Modify Word documents directly.
"""

from __future__ import annotations

from pathlib import Path

try:
    import pythoncom
    import win32com.client
except ImportError:
    pythoncom = None  # type: ignore
    win32com = None  # type: ignore

from abbreviations.listgenerator import (
    ListGenerationPlan,
)


LIST_HEADING = (
    "LIST OF ABBREVIATIONS AND DEFINITION OF TERMS"
)


def document_has_list_heading(
    document_text: str,
) -> bool:
    """Return True if the document already contains a list heading."""

    return LIST_HEADING in document_text.upper()


def normalized_path(
    file_path: str | Path,
) -> str:
    """Return a Windows-safe comparison path."""

    return str(
        Path(file_path).resolve()
    ).casefold()


def verify_active_document(
    active_document_path: str,
    expected_document_path: Path,
) -> None:
    """Ensure the active Word document is the expected audit output."""

    if (
        normalized_path(active_document_path)
        != normalized_path(expected_document_path)
    ):
        raise ValueError(
            "The active Word document does not match the "
            "document associated with this abbreviation review report."
        )


def insert_plan_at_active_selection(
    plan: ListGenerationPlan,
    expected_document_path: Path,
) -> dict:
    """
    Insert a generated list at the cursor in the active Word document.

    The active document remains open after insertion. The user can
    review, undo, save, or close it normally in Word.
    """

    if not plan.can_generate:
        raise ValueError(
            "List insertion is blocked because unresolved "
            "candidates remain."
        )

    pythoncom.CoInitialize()

    try:
        try:
            word = win32com.client.GetActiveObject(
                "Word.Application"
            )
        except Exception as error:
            raise RuntimeError(
                "No active Microsoft Word session was found. "
                "Open the audited output document in Word, place "
                "the cursor at the intended location, then retry."
            ) from error

        document = word.ActiveDocument

        verify_active_document(
            active_document_path=document.FullName,
            expected_document_path=expected_document_path,
        )

        selection = word.Selection
        selection_range = selection.Range

        if selection_range.Start != selection_range.End:
            raise ValueError(
                "Select a single insertion point in Word. "
                "Do not highlight existing text before inserting "
                "the list."
            )

        if document_has_list_heading(
            document.Content.Text
        ):
            raise ValueError(
                "The active document already contains a List of "
                "Abbreviations heading. Existing-list replacement "
                "is not enabled in this version."
            )

        selection.TypeText(
            f"{LIST_HEADING}\r\r"
        )

        table = document.Tables.Add(
            selection.Range,
            len(plan.entries) + 1,
            2,
        )

        try:
            table.Style = "Table Grid"
        except Exception:
            pass

        table.Cell(1, 1).Range.Text = "Abbreviation"
        table.Cell(1, 2).Range.Text = "Definition"

        table.Cell(1, 1).Range.Font.Bold = True
        table.Cell(1, 2).Range.Font.Bold = True

        for row_index, entry in enumerate(
            plan.entries,
            start=2,
        ):
            table.Cell(
                row_index,
                1,
            ).Range.Text = entry.token

            table.Cell(
                row_index,
                2,
            ).Range.Text = entry.definition

        table.Range.InsertParagraphAfter()

        document.Save()

        return {
            "document_path": document.FullName,
            "entry_count": len(plan.entries),
            "excluded_count": len(plan.excluded_tokens),
        }

    finally:
        pythoncom.CoUninitialize()
