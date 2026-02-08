import http.server
import socketserver
import json
import os
import webbrowser
import threading
import hashlib
import secrets
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from http.cookies import SimpleCookie

PORT = int(os.environ.get('PORT', 8000))

# Session storage (in production, use Redis or MongoDB)
sessions = {}  # {session_token: user_id}

# MongoDB Atlas connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = 'todo_app'

# Initialize MongoDB
print(f"🔍 Attempting to connect to MongoDB...")
print(f"🔍 MONGODB_URI present: {bool(os.environ.get('MONGODB_URI'))}")

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    
    db = client[DB_NAME]
    tasks_collection = db['tasks']
    sessions_collection = db['sessions']
    users_collection = db['users']
    credit_transfers_collection = db['credit_transfers']
    
    # Create indexes
    tasks_collection.create_index('archived')
    tasks_collection.create_index('needs_breakdown')
    tasks_collection.create_index('userId')
    sessions_collection.create_index('session_id', unique=True)
    sessions_collection.create_index('userId')
    users_collection.create_index('username', unique=True)
    credit_transfers_collection.create_index('userId')
    
    print("✅ Connected to MongoDB Atlas")
    print(f"📊 Database: {DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print(f"❌ Error type: {type(e).__name__}")
    print("Set MONGODB_URI environment variable with your Atlas connection string")

# Authentication helpers
def hash_password(password):
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password, hashed):
    """Verify password against hash"""
    try:
        salt, pwd_hash = hashed.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except:
        return False

def create_session(user_id):
    """Create new session token"""
    token = secrets.token_urlsafe(32)
    sessions[token] = str(user_id)
    return token

def get_user_from_session(session_token):
    """Get user ID from session token"""
    return sessions.get(session_token)

# Login page HTML
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Focus App</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .auth-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 400px;
            padding: 50px 40px;
        }
        h1 {
            text-align: center;
            color: #2d3748;
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .subtitle {
            text-align: center;
            color: #718096;
            font-size: 14px;
            margin-bottom: 40px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            outline: none;
            transition: all 0.3s ease;
        }
        input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-top: 10px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: #718096;
        }
        .link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>Welcome Back! 👋</h1>
        <p class="subtitle">Login to continue your focus sessions</p>
        
        <div class="error" id="errorMsg"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autocomplete="username">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            
            <button type="submit" class="btn">Login</button>
        </form>
        
        <div class="link">
            Don't have an account? <a href="/register">Sign up</a>
        </div>
    </div>

    <script>
        const form = document.getElementById('loginForm');
        const errorMsg = document.getElementById('errorMsg');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ username, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = '/';
                } else {
                    errorMsg.textContent = result.message;
                    errorMsg.style.display = 'block';
                }
            } catch (error) {
                errorMsg.textContent = 'Network error. Please try again.';
                errorMsg.style.display = 'block';
            }
        });
    </script>
</body>
</html>
'''

# Register page HTML
REGISTER_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up - Focus App</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .auth-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 400px;
            padding: 50px 40px;
        }
        h1 {
            text-align: center;
            color: #2d3748;
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .subtitle {
            text-align: center;
            color: #718096;
            font-size: 14px;
            margin-bottom: 40px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            outline: none;
            transition: all 0.3s ease;
        }
        input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-top: 10px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .success {
            background: #c6f6d5;
            color: #22543d;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .link {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: #718096;
        }
        .link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .link a:hover {
            text-decoration: underline;
        }
        .hint {
            font-size: 12px;
            color: #a0aec0;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>Create Account 🚀</h1>
        <p class="subtitle">Start tracking your focus sessions</p>
        
        <div class="error" id="errorMsg"></div>
        <div class="success" id="successMsg"></div>
        
        <form id="registerForm">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autocomplete="username">
                <div class="hint">At least 3 characters</div>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="new-password">
                <div class="hint">At least 6 characters</div>
            </div>
            
            <button type="submit" class="btn">Create Account</button>
        </form>
        
        <div class="link">
            Already have an account? <a href="/login">Login</a>
        </div>
    </div>

    <script>
        const form = document.getElementById('registerForm');
        const errorMsg = document.getElementById('errorMsg');
        const successMsg = document.getElementById('successMsg');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            errorMsg.style.display = 'none';
            successMsg.style.display = 'none';
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ username, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    successMsg.textContent = result.message + ' Redirecting to login...';
                    successMsg.style.display = 'block';
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1500);
                } else {
                    errorMsg.textContent = result.message;
                    errorMsg.style.display = 'block';
                }
            } catch (error) {
                errorMsg.textContent = 'Network error. Please try again.';
                errorMsg.style.display = 'block';
            }
        });
    </script>
</body>
</html>
'''

