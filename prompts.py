PROMPT_TASK_TYPE = """
Classify this assignment into one of:
homework, reading, lab_report, exam_prep, project, other

Title: "{task_title}"

Return ONLY valid JSON:
{{"task_type":"<one of the allowed values>"}}
""".strip()


PROMPT_BREAKDOWN = """
Break the following assignment into actionable study subtasks.

Assignment title: "{task_title}"
Student pace multiplier: {pace_multiplier}
- If pace_multiplier < 1.0, student is faster → reduce times.
- If pace_multiplier > 1.0, student is slower → increase times.

Make subtasks of about {chunk_seconds} seconds (~{chunk_minutes} minutes) each.

Return ONLY a valid JSON array (no markdown, no commentary).
Each element MUST be an object with EXACT keys:
- task (string)
- expectedTime (integer seconds)
- actualTime (integer seconds, set 0)
- done (boolean, set false)

Rules:
- Keep subtasks actionable and specific.
- Create 3–12 subtasks for most tasks.
- Do not include any extra keys.
""".strip()