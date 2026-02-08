# API Reference & Implementation Guide

## REST API Endpoints

### **Authentication**

```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password",
  "walletAddress": "xyz...abc"  # User's Solana wallet
}

Response: 200
{
  "userId": "507f1f77bcf86cd799439011",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "username": "john_doe"
}
```

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password"
}

Response: 200
{
  "userId": "507f1f77bcf86cd799439011",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "username": "john_doe"
}
```

```http
POST /api/auth/logout
Authorization: Bearer <token>

Response: 204 No Content
```

---

### **Task Management**

```http
POST /api/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Complete essay on climate change",
  "estimatedMinutes": 120
}

Response: 201
{
  "taskId": "507f1f77bcf86cd799439012",
  "title": "Complete essay on climate change",
  "status": "pending",
  "needsBreakdown": true,
  "createdAt": "2026-02-08T10:30:00Z"
}
```

```http
GET /api/tasks
Authorization: Bearer <token>

Response: 200
{
  "tasks": [
    {
      "taskId": "507f1f77bcf86cd799439012",
      "title": "Complete essay on climate change",
      "status": "in_progress",
      "taskType": "reading",
      "expectedTotalTime": 3600,
      "actualTotalTime": 1800,
      "subtasksCompleted": 3,
      "subtasksTotal": 8,
      "completionPercent": 37.5,
      "paceMultiplier": 1.05,
      "createdAt": "2026-02-08T10:30:00Z"
    }
  ]
}
```

```http
GET /api/tasks/{taskId}
Authorization: Bearer <token>

Response: 200
{
  "taskId": "507f1f77bcf86cd799439012",
  "title": "Complete essay on climate change",
  "taskType": "reading",
  "status": "in_progress",
  "expectedTotalTime": 3600,
  "actualTotalTime": 1800,
  "paceMultiplier": 1.05,
  "subtasks": [
    {
      "id": "st_1_abc123",
      "task": "Research current climate data and statistics",
      "expectedTime": 600,
      "actualTime": 450,
      "done": true,
      "completedAt": "2026-02-08T11:00:00Z"
    },
    {
      "id": "st_2_def456",
      "task": "Create outline for essay",
      "expectedTime": 300,
      "actualTime": 250,
      "done": true,
      "completedAt": "2026-02-08T11:15:00Z"
    },
    {
      "id": "st_3_ghi789",
      "task": "Write introduction and thesis",
      "expectedTime": 900,
      "actualTime": 0,
      "done": false
    }
  ],
  "createdAt": "2026-02-08T10:30:00Z"
}
```

```http
PATCH /api/tasks/{taskId}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "in_progress"  # or "completed", "abandoned"
}

Response: 200
{
  "message": "Task updated",
  "task": { ... }
}
```

---

### **Task Breakdown**

```http
POST /api/tasks/{taskId}/breakdown
Authorization: Bearer <token>

Response: 202 (Accepted - Processing)
{
  "breakdownRequestId": "uuid-12345",
  "status": "processing",
  "estimatedSeconds": 3
}
```

```http
GET /api/tasks/{taskId}/breakdown
Authorization: Bearer <token>

Response: 200
{
  "status": "complete",
  "taskType": "reading",
  "paceMultiplier": 1.05,
  "subtasks": [
    {
      "id": "st_1_abc123",
      "task": "Research current climate data and statistics",
      "expectedTime": 630,  # 600s * 1.05 multiplier
      "actualTime": 0,
      "done": false
    },
    ...
  ]
}
```

---

### **Subtask Tracking**

```http
PATCH /api/subtasks/{subtaskId}
Authorization: Bearer <token>
Content-Type: application/json

{
  "done": true,
  "actualTime": 450  # seconds
}

Response: 200
{
  "subtaskId": "st_1_abc123",
  "done": true,
  "actualTime": 450,
  "expectedTime": 630,
  "taskStatus": "in_progress",
  "allSubtasksDone": false
}
```

---

### **Task Completion & Rewards**

```http
POST /api/tasks/{taskId}/complete
Authorization: Bearer <token>

