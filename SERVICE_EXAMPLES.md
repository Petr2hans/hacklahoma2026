# Service Implementation Examples

This file shows how to refactor existing code into service modules.

## 1. Auth Service

**File: `app/services/auth_service.py`**

```python
import hashlib
import secrets
from typing import Dict, Optional
from bson import ObjectId
from datetime import datetime, timedelta
import jwt

from app.db import get_client
from app.config import JWT_SECRET, JWT_ALGORITHM

class AuthService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.users_col = self.db['users']
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt for storage"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt, pwd_hash = hashed.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except:
            return False
    
    def register_user(self, username: str, password: str, wallet_address: str) -> Dict:
        """
        Register new user
        Raises: ValueError if username exists
        """
        # Check if user exists
        if self.users_col.find_one({"username": username}):
            raise ValueError("Username already exists")
        
        if not wallet_address or len(wallet_address) < 30:
            raise ValueError("Invalid Solana wallet address")
        
        # Create user
        user = {
            "username": username,
            "passwordHash": self.hash_password(password),
            "walletAddress": wallet_address,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "totalCreditsEarned": 0,
            "totalTokensReceived": 0.0
        }
        
        result = self.users_col.insert_one(user)
        user["_id"] = str(result.inserted_id)
        
        # Create user profile
        profiles_col = self.db['user_profiles']
        profiles_col.insert_one({
            "_id": str(result.inserted_id),
            "paceByType": {},
            "createdAt": datetime.utcnow().isoformat() + "Z"
        })
        
        return {
            "userId": str(result.inserted_id),
            "username": username,
            "walletAddress": wallet_address,
            "token": self.generate_token(str(result.inserted_id))
        }
    
    def login_user(self, username: str, password: str) -> Dict:
        """
        Login user
        Raises: ValueError if credentials invalid
        """
        user = self.users_col.find_one({"username": username})
        if not user or not self.verify_password(password, user["passwordHash"]):
            raise ValueError("Invalid username or password")
        
        return {
            "userId": str(user["_id"]),
            "username": user["username"],
            "token": self.generate_token(str(user["_id"]))
        }
    
    def generate_token(self, user_id: str, expires_hours: int = 24) -> str:
        """Generate JWT token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify JWT token
        Returns: user_id if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            return self.users_col.find_one({"_id": ObjectId(user_id)})
        except:
            return None
```

---

## 2. Task Service

**File: `app/services/task_service.py`**

