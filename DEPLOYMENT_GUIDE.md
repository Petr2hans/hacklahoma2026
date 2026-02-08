# Deployment to Render.com - Complete Guide

This guide walks you through deploying your unified task management app to Render.com.

## Prerequisites

- GitHub account with your code repository
- Render.com account (free tier available)
- MongoDB Atlas account with a cluster running
- Google Gemini API key
- Solana tokens (if testing rewards)

## Step 1: Prepare Your Repository

### 1.1 Clean Up Files

Remove the misspelled requirements file:
```bash
cd /Users/petrgroshenko/Documents/Programing_projects/Git/hacklahoma2026
rm requirments.txt  # Remove the misspelled version
```

### 1.2 Verify All Files Are Present

Required files for deployment:
```
Todo_App_MongoDB/
├── todo_app_mongodb.py           # Main app
├── auth_service.py               # Authentication
├── task_service.py               # Task management
├── breakdown_service.py           # AI breakdown
├── completion_service.py          # Rewards
├── db.py                         # Database
├── config.py                     # Config
├── gemini_client.py              # Gemini API
├── parsers.py                    # JSON parsing
├── prompts.py                    # AI prompts
├── sol.py                        # Solana integration
├── pace.py                       # Pace logic
├── credit.py                     # Credit system
├── requirements.txt              # Dependencies
├── .env.example                  # Environment template
├── REFACTORING_SUMMARY.md        # What changed
├── ARCHITECTURE.md               # System design
├── API_REFERENCE.md              # API docs
└── QUICKSTART.md                 # Quick start
```

### 1.3 Create .gitignore

Create a `.gitignore` file to prevent secrets from being committed:

```bash
cat > .gitignore << 'EOF'
# Environment variables
.env
variables.env
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Developer files
.venv/
test_*.py
debug_*.py
EOF
```

### 1.4 Push to GitHub

```bash
git add .
git commit -m "Refactor into service layers and prepare for deployment"
git push origin main
```

## Step 2: Set Up MongoDB Atlas

### 2.1 Create MongoDB Cluster

1. Go to https://www.mongodb.com/cloud/atlas
2. Create a new cluster (free tier M0)
3. Create a database user with a strong password
4. Get your connection string

### 2.2 Configure IP Whitelist