# Main app HTML (same as before, but loads for authenticated users only)
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>To-Do List</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 500px;
            padding: 40px;
            position: relative;
        }

        .logout-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 600;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: #718096;
            background: white;
        }

        .logout-btn:hover {
            border-color: #f56565;
            color: #f56565;
        }

        h1 {
            text-align: center;
            color: #2d3748;
            font-size: 36px;
            margin-bottom: 40px;
            font-weight: 700;
        }

        .input-section {
            margin-bottom: 30px;
            display: flex;
            gap: 10px;
            align-items: center;
        }

        #taskInput {
            flex: 1;
            padding: 16px 20px;
            font-size: 16px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            outline: none;
            transition: all 0.3s ease;
        }

        #taskInput:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        #addBtn {
            width: 50px;
            height: 50px;
            font-size: 24px;
            font-weight: 300;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        #addBtn:hover {
            transform: scale(1.1);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }

        #addBtn:active {
            transform: scale(0.95);
        }

        .tasks-section {
            margin-bottom: 25px;
            max-height: 350px;
            overflow-y: auto;
            padding-right: 5px;
        }

        .tasks-section::-webkit-scrollbar {
            width: 8px;
        }

        .tasks-section::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }

        .tasks-section::-webkit-scrollbar-thumb {
            background: #cbd5e0;
            border-radius: 10px;
        }

        .tasks-section::-webkit-scrollbar-thumb:hover {
            background: #a0aec0;
        }

        .task-item {
            background: #f7fafc;
            padding: 16px 20px;
            margin-bottom: 10px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            cursor: pointer;
        }

        .task-item:hover {
            border-color: #667eea;
            background: #edf2f7;
        }

        .task-item:hover .delete-btn {
            opacity: 1;
        }

        .task-item.selected {
            background: #e6f0ff;
            border-color: #667eea;
        }

        .task-item.completed {
            opacity: 0.6;
        }

        .task-content {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .task-checkbox {
            font-size: 24px;
            color: #667eea;
        }

        .task-text {
            font-size: 16px;
            color: #2d3748;
            flex: 1;
        }

        .task-item.completed .task-text {
            text-decoration: line-through;
            color: #a0aec0;
        }

        .delete-btn {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #f56565;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            opacity: 0;
            flex-shrink: 0;
        }

        .delete-btn:hover {
            background: #e53e3e;
            transform: scale(1.2);
        }

        .delete-btn:active {
            transform: scale(0.9);
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #a0aec0;
            font-size: 16px;
        }

        .session-section {
            margin-top: 30px;
            text-align: center;
        }

        .timer-display {
            font-size: 48px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 20px;
            font-variant-numeric: tabular-nums;
        }

        .timer-display.running {
            color: #667eea;
        }

        .session-controls {
            display: flex;
            flex-direction: column;
            gap: 12px;
            align-items: center;
        }

        .session-btn {
            padding: 14px 36px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }

        .session-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4);
        }

        .session-btn:active {
            transform: translateY(0);
        }

        .stop-btn {
            padding: 0;
            font-size: 14px;
            font-weight: 500;
            border: none;
            background: none;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #718096;
            text-decoration: none;
        }

        .stop-btn:hover {
            color: #4a5568;
        }

        .finish-btn {
            padding: 14px 36px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);
        }

        .finish-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 101, 101, 0.4);
        }

        .finish-btn:active {
            transform: translateY(0);
        }

        .hidden {
            display: none;
        }

        .disabled {
            opacity: 0.5;
            pointer-events: none;
        }

        .task-duration {
            font-size: 12px;
            color: #a0aec0;
            margin-left: 8px;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(5px);
        }

        .modal.show {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 24px;
            padding: 50px 60px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideIn 0.4s ease;
        }

        @keyframes slideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .congrats-emoji {
            font-size: 80px;
            margin-bottom: 20px;
            animation: bounce 1s ease infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-15px); }
        }

        .congrats-title {
            font-size: 32px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 15px;
        }

        .congrats-message {
            font-size: 18px;
            color: #718096;
            margin-bottom: 30px;
            line-height: 1.6;
        }

        .session-stats {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            color: white;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            font-size: 16px;
        }

        .stat-row:last-child {
            margin-bottom: 0;
        }

        .stat-label {
            opacity: 0.9;
        }

        .stat-value {
            font-weight: 700;
            font-size: 20px;
        }

        .credits-section {
            background: linear-gradient(135deg, #f6ad55 0%, #ed8936 100%);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 25px;
            color: white;
        }

        .credits-earned {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .credits-label {
            font-size: 16px;
            opacity: 0.9;
        }

        .wallet-section {
            margin-bottom: 25px;
        }

        .wallet-label {
            font-size: 14px;
            color: #4a5568;
            margin-bottom: 8px;
            text-align: left;
            font-weight: 600;
        }

        .wallet-input {
            width: 100%;
            padding: 14px 16px;
            font-size: 14px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            outline: none;
            transition: all 0.3s ease;
            font-family: 'Courier New', monospace;
        }

        .wallet-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .wallet-input::placeholder {
            color: #a0aec0;
        }

        .close-modal-btn {
            padding: 14px 40px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }

        .close-modal-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4);
        }

        .close-modal-btn:active {
            transform: translateY(0);
        }

        .close-modal-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <button class="logout-btn" onclick="logout()">Logout</button>
        
        <h1>To-Do List</h1>
        
        <div class="input-section">
            <input type="text" id="taskInput" placeholder="Enter a new task..." autocomplete="off">
            <button id="addBtn">+</button>
        </div>

        <div class="tasks-section" id="tasksList">
            <div class="empty-state">No tasks yet. Add one above!</div>
        </div>

        <div class="session-section">
            <div class="timer-display" id="timerDisplay">00:00:00</div>
            <div class="session-controls">
                <button class="session-btn" id="startBtn">Start Session</button>
                <button class="finish-btn hidden" id="finishBtn">Finish Session</button>
                <button class="stop-btn hidden" id="stopBtn">Stop Session</button>
            </div>
        </div>
    </div>

    <!-- Congratulations Modal -->
    <div class="modal" id="congratsModal">
        <div class="modal-content">
            <div class="congrats-emoji">🎉</div>
            <h2 class="congrats-title">Great Work!</h2>
            <p class="congrats-message">You've completed your focus session. Here's what you accomplished:</p>
            
            <div class="session-stats">
                <div class="stat-row">
                    <span class="stat-label">Session Duration</span>
                    <span class="stat-value" id="modalDuration">--</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Tasks Completed</span>
                    <span class="stat-value" id="modalTasksCompleted">--</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total Tasks</span>
                    <span class="stat-value" id="modalTotalTasks">--</span>
                </div>
            </div>

            <div class="credits-section">
                <div class="credits-earned" id="creditsEarned">0</div>
                <div class="credits-label">Credits Earned 💰</div>
            </div>

            <div class="wallet-section">
                <div class="wallet-label">Wallet Address (to receive credits)</div>
                <input 
                    type="text" 
                    class="wallet-input" 
                    id="walletInput" 
                    placeholder="0x... or your wallet address"
                    autocomplete="off"
                >
            </div>
            
            <button class="close-modal-btn" id="closeModalBtn">Continue</button>
        </div>
    </div>

    <script>
        let tasks = [];
        let selectedIndex = null;
        let sessionRunning = false;
        let sessionPaused = false;
        let sessionStartTime = null;
        let timerInterval = null;
        let currentTaskStartTime = null;
        let currentSessionId = null;
        let creditsEarned = 0;

        function logout() {
            fetch('/api/logout', { method: 'POST' })
                .then(() => {
                    window.location.href = '/login';
                });
        }

        function calculateCredits(durationSeconds) {
            const durationMinutes = durationSeconds / 60;
            const roundedMinutes = Math.round(durationMinutes / 7) * 7;
            const credits = roundedMinutes / 15;
            return Math.max(0, credits);
        }

        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                tasks = await response.json();
                renderTasks();
            } catch (error) {
                console.error('Load failed:', error);
            }
        }

        async function saveTasks() {
            try {
                await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(tasks)
                });
            } catch (error) {
                console.error('Save failed:', error);
            }
        }

        async function endSession() {
            if (!sessionStartTime) return;
            
            const sessionDuration = Math.floor((Date.now() - sessionStartTime) / 1000);
            const tasksCompleted = tasks.filter(t => t.done && t.lastSessionId === currentSessionId).length;
            
            creditsEarned = calculateCredits(sessionDuration);
            
            const sessionData = {
                sessionId: currentSessionId,
                startTime: new Date(sessionStartTime).toISOString(),
                endTime: new Date().toISOString(),
                totalDuration: sessionDuration,
                tasksCompleted: tasksCompleted,
                creditsEarned: creditsEarned,
                timestamp: Date.now()
            };
            
            try {
                await fetch('/api/session', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(sessionData)
                });
                console.log('Session ended:', sessionData);
            } catch (error) {
                console.error('Failed to save session:', error);
            }
            
            const completedTasks = tasks.filter(t => t.done);
            if (completedTasks.length > 0) {
                await archiveToFile(completedTasks);
                await loadTasks();
            }
            
            showCongratsModal(sessionDuration, tasksCompleted, tasks.length);
            
            sessionRunning = false;
            sessionPaused = false;
            sessionStartTime = null;
            currentTaskStartTime = null;
            currentSessionId = null;
            clearInterval(timerInterval);
            
            const inputSection = document.querySelector('.input-section');
            inputSection.classList.remove('disabled');
            
            const startBtn = document.getElementById('startBtn');
            startBtn.textContent = 'Start Session';
            startBtn.classList.remove('hidden');
            
            document.getElementById('stopBtn').classList.add('hidden');
            document.getElementById('finishBtn').classList.add('hidden');
            
            const display = document.getElementById('timerDisplay');
            display.classList.remove('running');
            display.textContent = '00:00:00';
            
            renderTasks();
        }

        function showCongratsModal(duration, tasksCompleted, totalTasks) {
            document.getElementById('modalDuration').textContent = formatTime(duration);
            document.getElementById('modalTasksCompleted').textContent = tasksCompleted;
            document.getElementById('modalTotalTasks').textContent = totalTasks;
            document.getElementById('creditsEarned').textContent = creditsEarned.toFixed(2);
            
            const modal = document.getElementById('congratsModal');
            modal.classList.add('show');
        }

        async function closeCongratsModal() {
            const walletInput = document.getElementById('walletInput');
            const walletAddress = walletInput.value.trim();
            
            if (!walletAddress) {
                alert('⚠️ Please enter a wallet address to receive your credits!');
                walletInput.focus();
                return;
            }
            
            if (!walletAddress.startsWith('0x') || walletAddress.length < 20) {
                alert('⚠️ Please enter a valid wallet address (should start with 0x)');
                walletInput.focus();
                return;
            }
            
            const continueBtn = document.getElementById('closeModalBtn');
            continueBtn.disabled = true;
            continueBtn.textContent = 'Processing...';
            
            try {
                const response = await fetch('/api/credit-transfer', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        walletAddress: walletAddress,
                        credits: creditsEarned,
                        sessionId: currentSessionId || 'unknown'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    console.log('✅ Credits transferred:', result);
                    alert(`🎉 Success! ${creditsEarned.toFixed(2)} credits sent to ${walletAddress.slice(0, 10)}...`);
                    
                    const modal = document.getElementById('congratsModal');
                    modal.classList.remove('show');
                    
                    walletInput.value = '';
                    creditsEarned = 0;
                } else {
                    alert('❌ Failed to transfer credits. Please try again.');
                }
            } catch (error) {
                console.error('Credit transfer error:', error);
                alert('❌ Network error. Please check your connection and try again.');
            } finally {
                continueBtn.disabled = false;
                continueBtn.textContent = 'Continue';
            }
        }

        function formatTime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }

        function formatDuration(seconds) {
            if (seconds < 60) return `${seconds}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            return `${h}h ${m}m`;
        }

        function updateTimer() {
            if (!sessionRunning) return;
            const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
            document.getElementById('timerDisplay').textContent = formatTime(elapsed);
        }

        function startSession() {
            if (tasks.length === 0) {
                alert('⚠️ Please add at least one task before starting a session!');
                return;
            }
            
            sessionRunning = true;
            sessionPaused = false;
            
            if (!sessionStartTime) {
                sessionStartTime = Date.now();
                currentSessionId = 'session_' + Date.now();
            }
            
            currentTaskStartTime = Date.now();
            
            const inputSection = document.querySelector('.input-section');
            inputSection.classList.add('disabled');
            
            document.getElementById('startBtn').classList.add('hidden');
            document.getElementById('stopBtn').classList.remove('hidden');
            document.getElementById('finishBtn').classList.remove('hidden');
            
            const display = document.getElementById('timerDisplay');
            display.classList.add('running');
            
            timerInterval = setInterval(updateTimer, 1000);
        }

        function stopSession() {
            sessionRunning = false;
            sessionPaused = true;
            clearInterval(timerInterval);
            
            const startBtn = document.getElementById('startBtn');
            startBtn.textContent = 'Continue Session';
            startBtn.classList.remove('hidden');
            
            document.getElementById('stopBtn').classList.add('hidden');
            document.getElementById('finishBtn').classList.add('hidden');
            
            const display = document.getElementById('timerDisplay');
            display.classList.remove('running');
        }

        function renderTasks() {
            const tasksList = document.getElementById('tasksList');
            
            if (tasks.length === 0) {
                tasksList.innerHTML = '<div class="empty-state">No tasks yet. Add one above!</div>';
                selectedIndex = null;
                return;
            }

            tasksList.innerHTML = '';
            tasks.forEach((task, index) => {
                const taskItem = document.createElement('div');
                taskItem.className = `task-item ${task.done ? 'completed' : ''} ${selectedIndex === index ? 'selected' : ''}`;
                
                const durationText = task.actualTime ? `<span class="task-duration">(${formatDuration(task.actualTime)})</span>` : '';
                
                taskItem.innerHTML = `
                    <div class="task-content">
                        <span class="task-checkbox">${task.done ? '✓' : '○'}</span>
                        <span class="task-text">${escapeHtml(task.task)}${durationText}</span>
                    </div>
                    <button class="delete-btn">×</button>
                `;
                
                const taskContent = taskItem.querySelector('.task-content');
                taskContent.addEventListener('click', () => {
                    if (selectedIndex === index) {
                        const wasUndone = !tasks[index].done;
                        tasks[index].done = !tasks[index].done;
                        
                        if (wasUndone && sessionRunning && currentTaskStartTime) {
                            const actualTime = Math.floor((Date.now() - currentTaskStartTime) / 1000);
                            tasks[index].actualTime = (tasks[index].actualTime || 0) + actualTime;
                            tasks[index].completedAt = new Date().toISOString();
                            tasks[index].lastSessionId = currentSessionId;
                            
                            currentTaskStartTime = Date.now();
                        }
                        
                        saveTasks();
                        renderTasks();
                    } else {
                        selectedIndex = index;
                        renderTasks();
                    }
                });
                
                const deleteBtn = taskItem.querySelector('.delete-btn');
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm(`Delete task: "${task.task}"?`)) {
                        tasks.splice(index, 1);
                        selectedIndex = null;
                        saveTasks();
                        renderTasks();
                    }
                });
                
                tasksList.appendChild(taskItem);
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function addTask() {
            const input = document.getElementById('taskInput');
            const taskText = input.value.trim();
            
            if (taskText) {
                const newTask = {
                    task: taskText,
                    done: false,
                    expectedTime: 0,
                    actualTime: 0,
                    createdAt: new Date().toISOString(),
                    subtasks: [],
                    needsBreakdown: true
                };
                
                tasks.push(newTask);
                saveTasks();
                renderTasks();
                input.value = '';
                input.focus();
            }
        }

        async function archiveToFile(completedTasks) {
            try {
                await fetch('/api/archive', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        archived: completedTasks,
                        archivedAt: new Date().toISOString()
                    })
                });
                console.log('Archived tasks:', completedTasks);
            } catch (error) {
                console.error('Failed to archive:', error);
            }
        }

        document.getElementById('addBtn').addEventListener('click', addTask);
        document.getElementById('taskInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addTask();
        });
        document.getElementById('startBtn').addEventListener('click', startSession);
        document.getElementById('stopBtn').addEventListener('click', stopSession);
        document.getElementById('finishBtn').addEventListener('click', endSession);
        document.getElementById('closeModalBtn').addEventListener('click', closeCongratsModal);

        loadTasks();
    </script>
</body>
</html>
'''


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TodoHandler(http.server.SimpleHTTPRequestHandler):
    def get_session_token(self):
        """Extract session token from cookies"""
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return None
        
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        
        if 'session_token' in cookies:
            return cookies['session_token'].value
        return None
    
    def get_current_user(self):
        """Get current user ID from session"""
        token = self.get_session_token()
        if not token:
            return None
        return get_user_from_session(token)
    
    def require_auth(self):
        """Require authentication, redirect to login if not authenticated"""
        user_id = self.get_current_user()
        if not user_id:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return None
        return user_id
    
    def do_GET(self):
        if self.path == '/login':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(LOGIN_HTML.encode())
            
        elif self.path == '/register':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(REGISTER_HTML.encode())
            
        elif self.path == '/' or self.path == '/index.html':
            user_id = self.require_auth()
            if not user_id:
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
            
        elif self.path == '/api/tasks':
            user_id = self.require_auth()
            if not user_id:
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get tasks for THIS USER ONLY
            tasks = list(tasks_collection.find(
                {'userId': user_id, 'archived': False},
                {'task': 1, 'done': 1, 'expectedTime': 1, 'actualTime': 1,
                 'createdAt': 1, 'completedAt': 1, 'lastSessionId': 1, 
                 'subtasks': 1, 'needsBreakdown': 1}
            ).sort('_id', 1))
            
            for task in tasks:
                task['id'] = str(task['_id'])
                del task['_id']
            
            self.wfile.write(json.dumps(tasks, cls=JSONEncoder).encode())
            
        else:
            self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        if self.path == '/api/register':
            try:
                data = json.loads(post_data)
                username = data.get('username', '').strip()
                password = data.get('password', '')
                
                if len(username) < 3:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'Username must be at least 3 characters'
                    }).encode())
                    return
                
                if len(password) < 6:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'Password must be at least 6 characters'
                    }).encode())
                    return
                
                if users_collection.find_one({'username': username}):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'Username already exists'
                    }).encode())
                    return
                
                hashed_password = hash_password(password)
                user_id = users_collection.insert_one({
                    'username': username,
                    'password': hashed_password,
                    'createdAt': datetime.now().isoformat()
                }).inserted_id
                
                print(f"✅ New user registered: {username}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Account created successfully'
                }).encode())
                
            except Exception as e:
                print(f"Registration error: {e}")
                self.send_error(500)
                
        elif self.path == '/api/login':
            try:
                data = json.loads(post_data)
                username = data.get('username', '').strip()
                password = data.get('password', '')
                
                user = users_collection.find_one({'username': username})
                
                if not user or not verify_password(password, user['password']):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'Invalid username or password'
                    }).encode())
                    return
                
                session_token = create_session(str(user['_id']))
                
                print(f"✅ User logged in: {username}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age=2592000')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Login successful'
                }).encode())
                
            except Exception as e:
                print(f"Login error: {e}")
                self.send_error(500)
                
        elif self.path == '/api/logout':
            session_token = self.get_session_token()
            if session_token and session_token in sessions:
                del sessions[session_token]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Set-Cookie', 'session_token=; Path=/; HttpOnly; Max-Age=0')
            self.end_headers()
            self.wfile.write(b'{"success": true}')
                
        elif self.path == '/api/tasks':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                tasks = json.loads(post_data)
                
                # Delete existing tasks for THIS USER
                tasks_collection.delete_many({'userId': user_id, 'archived': False})
                
                # Insert tasks with USER ID
                for task in tasks:
                    task_id = task.pop('id', None)
                    task['userId'] = user_id  # ⭐ ADD USER ID
                    task['archived'] = False
                    task['done'] = bool(task.get('done', False))
                    task['expectedTime'] = int(task.get('expectedTime', 0))
                    task['actualTime'] = int(task.get('actualTime', 0))
                    task['needsBreakdown'] = bool(task.get('needsBreakdown', True))
                    task['subtasks'] = task.get('subtasks', [])
                    
                    tasks_collection.insert_one(task)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"Error saving tasks: {e}")
                self.send_error(500)
                
        elif self.path == '/api/session':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                session_data = json.loads(post_data)
                session_data['userId'] = user_id  # ⭐ ADD USER ID
                sessions_collection.insert_one(session_data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"Error saving session: {e}")
                self.send_error(500)
                
        elif self.path == '/api/archive':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                archive_data = json.loads(post_data)
                archived_tasks = archive_data['archived']
                archived_at = archive_data['archivedAt']
                
                for task in archived_tasks:
                    if 'id' in task:
                        task_id = task['id']
                        
                        # Archive only THIS USER's tasks
                        tasks_collection.update_one(
                            {'_id': ObjectId(task_id), 'userId': user_id},
                            {'$set': {
                                'archived': True,
                                'archivedAt': archived_at
                            }}
                        )
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"Error archiving tasks: {e}")
                self.send_error(500)
                
        elif self.path == '/api/credit-transfer':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                transfer_data = json.loads(post_data)
                wallet_address = transfer_data.get('walletAddress')
                credits = transfer_data.get('credits', 0)
                session_id = transfer_data.get('sessionId')
                
                # Log credit transfer WITH USER ID
                credit_record = {
                    'userId': user_id,  # ⭐ TRACK USER
                    'walletAddress': wallet_address,
                    'credits': credits,
                    'sessionId': session_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'pending'
                }
                
                credit_transfers_collection.insert_one(credit_record)
                
                print(f"💰 Credit Transfer: {credits} credits → {wallet_address} (User: {user_id})")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'credits': credits,
                    'walletAddress': wallet_address,
                    'message': 'Credits transferred successfully'
                }).encode())
                
            except Exception as e:
                print(f"Error transferring credits: {e}")
                self.send_error(500)
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass

def open_browser():
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == '__main__':
    with socketserver.TCPServer(("0.0.0.0", PORT), TodoHandler) as httpd:
        print(f"✨ To-Do App running at http://localhost:{PORT}")
        print(f"📊 Database: MongoDB Atlas - {DB_NAME}")
        print(f"🔐 Authentication: Enabled")
        
        if os.environ.get('PORT') is None:
            print("🌐 Opening browser...")
            threading.Timer(1.0, open_browser).start()
        else:
            print(f"🌐 Server running on port {PORT}")
            
        print("Press Ctrl+C to stop\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down server...")
            client.close()