```python
from typing import List, Dict, Optional
from bson import ObjectId
from datetime import datetime
from app.db import get_client
from app.config import KEY_USER_ID, KEY_TASK, KEY_DONE, KEY_CREATED

class TaskService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.tasks_col = self.db['tasks']
    
    def create_task(self, user_id: str, title: str, estimated_minutes: int = 60) -> Dict:
        """Create new task"""
        task = {
            KEY_USER_ID: user_id,
            KEY_TASK: title.strip(),
            "status": "pending",
            "estimatedMinutes": estimated_minutes,
            "expectedTotalTime": 0,  # Will be set after breakdown
            "actualTotalTime": 0,
            "subtasks": [],
            "taskType": None,
            "paceMultiplier": 1.0,
            "needsBreakdown": True,
            "creditEarned": False,
            "rewardSent": False,
            "rewardAmount": 0.0,
            KEY_CREATED: datetime.utcnow().isoformat() + "Z",
            "completedAt": None
        }
        
        result = self.tasks_col.insert_one(task)
        task["_id"] = str(result.inserted_id)
        return task
    
    def get_tasks(self, user_id: str, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get user's tasks"""
        query = {KEY_USER_ID: user_id}
        if status:
            query["status"] = status
        
        tasks = list(self.tasks_col.find(query).sort(KEY_CREATED, -1).limit(limit))
        
        # Convert ObjectIds to strings
        for task in tasks:
            task["_id"] = str(task["_id"])
        
        return tasks
    
    def get_task(self, user_id: str, task_id: str) -> Optional[Dict]:
        """Get single task by ID"""
        try:
            task = self.tasks_col.find_one({
                "_id": ObjectId(task_id),
                KEY_USER_ID: user_id
            })
            if task:
                task["_id"] = str(task["_id"])
            return task
        except:
            return None
    
    def update_task(self, user_id: str, task_id: str, updates: Dict) -> Optional[Dict]:
        """Update task fields"""
        try:
            result = self.tasks_col.find_one_and_update(
                {
                    "_id": ObjectId(task_id),
                    KEY_USER_ID: user_id
                },
                {"$set": updates},
                return_document=True
            )
            if result:
                result["_id"] = str(result["_id"])
            return result
        except:
            return None
    
    def update_subtasks(self, user_id: str, task_id: str, subtasks: List[Dict]) -> Optional[Dict]:
        """Update subtasks in a task"""
        return self.update_task(user_id, task_id, {
            "subtasks": subtasks,
            "expectedTotalTime": sum(st.get("expectedTime", 0) for st in subtasks),
            "needsBreakdown": False,
            "status": "ready"
        })
    
    def mark_subtask_done(self, user_id: str, task_id: str, subtask_id: str, actual_time: int) -> Optional[Dict]:
        """Mark a subtask as done and log time"""
        task = self.get_task(user_id, task_id)
        if not task:
            return None
        
        # Find and update subtask
        for st in task.get("subtasks", []):
            if st["id"] == subtask_id:
                st["done"] = True
                st["actualTime"] = actual_time
                st["completedAt"] = datetime.utcnow().isoformat() + "Z"
                break
        
        # Check if all subtasks done
        all_done = all(st["done"] for st in task.get("subtasks", []))
        task["status"] = "ready_for_completion" if all_done else "in_progress"
        
        # Calculate total actual time
        task["actualTotalTime"] = sum(st.get("actualTime", 0) for st in task.get("subtasks", []))
        
        return self.update_task(user_id, task_id, {
            "subtasks": task["subtasks"],
            "status": task["status"],
            "actualTotalTime": task["actualTotalTime"]
        })
    
    def delete_task(self, user_id: str, task_id: str) -> bool:
        """Soft-delete task (archive)"""
        try:
            result = self.tasks_col.update_one(
                {"_id": ObjectId(task_id), KEY_USER_ID: user_id},
                {"$set": {"status": "archived"}}
            )
            return result.modified_count > 0
        except:
            return False
```

---

## 3. Breakdown Service

**File: `app/services/breakdown_service.py`**

