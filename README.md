# 🚀 UNIFIED FOCUS APP - COMPLETE DEPLOYMENT PACKAGE

Your all-in-one focus app with:
- ✅ **Login/Register** authentication  
- ✅ **Gemini AI** task breakdown
- ✅ **Solana** crypto payments
- ✅ **User pace tracking**
- ✅ **Session timer** with credits

---

## 📦 What's Included:

```
focus-app-deploy/
├── app.py                 # Main unified app (RUN THIS!)
├── config.py              # Configuration loader
├── db.py                  # MongoDB helpers
├── workers_breakdown.py   # Gemini AI breakdown
├── gemini_client.py       # Gemini API client
├── pace.py                # User pace tracking
├── parsers.py             # JSON parsing
├── prompts.py             # AI prompts
├── credit.py              # Credit finalization
├── sol.py                 # Solana payments (FIXED!)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── templates/
│   ├── login.html         # Login page
│   ├── register.html      # Sign up page
│   └── app.html           # Main app UI
└── README.md              # This file
```

---

## 🚀 QUICK START (3 Steps!)

### Step 1: Set Up Environment

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your actual values
nano .env
```

**Required values:**
- `MONGODB_URI` - Your MongoDB Atlas connection string
- `GEMINI_API_KEY` - Get from https://aistudio.google.com/app/apikey
- `token_address` - Your Solana token mint address
- `sol_key` - Treasury keypair bytes as array

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the App!

```bash
python app.py
```

Visit: **http://localhost:8000** 🎉

---

## 📋 DETAILED SETUP

### MongoDB Atlas Setup

1. Go to https://mongodb.com/cloud/atlas
2. Create FREE M0 cluster
3. Create database user
4. Whitelist IP: `0.0.0.0/0`
5. Get connection string
6. Add to `.env`:
   ```
   MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
   ```

### Gemini API Setup

1. Go to https://aistudio.google.com/app/apikey
2. Create API key
3. Add to `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```

### Solana Setup (Optional - for payments)

**For Testing (Devnet):**
```bash
# Get devnet SOL
solana airdrop 2 YOUR_WALLET --url devnet

# Your treasury keypair bytes go in .env
sol_key=[1,2,3,...,64]
```

**For Production (Mainnet):**
- Use real wallet
- Fund with actual SOL
- Update RPC_URL in `sol.py` to mainnet

---

## 🌐 DEPLOY TO RENDER

### Step 1: Push to GitHub

```bash
git init
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/focus-app.git
git push -u origin main
```

### Step 2: Create Render Service

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect GitHub repo
4. Settings:
   - **Name**: focus-app
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`

### Step 3: Add Environment Variables

In Render dashboard → Environment tab, add ALL from `.env`:
- MONGODB_URI
- MONGODB_DB
- MONGODB_COLLECTION
- MONGODB_SESSIONS_COLLECTION
- MONGODB_PROFILE_COLLECTION
- GEMINI_API_KEY
- GEMINI_MODEL
- CHUNK_SECONDS
- MAX_SUBTASKS
- token_address
- sol_key

### Step 4: Deploy!

Click "Create Web Service" - Done in ~5 minutes! 🚀

Your app: `https://your-app.onrender.com`

---

## 🧪 TESTING LOCALLY

```bash
# 1. Start the app
python app.py

# 2. Open browser
# http://localhost:8000

# 3. Test flow:
#    a. Register new account
#    b. Login
#    c. Add task: "Complete homework"
#    d. Watch Gemini break it down! 🤖
#    e. Expand subtasks (▼ button)
#    f. Check off subtasks
#    g. Start session timer
#    h. Finish session
#    i. Enter Solana wallet
#    j. See credits transfer! 💰
```

---

## 🔧 TROUBLESHOOTING

### "MongoDB connection failed"
```bash
# Test connection
python -c "from pymongo import MongoClient; client = MongoClient('YOUR_URI'); client.admin.command('ping'); print('✅ Connected!')"
```

**Fixes:**
- Check URI is correct
- Verify IP whitelist: `0.0.0.0/0`
- Ensure user has read/write permissions

### "Gemini API error"
```bash
# Test API key
python list_models.py
```

**Fixes:**
- Check API key is valid
- Verify quota at https://aistudio.google.com/
- Try model: `gemini-1.5-flash`

### "Solana transfer failed"
```bash
# Test Solana
python sol.py
```

**Fixes:**
- Check wallet has SOL for gas
- Verify token mint address
- Ensure on correct network (devnet/mainnet)
- Check treasury has tokens to send

### "Breakdown not working"
```bash
# Test breakdown manually
python main.py
```

**Fixes:**
- Check Gemini API key
- Verify prompts.py exists
- Look at logs for error details

### "Tasks not showing"
- Check browser console (F12)
- Verify userId in MongoDB
- Look at server logs

---

## 📊 DATABASE SCHEMA

### tasks collection:
```javascript
{
  userId: "65c123...",
  task: "Complete homework",
  done: false,
  expectedTime: 3600,
  actualTime: 0,
  subtasks: [
    {
      id: "st_1_abc",
      task: "Read chapter 5",
      expectedTime: 1200,
      actualTime: 0,
      done: false
    }
  ],
  needsBreakdown: false,
  taskType: "homework",
  paceMultiplier: 1.2,
  createdAt: "2026-02-08T10:00:00Z"
}
```

### users collection:
```javascript
{
  username: "johndoe",
  password: "salt$hash",
  createdAt: "2026-02-08T10:00:00Z"
}
```

### credit_transfers collection:
```javascript
{
  userId: "65c123...",
  walletAddress: "7xKXtg...",
  credits: 360.0,
  sessionId: "session_xxx",
  status: "completed",
  transactionHash: "5BxQ7...",
  timestamp: "2026-02-08T11:30:00Z"
}
```

---

## 🎯 HOW IT WORKS

### User Flow:
1. **Register/Login** → Creates account
2. **Add Task** → "Study for exam"
3. **Auto-Breakdown** → Gemini AI splits into subtasks
4. **Work Session** → Start timer, check off subtasks
5. **Earn Credits** → 1 credit per 15 seconds
6. **Get Paid** → Solana transfers to wallet

### Behind the Scenes:
- **app.py** → HTTP server, routing, auth
- **workers_breakdown.py** → Calls Gemini AI
- **sol.py** → Sends Solana tokens
- **pace.py** → Adapts to user speed
- **MongoDB** → Stores everything

---

## 🔐 SECURITY

✅ Passwords hashed (SHA-256 + salt)
✅ HttpOnly session cookies
✅ User data isolated by userId
✅ Private keys in .env (never committed)
✅ HTTPS in production (Render auto)

---

## 📈 NEXT STEPS

After deployment:
1. Test with real users
2. Monitor Render logs
3. Check MongoDB Atlas metrics
4. Track Solana transactions
5. Iterate on Gemini prompts
6. Add features:
   - Email notifications
   - Statistics dashboard
   - Leaderboards
   - Mobile app

---

## 🆘 NEED HELP?

1. Check logs: `python app.py` (local) or Render dashboard (prod)
2. Test components individually: `python main.py`, `python sol.py`
3. Verify environment: `python final_check.py`
4. Check GitHub Issues

---

## 🎉 YOU'RE READY!

You now have a **complete, production-ready app** that:
- Authenticates users
- Breaks down tasks with AI
- Pays users in crypto
- Tracks performance
- Scales automatically

**Just deploy to Render and GO!** 🚀

---

**Made with 💜 by your friendly AI assistant**
