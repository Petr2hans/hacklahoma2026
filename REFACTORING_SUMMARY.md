# Unified Task Breakdown & Reward App - Refactoring Complete

## What Was Changed

This refactoring consolidates all app features into one unified flow while maintaining backward compatibility with the existing HTTP server (no new frameworks added).

### **Service Modules Created**

1. **auth_service.py** - User authentication
   - `register_user()` - Create new user with validation
   - `login_user()` - Authenticate user
   - `update_user_wallet()` - Store Solana wallet address
   - `update_user_tokens()` - Track earned rewards

2. **task_service.py** - Task management
   - `create_task()` - Create new task
   - `get_user_tasks()` - Fetch all user tasks
   - `get_task_by_id()` - Get single task
   - `mark_subtask_done()` - Log progress with time tracking
   - `archive_task()` - Soft delete
   - `update_task_breakdown()` - Store AI breakdown results
   - `complete_task()` - Mark as completed

3. **breakdown_service.py** - AI-powered task breakdown
   - `infer_task_type()` - Use Gemini to classify task
   - `breakdown_task()` - Use Gemini to generate subtasks with time estimates
   - `request_breakdown()` - Main entry point that coordinates breakdown and storage
   - Integrates pace multiplier tracking for personalized time estimates
   - Returns structured sections and flat subtask lists

4. **completion_service.py** - Task completion with rewards
   - `evaluate_task_completion()` - Calculate credit earned based on time ratio
   - `complete_task_with_reward()` - End-to-end: evaluate → update pace → send reward
   - `get_reward_history()` - Fetch past rewards and transfer status
   - Automatic Solana token transfer on task completion (if credit earned)
   - Async reward sending (non-blocking)

### **Main App Changes (todo_app_mongodb.py)**

**Before:**
- All logic mixed in one 1700+ line file
- Placeholder task breakdown function
- No real integration between features
- Credits/rewards never sent

**After:**
- Clean service layer separation
- Real Gemini API integration for breakdowns
- Complete task flow: create → breakdown → track → complete → reward
- New unified endpoints:
  - `/api/tasks-complete` - Complete task with full evaluation and rewards
  - `/api/breakdown` - Real breakdown using Gemini + pace tracking
  - Updated `/api/tasks` - Now uses task_service
  - Updated `/api/rewards` - Get reward history

### **Key Features of Unified Flow**

```
User Registration/Login
     ↓
Create Task (title)
     ↓
Request AI Breakdown (Gemini)
     ├→ Infer task type
     ├→ Apply pace multiplier
     ├→ Generate subtasks with time estimates
     └→ Store in MongoDB
     ↓
Track Progress (mark subtasks done, log time)
     ├→ Update actual time spent
     └→ Check completion status
     ↓
Complete Task
     ├→ Evaluate: actual_time vs expected_time
     ├→ Update pace multiplier (faster/slower)
     ├→ Send 5 SOL token if credit earned (async)
     └→ Return feedback to user
     ↓
View Rewards (reward history, total earned)
```

### **Database Schema**

All data is stored in MongoDB with these collections:

- **users** - User accounts with wallets and stats
- **tasks** - Tasks with subtasks, time tracking, status
- **user_profiles** - Per-task-type pace multipliers
- **credit_transfers** - Reward transfer logs
- **sessions** - Study session logs

### **Environment Variables Required**

```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=todo_app

# Gemini API
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# Solana (Devnet for testing)
token_address=TokenMintAddress...
sol_key=base58-encoded-treasury-keypair

# Server
PORT=8000
```

## **How to Deploy to Render.com**

### Step 1: Prepare Your Repository

```bash
# Ensure all Python files are in root
# Check requirements.txt has all dependencies
pip freeze > requirements.txt

# Verify essential files exist:
# - todo_app_mongodb.py (main)
# - auth_service.py
# - task_service.py
# - breakdown_service.py
# - completion_service.py
# - db.py, config.py
# - gemini_client.py, parsers.py, prompts.py
# - sol.py, pace.py, credit.py
```

### Step 2: Update requirements.txt

```bash
pip install \
  pymongo \
  solana \
  solders \
  google-generativeai \
  httpx \
  aiohttp

pip freeze > requirements.txt
```

### Step 3: Create Server Start Script

Create `render_start.sh`:

```bash
#!/bin/bash
python todo_app_mongodb.py
```

Make it executable:
```bash
chmod +x render_start.sh
```

### Step 4: Create render.yaml

Create `render.yaml` in your repository root:

```yaml
services:
  - type: web
    name: task-reward-app
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python todo_app_mongodb.py
    envVars:
      - key: MONGODB_URI
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: token_address
        sync: false
      - key: sol_key
        sync: false
      - key: PORT
        value: "8000"
```

### Step 5: Deploy to Render

