# Task Breakdown & Reward App - Unified Architecture

## Overview

This app creates a gamified study experience where users:
1. **Authenticate** → Create accounts & login
2. **Input Tasks** → Write down assignments/study goals
3. **Get AI Breakdown** → Gemini breaks tasks into actionable subtasks with time estimates
4. **Study with Tracking** → Complete subtasks while app tracks time
5. **Earn Rewards** → Receive Solana tokens upon completion

---

## Current State: Features in Isolation

### 📁 File-by-File Breakdown

| File | Features | Purpose |
|------|----------|---------|
| **todo_app_mongodb.py** | HTTP server, Auth (login/signup), Task CRUD, Session mgmt | Main app server & UI |
| **gemini_client.py** | Gemini API calls | Makes API requests to Google Gemini |
| **workers_breakdown.py** | Task decomposition logic, Pace multiplier application | Breaks jobs into subtasks with time estimation |
| **sol.py** | Solana token transfers | Sends reward tokens to user wallets |
| **credit.py** | Task completion evaluation, Pace multiplier updates | Determines if user earned credit & adjusts future estimates |
| **pace.py** | Pace multiplier calculations | Tracks per-task-type performance |
| **config.py** | Environment variables & constants | Central configuration |
| **db.py** | MongoDB connection & collection helpers | Database abstraction |
| **parsers.py** | JSON parsing utilities | Extracts JSON from Gemini responses |
| **prompts.py** | Gemini prompt templates | AI prompt engineering |
| **main.py** | Runs breakdown worker for all users | Background worker (currently standalone) |

---

## Proposed Unified Flow

### **User Journey**

```
1. USER AUTHENTICATION
   ↓
2. CREATE TASK
   ↓
3. BREAKDOWN REQUEST
   ├─→ Infer task type (Gemini)
   ├─→ Get user's pace multiplier for that type
   ├─→ Generate subtasks (Gemini)
   ├─→ Store in MongoDB
   └─→ Return to user
   ↓
4. USER STUDIES & TRACKS TIME
   ├─→ Mark subtasks as done
   ├─→ Record actual time spent
   └─→ Update MongoDB
   ↓
5. COMPLETE TASK
   ├─→ Evaluate: actual time vs expected time
   ├─→ Determine if user earned credit
   ├─→ Update pace multiplier for that task type
   ├─→ Send Solana reward (if credit earned)
   └─→ Return feedback to user
   ↓
6. USER GETS REWARD
   └─→ Tokens appear in wallet
```

---

## Recommended Architecture Changes

### 🏗️ **1. Consolidate Data Models**

**MongoDB Collections should be:**

```json
{
  "users": {
    "_id": "user_mongo_id",
    "username": "string",
    "passwordHash": "string",
    "walletAddress": "solana_public_key",
    "createdAt": "ISO-8601",
    "totalCreditsEarned": 0,
    "totalTokensReceived": 0.0
  },
  
  "tasks": {
    "_id": "task_mongo_id",
    "userId": "user_mongo_id",
    "title": "string",
    "taskType": "homework|reading|lab_report|exam_prep|project|other",
    "status": "pending|in_progress|completed|abandoned",
    "expectedTotalTime": 3600,
    "actualTotalTime": 0,
    "subtasks": [
      {
        "id": "st_1_abc123",
        "task": "string",
        "expectedTime": 600,
        "actualTime": 0,
        "done": false,
        "completedAt": null
      }
    ],
    "needsBreakdown": true,
    "paceMultiplier": 1.0,
    "creditEarned": false,
    "rewardSent": false,
    "rewardAmount": 0.0,
    "createdAt": "ISO-8601",
    "completedAt": null
  },
  
  "userProfiles": {
    "_id": "user_id",
    "paceByType": {
      "homework": { "multiplier": 1.1, "n": 5 },
      "reading": { "multiplier": 0.9, "n": 3 }
    },
    "createdAt": "ISO-8601"
  },
  
  "creditTransfers": {
    "_id": "transfer_id",
    "userId": "string",
    "taskId": "string",
    "amount": 5.0,
    "txHash": "solana_transaction_hash",
    "status": "pending|confirmed|failed",
    "createdAt": "ISO-8601"
  }
}
```

