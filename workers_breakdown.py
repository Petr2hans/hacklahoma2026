import time
import uuid
from typing import Any, Dict, List, Tuple

from db import tasks_col, profiles_col
from gemini_client import call_gemini
from parsers import parse_json_array, parse_json_object
from prompts import PROMPT_BREAKDOWN, PROMPT_TASK_TYPE
from pace import get_pace_multiplier, clamp
from config import (
    CHUNK_SECONDS, MAX_SUBTASKS,
    KEY_USER_ID, KEY_TASK, KEY_DONE, KEY_EXPECTED, KEY_SUBTASKS,
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

def apply_pace(subtasks: List[Dict[str, Any]], pace: float) -> List[Dict[str, Any]]:
    # clamp each subtask between 5 and 45 minutes
    MIN_S, MAX_S = 300, 2700
    out = []
    for st in subtasks:
        s = dict(st)
        s["expectedTime"] = int(clamp(int(s["expectedTime"]) * pace, MIN_S, MAX_S))
        out.append(s)
    return out

def breakdown_one_task(user_id: str, doc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str, float]:
    title = (doc.get(KEY_TASK) or "").strip()
    if not title:
        raise ValueError("Missing task title")

    # per-user pace
    prof = ensure_profile(user_id)
    task_type = doc.get(KEY_TASK_TYPE) or infer_task_type(title)
    pace = get_pace_multiplier(prof, task_type)

    prompt = PROMPT_BREAKDOWN.format(
        task_title=title,
        pace_multiplier=pace,
        chunk_seconds=CHUNK_SECONDS,
        chunk_minutes=int(CHUNK_SECONDS / 60),
    )

    text = call_gemini(prompt, temperature=0.2)
    raw = parse_json_array(text)

    cleaned: List[Dict[str, Any]] = []
    for i, st in enumerate(raw[:MAX_SUBTASKS], start=1):
        for k in ("task", "expectedTime", "actualTime", "done"):
            if k not in st:
                raise ValueError(f"Missing key '{k}' in subtask: {st}")

        cleaned.append({
            "id": f"st_{i}_{uuid.uuid4().hex[:6]}",
            "task": str(st["task"]).strip(),
            "expectedTime": int(st["expectedTime"]),
            "actualTime": int(st["actualTime"]),
            "done": bool(st["done"]),
        })

    cleaned = apply_pace(cleaned, pace)
    return cleaned, task_type, pace

def run_breakdown_for_user(user_id: str, limit: int = 10) -> int:
    tcol = tasks_col()

    query = {
        KEY_USER_ID: user_id,
        KEY_NEEDS_BREAKDOWN: True,
        KEY_ARCHIVED: False,
        KEY_DONE: False,   # don't breakdown completed tasks
    }

    cursor = tcol.find(query).sort(KEY_CREATED, 1).limit(limit)

    processed = 0
    for doc in cursor:
        try:
            subtasks, task_type, pace = breakdown_one_task(user_id, doc)
            expected_new = sum(st["expectedTime"] for st in subtasks)

            tcol.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    KEY_SUBTASKS: subtasks,
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