```python
from typing import Dict, List, Tuple, Optional
from app.db import get_client
from app.utils.gemini_client import call_gemini
from app.utils.parsers import parse_json_array, parse_json_object
from app.utils.prompts import PROMPT_BREAKDOWN, PROMPT_TASK_TYPE
from app.services.profile_service import ProfileService
from app.config import CHUNK_SECONDS, MAX_SUBTASKS
import uuid

class BreakdownService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.tasks_col = self.db['tasks']
        self.profile_service = ProfileService()
    
    def infer_task_type(self, task_title: str) -> str:
        """Use Gemini to infer task type"""
        allowed_types = {"homework", "reading", "lab_report", "exam_prep", "project", "other"}
        
        try:
            response = call_gemini(
                PROMPT_TASK_TYPE.format(task_title=task_title),
                temperature=0.0
            )
            obj = parse_json_object(response)
            task_type = str(obj.get("task_type", "other")).strip()
            
            return task_type if task_type in allowed_types else "other"
        except Exception as e:
            print(f"Error inferring task type: {e}")
            return "other"
    
    def breakdown_task(self, user_id: str, task_title: str, task_type: Optional[str] = None) -> Dict:
        """
        Break down a task using Gemini
        Returns: subtasks, task_type, pace_multiplier
        """
        # Infer type if not provided
        if not task_type:
            task_type = self.infer_task_type(task_title)
        
        # Get user's pace multiplier
        profile = self.profile_service.ensure_profile(user_id)
        pace = self.profile_service.get_pace_multiplier(profile, task_type)
        
        # Call Gemini with pace multiplier
        prompt = PROMPT_BREAKDOWN.format(
            task_title=task_title,
            pace_multiplier=pace,
            chunk_seconds=CHUNK_SECONDS,
            chunk_minutes=int(CHUNK_SECONDS / 60)
        )
        
        try:
            response = call_gemini(prompt, temperature=0.2)
            raw_subtasks = parse_json_array(response)
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            raise Exception(f"Failed to break down task: {str(e)}")
        
        # Clean and validate subtasks
        subtasks = self._process_subtasks(raw_subtasks, pace)
        
        return {
            "subtasks": subtasks,
            "taskType": task_type,
            "paceMultiplier": pace
        }
    
    def _process_subtasks(self, raw: List[Dict], pace: float) -> List[Dict]:
        """Process and validate subtasks from Gemini"""
        required_keys = {"task", "expectedTime", "actualTime", "done"}
        min_time, max_time = 300, 2700  # 5-45 minutes
        
        cleaned = []
        for i, st in enumerate(raw[:MAX_SUBTASKS], start=1):
            # Validate keys
            if not all(k in st for k in required_keys):
                raise ValueError(f"Subtask missing required keys: {st}")
            
            # Apply pace multiplier and clamp times
            expected = int(st["expectedTime"]) * pace
            expected = max(min_time, min(expected, max_time))
            
            cleaned.append({
                "id": f"st_{i}_{uuid.uuid4().hex[:6]}",
                "task": str(st["task"]).strip(),
                "expectedTime": int(expected),
                "actualTime": 0,
                "done": False
            })
        
        return cleaned
    
    def request_breakdown(self, user_id: str, task_id: str) -> Dict:
        """
        Main entry point: Break down a task and update MongoDB
        """
        from app.services.task_service import TaskService
        
        task_service = TaskService()
        task = task_service.get_task(user_id, task_id)
        
        if not task:
            raise ValueError("Task not found")
        
        # Perform breakdown
        breakdown_result = self.breakdown_task(user_id, task["task"])
        
        # Update MongoDB
        task_service.update_task(
            user_id,
            task_id,
            {
                "subtasks": breakdown_result["subtasks"],
                "taskType": breakdown_result["taskType"],
                "paceMultiplier": breakdown_result["paceMultiplier"],
                "expectedTotalTime": sum(st["expectedTime"] for st in breakdown_result["subtasks"]),
                "needsBreakdown": False,
                "status": "ready"
            }
        )
        
        return breakdown_result
```

---

## 4. Completion & Reward Service

**File: `app/services/completion_service.py`**

```python
from typing import Dict, Optional
from datetime import datetime
from app.db import get_client
from app.services.task_service import TaskService
from app.services.profile_service import ProfileService
from app.services.reward_service import RewardService

class CompletionService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.task_service = TaskService()
        self.profile_service = ProfileService()
        self.reward_service = RewardService()
    
    async def complete_task(self, user_id: str, task_id: str) -> Dict:
        """
        Complete a task:
        1. Evaluate if user earned credit
        2. Update pace multiplier
        3. Send Solana reward if earned
        4. Return feedback
        """
        task = self.task_service.get_task(user_id, task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Calculate actual vs expected time
        expected = task.get("expectedTotalTime", 0)
        actual = task.get("actualTotalTime", 0)
        
        if expected <= 0:
            raise ValueError("Expected time not set")
        
        # Determine if credit earned
        ratio = actual / expected
        credit_earned = ratio <= 1.0
        
        # Update pace multiplier
        profile = self.profile_service.ensure_profile(user_id)
        old_multiplier = self.profile_service.get_pace_multiplier(
            profile, 
            task.get("taskType", "other")
        )
        
        profile = self.profile_service.update_pace_multiplier(
            profile,
            task.get("taskType", "other"),
            ratio,
            lr=0.15
        )
        
        new_multiplier = self.profile_service.get_pace_multiplier(
            profile,
            task.get("taskType", "other")
        )
        
        # Send reward if credit earned
        reward_amount = 0.0
        if credit_earned:
            try:
                users_col = self.db['users']
                user = users_col.find_one({"_id": user_id})
                
                reward_amount = 5.0  # Fixed reward per task
                await self.reward_service.send_reward(
                    user_id,
                    task_id,
                    user["walletAddress"],
                    reward_amount
                )
                
                # Update user stats
                users_col.update_one(
                    {"_id": user_id},
                    {
                        "$inc": {
                            "totalCreditsEarned": 1,
                            "totalTokensReceived": reward_amount
                        }
                    }
                )
            except Exception as e:
                print(f"Warning: Reward send failed: {e}")
                # Don't fail the entire completion, just log
                reward_amount = 0.0
        
        # Mark task as completed
        self.task_service.update_task(
            user_id,
            task_id,
            {
                "status": "completed",
                "completedAt": datetime.utcnow().isoformat() + "Z",
                "creditEarned": credit_earned,
                "rewardAmount": reward_amount,
                "rewardSent": reward_amount > 0
            }
        )
        
        return {
            "taskId": task_id,
            "status": "completed",
            "creditEarned": credit_earned,
            "feedback": self._get_feedback(credit_earned, ratio),
            "rewardAmount": reward_amount,
            "rewardStatus": "pending" if reward_amount > 0 else "none",
            "actualTotalTime": actual,
            "expectedTotalTime": expected,
            "timeRatio": round(ratio, 3),
            "oldPaceMultiplier": round(old_multiplier, 3),
            "newPaceMultiplier": round(new_multiplier, 3),
            "completedAt": datetime.utcnow().isoformat() + "Z"
        }
    
    def _get_feedback(self, credit_earned: bool, ratio: float) -> str:
        """Generate motivational feedback"""
        if credit_earned:
            if ratio < 0.5:
                return "Wow! 🚀 You crushed this! Way faster than expected!"
            elif ratio < 0.9:
                return "Great job! 🎉 You finished faster than expected!"
            else:
                return "Nice work! 💪 You completed this on time!"
        else:
            return "Keep practicing! 💪 Next time will be faster."
```