---

### 🔄 **2. Service Layer Architecture**

Create service modules to separate concerns:

```
services/
├── auth_service.py          # User registration, login, session mgmt
├── task_service.py          # Create, read, update task metadata
├── breakdown_service.py      # Task decomposition (Gemini integration)
├── tracking_service.py       # Update subtask progress
├── credit_service.py         # Evaluate completion, update pace
├── reward_service.py         # Send Solana tokens
└── user_profile_service.py   # Manage pace multipliers
```

---

### 🔌 **3. HTTP API Endpoints**

**Consolidate into ONE REST API:**

```
POST   /api/auth/register         → Register user
POST   /api/auth/login            → Login user
POST   /api/auth/logout           → Logout user

POST   /api/tasks                 → Create task (needs breakdown)
GET    /api/tasks                 → Get all user tasks
GET    /api/tasks/{taskId}        → Get task details with subtasks
PATCH  /api/tasks/{taskId}        → Update task status
DELETE /api/tasks/{taskId}        → Archive task

POST   /api/tasks/{taskId}/breakdown    → Request AI breakdown
GET    /api/tasks/{taskId}/breakdown    → Get breakdown status

PATCH  /api/subtasks/{subtaskId}       → Mark subtask done, log time
POST   /api/tasks/{taskId}/complete    → Finalize task → credit + reward

GET    /api/profile                     → Get user profile & pace data
GET    /api/rewards                     → Get reward history
```

---

### 🤖 **4. Unified Breakdown Flow**

**Current issues:**
- `breakdown_task()` in todo_app_mongodb.py is a placeholder
- Actual breakdown logic in `workers_breakdown.py` is a background worker
- No real-time integration

**Solution:**
```python
# app/services/breakdown_service.py

async def request_task_breakdown(user_id: str, task_id: str):
    """
    Called when user submits a task.
    Synchronously (or async) breaks down task and stores.
    """
    task = tasks_col().find_one({"_id": ObjectId(task_id), "userId": user_id})
    if not task:
        raise ValueError("Task not found")
    
    # 1. Infer task type
    task_type = infer_task_type(task["title"])
    
    # 2. Get user's pace multiplier
    profile = ensure_profile(user_id)
    pace = get_pace_multiplier(profile, task_type)
    
    # 3. Call Gemini to break down
    subtasks = call_gemini_breakdown(task["title"], pace)
    
    # 4. Store in MongoDB
    tasks_col().update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "subtasks": subtasks,
            "taskType": task_type,
            "paceMultiplier": pace,
            "expectedTotalTime": sum(st["expectedTime"] for st in subtasks),
            "needsBreakdown": False,
            "status": "pending"
        }}
    )
    
    return {"subtasks": subtasks, "taskType": task_type, "pace": pace}
```

---

### 🎯 **5. Task Completion & Reward Flow**

**Current issues:**
- `credit.py` finalizes tasks but doesn't send rewards
- `sol.py` sends tokens but isn't called anywhere
- No unified completion endpoint

