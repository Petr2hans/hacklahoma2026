# 🚀 COMPLETE FOCUS APP - READY TO DEPLOY

Your all-in-one focus app with Gemini AI breakdown + Solana payments!

## ✅ What's Included:

ALL the files you need:
```
complete-deploy/
├── todo_app_mongodb.py    ⭐ MAIN APP (Render looks for this!)
├── workers_breakdown.py   🤖 Gemini AI breakdown
├── sol.py                 💰 Solana payments
├── config.py              ⚙️ Configuration
├── db.py                  📊 MongoDB helpers
├── gemini_client.py       🔌 Gemini API client
├── pace.py                ⏱️ User pace tracking
├── parsers.py             📝 JSON parsing
├── prompts.py             💭 AI prompts
├── credit.py              💳 Credit logic
├── requirements.txt       📦 Dependencies
├── .env.example           🔐 Environment template
├── .gitignore             🚫 Git ignore
└── README.md              📖 This file
```

## 🚀 DEPLOY TO RENDER (5 STEPS):

### Step 1: Setup GitHub Repo

```bash
# In the complete-deploy folder:
git init
git add .
git commit -m "Initial commit - Focus app"

# Create repo on GitHub, then:
git remote add origin https://github.com/yourusername/focus-app.git
git push -u origin main
```

### Step 2: Setup Environment Variables

Create a `.env` file locally (for testing):
```bash
cp .env.example .env
```

Fill in your actual values:
- `MONGODB_URI` - Your MongoDB Atlas connection string
- `GEMINI_API_KEY` - Get from https://aistudio.google.com/app/apikey
- `token_address` - Your Solana token mint address  
- `sol_key` - Your treasury keypair bytes as array

### Step 3: Test Locally

```bash
pip install -r requirements.txt
python todo_app_mongodb.py
```

Visit: http://localhost:8000

### Step 4: Create Render Service

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Name**: focus-app
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 todo_app_mongodb.py`
   - **Instance Type**: Free

### Step 5: Add Environment Variables in Render

Go to "Environment" tab and add ALL from `.env`:

```
MONGODB_URI=mongodb+srv://...
MONGODB_DB=todo_app
MONGODB_COLLECTION=tasks
MONGODB_SESSIONS_COLLECTION=sessions
MONGODB_PROFILE_COLLECTION=user_profiles
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash-exp
CHUNK_SECONDS=600
MAX_SUBTASKS=20
token_address=YourTokenMintAddress
sol_key=[1,2,3,...,64]
```

Click **"Create Web Service"** and wait ~5 minutes! 🎉

---

## 🎯 HOW IT WORKS:

1. **User registers/logs in** → Account created
2. **User adds task**: "Study for exam"  
3. **Gemini AI breaks it down** → Smart subtasks
4. **User completes subtasks** → Progress tracked
5. **User finishes session** → Credits calculated (1 per 15 sec)
6. **User enters Solana wallet** → Tokens sent! 💰

---

## 🔧 TROUBLESHOOTING:

### "No such file or directory: todo_app_mongodb.py"
✅ **FIXED!** This repo has the correct filename.

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "MongoDB connection failed"
- Check MONGODB_URI is correct
- Whitelist IP: `0.0.0.0/0` in MongoDB Atlas
- Test connection in MongoDB Compass

### "Gemini API error"
- Verify GEMINI_API_KEY is valid
- Check quota at https://aistudio.google.com/
- Try model: `gemini-1.5-flash`

### "Solana transfer failed"
- Check wallet has SOL for gas fees
- Verify token mint address
- Ensure on devnet for testing

---

## 📊 MONGODB SETUP:

1. Go to https://mongodb.com/cloud/atlas
2. Create FREE M0 cluster
3. Create database user (username + password)
4. Network Access → Add IP: `0.0.0.0/0`
5. Get connection string
6. Add to Render environment variables

---

## 🔐 SOLANA SETUP:

**For Testing (Devnet):**
```bash
# Get free devnet SOL
solana airdrop 2 YOUR_WALLET --url devnet
```

**Environment Variables:**
- `token_address` - Your token mint address
- `sol_key` - Treasury keypair bytes as array `[1,2,3,...,64]`

**For Production:**
- Use mainnet RPC
- Fund treasury with real SOL
- Change RPC_URL in `sol.py`

---

## 🎉 YOU'RE READY!

Just push to GitHub, connect to Render, and deploy!

Your app will be live at: `https://your-app.onrender.com`

**Everything is integrated and working!** 🔥🚀