---

## 5. Profile Service

**File: `app/services/profile_service.py`**

```python
from typing import Dict, Optional
from datetime import datetime
from app.db import get_client

class ProfileService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.profiles_col = self.db['user_profiles']
    
    MIN_MULT = 0.6
    MAX_MULT = 1.8
    
    def ensure_profile(self, user_id: str) -> Dict:
        """Ensure user profile exists"""
        profile = self.profiles_col.find_one({"_id": user_id})
        
        if not profile:
            profile = {
                "_id": user_id,
                "paceByType": {},
                "createdAt": datetime.utcnow().isoformat() + "Z"
            }
            self.profiles_col.insert_one(profile)
        
        return profile
    
    def get_pace_multiplier(self, profile: Dict, task_type: str) -> float:
        """Get pace multiplier for task type"""
        pace_by_type = profile.get("paceByType", {}) or {}
        info = pace_by_type.get(task_type)
        
        if not info:
            return 1.0
        
        try:
            mult = float(info.get("multiplier", 1.0))
            return self._clamp(mult, self.MIN_MULT, self.MAX_MULT)
        except:
            return 1.0
    
    def update_pace_multiplier(
        self,
        profile: Dict,
        task_type: str,
        ratio: float,
        lr: float = 0.15
    ) -> Dict:
        """
        Update pace multiplier based on performance ratio
        ratio = actualTime / expectedTime
        if ratio <= 1.0: user was faster → decrease multiplier
        if ratio > 1.0: user was slower → increase multiplier
        """
        ratio = self._clamp(float(ratio), self.MIN_MULT, self.MAX_MULT)
        
        pace_by_type = profile.get("paceByType", {}) or {}
        current = pace_by_type.get(task_type, {"multiplier": 1.0, "n": 0})
        
        old = float(current.get("multiplier", 1.0))
        n = int(current.get("n", 0))
        
        # Weighted average update
        new = old * (1 - lr) + ratio * lr
        new = self._clamp(new, self.MIN_MULT, self.MAX_MULT)
        
        pace_by_type[task_type] = {
            "multiplier": new,
            "n": n + 1
        }
        
        profile["paceByType"] = pace_by_type
        
        # Save to database
        self.profiles_col.replace_one(
            {"_id": profile["_id"]},
            profile
        )
        
        return profile
    
    def _clamp(self, x: float, lo: float, hi: float) -> float:
        """Clamp value between bounds"""
        return max(lo, min(hi, x))
```

---

## 6. Reward Service

**File: `app/services/reward_service.py`**

