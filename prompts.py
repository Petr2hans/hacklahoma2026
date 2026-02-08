PROMPT_TASK_TYPE = """
Classify this assignment into one of:
homework, reading, lab_report, exam_prep, project, other

Title: "{task_title}"

Return ONLY valid JSON:
{{"task_type":"<one of the allowed values>"}}
""".strip()

# NEW: sections + subtasks in one response
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