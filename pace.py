from typing import Dict, Any

MIN_MULT = 0.6
MAX_MULT = 1.8

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def get_pace_multiplier(profile_doc: Dict[str, Any], task_type: str) -> float:
    info = (profile_doc.get("paceByType", {}) or {}).get(task_type)
    if not info:
        return 1.0
    try:
        return clamp(float(info.get("multiplier", 1.0)), MIN_MULT, MAX_MULT)
    except Exception:
        return 1.0

def update_pace_multiplier(profile_doc: Dict[str, Any], task_type: str, ratio: float, lr: float = 0.15) -> Dict[str, Any]:
    ratio = clamp(float(ratio), MIN_MULT, MAX_MULT)

    pace_by_type = profile_doc.get("paceByType", {}) or {}
    current = pace_by_type.get(task_type, {"multiplier": 1.0, "n": 0})

    old = float(current.get("multiplier", 1.0))
    n = int(current.get("n", 0))

    new = old * (1 - lr) + ratio * lr
    new = clamp(new, MIN_MULT, MAX_MULT)

    pace_by_type[task_type] = {"multiplier": new, "n": n + 1}
    profile_doc["paceByType"] = pace_by_type
    return profile_doc