```python
import asyncio
from typing import Optional
from datetime import datetime
from app.db import get_client
from app.sol import send_study_reward  # Import existing async function

class RewardService:
    def __init__(self):
        self.db = get_client()['todo_app']
        self.transfers_col = self.db['credit_transfers']
    
    async def send_reward(self, user_id: str, task_id: str, wallet: str, amount: float) -> str:
        """
        Send Solana reward and log transaction
        Returns: transaction hash or transfer ID
        """
        # Create pending transfer record
        transfer = {
            "userId": user_id,
            "taskId": task_id,
            "wallet": wallet,
            "amount": amount,
            "status": "pending",
            "txHash": None,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "confirmedAt": None
        }
        
        result = self.transfers_col.insert_one(transfer)
        transfer_id = str(result.inserted_id)
        
        try:
            # Send tokens asynchronously
            await send_study_reward(wallet, amount)
            
            # Update transfer status
            self.transfers_col.update_one(
                {"_id": transfer_id},
                {
                    "$set": {
                        "status": "confirmed",
                        "confirmedAt": datetime.utcnow().isoformat() + "Z"
                    }
                }
            )
            
            return transfer_id
        
        except Exception as e:
            # Mark as failed but don't crash
            self.transfers_col.update_one(
                {"_id": transfer_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e)
                    }
                }
            )
            raise
    
    def get_reward_history(self, user_id: str, limit: int = 50) -> list:
        """Get user's reward history"""
        transfers = list(
            self.transfers_col.find({"userId": user_id})
            .sort("createdAt", -1)
            .limit(limit)
        )
        
        for t in transfers:
            t["_id"] = str(t["_id"])
        
        return transfers
    
    def get_total_rewards(self, user_id: str) -> float:
        """Get total rewards earned"""
        result = self.transfers_col.aggregate([
            {"$match": {"userId": user_id, "status": "confirmed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        
        docs = list(result)
        return docs[0]["total"] if docs else 0.0
```

---

## Sample Flask/FastAPI Route Handler

**File: `app/routes/tasks.py`**

```python
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from app.services.task_service import TaskService
from app.services.breakdown_service import BreakdownService
from app.services.completion_service import CompletionService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
auth_service = AuthService()

def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract user ID from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.replace("Bearer ", "")
    user_id = auth_service.verify_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user_id

@router.post("")
async def create_task(
    request: dict,
    user_id: str = Depends(get_current_user)
):
    """Create a new task"""
    if "title" not in request or not request["title"]:
        raise HTTPException(status_code=400, detail="Title required")
    
    task_service = TaskService()
    task = task_service.create_task(
        user_id,
        request["title"],
        request.get("estimatedMinutes", 60)
    )
    
    return {"statusCode": 201, "task": task}

@router.get("")
async def get_tasks(
    user_id: str = Depends(get_current_user),
    status: Optional[str] = None
):
    """Get all user's tasks"""
    task_service = TaskService()
    tasks = task_service.get_tasks(user_id, status=status)
    
    return {"statusCode": 200, "tasks": tasks}

@router.post("/{taskId}/breakdown")
async def request_breakdown(
    taskId: str,
    user_id: str = Depends(get_current_user)
):
    """Request AI breakdown of task"""
    breakdown_service = BreakdownService()
    
    try:
        result = breakdown_service.request_breakdown(user_id, taskId)
        return {"statusCode": 200, "breakdown": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{taskId}/complete")
async def complete_task(
    taskId: str,
    user_id: str = Depends(get_current_user)
):
    """Complete a task and receive rewards"""
    completion_service = CompletionService()
    
    try:
        result = await completion_service.complete_task(user_id, taskId)
        return {"statusCode": 200, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## How to Use These Services

```python
# In your main FastAPI app:
from fastapi import FastAPI
from app.routes import tasks, auth, profile

app = FastAPI(title="Task Breakdown Reward App")

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(profile.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

**Key Points:**
1. Each service is responsible for one domain
2. Services call each other where needed
3. Database operations are abstracted in services
4. Async operations (Gemini API, Solana) are handled in services
5. Routes are thin and delegate to services
6. Easy to test services independently
7. Easy to swap implementations (e.g., use different LLM)
