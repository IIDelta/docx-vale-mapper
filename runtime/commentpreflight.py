from __future__ import annotations

import json
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.abbreviationvalidator import clean_text
from validators.fieldprotection import protected_field_ranges, ranges_overlap


from word.reader import vale_text_with_offset

def resolve_comment_offset(raw_text: str, item: dict) -> int | None:
    """Resolve a planned comment target within one Word paragraph."""
    match_text = item.get("match", "")
    span = item.get("span")
    vale_text, leading_offset = vale_text_with_offset(raw_text)

    if isinstance(span, list) and span:
        vale_offset = int(span[0]) - 1
        if vale_text[vale_offset : vale_offset + len(match_text)] == match_text:
            return vale_offset + leading_offset

    candidate = vale_text.find(match_text)
    return candidate + leading_offset if candidate >= 0 else None



def run_comment_preflight(
    source_path: Path,
    plan_path: Path,
    manifest_path: Path,
    output_base: Path,
) -> Path:
    plan = json.loads(
        plan_path.read_text(encoding="utf-8")
    )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    result = {
        "source_sha256_matches": (
            calculate_sha256(source_path)
            == manifest.get("source_sha256")
        ),
        "candidate_count": len(
            plan.get("comment_plan", [])
        ),
        "verified_comments": [],
        "unverified_comments": [],
    }

    if not result["source_sha256_matches"]:
        for entry in plan.get("comment_plan", []):
            result["unverified_comments"].append(
                {
                    "plan": entry,
                    "reason": "source_sha256_mismatch",
                }
            )

    else:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        word = None
        document = None

        try:
            word = win32com.client.DispatchEx(
                "Word.Application"
            )

            word.Visible = False

            document = word.Documents.Open(
                str(source_path.resolve()),
                ReadOnly=True,
            )

            protected_ranges = protected_field_ranges(
                document
            )

            for entry in plan.get("comment_plan", []):
                finding = entry["finding"]

                try:
                    paragraph_index = int(
                        finding["ParagraphIndex"]
                    )

                    paragraph = document.Paragraphs.Item(
                        paragraph_index
                    )

                    raw_text = paragraph.Range.Text

                    expected_text = finding.get(
                        "Context",
                        {},
                    ).get(
                        "paragraph_text",
                        "",
                    )

                    if clean_text(raw_text) != expected_text:
                        raise ValueError(
                            "paragraph_text_mismatch"
                        )

                    match_text = finding.get("Match", "")

                    # Create a mock 'item' expected by resolve_comment_offset
                    offset = resolve_comment_offset(
                        raw_text,
                        {
                            "match": match_text,
                            "span": finding.get("Span")
                        }
                    )

                    if offset is None:
                        raise ValueError(
                            "match_occurrence_not_found"
                        )

                    start = paragraph.Range.Start + offset
                    end = start + len(match_text)

                    if ranges_overlap(
                        start,
                        end,
                        protected_ranges,
                    ):
                        raise ValueError(
                            "protected_word_field"
                        )

                    # Verify text mismatch on actual raw string 
                    extracted_text = raw_text[offset : offset + len(match_text)]
                    if extracted_text.replace('\r', ' ').replace('\x07', ' ').replace('\x0b', ' ').replace('\n', ' ') != match_text:
                        raise ValueError(f"text_mismatch_at_offset: expected {repr(match_text)}, got {repr(extracted_text)}")

                    result["verified_comments"].append(
                        {
                            **entry,
                            "verified_range_start": start,
                            "verified_range_end": end,
                        }
                    )

                except Exception as error:
                    result["unverified_comments"].append(
                        {
                            "plan": entry,
                            "reason": str(error),
                        }
                    )

        finally:
            if document is not None:
                document.Close(SaveChanges=False)

            if word is not None:
                word.Quit()

            pythoncom.CoUninitialize()

    result["verified_count"] = len(
        result["verified_comments"]
    )

    result["unverified_count"] = len(
        result["unverified_comments"]
    )

    output_path = output_base.with_suffix(
        ".commentpreflight.json"
    )

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path