**Solution:**
```python
# app/services/completion_service.py

async def complete_task(user_id: str, task_id: str):
    """
    Called when user finishes all subtasks.
    1. Evaluate: did they earn credit?
    2. Update pace multiplier
    3. Send Solana reward
    4. Return feedback
    """
    task = tasks_col().find_one({"_id": ObjectId(task_id), "userId": user_id})
    if not task:
        raise ValueError("Task not found")
    
    # Update task status
    task["status"] = "completed"
    task["completedAt"] = now_iso()
    
    # Calculate actual time
    actual_total = sum(st.get("actualTime", 0) for st in task.get("subtasks", []))
    expected_total = task.get("expectedTotalTime", 0)
    task["actualTotalTime"] = actual_total
    
    # Evaluate credit
    ratio = actual_total / expected_total if expected_total > 0 else 0
    credit_earned = ratio <= 1.0
    task["creditEarned"] = credit_earned
    
    # Update pace multiplier
    profile = profiles_col().find_one({"_id": user_id})
    profile = update_pace_multiplier(profile, task["taskType"], ratio)
    profiles_col().replace_one({"_id": user_id}, profile)
    
    # Send reward if credit earned
    reward_amount = 5.0 if credit_earned else 0.0
    if reward_amount > 0:
        user = users_col().find_one({"_id": ObjectId(user_id)})
        await send_study_reward(user["walletAddress"], reward_amount)
        task["rewardAmount"] = reward_amount
        task["rewardSent"] = True
        
        # Log transfer
        credit_transfers_col().insert_one({
            "userId": user_id,
            "taskId": str(task_id),
            "amount": reward_amount,
            "status": "pending",
            "createdAt": now_iso()
        })
    
    tasks_col().replace_one({"_id": ObjectId(task_id)}, task)
    
    return {
        "creditEarned": credit_earned,
        "rewardAmount": reward_amount,
        "newPaceMultiplier": profile["paceByType"][task["taskType"]]["multiplier"],
        "feedback": f"{"Great job! 🎉" if credit_earned else "Keep practicing! 💪}"
    }
```

---

### ⏱️ **6. Real-time Subtask Tracking**

**Endpoint to update progress:**

```python
# PATCH /api/subtasks/{subtaskId}
{
    "done": true,
    "actualTime": 450  # seconds spent
}

# Service logic:
def update_subtask(user_id: str, subtask_id: str, done: bool, actual_time: int):
    task = tasks_col().find_one({
        "userId": user_id,
        "subtasks.id": subtask_id
    })
    
    for st in task["subtasks"]:
        if st["id"] == subtask_id:
            st["done"] = done
            st["actualTime"] = actual_time
            if done:
                st["completedAt"] = now_iso()
    
    # Check if all subtasks done
    all_done = all(st["done"] for st in task["subtasks"])
    if all_done:
        task["status"] = "ready_for_completion"
    else:
        task["status"] = "in_progress"
    
    tasks_col().replace_one({"_id": task["_id"]}, task)
```

---

## 🚀 **Implementation Roadmap**

### **Phase 1: Consolidate Backend Services** (1-2 days)
- [ ] Refactor `db.py` with complete models
- [ ] Create `services/` directory
- [ ] Extract functions from `todo_app_mongodb.py` into services
- [ ] Create unified API router

### **Phase 2: Integrate Gemini Breakdown** (1-2 days)
- [ ] Connect breakdown_service to HTTP endpoint
- [ ] Make breakdown synchronous (or async with polling)
- [ ] Test end-to-end: create task → get breakdown

### **Phase 3: Integrate Completion & Rewards** (2-3 days)
- [ ] Create completion_service
- [ ] Integrate credit.py logic
- [ ] Integrate sol.py (async token transfer)
- [ ] Test: complete task → earn credit → receive tokens

### **Phase 4: Frontend Integration** (2-3 days)
- [ ] Update HTML/Dashboard to call new API endpoints
- [ ] Add real-time subtask progress
- [ ] Display reward feedback
- [ ] Show pace improvements

### **Phase 5: Background Worker** (1 day)
- [ ] Keep `main.py` for periodic cleanup/retry
- [ ] Move breakdowns to real-time API

### **Phase 6: Testing & Polish** (2-3 days)
- [ ] Integration tests
- [ ] Error handling
- [ ] User feedback UX

---

## 🗂️ **Suggested New Project Structure**