1. In MongoDB Atlas, go to **Network Access**
2. Click **Add IP Address**
3. For Render deployment, use `0.0.0.0/0` (or add Render's specific IP later)
4. Ensure your local development IP is also whitelisted

### 2.3 Get Connection String

In MongoDB Atlas:
1. Click **Clusters** → **Connect**
2. Choose "Connect your application"
3. Copy the connection string, it looks like:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

## Step 3: Set Up Google Gemini API

### 3.1 Enable the API

1. Go to https://console.cloud.google.com
2. Create a new project
3. Go to **APIs & Services** → **Library**
4. Search for "Generative Language API"
5. Click **Enable**

### 3.2 Create API Key

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **API Key**
3. Copy the API key

## Step 4: Prepare Solana (Optional but Recommended)

### 4.1 Create Devnet Wallet

With Solana CLI:
```bash
solana-keygen new --outfile ./treasury.json
solana config set --url https://api.devnet.solana.com
solana airdrop 2 $(solana address)  # Get free devnet SOL
```

Or use https://phantom.app for a browser wallet

### 4.2 Get Your Token Mint Address

If you have a custom token, get its mint address. Otherwise, use Wrapped SOL:
```
So11111111111111111111111111111111111112
```

### 4.3 Encode Your Keypair

Convert your keypair to base58 for environment variable:
```python
import json
import base58

with open('./treasury.json') as f:
    keypair = json.load(f)

secret_bytes = bytes(keypair)
base58_key = base58.b58encode(secret_bytes).decode()
print(base58_key)
```

## Step 5: Deploy to Render

### 5.1 Connect GitHub Repository

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Click **Connect GitHub account**
4. Select your repository
5. Authorize Render with GitHub

### 5.2 Configure Service Settings

Fill in the following:

| Field | Value |
|-------|-------|
| **Name** | `task-reward-app` |
| **Environment** | `Python 3` |
| **Region** | `Oregon (US West)` |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python todo_app_mongodb.py` |

### 5.3 Add Environment Variables

Click **Environment** and add:

```
MONGODB_URI = mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB = todo_app
GEMINI_API_KEY = your-google-api-key
token_address = So11111111111111111111111111111111111112
sol_key = your-base58-encoded-keypair
PORT = 8000
```

### 5.4 Configure Health Check

1. Go to **Settings**
2. Set **Health Check Path** to `/`
3. This will check if your app is responding

### 5.5 Deploy

1. Click **Create Web Service**
2. Render will automatically build and deploy
3. Watch the logs for any errors

## Step 6: Verify Deployment

### 6.1 Check Deployment Status

In Render dashboard:
- **Live** = App is running
- **Deploying** = Still building
- **Error** = Check logs

### 6.2 Test Your App

```bash
# Get your Render URL from the dashboard
curl https://your-app.onrender.com/

# Test registration
curl -X POST https://your-app.onrender.com/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'
```

### 6.3 View Logs

In Render dashboard, click **Logs** to see:
- Application output
- Errors and warnings
- API requests

## Step 7: Fix Common Issues

### Issue: Build Fails - "No module named X"

**Solution:**
```bash
# Locally, run:
pip freeze > requirements.txt

# Then push to GitHub
git add requirements.txt
git commit -m "Update requirements"
git push origin main

# Render will rebuild automatically
```

### Issue: MongoDB Connection Timeout

**Solution:**
1. In MongoDB Atlas → **Network Access**
2. Add Render server IP:
   - Check Render logs for outgoing IP
   - Or use `0.0.0.0/0` for public access
3. Redeploy service in Render

### Issue: Gemini API Rate Limited

**Solution:**
- Add caching for task breakdowns
- Check your API quota in Google Cloud Console
- Contact Google for quota increase

### Issue: Solana Tokens Not Sending

**Solution:**
1. Verify Treasury wallet has devnet SOL:
   ```bash
   solana balance <your-address>
   ```
2. Check token mint address is correct
3. Verify keypair is valid:
   ```bash
   solana address
   ```

## Step 8: Monitor Your App

### Set Up Error Tracking (Optional)

For production, add Sentry monitoring:

```bash
pip install sentry-sdk
```

In `todo_app_mongodb.py` at the top:

```python
import sentry_sdk

sentry_sdk.init("your-sentry-dsn-here")
```

### Monitor Database Usage

In MongoDB Atlas:
- Check **Metrics** for connection count
- Monitor storage usage (M0 free tier = 512MB)
- Set up alerts for high CPU usage

### Monitor API Costs

- Monitor Gemini API usage in Google Cloud Console
- Monitor Solana RPC calls (free tier has limits)
- Set up alerts for cost overage

## Step 9: Production Checklist

Before going live:

- [ ] All environment variables are set correctly
- [ ] MongoDB backups are enabled
- [ ] Error logging is configured
- [ ] CORS headers are correct
- [ ] HTTPS is enabled (Render provides free SSL)
- [ ] Frontend is updated to use new API endpoints
- [ ] Rate limiting is configured
- [ ] Password hashing is secure (SHA256 with salt)
- [ ] Sensitive data is not logged
- [ ] Tests pass locally
- [ ] Database indexes are created
- [ ] Backup plan is in place

## Step 10: Custom Domain (Optional)

To add your own domain:

1. In Render dashboard, go to **Settings**
2. Click **Add Custom Domain**
3. Enter your domain (e.g., `app.example.com`)
4. Update your domain's DNS records to point to Render
5. Render will automatically provision HTTPS

## Scaling Considerations

For high traffic:

### Upgrade Render Plan
- Free plan: auto-sleeps after 15 min inactivity
- Paid plan: always running, guaranteed resources

### Upgrade MongoDB
- M0 (free): 512MB storage, limited connections
- M2+ (paid): More storage and connections

### Add Caching Layer
- Cache Gemini breakdowns
- Cache user profiles
- Add Redis for session management

### Database Optimization
- Add indexes on frequently queried fields
- Archive old completed tasks
- Use connection pooling

## Monitoring & Alerts

### Set Up Email Alerts

In Render dashboard:
1. Go to **Settings** → **Notifications**
2. Enable email for:
   - Deploy failures
   - High memory usage
   - Service errors

### Monitor Log Levels

Check logs daily for:
- ERROR: Fix immediately
- WARN: Monitor and fix soon
- INFO: Optional monitoring

## Troubleshooting Commands

### SSH into Your Render Server

```bash
# Render doesn't allow direct SSH, but you can:
# 1. Check logs in dashboard
# 2. Add logging to your Python code
```

### Deploy New Code

```bash
git commit -m "Fix bug"
git push origin main
# Render auto-deploys on push
```

### Rollback to Previous Version

```bash
# In Render dashboard → Deployments
# Click "Deploy" next to an older version
```

## Next Steps

1. **Update Frontend** - Wire up new `/api/tasks-complete` endpoint
2. **Add Testing** - Create integration tests for full flow
3. **Set Up CI/CD** - Auto-run tests before deploy
4. **Add Analytics** - Track user behavior
5. **Improve Performance** - Profile and optimize

## Support & Resources

- [Render Documentation](https://render.com/docs)
- [MongoDB Atlas Help](https://docs.atlas.mongodb.com)
- [Google Gemini Docs](https://ai.google.dev/docs)
- [Solana Documentation](https://docs.solana.com)

---

**Your app is now live!** 🚀

Access it at: `https://your-app.onrender.com`

Next step: Update your frontend JavaScript to use the new unified endpoints.
