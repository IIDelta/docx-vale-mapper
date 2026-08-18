from __future__ import annotations

import json
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.abbreviationvalidator import clean_text
from validators.fieldprotection import protected_field_ranges, ranges_overlap


from word.reader import vale_text_with_offset

def resolve_preflight_offset(raw: str, item: dict) -> int | None:
    match_text = item["match"]
    span = item.get("span")
    vale_text, leading_offset = vale_text_with_offset(raw)

    if isinstance(span, list) and span:
        # Vale spans are 1-based inclusive. So [261, 263] for length 3.
        # Python 0-based start index is span[0] - 1
        vale_offset = int(span[0]) - 1
        # Verify the match is actually at this offset in vale_text
        if vale_text[vale_offset : vale_offset + len(match_text)] == match_text:
            return vale_offset + leading_offset

    # Fallback to searching if span is missing or invalid
    occurrence_index = int(item.get("occurrence_index", 0))
    start = 0
    for _ in range(occurrence_index + 1):
        start = vale_text.find(match_text, start)
        if start < 0:
            return None
        if _ < occurrence_index:
            start += len(match_text)
            
    return start + leading_offset
def run_preflight(source_path: Path, plan_path: Path, manifest_path: Path, output_base: Path) -> Path:
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    result={"source_sha256_matches": calculate_sha256(source_path)==manifest.get("source_sha256"), "candidate_count": len(plan.get("auto_fix_plan",[])), "verified_auto_fixes": [], "unverified_auto_fixes": []}
    if not result["source_sha256_matches"]:
        for item in plan.get("auto_fix_plan",[]): result["unverified_auto_fixes"].append({"plan":item,"reason":"source_sha256_mismatch"})
    else:
        import pythoncom, win32com.client
        pythoncom.CoInitialize(); word=None; doc=None
        try:
            word=win32com.client.DispatchEx("Word.Application"); word.Visible=False
            doc=word.Documents.Open(str(source_path.resolve()), ReadOnly=True)
            protected=protected_field_ranges(doc)
            for item in plan.get("auto_fix_plan",[]):
                try:
                    paragraph=doc.Paragraphs.Item(int(item["paragraph_index"]))
                    raw=paragraph.Range.Text
                    if clean_text(raw)!=item.get("paragraph_text",""):
                        raise ValueError("paragraph_text_mismatch")
                    offset = resolve_preflight_offset(raw, item)
                    if offset is None: raise ValueError("match_occurrence_not_found")
                    start=paragraph.Range.Start+offset; end=start+len(item["match"])
                    if ranges_overlap(start,end,protected): raise ValueError("protected_word_field")

                    # Verify text mismatch on actual raw string 
                    extracted_text = raw[offset : offset + len(item["match"])]
                    if extracted_text.replace('\xa0', ' ').replace('\r', ' ').replace('\x07', ' ').replace('\x0b', ' ').replace('\n', ' ') != item["match"]:
                        raise ValueError(f"text_mismatch_at_offset: expected {repr(item['match'])}, got {repr(extracted_text)}")
                    result["verified_auto_fixes"].append({**item,"verified_range_start":start,"verified_range_end":end})
                except Exception as error:
                    result["unverified_auto_fixes"].append({"plan":item,"reason":str(error)})
        finally:
            if doc is not None: doc.Close(SaveChanges=False)
            if word is not None: word.Quit()
            pythoncom.CoUninitialize()
    result["verified_count"]=len(result["verified_auto_fixes"])
    result["unverified_count"]=len(result["unverified_auto_fixes"])
    path=output_base.with_suffix(".autofixpreflight.json")
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path
