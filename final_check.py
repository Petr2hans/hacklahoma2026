from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


REQUIRED_TASK_KEYS = [
    "userId", "task", "done", "expectedTime", "actualTime",
    "createdAt", "subtasks", "needsBreakdown", "archived"
]

DB_DEFAULT = "todo_app"
TASKS_DEFAULT = "tasks"
PROFILES_DEFAULT = "user_profiles"


def die(msg: str) -> None:
    print("\n❌ FINAL CHECK FAILED:", msg)
    sys.exit(1)


def ok(msg: str) -> None:
    print("✅", msg)


def warn(msg: str) -> None:
    print("⚠️", msg)


def main() -> None:
    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (os.getenv("MONGODB_DB") or DB_DEFAULT).strip()
    tasks_name = (os.getenv("MONGODB_COLLECTION") or TASKS_DEFAULT).strip()
    profiles_name = (os.getenv("MONGODB_PROFILE_COLLECTION") or PROFILES_DEFAULT).strip()
    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()

    if not uri:
        die("MONGODB_URI missing in .env")
    ok("MONGODB_URI loaded")

    if not gemini_key:
        warn("GEMINI_API_KEY missing (Gemini calls will fail).")
    else:
        ok("GEMINI_API_KEY loaded")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
    except ServerSelectionTimeoutError as e:
        die(f"MongoDB ping timeout. Check Atlas IP allowlist + URI.\n{e}")
    except Exception as e:
        die(f"MongoDB connection error: {e}")

    ok("Connected to MongoDB Atlas (ping ok)")

    db = client[db_name]
    tasks = db[tasks_name]
    profiles = db[profiles_name]

    ok(f"Using DB='{db_name}', tasks='{tasks_name}', profiles='{profiles_name}'")

    sample = tasks.find_one()
    if not sample:
        warn("No documents in tasks collection. Add tasks and re-run.")
        return

    keys = set(sample.keys())
    print("\nSample task keys:", sorted(keys))

    missing = [k for k in REQUIRED_TASK_KEYS if k not in keys]
    if missing:
        warn(f"Sample task missing keys: {missing}")
        warn("Old tasks may be missing new fields; ensure new tasks include these keys.")
    else:
        ok("Sample task contains required keys (including userId).")

    user_ids = tasks.distinct("userId", {"archived": False})
    user_ids = [str(u) for u in user_ids if u is not None and str(u).strip() != ""]
    if not user_ids:
        die("No userId values found in tasks. Multi-user setup requires userId on each task.")
    ok(f"Found {len(user_ids)} distinct userId(s). Example: {user_ids[0]}")

    total_eligible = 0
    for uid in user_ids[:10]:
        eligible = tasks.count_documents({
            "userId": uid,
            "needsBreakdown": True,
            "archived": False,
            "done": False
        })
        if eligible:
            print(f"  userId={uid} -> {eligible} breakdown-eligible task(s)")
        total_eligible += eligible

    if total_eligible == 0:
        warn("No tasks currently eligible for breakdown (needsBreakdown=true, done=false, archived=false).")
    else:
        ok(f"Total breakdown-eligible tasks (checked users) = {total_eligible}")

    test_uid = user_ids[0]
    prof = profiles.find_one({"_id": test_uid})
    if not prof:
        profiles.insert_one({"_id": test_uid, "paceByType": {}, "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        ok(f"Created profile for userId={test_uid}")
    else:
        ok(f"Profile exists for userId={test_uid}")

    profiles.update_one({"_id": test_uid}, {"$set": {"lastCheckedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}})
    ok("Profiles collection is writable")

    print("\n🎉 FINAL CHECK PASSED.")


if __name__ == "__main__":
    main()