# ✅ DEPLOYMENT CHECKLIST

## 📥 Download ALL Files:
Download all 14 files above and put them in one folder

## 📋 Step-by-Step Deployment:

### 1. Setup Git Repo
```bash
cd your-folder
git init
git add .
git commit -m "Initial commit"
```

### 2. Create GitHub Repo
- Go to github.com
- Click "New repository"
- Name it: `focus-app`
- Don't initialize with README
- Copy the commands and run them:
```bash
git remote add origin https://github.com/yourusername/focus-app.git
git push -u origin main
```

### 3. Setup Render
- Go to render.com
- Click "New +" → "Web Service"
- Connect GitHub
- Select your `focus-app` repo
- Settings:
  - Name: `focus-app`
  - Build: `pip install -r requirements.txt`
  - Start: `python3 todo_app_mongodb.py` ⭐ THIS IS IMPORTANT!
  
### 4. Add Environment Variables in Render
Click "Environment" tab, add these:

**MongoDB:**
```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB=todo_app
MONGODB_COLLECTION=tasks
MONGODB_SESSIONS_COLLECTION=sessions
MONGODB_PROFILE_COLLECTION=user_profiles
```

**Gemini:**
```
GEMINI_API_KEY=your_key_from_google
GEMINI_MODEL=gemini-2.0-flash-exp
CHUNK_SECONDS=600
MAX_SUBTASKS=20
```

**Solana:**
```
token_address=your_token_mint_address
sol_key=[1,2,3,...,64]
```

### 5. Deploy!
Click "Create Web Service" - Done! 🎉

---

## 🧪 How to Get Your Values:

### MongoDB URI:
1. Go to mongodb.com/cloud/atlas
2. Create cluster (FREE)
3. Database Access → Add user
4. Network Access → Add `0.0.0.0/0`
5. Connect → Drivers → Copy connection string

### Gemini API Key:
1. Go to aistudio.google.com/app/apikey
2. Create API key
3. Copy it

### Solana (for testing):
```bash
# Use devnet for testing
token_address=TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
sol_key=[your,keypair,bytes,here]
```

---

## ✅ Final Checks:

- [ ] All 14 files downloaded
- [ ] Pushed to GitHub
- [ ] Render service created
- [ ] Environment variables added
- [ ] Deployment successful

Your app: `https://your-app.onrender.com` 🚀
