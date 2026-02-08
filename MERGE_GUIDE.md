# Project Merge Summary & Quick Start

## 📋 What You Have

Your repository has **7 key features spread across 11 files**. Here's the summary:

| Feature | Current File(s) | Status |
|---------|-----------------|--------|
| **User Authentication** | `todo_app_mongodb.py` | ✅ Implemented (basic) |
| **HTTPServer & Frontend** | `todo_app_mongodb.py` | ✅ Implemented (vanilla HTML) |
| **Task Management** | `todo_app_mongodb.py` | ✅ Implemented (basic) |
| **AI Task Breakdown** | `workers_breakdown.py` | ✅ Implemented (background worker only) |
| **Pace Tracking** | `pace.py`, `workers_breakdown.py` | ✅ Implemented |
| **Credit Evaluation** | `credit.py` | ✅ Implemented (not integrated) |
| **Solana Rewards** | `sol.py` | ✅ Implemented (not integrated) |
| **Gemini Integration** | `gemini_client.py`, `prompts.py` | ✅ Implemented |
| **Parsing & Utils** | `parsers.py`, `config.py`, `db.py`  | ✅ Implemented |
| **Unified Flow** | ❌ MISSING | 🔴 Not connected |

---

## 🎯 The Problem

**All features exist but are NOT connected in a single user flow.**

Current state:
- Users can **register and login** ✅
- Users can **create tasks** ✅
- Users can **see a breakdown placeholder** (but not real breakdown) ❌
- Users **cannot track progress** ❌
- **Rewards are never sent** ❌
- **Pace tracking sits in background worker only** ❌

---

## ✨ The Solution

### **3 Core Steps to Merge Everything:**

### **1️⃣ Convert to Service Layer Pattern** (1-2 days)

Move business logic out of `todo_app_mongodb.py` into service modules:

```
Before: Everything in one 1700-line file
After:  
├── auth_service.py        (200 lines)
├── task_service.py        (200 lines)
├── breakdown_service.py   (200 lines)
├── completion_service.py  (250 lines)
├── reward_service.py      (150 lines)
├── profile_service.py     (150 lines)
└── route handlers         (thin)
```

**Benefits:**
- Testable in isolation
- Reusable across endpoints
- Easier to maintain
- Clear separation of concerns

### **2️⃣ Connect Endpoints to Services** (1-2 days)

Create REST API that calls services:

```
POST   /api/tasks/{id}/breakdown    → breakdown_service.request_breakdown()
PATCH  /api/subtasks/{id}           → task_service.mark_subtask_done()
POST   /api/tasks/{id}/complete     → completion_service.complete_task()
```

**Before (placeholder):**
```python
def breakdown_task(task_title, user_id):
    return {
        "sections": [
            {"title": "Getting Started", "expectedTime": 900, ...}
        ]
    }
```

**After (real):**
```python
async def breakdown_task(user_id, task_id):
    # Call Gemini API
    # Apply pace multiplier
    # Store in MongoDB
    # Return result
    return real_breakdown
```

### **3️⃣ Enable Real-time Reward Flow** (2-3 days)

Wire up completion → credit evaluation → Solana transfer:

```python
# When user completes task:
1. Evaluate: did_they_earn_credit = actual_time <= expected_time
2. Update: pace_multiplier *= (0.95 if earned_credit else 1.05)
3. Reward: send 5 SOL tokens if credit_earned
4. Feedback: show result to user
```

---

## 📁 Recommended New Project Structure

Create this structure (keep old files in `old/` folder):

```
hacklahoma2026/
├── app/
│   ├── main.py                          # FastAPI app
│   ├── config.py                        # Settings
│   ├── db.py                            # DB connection
│   │
│   ├── models/
│   │   ├── schemas.py                   # Pydantic schemas (optional)
│   │   └── types.py                     # TypedDicts
│   │
│   ├── services/
│   │   ├── auth_service.py              # NEW: Registration, login
│   │   ├── task_service.py              # NEW: Task CRUD
│   │   ├── breakdown_service.py         # NEW: Gemini integration
│   │   ├── completion_service.py        # NEW: Evaluation + rewards
│   │   ├── reward_service.py            # NEW: Solana transfers
│   │   └── profile_service.py           # NEW: Pace tracking
│   │
│   ├── routes/
│   │   ├── auth.py                      # NEW: Auth endpoints
│   │   ├── tasks.py                     # NEW: Task endpoints
│   │   ├── subtasks.py                  # NEW: Subtask endpoints
│   │   └── profile.py                   # NEW: Profile endpoints
│   │
│   ├── utils/
│   │   ├── gemini_client.py             # Keep: Gemini API calls
│   │   ├── parsers.py                   # Keep: JSON parsing
│   │   ├── prompts.py                   # Keep: Prompt templates
│   │   └── solana.py                    # Keep: Solana logic
│   │
│   └── static/
│       ├── index.html                   # Updated UI
│       ├── style.css                    # Styling
│       └── main.js                      # Frontend logic
│
├── tests/                               # NEW: Test files
├── old/                                 # Backup of current code
├── ARCHITECTURE.md                      # NEW: This document
├── API_REFERENCE.md                     # NEW: API spec
├── SERVICE_EXAMPLES.md                  # NEW: Code examples
├── requirements.txt                     # Keep: Add fastapi, uvicorn
├── .env.example                         # Keep: Env template
└── README.md                            # Update
```

