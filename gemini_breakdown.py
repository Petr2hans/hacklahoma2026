"""
Gemini-powered Task Breakdown Module
Integrated from Friend 1's code
"""

import json
import time
import uuid
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Tuple

# Configuration
CHUNK_SECONDS = 600  # 10 minutes default
MAX_SUBTASKS = 25
MAX_SECTIONS = 8
MIN_MULT = 0.6
MAX_MULT = 1.8

ALLOWED_TYPES = {"homework", "reading", "lab_report", "exam_prep", "project", "other"}

# ============================================
# PROMPTS
# ============================================

PROMPT_TASK_TYPE = """
Classify this assignment into one of:
homework, reading, lab_report, exam_prep, project, other

Title: "{task_title}"

Return ONLY valid JSON:
{{"task_type":"<one of the allowed values>"}}
""".strip()

PROMPT_BREAKDOWN_WITH_SECTIONS = """
You are a study-planning assistant.

Create a structured plan for this assignment as SECTIONS, each containing subtasks.
The student pace multiplier is {pace_multiplier}:
- < 1.0 means student is faster → reduce times a bit
- > 1.0 means student is slower → increase times a bit

Assignment title: "{task_title}"

Rules:
- Create 2–6 sections.
- Each section has 2–6 subtasks.
- Each subtask should be actionable and specific.
- Target per-subtask time around {chunk_seconds} seconds (~{chunk_minutes} minutes), but allow variation.
- expectedTime values are IN SECONDS.
- actualTime must be 0, done must be false.
- Do not include any extra keys.

Return ONLY valid JSON (no markdown, no commentary) with EXACT structure:

{{
  "sections": [
    {{
      "title": "string",
      "items": [
        {{"task":"string","expectedTime":123,"actualTime":0,"done":false}}
      ]
    }}
  ]
}}
""".strip()

# ============================================
# GEMINI CLIENT
# ============================================

def call_gemini(prompt: str, api_key: str, temperature: float = 0.2, timeout_s: int = 30) -> str:
    """Call Gemini API with a prompt"""
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    
    model = "gemini-2.0-flash-exp"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    
    full_url = f"{url}?key={urllib.parse.quote(api_key)}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(full_url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
        
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")

# ============================================
# PARSERS
# ============================================

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from response"""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if "\n" in t:
            t = t.split("\n", 1)[1].strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    return t

def parse_json_object(text: str) -> Dict[str, Any]:
    """Extract JSON object from Gemini response"""
    t = _strip_code_fences(text)
    
    # Try direct parse
    try:
        data = json.loads(t)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    
    # Extract first {...}
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = t[start:end+1]
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data
    
    raise ValueError("Could not parse JSON from Gemini response")

def flatten_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert sections -> flat subtasks list"""
    flat: List[Dict[str, Any]] = []
    for sec in sections:
        for item in sec.get("items", []) or []:
            flat.append(item)
    return flat

# ============================================
# PACE MANAGEMENT
# ============================================

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value between min and max"""
    return max(lo, min(hi, x))

def get_pace_multiplier(profiles_collection, user_id: str, task_type: str) -> float:
    """Get user's pace multiplier for a specific task type"""
    try:
        profile = profiles_collection.find_one({"_id": user_id})
        if not profile:
            return 1.0
        
        info = (profile.get("paceByType", {}) or {}).get(task_type)
        if not info:
            return 1.0
        
        return clamp(float(info.get("multiplier", 1.0)), MIN_MULT, MAX_MULT)
    except Exception:
        return 1.0

def ensure_profile(profiles_collection, user_id: str) -> Dict[str, Any]:
    """Ensure user profile exists in database"""
    prof = profiles_collection.find_one({"_id": user_id})
    if not prof:
        prof = {
            "_id": user_id,
            "paceByType": {},
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        profiles_collection.insert_one(prof)
    return prof

# ============================================
# TASK BREAKDOWN
# ============================================

def infer_task_type(task_title: str, api_key: str) -> str:
    """Use Gemini to classify task type"""
    try:
        text = call_gemini(
            PROMPT_TASK_TYPE.format(task_title=task_title),
            api_key,
            temperature=0.0
        )
        obj = parse_json_object(text)
        t = str(obj.get("task_type", "other")).strip()
        return t if t in ALLOWED_TYPES else "other"
    except Exception as e:
        print(f"⚠️  Task type inference failed: {e}, using 'other'")
        return "other"

def _add_ids_and_validate_sections(raw_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate sections and add unique IDs to each subtask"""
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("Model returned no sections")
    
    sections: List[Dict[str, Any]] = []
    subtask_counter = 0
    
    for s_idx, sec in enumerate(raw_sections[:MAX_SECTIONS], start=1):
        title = str(sec.get("title", f"Section {s_idx}")).strip() or f"Section {s_idx}"
        items = sec.get("items", [])
        if not isinstance(items, list) or not items:
            raise ValueError(f"Section '{title}' has no items")
        
        clean_items: List[Dict[str, Any]] = []
        for item in items:
            if subtask_counter >= MAX_SUBTASKS:
                break
            
            # Validate required keys
            for k in ("task", "expectedTime", "actualTime", "done"):
                if k not in item:
                    raise ValueError(f"Missing key '{k}' in item: {item}")
            
            task_text = str(item["task"]).strip()
            if not task_text:
                raise ValueError("Subtask task must be non-empty")
            
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
            "expectedTime": section_expected,
            "items": clean_items
        })
    
    return sections

def _apply_pace_to_sections(sections: List[Dict[str, Any]], pace: float) -> List[Dict[str, Any]]:
    """Apply pace multiplier to all subtask times"""
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

def breakdown_task_with_gemini(
    task_title: str,
    user_id: str,
    profiles_collection,
    api_key: str,
    task_type: str = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str, float]:
    """
    Main function to breakdown a task using Gemini AI
    
    Returns:
        - sections: List of sections with subtasks
        - flat: Flattened list of all subtasks
        - task_type: Type of task (homework, reading, etc.)
        - pace: Pace multiplier used
    """
    if not task_title or not task_title.strip():
        raise ValueError("Missing task title")
    
    # Ensure user profile exists
    ensure_profile(profiles_collection, user_id)
    
    # Infer task type if not provided
    if not task_type:
        task_type = infer_task_type(task_title, api_key)
    
    # Get user's pace multiplier for this task type
    pace = get_pace_multiplier(profiles_collection, user_id, task_type)
    
    # Build prompt
    prompt = PROMPT_BREAKDOWN_WITH_SECTIONS.format(
        task_title=task_title,
        pace_multiplier=pace,
        chunk_seconds=CHUNK_SECONDS,
        chunk_minutes=int(CHUNK_SECONDS / 60),
    )
    
    # Call Gemini
    print(f"🤖 Calling Gemini to breakdown: {task_title[:50]}...")
    text = call_gemini(prompt, api_key, temperature=0.2)
    obj = parse_json_object(text)
    
    # Validate and add IDs
    raw_sections = obj.get("sections")
    sections = _add_ids_and_validate_sections(raw_sections)
    
    # Apply pace multiplier
    sections = _apply_pace_to_sections(sections, pace)
    
    # Create flat list
    flat = flatten_sections(sections)
    
    print(f"✅ Generated {len(sections)} sections with {len(flat)} subtasks")
    
    return sections, flat, task_type, pace
