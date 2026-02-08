# Quick Start Guide

## Local Development

### 1. Clone and Setup

```bash
cd hacklahoma2026
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with:
- Your MongoDB Atlas connection string
- Your Google Gemini API key
- Your Solana devnet token address
- Your Treasury keypair (base58 encoded)

### 4. Run Locally

```bash
python todo_app_mongodb.py
```

The app will start at `http://localhost:8000`

## Understanding the Unified Flow

### Complete Task Journey

1. **User registers/logs in**
   - Password hashed with bcrypt
   - Session token created
   - Stored in MongoDB `users` collection

2. **User creates a task**
   - Task stored with title, description
   - Initial pace multiplier applied (default 1.0)
   - Example: "Learn Python Decorators" → expects 2 hours

3. **AI breaks down the task**
   ```
   POST /api/breakdown
   {
     "taskId": "64abc123...",
     "title": "Learn Python Decorators",
     "description": "Understand how decorators work..."
   }
   
   Returns:
   {
     "sections": [
       {
         "name": "Fundamentals",
         "subtasks": [
           {"title": "Understand functions as first-class objects", "estimatedTime": 15},
           {"title": "Learn @ syntax", "estimatedTime": 10}
         ]
       }
     ]
   }
   ```
   - Gemini infers task type (e.g., "learning")
   - Applies pace multiplier: 2 hours × pace = personalized estimate
   - Generates subtasks with time estimates
   - Groups into sections for UI display

4. **User tracks progress**
   - Marks subtasks as done as they work
   - Logs actual time spent
   - App calculates pace multiplier changes

5. **User completes the task**
   ```
   POST /api/tasks-complete
   {
     "taskId": "64abc123...",
     "walletAddress": "User5Z1...Ak9"
   }
   ```
   - Compares actual_time vs expected_time
   - Ratio = actual_time / expected_time
   - If ratio ≤ 1.0: User earned credit!
   - Credit increases pace multiplier slightly (future tasks easier)
   - 5 SOL tokens sent to user's wallet (async)
   - Returns success response with feedback

6. **User sees reward**
   ```
   {
     "success": true,
     "creditEarned": true,
     "tokensEarned": 5,
     "message": "Great job! Completed in time. 5 SOL earned!",
     "transactionHash": "xyz123...",
     "newPaceMultiplier": 1.05
   }
   ```

## API Endpoints

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secure123"
  }'

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secure123"
  }'
# Returns: {"success": true, "token": "session_..."}

# Logout
curl -X POST http://localhost:8000/api/logout \
  -H "Cookie: session_token=session_..."
```

### Tasks

```bash
# Get all tasks
curl -X GET http://localhost:8000/api/tasks \
  -H "Cookie: session_token=session_..."

# Create/Update tasks (bulk)
curl -X POST http://localhost:8000/api/tasks \
  -H "Cookie: session_token=session_..." \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "_id": "64abc123...",
        "title": "Learn Python Decorators",
        "description": "...",
        "status": "active"
      }
    ]
  }'

# Request AI breakdown
curl -X POST http://localhost:8000/api/breakdown \
  -H "Cookie: session_token=session_..." \
  -H "Content-Type: application/json" \
  -d '{
    "taskId": "64abc123...",
    "title": "Learn Python Decorators"
  }'

# Complete task with rewards
curl -X POST http://localhost:8000/api/tasks-complete \
  -H "Cookie: session_token=session_..." \
  -H "Content-Type: application/json" \
  -d '{
    "taskId": "64abc123...",
    "walletAddress": "User5Z1...Ak9"
  }'
```

### Rewards

```bash
# Get reward history
curl -X GET http://localhost:8000/api/rewards \
  -H "Cookie: session_token=session_..."
# Returns: [{taskId, amountEarned, timestamp, transactionHash}, ...]
```

## Testing Checklist

- [ ] User can register with valid credentials
- [ ] User cannot register with existing username
- [ ] User can login with correct password
- [ ] User cannot login with wrong password
- [ ] User can create a task
- [ ] AI breaks down task into subtasks
- [ ] Subtask time estimates applied with pace multiplier
- [ ] User can mark subtasks as done
- [ ] Total time tracked correctly
- [ ] If completed faster than estimate: credit earned
- [ ] Solana tokens sent on reward
- [ ] Pace multiplier updates after completion
- [ ] Reward history shows past completions

## Debugging

### Check Gemini Integration

```python
# In Python shell
from gemini_client import get_gemini_client
client = get_gemini_client()
response = client.generate_content("What is a decorator in Python?")
print(response.text)
```

### Check Solana Connection

```python
# In Python shell
from sol import send_tokens
from solders.keypair import Keypair

result = send_tokens(
    receiver="User5Z1...Ak9",
    amount=1
)
print(result)
```

### Check MongoDB Connection

```python
# In Python shell
from db import get_client
client = get_client()
db = client['todo_app']
print(db.list_collection_names())
```

## Performance Tips

1. **Gemini caching** - Reuse task breakdowns to avoid API calls
2. **Session tokens** - Use in-memory cache for quick validation
3. **Async rewards** - Token transfers happen async (don't block UI)
4. **Database indexing** - Add indexes on userId, taskId for speed
5. **Pace multiplier** - Cache user profiles to avoid DB hits

## Security Checklist

- [ ] Password hashing with bcrypt (never plain text)
- [ ] Session tokens validated on each request
- [ ] Wallet addresses validated before token transfer
- [ ] API keys stored in environment, never in code
- [ ] MongoDB connection requires authentication
- [ ] CORS headers set correctly for frontend
- [ ] Error messages don't expose internal details

## Deployment Checklist

Before deploying to Render:

- [ ] All dependencies listed in requirements.txt
- [ ] Environment variables configured in Render dashboard
- [ ] MongoDB Atlas IP whitelist includes Render server
- [ ] Solana devnet tokens available in Treasury wallet
- [ ] Frontend updated to call new `/api/tasks-complete` endpoint
- [ ] Error logging configured
- [ ] Database backups enabled on MongoDB Atlas

## Common Issues

**Q: "Gemini API rate limit exceeded"**
A: Add caching layer - store breakdowns in MongoDB, reuse for similar tasks

**Q: "Token transfer failed"**  
A: Check Treasury wallet has tokens, verify recipient wallet is valid

**Q: "MongoDB connection timeout"**  
A: Ensure Render IP is in MongoDB Atlas IP whitelist (or set to 0.0.0.0 for dev)

**Q: "CORS error from frontend"**  
A: Add `Access-Control-Allow-Origin` headers in HTTP response handlers

---

Ready to build? Start the app and check it out at http://localhost:8000 🚀
