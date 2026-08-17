from __future__ import annotations

import json
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.abbreviationvalidator import clean_text
from validators.fieldprotection import protected_field_ranges, ranges_overlap


def occurrence_offset(text: str, match: str, occurrence_index: int) -> int | None:
    start = 0
    for _ in range(occurrence_index + 1):
        start = text.find(match, start)
        if start < 0:
            return None
        if _ < occurrence_index:
            start += len(match)
    return start


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
                    offset=occurrence_offset(raw,item["match"],int(item.get("occurrence_index",0)))
                    if offset is None: raise ValueError("match_occurrence_not_found")
                    start=paragraph.Range.Start+offset; end=start+len(item["match"])
                    if ranges_overlap(start,end,protected): raise ValueError("protected_word_field")
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
