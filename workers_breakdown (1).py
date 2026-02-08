import time
import uuid
from typing import Any, Dict, List, Tuple

from db import tasks_col, profiles_col
from gemini_client import call_gemini
from parsers import parse_json_object, flatten_sections
from prompts import PROMPT_BREAKDOWN_WITH_SECTIONS, PROMPT_TASK_TYPE
from pace import get_pace_multiplier, clamp
from config import (
    CHUNK_SECONDS, MAX_SUBTASKS, MAX_SECTIONS,
    KEY_USER_ID, KEY_TASK, KEY_DONE, KEY_EXPECTED, KEY_SUBTASKS, KEY_SECTIONS,
    KEY_NEEDS_BREAKDOWN, KEY_ARCHIVED, KEY_CREATED, KEY_TASK_TYPE
)

ALLOWED_TYPES = {"homework", "reading", "lab_report", "exam_prep", "project", "other"}

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def infer_task_type(task_title: str) -> str:
    text = call_gemini(PROMPT_TASK_TYPE.format(task_title=task_title), temperature=0.0)
    obj = parse_json_object(text)
    t = str(obj.get("task_type", "other")).strip()
    return t if t in ALLOWED_TYPES else "other"

def ensure_profile(user_id: str) -> Dict[str, Any]:
    pcol = profiles_col()
    prof = pcol.find_one({"_id": user_id})
    if not prof:
        prof = {"_id": user_id, "paceByType": {}, "createdAt": now_iso()}
        pcol.insert_one(prof)
    return prof

def _add_ids_and_validate_sections(raw_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate + add ids to each subtask, clamp expectedTime.
    Each section becomes:
      { title, expectedTime, items:[{id, task, expectedTime, actualTime, done}] }
    """
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("Model returned no sections.")

    sections: List[Dict[str, Any]] = []
    subtask_counter = 0

    for s_idx, sec in enumerate(raw_sections[:MAX_SECTIONS], start=1):
        title = str(sec.get("title", f"Section {s_idx}")).strip() or f"Section {s_idx}"
        items = sec.get("items", [])
        if not isinstance(items, list) or not items:
            raise ValueError(f"Section '{title}' has no items.")

        clean_items: List[Dict[str, Any]] = []
        for item in items:
            if subtask_counter >= MAX_SUBTASKS:
                break

            for k in ("task", "expectedTime", "actualTime", "done"):
                if k not in item:
                    raise ValueError(f"Missing key '{k}' in item: {item}")

            task_text = str(item["task"]).strip()
            if not task_text:
                raise ValueError("Subtask task must be non-empty.")

            exp = int(item["expectedTime"])
            act = int(item["actualTime"])
            done = bool(item["done"])

            if exp <= 0:
                raise ValueError("expectedTime must be > 0")
            if act < 0:
                raise ValueError("actualTime must be >= 0")

            subtask_counter += 1
            clean_items.append({
                "id": f"st_{subtask_counter}_{uuid.uuid4().hex[:6]}",
                "task": task_text,
                "expectedTime": exp,
                "actualTime": act,
                "done": done
            })

        section_expected = sum(x["expectedTime"] for x in clean_items)
        sections.append({
            "title": title,
            "expectedTime": section_expected,   # helpful for UI
            "items": clean_items
        })

    return sections

def _apply_pace_to_sections(sections: List[Dict[str, Any]], pace: float) -> List[Dict[str, Any]]:
    """
    Apply pace multiplier by scaling expectedTime for each subtask.
    """
    MIN_S, MAX_S = 300, 3600  # 5 min to 60 min
    out: List[Dict[str, Any]] = []

    for sec in sections:
        items2 = []
        for st in sec["items"]:
            st2 = dict(st)
            st2["expectedTime"] = int(clamp(st2["expectedTime"] * pace, MIN_S, MAX_S))
            items2.append(st2)
        out.append({
            "title": sec["title"],
            "expectedTime": sum(i["expectedTime"] for i in items2),
            "items": items2
        })

    return out

def breakdown_one_task(user_id: str, doc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str, float]:
    title = (doc.get(KEY_TASK) or "").strip()
    if not title:
        raise ValueError("Missing task title")

    prof = ensure_profile(user_id)
    task_type = doc.get(KEY_TASK_TYPE) or infer_task_type(title)
    pace = get_pace_multiplier(prof, task_type)

    prompt = PROMPT_BREAKDOWN_WITH_SECTIONS.format(
        task_title=title,
        pace_multiplier=pace,
        chunk_seconds=CHUNK_SECONDS,
        chunk_minutes=int(CHUNK_SECONDS / 60),
    )

    text = call_gemini(prompt, temperature=0.2)
    obj = parse_json_object(text)

    raw_sections = obj.get("sections")
    sections = _add_ids_and_validate_sections(raw_sections)
    sections = _apply_pace_to_sections(sections, pace)

    flat = flatten_sections(sections)
    expected_total = sum(x["expectedTime"] for x in flat)

    return sections, flat, task_type, pace

def run_breakdown_for_user(user_id: str, limit: int = 10) -> int:
    tcol = tasks_col()

    query = {
        KEY_USER_ID: user_id,
        KEY_NEEDS_BREAKDOWN: True,
        KEY_ARCHIVED: False,
        KEY_DONE: False
    }

    cursor = tcol.find(query).sort(KEY_CREATED, 1).limit(limit)

    processed = 0
    for doc in cursor:
        try:
            sections, flat, task_type, pace = breakdown_one_task(user_id, doc)
            expected_new = sum(st["expectedTime"] for st in flat)

            tcol.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    KEY_SECTIONS: sections,       # <-- NEW: for UI
                    KEY_SUBTASKS: flat,           # keep flat list too
                    KEY_NEEDS_BREAKDOWN: False,
                    KEY_EXPECTED: expected_new,
                    KEY_TASK_TYPE: task_type,
                    "paceMultiplierUsed": pace,
                    "breakdownStatus": "ok",
                    "breakdownError": None,
                    "breakdownUpdatedAt": now_iso(),
                }}
            )
            processed += 1

        except Exception as e:
            tcol.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "breakdownStatus": "error",
                    "breakdownError": str(e),
                    "breakdownUpdatedAt": now_iso(),
                }}
            )

    return processed

def run_breakdown_for_all_users(limit_per_user: int = 10) -> Dict[str, int]:
    tcol = tasks_col()
    user_ids = tcol.distinct(KEY_USER_ID, {KEY_ARCHIVED: False})
    user_ids = [str(u) for u in user_ids if u is not None and str(u).strip() != ""]

    results: Dict[str, int] = {}
    for uid in user_ids:
        results[uid] = run_breakdown_for_user(uid, limit=limit_per_user)
    return results