Response: 200
{
  "taskId": "507f1f77bcf86cd799439012",
  "status": "completed",
  "creditEarned": true,
  "feedback": "Great job! 🎉 You completed this faster than expected!",
  "rewardAmount": 5.0,
  "rewardStatus": "pending",
  "rewardTxHash": null,
  "newPaceMultiplier": 1.0,
  "actualTotalTime": 1750,
  "expectedTotalTime": 3600,
  "timeRatio": 0.486
}
```

---

### **User Profile**

```http
GET /api/profile
Authorization: Bearer <token>

Response: 200
{
  "userId": "507f1f77bcf86cd799439011",
  "username": "john_doe",
  "walletAddress": "xyz...abc",
  "totalTasksCompleted": 12,
  "totalTasksCreated": 18,
  "completionRate": 0.667,
  "totalTokensReceived": 45.5,
  "creditsEarned": 9,
  "paceByType": {
    "homework": {
      "multiplier": 1.2,
      "n": 5,
      "trend": "improving"
    },
    "reading": {
      "multiplier": 0.95,
      "n": 3,
      "trend": "stable"
    },
    "exam_prep": {
      "multiplier": 1.15,
      "n": 4,
      "trend": "improving"
    }
  },
  "createdAt": "2026-01-15T08:00:00Z",
  "lastActivityAt": "2026-02-08T11:30:00Z"
}
```

---

### **Reward History**

```http
GET /api/rewards
Authorization: Bearer <token>

Response: 200
{
  "rewards": [
    {
      "rewardId": "507f1f77bcf86cd799439020",
      "taskId": "507f1f77bcf86cd799439012",
      "taskTitle": "Complete essay on climate change",
      "amount": 5.0,
      "status": "confirmed",
      "txHash": "5qHnguPVZxYXQ...",
      "createdAt": "2026-02-08T11:45:00Z",
      "confirmedAt": "2026-02-08T11:50:00Z"
    },
    {
      "rewardId": "507f1f77bcf86cd799439019",
      "taskId": "507f1f77bcf86cd799439011",
      "taskTitle": "Read chapter 5-7",
      "amount": 5.0,
      "status": "confirmed",
      "txHash": "7kPmloqQwAZRa...",
      "createdAt": "2026-02-07T14:20:00Z",
      "confirmedAt": "2026-02-07T14:25:00Z"
    }
  ],
  "totalRewards": 45.5,
  "pendingRewards": 0.0
}
```

---

## Error Responses

All errors follow this format:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_request",
  "message": "Task title is required",
  "timestamp": "2026-02-08T10:30:00Z"
}
```

### Common Error Codes

| Code | Error | Message |
|------|-------|---------|
| 400 | `invalid_request` | Missing or invalid parameters |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | User doesn't have permission |
| 404 | `not_found` | Resource not found |
| 409 | `conflict` | Username already exists |
| 429 | `rate_limited` | Too many requests |
| 500 | `server_error` | Internal server error |

---

## Implementation Checklist by Phase

### ✅ **Phase 1: Consolidate Services** (Days 1-2)

- [ ] Create `app/services/` directory
- [ ] Move `auth_service.py` logic from `todo_app_mongodb.py`
  - `register_user()`, `login_user()`, `verify_session()`
- [ ] Create `task_service.py` 
  - `create_task()`, `get_user_tasks()`, `get_task_details()`
- [ ] Create `profile_service.py`
  - `get_user_profile()`, `get_pace_multiplier()`, `ensure_profile()`
- [ ] Create `app/routes/` directory with route handlers
- [ ] Refactor `db.py` to use config constants
- [ ] Add JWT token library: `pip install pyjwt`

**Test**: Can register user → Login → Get profile

---

### ✅ **Phase 2: Breakdown Integration** (Days 2-3)

- [ ] Create `breakdown_service.py`
  - `infer_task_type()` - call Gemini
  - `breakdown_task()` - call Gemini with pace multiplier
  - `request_breakdown()` - triggerable from HTTP
- [ ] Create POST/GET `/api/tasks/{taskId}/breakdown`
- [ ] Integrate `workers_breakdown.py` logic
- [ ] Add async support (optional: `asyncio`, `httpx`)
- [ ] Add timeout handling & error recovery

