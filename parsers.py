import json
from typing import Any, Dict, List

def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if "\n" in t:
            t = t.split("\n", 1)[1].strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    return t

def parse_json_array(text: str) -> List[Dict[str, Any]]:
    t = _strip_code_fences(text)

    try:
        data = json.loads(t)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    start = t.find("[")
    end = t.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = t[start:end+1]
        data = json.loads(candidate)
        if isinstance(data, list):
            return data

    raise ValueError("Could not parse a JSON array from model output.")

def parse_json_object(text: str) -> Dict[str, Any]:
    t = _strip_code_fences(text)

    try:
        data = json.loads(t)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = t[start:end+1]
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data

    raise ValueError("Could not parse a JSON object from model output.")