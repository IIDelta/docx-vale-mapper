from __future__ import annotations
from typing import Any

import json
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.abbreviationvalidator import clean_text
from validators.fieldprotection import protected_field_ranges, ranges_overlap

from word.reader import vale_text_with_offset
from validators.valespan import resolve_match_offsets

def resolve_preflight_offset(raw: str, item: dict) -> int | None:
    match_text = item["match"]
    span = item.get("span")
    vale_text, leading_offset = vale_text_with_offset(raw)

    if span:
        offsets = resolve_match_offsets(vale_text, match_text, span)
        if offsets is not None:
            return offsets[0] + leading_offset
            
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

def run_preflight(source_path: Path, plan_path: Path, manifest_path: Path, output_base: Path, doc: Any = None) -> Path:
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    result={"source_sha256_matches": calculate_sha256(source_path)==manifest.get("source_sha256"), "candidate_count": len(plan.get("auto_fix_plan",[])), "verified_auto_fixes": [], "unverified_auto_fixes": []}
    if not result["source_sha256_matches"]:
        for item in plan.get("auto_fix_plan",[]): result["unverified_auto_fixes"].append({"plan":item,"reason":"source_sha256_mismatch"})
    else:
        from word.lifecycle import WordAppSession
        own_doc = False
        word_session = None
        if doc is None:
            try:
                word_session = WordAppSession(visible=False, screen_updating=True)
                word = word_session.__enter__()
                doc = word.Documents.Open(str(source_path.resolve()), ReadOnly=True)
                own_doc = True
            except Exception:
                pass
        
        if doc is not None:
            try:
                from word.lifecycle import with_com_retry
                protected=with_com_retry(lambda: protected_field_ranges(doc), retries=5, delay=1.0)
                
                auto_fix_plan = plan.get("auto_fix_plan",[])
                required_indices = {int(item["paragraph_index"]) for item in auto_fix_plan}
                
                def extract_paragraphs():
                    paragraph_data = {}
                    if required_indices:
                        max_idx = max(required_indices)
                        for i, paragraph in enumerate(doc.Paragraphs, start=1):
                            if i in required_indices:
                                paragraph_data[i] = {
                                    "start": paragraph.Range.Start,
                                    "text": paragraph.Range.Text
                                }
                            if i >= max_idx:
                                break
                    return paragraph_data
                
                paragraph_data = with_com_retry(extract_paragraphs, retries=5, delay=1.0)
                            
                for item in auto_fix_plan:
                    try:
                        p_index = int(item["paragraph_index"])
                        p_data = paragraph_data.get(p_index)
                        if not p_data:
                            raise ValueError("paragraph_not_found")
                            
                        raw = p_data["text"]
                        paragraph_start = p_data["start"]
                        
                        if clean_text(raw)!=item.get("paragraph_text",""):
                            raise ValueError("paragraph_text_mismatch")
                        offset = resolve_preflight_offset(raw, item)
                        if offset is None: raise ValueError("match_occurrence_not_found")
                        start=paragraph_start+offset; end=start+len(item["match"])
                        if ranges_overlap(start,end,protected): raise ValueError("protected_word_field")

                        # Verify text mismatch on actual raw string 
                        extracted_text = raw[offset : offset + len(item["match"])]
                        if extracted_text.replace('\xa0', ' ').replace('\r', ' ').replace('\x07', ' ').replace('\x0b', ' ').replace('\n', ' ') != item["match"]:
                            raise ValueError(f"text_mismatch_at_offset: expected {repr(item['match'])}, got {repr(extracted_text)}")
                        result["verified_auto_fixes"].append({**item,"verified_range_start":start,"verified_range_end":end})
                    except Exception as error:
                        result["unverified_auto_fixes"].append({"plan":item,"reason":str(error)})
            finally:
                if own_doc:
                    if doc is not None:
                        try:
                            doc.Close(SaveChanges=False)
                        except Exception:
                            pass
                    if word_session is not None:
                        word_session.__exit__(None, None, None)
    result["verified_count"]=len(result["verified_auto_fixes"])
    result["unverified_count"]=len(result["unverified_auto_fixes"])
    path=output_base.with_suffix(".autofixpreflight.json")
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path
