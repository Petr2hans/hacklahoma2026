# 📚 Focus App with Solana Rewards

A productivity app that rewards users with crypto tokens for completing focus sessions!

## ✨ Features

- 🔐 User authentication (register/login)
- 🤖 **AI-powered task breakdown** using Google Gemini
- ✅ Smart task management with intelligent subtasks
- 📊 **Adaptive pace learning** - gets better at estimating YOUR pace
- ⏱️ Focus session timer
- 💰 Earn tokens for staying focused
- 🪙 **Automatic Solana token payments** via background worker
- 📈 Task type classification (homework, reading, lab reports, etc.)
- 🧠 Personalized time estimates based on your history
- 🎯 Section-based task organization

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Set Environment Variables
```bash
export MONGODB_URI="your_mongodb_connection_string"
export GEMINI_API_KEY="your_gemini_api_key"  # Get from: https://makersuite.google.com/app/apikey
export token_address="your_solana_token_mint"
export sol_key="[your,treasury,keypair,bytes]"
```

### 3. Run the Server
```bash
python server_integrated.py
```

### 4. Open Browser
```
http://localhost:8000
```

**📖 For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

---

## 📁 Project Files

```
├── server_integrated.py      # Main application server
├── requirements.txt          # Python dependencies
├── SETUP_GUIDE.md           # Detailed setup instructions
├── INTEGRATION_SUMMARY.md   # Technical documentation
├── .env.example             # Environment variables template
└── .gitignore               # Git ignore rules
```

---

## 💡 How It Works

### User Experience:
1. **Register/Login** → Create account
2. **Add Tasks** → Enter what you need to work on
3. **AI Breakdown** → Gemini generates intelligent subtasks automatically
4. **Start Session** → Begin focus timer
5. **Complete Subtasks** → Check off work as you go
6. **Finish Session** → Get credits based on time (1 credit = 15 seconds)
7. **Enter Wallet** → Receive Solana tokens automatically!
8. **Pace Adapts** → App learns your speed and adjusts future estimates

### Behind the Scenes:
- **Frontend**: Vanilla JavaScript with modern UI
- **Backend**: Python HTTP server with MongoDB
- **AI**: Google Gemini breaks down tasks intelligently
- **Payments**: Background worker processes Solana transactions every 30 seconds
- **Learning**: Tracks your pace by task type and adapts over time

---

## 🏗️ Architecture

```
User Browser
    ↓
Python HTTP Server (port 8000)
    ↓
MongoDB Atlas (tasks, users, sessions)
    ↓
Background Payment Worker (thread)
    ↓
Solana Blockchain (Devnet)
```

---

## 💰 Reward System

**Credits Calculation:**
- 1 credit = 15 seconds of focus time
- 1 minute = 4 credits
- 1 hour = 240 credits

**Example:**
- 45-minute session = 180 credits = 180 tokens sent to your wallet!

---

## 🔧 Configuration

### Default Settings:
- **Port**: 8000 (change with `PORT` env var)
- **Network**: Solana Devnet
- **Payment Interval**: 30 seconds
- **Token Decimals**: 9

### Customization:
Edit these in `server_integrated.py`:
- `DECIMALS` (line 21) - Token decimal places
- `sleep(30)` (line 163) - Payment worker frequency
- `calculateCredits()` (frontend) - Credits calculation formula

---

## 🛡️ Security

**⚠️ CRITICAL - DO NOT COMMIT:**
- Treasury keypair (`sol_key`)
- MongoDB credentials
- `.env` file

**Before Production:**
- [ ] Switch to Solana Mainnet
- [ ] Use bcrypt for passwords
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Store sessions in MongoDB
- [ ] Validate all inputs
- [ ] Use secrets manager for keys

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Dependencies won't install | Try without `--break-system-packages` flag |
| MongoDB connection fails | Check URI and IP whitelist in Atlas |
| Payments not processing | Verify treasury has SOL + tokens |
| Invalid wallet error | Use proper Solana address (32-44 chars) |
| Port already in use | Change with `export PORT=8080` |

**More help:** See [SETUP_GUIDE.md](SETUP_GUIDE.md) troubleshooting section

---

## 🎯 Development Roadmap

### ✅ Completed:
- [x] User authentication
- [x] Task management
- [x] Focus timer
- [x] Solana integration
- [x] Background payment worker
- [x] MongoDB persistence
- [x] **Gemini AI task breakdown** ✨
- [x] **Adaptive pace learning** 🧠
- [x] **Task type classification** 📊

### 📋 Future Features:
- [ ] Leaderboard
- [ ] Task categories & tags
- [ ] Pomodoro timer mode
- [ ] Daily/weekly statistics dashboard
- [ ] Mobile app
- [ ] Social features & friends
- [ ] Export session data
- [ ] Integration with calendar apps

---

## 👥 Team

Built collaboratively by:
- **You**: Main server architecture, UI, MongoDB integration, final integration
- **Friend 1**: Gemini AI task breakdown system ✅ *Integrated!*
- **Friend 2**: Solana payment system ✅ *Integrated!*

**All components successfully merged and working together!** 🎉

---

## 📜 License

MIT License - Feel free to use for your own projects!

---

## 🤝 All Components Integrated!

✅ **Your Server** - Core architecture, UI, auth, MongoDB  
✅ **Friend 1's Gemini** - AI task breakdown with adaptive learning  
✅ **Friend 2's Solana** - Blockchain payment system  

**Everything is working together!**  
See `COMPLETE_INTEGRATION.md` for full details on how all three parts work together.

---

## 📞 Support

Having issues? Check:
1. Console logs (very detailed!)
2. [SETUP_GUIDE.md](SETUP_GUIDE.md) troubleshooting
3. MongoDB Atlas connection status
4. Solana Explorer for transaction status

---

**Happy building! 🚀**