---

## 🚀 Quick Start (Choose One Path)

### **Path A: Start from Scratch (Recommended)**

```bash
# 1. Create new FastAPI project
mkdir app && cd app
touch __init__.py main.py config.py db.py

# 2. Create services
mkdir services
touch services/{auth,task,breakdown,completion,reward,profile}_service.py

# 3. Create routes
mkdir routes
touch routes/{auth,tasks,subtasks,profile}.py

# 4. Create utils (copy from existing)
mkdir utils
cp ../{gemini_client,parsers,prompts,sol}.py utils/

# 5. Update requirements
pip install fastapi uvicorn pyjwt pymongo solana solders

# 6. Implement each service (start with auth_service.py)
# See SERVICE_EXAMPLES.md for code
```

### **Path B: Refactor Existing Code**

```bash
# 1. Backup current files
mkdir old
mv todo_app_mongodb.py workers_breakdown.py main.py old/

# 2. Extract functions from old files into new services
# Use SERVICE_EXAMPLES.md as template

# 3. Create thin route handlers that call services

# 4. Test each service independently

# 5. Update HTML frontend to call new API endpoints
```

---

## 📊 Data Flow After Merge

```
USER SIGNUP
├─ POST /auth/register (username, password, wallet)
├─ AuthService.register_user()
├─ Store in MongoDB
└─ Return JWT token

CREATE TASK
├─ POST /tasks (title, estimatedMinutes)
├─ TaskService.create_task()
├─ Return task with ID
└─ Frontend shows "Ready for breakdown" button

REQUEST BREAKDOWN
├─ POST /tasks/{id}/breakdown
├─ BreakdownService.request_breakdown()
│  ├─ Infer task type (Gemini)
│  ├─ Get pace multiplier (ProfileService)
│  ├─ Break down task (Gemini)
│  └─ Store in MongoDB
├─ Return subtasks to user
└─ Frontend shows subtask checklist

TRACK PROGRESS
├─ PATCH /subtasks/{id} (mark done, log time)
├─ TaskService.mark_subtask_done()
├─ Check if all done
└─ If yes: Show "Complete Task" button

COMPLETE TASK
├─ POST /tasks/{id}/complete
├─ CompletionService.complete_task()
│  ├─ Calculate: ratio = actual/expected
│  ├─ ProfileService.update_pace_multiplier()
│  ├─ If ratio <= 1.0:
│  │  ├─ RewardService.send_reward() (async)
│  │  └─ Log transfer in MongoDB
│  └─ Return result
├─ Return feedback + reward info
└─ Frontend shows "✨ You earned 5 SOL!" or "Try again 💪"

REWARD (Async)
├─ RewardService sends Solana tokens
├─ Watch blockchain for confirmation
├─ Update transfer status in MongoDB
└─ User sees token in wallet
```

---

## ✅ Implementation Checklist

### **Week 1: Services**
- [ ] Create `services/` directory
- [ ] Implement `auth_service.py`
- [ ] Implement `task_service.py`
- [ ] Implement `profile_service.py`
- [ ] Test services with pytest

### **Week 1-2: Breakdown**
- [ ] Implement `breakdown_service.py`
- [ ] Integration test: create task → get breakdown
- [ ] Update MongoDB to store breakdown results
- [ ] Handle Gemini API errors

### **Week 2: Completion & Rewards**
- [ ] Implement `completion_service.py`
- [ ] Implement `reward_service.py`
- [ ] Integration test: complete task → earn credit → send tokens
- [ ] Handle Solana wallet errors

### **Week 2-3: API Routes**
- [ ] Create `routes/auth.py` with endpoints
- [ ] Create `routes/tasks.py` with endpoints
- [ ] Create `routes/subtasks.py` with endpoints
- [ ] Add JWT authentication middleware

