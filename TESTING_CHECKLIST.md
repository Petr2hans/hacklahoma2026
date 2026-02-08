# ✅ Final Testing Checklist

## Pre-Launch Checklist

### Environment Setup
- [ ] Set `MONGODB_URI` environment variable
- [ ] Set `GEMINI_API_KEY` environment variable (get from https://makersuite.google.com/app/apikey)
- [ ] Set `token_address` environment variable
- [ ] Set `sol_key` environment variable
- [ ] All dependencies installed (`pip install -r requirements.txt`)

### File Structure
```
your-project/
├── server_integrated.py       ✅ Main server (updated with Gemini)
├── gemini_breakdown.py        ✅ NEW - Friend 1's AI module
├── requirements.txt           ✅ Dependencies
├── .env.example              ✅ Updated with GEMINI_API_KEY
├── README.md                 ✅ Updated docs
├── COMPLETE_INTEGRATION.md   ✅ Full integration guide
├── SETUP_GUIDE.md            ✅ Setup instructions
├── TROUBLESHOOTING.md        ✅ Debugging guide
├── debug_payments.py         ✅ Payment debugger
├── manual_payment.py         ✅ Manual payment tester
└── test_imports.py           ✅ Import checker
```

---

## Testing Steps

### 1. Environment Test
```bash
# Check all env vars are set
python -c "
import os
print('MONGODB_URI:', '✅' if os.getenv('MONGODB_URI') else '❌')
print('GEMINI_API_KEY:', '✅' if os.getenv('GEMINI_API_KEY') else '❌')
print('token_address:', '✅' if os.getenv('token_address') else '❌')
print('sol_key:', '✅' if os.getenv('sol_key') else '❌')
"
```

Expected output:
```
MONGODB_URI: ✅
GEMINI_API_KEY: ✅
token_address: ✅
sol_key: ✅
```

### 2. Import Test
```bash
python test_imports.py
```

Expected output:
```
Testing Solana package imports...
============================================================
✅ solana.rpc.async_api.AsyncClient
✅ solders (Keypair, Pubkey, VersionedTransaction, MessageV0)
✅ spl.token (direct import)
✅ pymongo (MongoClient, ObjectId)
============================================================

🎉 All imports successful!
```

### 3. Database Connection Test
```bash
python debug_payments.py
```

Expected to see:
```
1️⃣ Checking Environment Variables...
✅ MONGODB_URI: mongodb+srv://...
✅ token_address: ...
✅ sol_key: Set (length: ...)
✅ GEMINI_API_KEY: Set (length: ...)

2️⃣ Checking MongoDB Connection...
✅ Connected to MongoDB
```

### 4. Start Server
```bash
python server_integrated.py
```

Expected output:
```
💰 Payment worker thread started
✅ Connected to MongoDB Atlas
📊 Database: todo_app

============================================================
✨ To-Do App with Solana Rewards & AI Breakdown
============================================================
🌐 Server: http://localhost:8000
📊 Database: MongoDB Atlas - todo_app
🔐 Auth: Enabled
🤖 AI Breakdown: Active (Gemini)  ← Should say "Active"!
💰 Solana Payments: Active (background worker)
🔗 Network: Solana Devnet
============================================================
```

**IMPORTANT:** Check that it says `🤖 AI Breakdown: Active (Gemini)`  
If it says "Disabled", your GEMINI_API_KEY isn't set!

---

## Feature Testing

### Test 1: User Registration ✅
1. Go to http://localhost:8000/register
2. Create account with username + password (6+ chars)
3. Should redirect to login
4. Login with credentials
5. Should redirect to main app

**Expected:** Account created, can login successfully

---

### Test 2: AI Task Breakdown ✅ (MOST IMPORTANT!)
1. Login to the app
2. Add a task: "Write a 5-page essay on climate change"
3. Watch server console logs

**Expected server output:**
```
🤖 Calling Gemini to breakdown: Write a 5-page essay on climate change...
✅ Generated X sections with Y subtasks
```

**Expected in UI:**
- Task appears with expand button (▼)
- Click to expand shows sections like:
  - Research & Planning
  - Writing
  - Review & Editing
- Each section has multiple subtasks
- Each subtask has estimated time

**If this fails:**
- Check server logs for error
- Verify GEMINI_API_KEY is correct
- Try a different task description
- Check COMPLETE_INTEGRATION.md troubleshooting

---

### Test 3: Task Types ✅
Try different task types to test classification:

1. "Read Chapter 5 of Biology textbook" → should classify as `reading`
2. "Complete calculus homework problems 1-20" → `homework`
3. "Write lab report on chemical reactions" → `lab_report`
4. "Study for midterm exam" → `exam_prep`
5. "Build a web scraper in Python" → `project`

**Check MongoDB `tasks` collection:**
Should see `taskType` field with correct classification

---

### Test 4: Focus Session ✅
1. Add at least one task
2. Click "Start Session"
3. Wait 1-2 minutes
4. Check off a few subtasks
5. Click "Finish Session"

**Expected:**
- Timer counts up
- Modal shows session stats
- Credits calculated (1 credit per 15 sec)
- Prompted for wallet address

---

### Test 5: Solana Payment ✅
1. Complete a session (at least 30 seconds)
2. Enter a valid Solana wallet address
3. Click "Queue Payment"
4. Watch server console

**Expected server output (within 30 seconds):**
```
💳 Credit transfer queued: X credits → abc123...
📤 [Cycle X] Processing 1 pending transfer(s)...
✅ [abc123] Sent X tokens to abc123...
🔗 https://explorer.solana.com/tx/...?cluster=devnet
```

**Check:**
- Transaction link works on Solana Explorer
- Transfer marked as `completed` in MongoDB
- Tokens visible in recipient wallet

---

### Test 6: Pace Adaptation ✅
1. Complete 2-3 tasks of the same type (e.g., all homework)
2. Check MongoDB `user_profiles` collection
3. Look at `paceByType` field

**Expected:**
```javascript
{
  _id: "your_user_id",
  paceByType: {
    homework: {
      multiplier: 1.2,  // If you took longer than estimated
      n: 3              // Number of completions
    }
  }
}
```

4. Add another task of same type
5. Notice time estimates are adjusted based on your pace!

---

## MongoDB Validation

After testing, check these collections exist with data:

```bash
# Using MongoDB Compass or mongosh:
use todo_app

db.users.countDocuments()           # Should be > 0
db.tasks.countDocuments()           # Should be > 0
db.sessions.countDocuments()        # Should be > 0  
db.credit_transfers.countDocuments() # Should be > 0
db.user_profiles.countDocuments()   # Should be > 0 (NEW!)
```

**Check one task document:**
```javascript
db.tasks.findOne()

// Should have:
{
  userId: "...",
  task: "...",
  sections: [...],      // From Gemini ✅
  taskType: "homework", // From Gemini ✅
  paceMultiplierUsed: 1.0,
  needsBreakdown: false,
  done: false
}
```

---

## Common Issues & Quick Fixes

### "🤖 AI Breakdown: Disabled (no API key)"
```bash
export GEMINI_API_KEY="your_key_here"
# Restart server
```

### "❌ Gemini breakdown failed"
Check server error, common causes:
- Invalid API key
- Rate limit (wait 1 minute)
- Network issue
- Malformed task title

### "No subtasks appear after adding task"
Check:
1. Server logs for Gemini call
2. MongoDB tasks collection for `sections` field
3. Browser console for JavaScript errors

### "Payments not sending"
Run diagnostic:
```bash
python debug_payments.py
```

### "Import errors"
```bash
python test_imports.py
# Update imports in server_integrated.py based on output
```

---

## Performance Benchmarks

Expected performance:
- **Task addition**: < 0.5 seconds
- **Gemini breakdown**: 2-5 seconds (first time)
- **Session start/stop**: Instant
- **Payment queueing**: < 1 second
- **Payment processing**: 5-15 seconds
- **Page load**: < 2 seconds

If slower:
- Check MongoDB connection latency
- Verify Gemini API response time
- Check Solana network status

---

## Final Deployment Checklist

Before going to production:

- [ ] Switch Solana from Devnet to Mainnet
- [ ] Update RPC_URL in server
- [ ] Get real tokens minted
- [ ] Use production MongoDB cluster
- [ ] Enable MongoDB connection pooling
- [ ] Add rate limiting to API endpoints
- [ ] Use bcrypt for password hashing
- [ ] Enable HTTPS
- [ ] Set secure session cookies
- [ ] Add error monitoring (Sentry, etc.)
- [ ] Set up backups for MongoDB
- [ ] Add admin dashboard
- [ ] Write privacy policy
- [ ] Add terms of service
- [ ] Test with real users

---

## Success Criteria

Your app is ready when:

✅ Users can register and login  
✅ Tasks are intelligently broken down by AI  
✅ Subtasks appear organized in sections  
✅ Timer works correctly  
✅ Credits are calculated accurately  
✅ Solana payments complete successfully  
✅ User pace adapts over time  
✅ No errors in server logs  
✅ All MongoDB collections populated  
✅ Background worker processes payments  

---

## Need Help?

1. Check server console logs
2. Run `python debug_payments.py`
3. Check MongoDB data
4. Review `COMPLETE_INTEGRATION.md`
5. Check `TROUBLESHOOTING.md`
6. Test individual components separately

**Your app now has ALL THREE components working! 🎉**