1. Push code to GitHub
2. Go to https://dashboard.render.com
3. Create new **Web Service**
4. Connect your GitHub repository
5. Set **Build Command**: `pip install -r requirements.txt`
6. Set **Start Command**: `python todo_app_mongodb.py`
7. Add **Environment Variables**:
   - MONGODB_URI (from MongoDB Atlas)
   - GEMINI_API_KEY (from Google Cloud)
   - token_address (Solana token mint)
   - sol_key (Treasury keypair)
8. Deploy!

### Step 6: Set Environment Variables on Render

In your Render dashboard:

1. Go to service settings
2. Click "Environment"
3. Add variables:
   ```
   MONGODB_URI = mongodb+srv://...
   GEMINI_API_KEY = xxx
   token_address = xxx
   sol_key = xxx
   ```
4. Save and redeploy

### Step 7: Monitor Deployment

```bash
# Watch logs
tail -f logs

# Check status
curl https://your-service.onrender.com/
```

## **Testing the App**

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGODB_URI="mongodb://localhost:27017/"
export GEMINI_API_KEY="your-key"
export token_address="your-token"
export sol_key="your-key"

# Run the app
python todo_app_mongodb.py

# Access at http://localhost:8000
```

### Test Full Flow Manually

1. **Register** at `/register`
2. **Login** with credentials created
3. **Create Task** - Type task name and press +
4. **Wait for Breakdown** - Gemini will break it down automatically
5. **Track Progress** - Click subtasks to mark as done
6. **Complete Task** - When all done, click the complete button
7. **Receive Reward** - If you beat the time estimate, you'll get SOL tokens!

### Test API Directly

```bash
# Register
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# Create task
curl -X GET http://localhost:8000/api/tasks \
  -H "Cookie: session_token=YOUR_TOKEN"
```

## **File Structure After Refactoring**

```
hacklahoma2026/
├── todo_app_mongodb.py          # Main HTTP server (refactored)
├── auth_service.py               # NEW: Authentication service
├── task_service.py               # NEW: Task management service
├── breakdown_service.py           # NEW: AI breakdown service
├── completion_service.py          # NEW: Completion & rewards service
├── db.py                          # MongoDB connection (unchanged)
├── config.py                      # Configuration (updated)
├── gemini_client.py               # Gemini API (unchanged)
├── parsers.py                     # JSON parsing (unchanged)
├── prompts.py                     # Gemini prompts (unchanged)
├── sol.py                         # Solana integration (fixed)
├── pace.py                        # Pace multiplier (unchanged)
├── credit.py                      # Credit evaluation (now integrated)
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── render.yaml                    # Render deployment config
├── REFACTORING_SUMMARY.md         # This file
├── ARCHITECTURE.md                # System design documentation
└── API_REFERENCE.md              # API endpoint documentation
```

## **Key Improvements**

✅ **Unified Flow** - All features work together seamlessly  
✅ **Real Gemini Integration** - Tasks actually broken down by AI  
✅ **Pace Tracking** - System learns your speed per task type  
✅ **Real Rewards** - Solana tokens sent on task completion  
✅ **Clean Architecture** - Services separated from HTTP handlers  
✅ **No New Frameworks** - Still using standard library HTTP server  
✅ **Render Compatible** - Easy deployment with environment variables  
✅ **Backward Compatible** - Existing API endpoints still work  
✅ **Error Handling** - Graceful fallbacks if Gemini/Solana unavailable  
✅ **Async Rewards** - Non-blocking token transfers don't slow down UI  

## **Next Steps for Production**

1. **Add Rate Limiting** - Prevent Gemini API abuse
2. **Add Monitoring** - Use Sentry for error tracking
3. **Add Logging** - Use structured logging for debugging
4. **Database Backups** - Configure MongoDB Atlas backups
5. **API Authentication** - Add JWT tokens if needed
6. **Frontend Updates** - Update HTML to call new `/api/tasks-complete` endpoint
7. **Testing** - Add integration tests for full flow
8. **Security** - Review password handling, wallet storage, API keys

## **Troubleshooting**

**Gemini breaks down all tasks to same structure?**
- Check GEMINI_API_KEY is set correctly
- Check internet connection to Google API
- Check rate limiting hasn't kicked in

**Solana rewards not sending?**
- Verify token_address is correct
- Verify sol_key is valid base58 keypair
- Check Treasury wallet has enough tokens
- Check network is set to devnet

**MongoDB connection failing?**
- Check MONGODB_URI connection string
- Verify MongoDB Atlas cluster is running
- Check IP whitelist allows Render server

**Tasks not being created?**
- Check userId is correctly passed
- Verify task title is non-empty
- Check MongoDB credentials

---

**Questions or issues?**  
Check the ARCHITECTURE.md and API_REFERENCE.md files for detailed system design and endpoint documentation.

The app is now ready for production deployment! 🚀