### **Week 3: Frontend**
- [ ] Update HTML form for task creation
- [ ] Add breakdown display UI
- [ ] Add subtask progress tracker
- [ ] Add reward notification
- [ ] Connect all forms to new API

### **Week 3-4: Testing & Polish**
- [ ] Integration tests
- [ ] Error handling
- [ ] Logging
- [ ] Security review
- [ ] Performance testing
- [ ] Documentation

---

## 🔑 Key Files to Read/Understand

| File | Why | Reading Time |
|------|-----|--------------|
| `ARCHITECTURE.md` | System design | 15 min |
| `API_REFERENCE.md` | API spec | 10 min |
| `SERVICE_EXAMPLES.md` | Code examples | 30 min |
| `todo_app_mongodb.py` | Current implementation | 45 min |
| `workers_breakdown.py` | Breakdown logic | 20 min |
| `sol.py` | Solana integration | 15 min |
| `credit.py` | Credit evaluation | 10 min |

---

## 💡 Pro Tips

### **1. Start Small, Test Often**
- Implement `auth_service` first
- Write unit tests for each service
- Test with Postman/curl before integrating

### **2. Use Async for I/O**
```python
# Gemini API calls (slow) → make async
async def call_gemini_async(prompt):
    ...

# Solana transfers (very slow) → make async
async def send_tokens():
    ...

# Regular DB operations → can be sync, but async ok too
```

### **3. Error Handling**
```python
try:
    breakdown = breakdown_service.request_breakdown(user_id, task_id)
except GeminiError:
    return {"error": "AI service unavailable, try again later"}
except SolanaError:
    return {"error": "Reward pending, check wallet later"}
except ValidationError:
    return {"error": "Invalid data"}
```

### **4. Logging Everything**
```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"User {user_id} completed task {task_id}")
logger.warning(f"Solana transaction slow: {tx_hash}")
logger.error(f"Gemini API failed: {error}")
```

### **5. Test on Devnet First**
- Use Solana Devnet for token testing
- Don't use real wallet until production ready
- Monitor RPC rate limits

---

## 🎓 Learning Resources

If stuck on any component:

**Authentication:**
- [JWT tutorial](https://jwt.io/introduction)
- [FastAPI security docs](https://fastapi.tiangolo.com/tutorial/security/)

**Gemini API:**
- [Gemini API docs](https://ai.google.dev/docs)
- Your existing `gemini_client.py` + `prompts.py`

**MongoDB:**
- [PyMongo tutorial](https://pymongo.readthedocs.io/)
- Your existing `db.py`

**Solana:**
- [Solana dev guide](https://solana.com/docs/core/clusters)
- Your existing `sol.py`

**FastAPI:**
- [Official tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Request/response models](https://fastapi.tiangolo.com/tutorial/body/)

---

## 🤔 FAQ

**Q: Should I use FastAPI or Flask?**
> FastAPI is faster to build and has auto-documentation. Flask if you prefer simplicity.

**Q: How long will this take?**
> 2-3 weeks for one developer, 1 week for a team of 2-3.

**Q: Do I need to rewrite everything?**
> No! Copy functions from old files into new services, then refactor.

**Q: Which endpoint should I implement first?**
> POST /auth/register → POST /auth/login → GET /profile
> Then POST /tasks → POST /tasks/{id}/breakdown

**Q: How do I test without Solana?**
> Mock the `send_study_reward()` function in tests, or use Solana devnet.

**Q: Can I keep using the HTTP server?**
> Yes, temporarily. But replace with FastAPI/Flask once services stabilize.

---

## 📞 Need Help?

1. **Read ARCHITECTURE.md** - It explains the whole system
2. **Check SERVICE_EXAMPLES.md** - Copy-paste code templates
3. **Reference API_REFERENCE.md** - See what each endpoint does
4. **Debug with logging** - Add `print()` or `logger.info()` everywhere
5. **Test incrementally** - Don't wait until the end

---

## 🎉 Success Metrics

When done, you should have:

✅ Users can register & login  
✅ Users can create & list tasks  
✅ Users can request AI breakdown in real-time  
✅ Users can track subtask progress  
✅ Users can complete tasks and see instant feedback  
✅ Users receive Solana tokens automatically  
✅ Users' pace multipliers update based on performance  

**Total**: One cohesive app flow from authentication → task creation → AI breakdown → tracking → completion → rewards

---

**You have all the building blocks. Now it's time to assemble them into one beautiful machine.** 🚀

Good luck!
