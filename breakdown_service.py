"""
Breakdown Service
Handles AI-powered task breakdown using Gemini API
Integrates pace multiplier tracking
"""

import time
import uuid
from typing import Dict, Any, List, Tuple

from gemini_client import call_gemini
from parsers import parse_json_array
from prompts import PROMPT_BREAKDOWN, PROMPT_TASK_TYPE
from pace import get_pace_multiplier, update_pace_multiplier, clamp
from config import CHUNK_SECONDS, MAX_SUBTASKS, KEY_USER_ID, KEY_TASK_TYPE
from db import get_client
from task_service import get_task_by_id, update_task_breakdown

def get_profiles_collection():
    """Get user profiles collection from MongoDB"""
    client = get_client()
    return client['todo_app']['user_profiles']

def now_iso() -> str:
    """Get current time in ISO format"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def ensure_profile(user_id: str) -> Dict[str, Any]:
    """Ensure user profile exists, create if not"""
    profiles_col = get_profiles_collection()
    prof = profiles_col.find_one({"_id": user_id})
    
    if not prof:
        prof = {"_id": user_id, "paceByType": {}, "createdAt": now_iso()}
        profiles_col.insert_one(prof)
    
    return prof

def infer_task_type(task_title: str) -> str:
    """Use Gemini to infer task type"""
    allowed_types = {"homework", "reading", "lab_report", "exam_prep", "project", "other"}
    
    try:
        response = call_gemini(
            PROMPT_TASK_TYPE.format(task_title=task_title),
            temperature=0.0
        )
        # Parse response
        import json
        # Try to extract JSON from response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            obj = json.loads(response[start:end])
            task_type = str(obj.get("task_type", "other")).strip()
            return task_type if task_type in allowed_types else "other"
    except Exception as e:
        print(f"⚠️ Error inferring task type: {e}")
    
    return "other"

def breakdown_task(user_id: str, task_title: str, task_type: str = None) -> Dict[str, Any]:
    """
    Break down a task using Gemini API
    
    Returns dict with:
    - sections: list of task sections with subtasks
    - subtasks: flat list of all subtasks
    - taskType: inferred task type
    - paceMultiplier: personalized pace multiplier
    """
    try:
        # Infer type if not provided
        if not task_type:
            task_type = infer_task_type(task_title)
        
        # Get user's pace multiplier
        profile = ensure_profile(user_id)
        pace = get_pace_multiplier(profile, task_type)
        
        # Call Gemini with pace multiplier
        prompt = PROMPT_BREAKDOWN.format(
            task_title=task_title,
            pace_multiplier=pace,
            chunk_seconds=CHUNK_SECONDS,
            chunk_minutes=int(CHUNK_SECONDS / 60),
        )
        
        response = call_gemini(prompt, temperature=0.2)
        raw_subtasks = parse_json_array(response)
        
        # Process and validate subtasks
        processed_subtasks = _process_subtasks(raw_subtasks, pace)
        
        # Group subtasks into sections for UI
        sections = _group_into_sections(processed_subtasks)
        
        return {
            "sections": sections,
            "subtasks": processed_subtasks,
            "taskType": task_type,
            "paceMultiplier": pace
        }
    
    except Exception as e:
        print(f"❌ Error breaking down task: {e}")
        # Return a simple fallback breakdown
        return {
            "sections": [{
                "title": "Work on this task",
                "expectedTime": 60 * 10,  # 10 minutes
                "items": [{
                    "id": f"st_1_{uuid.uuid4().hex[:6]}",
                    "task": task_title,
                    "expectedTime": 60 * 10,
                    "actualTime": 0,
                    "done": False
                }]
            }],
            "subtasks": [{
                "id": f"st_1_{uuid.uuid4().hex[:6]}",
                "task": task_title,
                "expectedTime": 60 * 10,
                "actualTime": 0,
                "done": False
            }],
            "taskType": task_type or "other",
            "paceMultiplier": 1.0
        }

def _process_subtasks(raw: List[Dict[str, Any]], pace: float) -> List[Dict[str, Any]]:
    """Process and validate subtasks from Gemini"""
    required_keys = {"task", "expectedTime", "actualTime", "done"}
    min_time, max_time = 300, 2700  # 5-45 minutes
    
    cleaned = []
    for i, st in enumerate(raw[:MAX_SUBTASKS], start=1):
        try:
            # Validate keys
            if not all(k in st for k in required_keys):
                continue
            
            # Apply pace multiplier and clamp times
            expected = int(st.get("expectedTime", 600)) * pace
            expected = max(min_time, min(expected, max_time))
            
            cleaned.append({
                "id": f"st_{i}_{uuid.uuid4().hex[:6]}",
                "task": str(st.get("task", "")).strip(),
                "expectedTime": int(expected),
                "actualTime": 0,
                "done": False
            })
        except Exception as e:
            print(f"⚠️ Error processing subtask: {e}")
            continue
    
    # If no valid subtasks, return at least one
    if not cleaned:
        cleaned = [{
            "id": f"st_1_{uuid.uuid4().hex[:6]}",
            "task": "Complete this task",
            "expectedTime": 1800,  # 30 minutes default
            "actualTime": 0,
            "done": False
        }]
    
    return cleaned

def _group_into_sections(subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group subtasks into sections for better UI organization"""
    
    if not subtasks:
        return []
    
    # Simple grouping: divide into 3 sections (start, main, finish)
    sections = []
    third = max(1, len(subtasks) // 3)
    
    if third < len(subtasks):
        sections.append({
            "title": "Getting Started",
            "expectedTime": sum(st.get("expectedTime", 0) for st in subtasks[:third]),
            "items": subtasks[:third]
        })
        
        mid_third = subtasks[third:2*third]
        if mid_third:
            sections.append({
                "title": "Main Work",
                "expectedTime": sum(st.get("expectedTime", 0) for st in mid_third),
                "items": mid_third
            })
        
        last_third = subtasks[2*third:]
        if last_third:
            sections.append({
                "title": "Wrap Up",
                "expectedTime": sum(st.get("expectedTime", 0) for st in last_third),
                "items": last_third
            })
    else:
        # All in one section if only a few subtasks
        sections.append({
            "title": "Tasks",
            "expectedTime": sum(st.get("expectedTime", 0) for st in subtasks),
            "items": subtasks
        })
    
    return sections

def request_breakdown(user_id: str, task_id: str) -> Tuple[bool, str, Dict]:
    """
    Main entry point: Break down a task and update MongoDB
    
    Returns: (success, message, breakdown_result)
    """
    # Get task
    task = get_task_by_id(user_id, task_id)
    if not task:
        return False, "Task not found", {}
    
    try:
        # Perform breakdown
        breakdown_result = breakdown_task(user_id, task['task'], task.get('taskType'))
        
        # Update task in MongoDB
        updated_task = update_task_breakdown(user_id, task_id, breakdown_result)
        
        if not updated_task:
            return False, "Failed to update task with breakdown", {}
        
        print(f"✅ Task breakdown completed: {task['task']}")
        
        return True, "Breakdown successful", breakdown_result
    
    except Exception as e:
        print(f"❌ Error in request_breakdown: {e}")
        return False, str(e), {}