```
hacklahoma2026/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI/Flask app startup
│   ├── config.py                  # Configuration (moved from root)
│   ├── db.py                      # MongoDB connection (moved from root)
│   │
│   ├── models/
│   │   ├── user.py               # User, Session schemas
│   │   ├── task.py               # Task, Subtask schemas
│   │   └── reward.py             # CreditTransfer schemas
│   │
│   ├── services/
│   │   ├── auth_service.py       # User registration, login, sessions
│   │   ├── task_service.py       # Task CRUD
│   │   ├── breakdown_service.py  # Gemini integration
│   │   ├── tracking_service.py   # Subtask progress
│   │   ├── credit_service.py     # Completion evaluation
│   │   ├── reward_service.py     # Solana transfers
│   │   └── profile_service.py    # Pace multipliers
│   │
│   ├── routes/
│   │   ├── auth.py               # POST /auth/login, /auth/register
│   │   ├── tasks.py              # GET, POST, PATCH /tasks
│   │   ├── subtasks.py           # PATCH /subtasks/{id}
│   │   └── profile.py            # GET /profile, /rewards
│   │
│   ├── utils/
│   │   ├── parsers.py
│   │   ├── prompts.py
│   │   └── gemini_client.py
│   │
│   └── static/
│       ├── index.html            # Main UI
│       ├── style.css
│       └── app.js
│
├── tests/
│   ├── test_auth.py
│   ├── test_breakdown.py
│   ├── test_rewards.py
│   └── test_integration.py
│
├── old/                           # Archive current files
│   ├── todo_app_mongodb.py
│   ├── main.py
│   └── ...
│
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md               # This file
└── README.md
```

---

## 🔐 **Authentication Flow**

```
User visits app → Redirect to /login page
    ↓
User enters username & password → POST /auth/register or /auth/login
    ↓
Server validates, hashes password, stores user
    ↓
Server creates session token (or JWT)
    ↓
Client stores token in httpOnly cookie or LocalStorage
    ↓
All subsequent requests include token in header or cookie
    ↓
Server verifies token on protected routes
```

---

## 💰 **Reward System**

```
Task Completion Flow:
├─ User marks all subtasks done
├─ Frontend calls: POST /api/tasks/{taskId}/complete
├─ Backend evaluates:
│  ├─ actual_time vs expected_time
│  ├─ Ratio determines if credit earned
│  └─ Updates pace multiplier for next similar task
├─ If credit earned:
│  ├─ Sends Solana tokens async
│  ├─ Logs transfer in MongoDB
│  └─ Returns reward feedback to user
└─ User sees reward notification
```

**Reward Logic:**
- Task type: homework, reading, lab_report, exam_prep, project, other
- User has pace multiplier per type (0.6–1.8x)
- If user beats expected time: **+5 tokens** + multiplier decreases (0.95x)
- If user misses expected time: **+0 tokens** + multiplier increases (1.05x)
- This adapts expectations to user's actual speed

---

## 🛠️ **Tech Stack Recommendations**

| Layer | Current | Recommended |
|-------|---------|-------------|
| **Backend Framework** | http.server (standard lib) | FastAPI or Flask |
| **Database** | MongoDB ✓ | Keep MongoDB ✓ |
| **Async Tasks** | None | Celery (optional) + RabbitMQ |
| **LLM Client** | urllib (custom) | anthropic or openai lib + retry |
| **Solana Client** | solders ✓ | Keep solders ✓ |
| **Auth** | Custom sessions | JWT or OAuth2 |
| **Frontend** | Vanilla HTML/SQL | React / Vue 3 (optional) |
| **API Documentation** | None | Auto-generated (FastAPI) |

---

## 📊 **Key Metrics to Track**

Once unified, monitor:
- **Completion rate:** Tasks finished / Tasks created per user
- **Credit ratio:** Completed within expected time / Total completed
- **Pace evolution:** How much multiplier changed per task type
- **Reward distribution:** Total tokens sent, frequency per user
- **User retention:** Days active, tasks per session

---

## ✅ **Next Steps**

1. **Review** this architecture with your team
2. **Pick a web framework** (FastAPI is fastest to implement)
3. **Start Phase 1** (consolidate services)
4. **Deploy incrementally** (test each service in isolation first)
5. **Monitor** with logging and error tracking

---

**Questions?** Each service can be built independently, so you can parallelize development across multiple teammates.
