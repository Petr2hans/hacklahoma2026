from dotenv import load_dotenv
load_dotenv()

import os

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DB_NAME = os.getenv("MONGODB_DB", "todo_app").strip()
TASKS_COLLECTION = os.getenv("MONGODB_COLLECTION", "tasks").strip()
SESSIONS_COLLECTION = os.getenv("MONGODB_SESSIONS_COLLECTION", "sessions").strip()
PROFILE_COLLECTION = os.getenv("MONGODB_PROFILE_COLLECTION", "user_profiles").strip()

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()  # <-- IMPORTANT FIX
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Worker settings
CHUNK_SECONDS = int(os.getenv("CHUNK_SECONDS", "600"))
MAX_SUBTASKS = int(os.getenv("MAX_SUBTASKS", "25"))
MAX_SECTIONS = int(os.getenv("MAX_SECTIONS", "8"))

# Mongo keys (your schema)
KEY_ID = "_id"
KEY_USER_ID = "userId"
KEY_TASK = "task"
KEY_DONE = "done"
KEY_EXPECTED = "expectedTime"
KEY_ACTUAL = "actualTime"
KEY_CREATED = "createdAt"
KEY_COMPLETED = "completedAt"
KEY_SUBTASKS = "subtasks"
KEY_SECTIONS = "sections"  # <-- NEW
KEY_NEEDS_BREAKDOWN = "needsBreakdown"
KEY_ARCHIVED = "archived"
KEY_LAST_SESSION = "lastSessionId"

# Optional
KEY_TASK_TYPE = "taskType"