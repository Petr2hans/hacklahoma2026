import time
from typing import Dict, Any
from bson import ObjectId

from db import tasks_col, profiles_col
from pace import update_pace_multiplier
from config import KEY_USER_ID, KEY_EXPECTED, KEY_ACTUAL, KEY_TASK_TYPE

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def ensure_profile_doc(user_id: str) -> Dict[str, Any]:
    pcol = profiles_col()
    prof = pcol.find_one({"_id": user_id})
    if not prof:
        prof = {"_id": user_id, "paceByType": {}, "createdAt": now_iso()}
        pcol.insert_one(prof)
    return prof

def finalize_task(task_id: str) -> Dict[str, Any]:
    """
    Call this when your app marks a task as completed and actualTime is set.

    Rule:
    - if actualTime <= expectedTime => credit yes and next time less time
    - else => credit no and next time more time
    """
    tcol = tasks_col()
    pcol = profiles_col()

    doc = tcol.find_one({"_id": ObjectId(task_id)})
    if not doc:
        raise ValueError("Task not found")

    user_id = str(doc.get(KEY_USER_ID) or "").strip()
    if not user_id:
        raise ValueError("Task missing userId")

    expected = int(doc.get(KEY_EXPECTED) or 0)
    actual = int(doc.get(KEY_ACTUAL) or 0)
    task_type = doc.get(KEY_TASK_TYPE, "other")

    if expected <= 0:
        raise ValueError("expectedTime is missing/0; cannot compute credit or pace update.")
    if actual < 0:
        raise ValueError("actualTime invalid")

    ratio = actual / expected
    credit = ratio <= 1.0

    # Example points: 1 point per minute saved (only if credit)
    saved = max(0, expected - actual)
    points = int(saved // 60) if credit else 0

    profile = ensure_profile_doc(user_id)
    profile = update_pace_multiplier(profile, task_type, ratio=ratio, lr=0.15)
    pcol.update_one({"_id": user_id}, {"$set": profile}, upsert=True)

    tcol.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "creditAwarded": credit,
            "creditPoints": points,
            "completionRatio": ratio,
            "paceUpdatedAt": now_iso(),
        }}
    )

    return {
        "task_id": task_id,
        "userId": user_id,
        "taskType": task_type,
        "expectedTime": expected,
        "actualTime": actual,
        "ratio": ratio,
        "creditAwarded": credit,
        "creditPoints": points,
        "newPace": profile["paceByType"].get(task_type),
    }