**Test**: Create task → Request breakdown → Get subtasks in response

---

### ✅ **Phase 3: Completion & Rewards** (Days 3-5)

- [ ] Create `completion_service.py`
  - `complete_task()` - evaluate credit
  - Integrate `credit.py` logic
- [ ] Create `reward_service.py`
  - `send_reward()` - wraps `sol.py` async call
  - Track reward status in MongoDB
- [ ] Create POST `/api/tasks/{taskId}/complete`
- [ ] Create GET `/api/rewards` endpoint
- [ ] Add Solana transaction monitoring
- [ ] Handle async errors (wallet not found, insufficient funds, etc.)

**Test**: Complete task with credit → Check that tokens sent → Verify in wallet

---

### ✅ **Phase 4: Subtask Tracking** (Days 5-6)

- [ ] Create `tracking_service.py`
  - `update_subtask()` - mark done, log time
  - Check if all subtasks done
- [ ] Create PATCH `/api/subtasks/{subtaskId}`
- [ ] Update task status automatically
- [ ] Add real-time progress calculation

**Test**: Mark subtasks done one-by-one → Verify task status changes → Auto-enable completion

---

### ✅ **Phase 5: Frontend Updates** (Days 6-7)

- [ ] Update HTML form for task creation
- [ ] Add task details view with subtasks
- [ ] Add subtask progress tracking UI
- [ ] Add reward notification pop-up
- [ ] Add user profile dashboard
- [ ] Add reward history view
- [ ] Connect all forms to new API endpoints

**Test**: End-to-end flow: login → create task → get breakdown → track progress → complete → see reward

---

### ✅ **Phase 6: Polish & Testing** (Days 7-8)

- [ ] Write integration tests
- [ ] Add error handling & user feedback
- [ ] Add logging for debugging
- [ ] Performance test with multiple concurrent users
- [ ] Solana testnet validation
- [ ] Security review (password hashing, token validation, SQL injection)
- [ ] Documentation & README

---

## Quick Command Reference

### Run the unified app:
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGODB_URI="mongodb://..."
export GEMINI_API_KEY="..."
export token_address="..."
export sol_key="..."

# Run with FastAPI (recommended)
pip install fastapi uvicorn
uvicorn app.main:app --reload --port 8000

# Or with Flask
# pip install flask
# python -m flask run
```

### Run tests:
```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Monitor Solana transactions:
```bash
curl "https://api.devnet.solana.com" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getSignatureStatuses","params":[[<tx_hash>]]}'
```

---

## Environment Variables

```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=todo_app

# Gemini API
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# Solana
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_TOKEN_ADDRESS=TokenMintPublicKey...
SOLANA_TREASURY_KEY=base58-encoded-keypair

# Server
PORT=8000
DEBUG=true

# JWT
JWT_SECRET=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
```

---

## Recommended Testing Workflow

1. **Unit Tests** (each service)
   - Auth: register, login, password validation
   - Task: create, retrieve, update status
   - Breakdown: task type inference, subtask generation
   - Completion: credit calculation, pace update
   - Reward: token transfer logic

2. **Integration Tests**
   - Full flow: auth → create task → breakdown → track → complete → reward
   - Error scenarios: missing data, API failures, timeout

3. **Manual Testing**
   - UI flow end-to-end
   - Solana token transfer on testnet
   - Pace multiplier changes over multiple tasks

4. **Load Testing**
   - Multiple users creating tasks simultaneously
   - Gemini API rate limiting
   - MongoDB connection pooling

---

## Deployment Checklist

- [ ] Environment variables set on server
- [ ] MongoDB backup configured
- [ ] Solana mainnet wallet funded
- [ ] Gemini API quota verified
- [ ] CORS configured for production domain
- [ ] SSL/TLS enabled (HTTPS)
- [ ] Rate limiting enabled
- [ ] Error logging configured (Sentry, etc.)
- [ ] Monitoring & alerts set up
- [ ] Database indexes created
- [ ] Read replicas configured (optional)
