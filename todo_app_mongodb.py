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

# Import new service modules
from auth_service import (
    register_user, login_user, get_user_by_id, 
    update_user_wallet, hash_password, verify_password
)
from task_service import (
    create_task, get_user_tasks, get_task_by_id,
    mark_subtask_done, archive_task, save_user_tasks, complete_task
)
from breakdown_service import request_breakdown
from completion_service import complete_task_with_reward, get_reward_history

PORT = int(os.environ.get('PORT', 8000))

# Session storage
sessions = {}  # {session_token: user_id}

# MongoDB Atlas connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = 'todo_app'

print(f"🔍 Attempting to connect to MongoDB...")

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
    tasks_collection.create_index('needsBreakdown')
    tasks_collection.create_index('userId')
    sessions_collection.create_index('session_id', unique=True)
    sessions_collection.create_index('userId')
    users_collection.create_index('username', unique=True)
    credit_transfers_collection.create_index('userId')
    
    print("✅ Connected to MongoDB Atlas")
    print(f"📊 Database: {DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

def create_session(user_id):
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    sessions[token] = str(user_id)
    return token

def get_current_user_from_token(token):
    """Get user ID from session token"""
    return sessions.get(token)
    sessions[token] = str(user_id)
    return token

def get_user_from_session(session_token):
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
        .error, .success {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .error {
            background: #fed7d7;
            color: #c53030;
        }
        .success {
            background: #c6f6d5;
            color: #22543d;
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

# Main app HTML with SUBTASKS UI
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>To-Do List with Breakdown</title>
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
            max-width: 600px;
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

        .tasks-section {
            margin-bottom: 25px;
            max-height: 450px;
            overflow-y: auto;
            padding-right: 5px;
        }

        .task-item {
            background: #f7fafc;
            padding: 16px 20px;
            margin-bottom: 10px;
            border-radius: 12px;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .task-item:hover {
            border-color: #667eea;
            background: #edf2f7;
        }

        .task-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
        }

        .task-main {
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
            font-weight: 600;
            flex: 1;
        }

        .task-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .expand-btn {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .expand-btn:hover {
            background: #5568d3;
            transform: scale(1.1);
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
        }

        .task-item:hover .delete-btn {
            opacity: 1;
        }

        .delete-btn:hover {
            background: #e53e3e;
            transform: scale(1.2);
        }

        /* Subtasks Section */
        .subtasks-container {
            display: none;
            margin-top: 15px;
            padding-left: 36px;
        }

        .subtasks-container.expanded {
            display: block;
        }

        .section-title {
            font-size: 13px;
            font-weight: 700;
            color: #667eea;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            margin-top: 15px;
        }

        .section-title:first-child {
            margin-top: 0;
        }

        .subtask-item {
            background: white;
            padding: 10px 14px;
            margin-bottom: 6px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease;
        }

        .subtask-item:hover {
            border-color: #667eea;
            background: #f7fafc;
        }

        .subtask-checkbox {
            width: 18px;
            height: 18px;
            border: 2px solid #cbd5e0;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .subtask-checkbox.checked {
            background: #48bb78;
            border-color: #48bb78;
        }

        .subtask-checkbox.checked::after {
            content: '✓';
            color: white;
            font-size: 12px;
            font-weight: bold;
        }

        .subtask-text {
            flex: 1;
            font-size: 14px;
            color: #4a5568;
        }

        .subtask-item.done .subtask-text {
            text-decoration: line-through;
            color: #a0aec0;
        }

        .subtask-time {
            font-size: 11px;
            color: #a0aec0;
            font-weight: 500;
        }

        .breakdown-status {
            font-size: 12px;
            color: #718096;
            margin-top: 8px;
            font-style: italic;
        }

        .breakdown-status.loading {
            color: #667eea;
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

        .stop-btn {
            padding: 0;
            font-size: 14px;
            font-weight: 500;
            border: none;
            background: none;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #718096;
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

        .hidden {
            display: none;
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
            margin-bottom: 12px;
            font-size: 16px;
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

        .close-modal-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
            <p class="congrats-message">You've completed your focus session!</p>
            
            <div class="session-stats">
                <div class="stat-row">
                    <span>Session Duration</span>
                    <span class="stat-value" id="modalDuration">--</span>
                </div>
                <div class="stat-row">
                    <span>Tasks Completed</span>
                    <span class="stat-value" id="modalTasksCompleted">--</span>
                </div>
            </div>

            <div class="credits-section">
                <div class="credits-earned" id="creditsEarned">0</div>
                <div>Credits Earned 💰</div>
            </div>

            <div class="wallet-section">
                <div class="wallet-label">Wallet Address (to receive credits)</div>
                <input 
                    type="text" 
                    class="wallet-input" 
                    id="walletInput" 
                    placeholder="Enter your wallet address (any crypto)"
                    autocomplete="off"
                >
            </div>
            
            <button class="close-modal-btn" id="closeModalBtn">Continue</button>
        </div>
    </div>

    <script>
        let tasks = [];
        let sessionRunning = false;
        let sessionStartTime = null;
        let timerInterval = null;
        let currentSessionId = null;
        let creditsEarned = 0;

        function logout() {
            fetch('/api/logout', { method: 'POST' })
                .then(() => {
                    window.location.href = '/login';
                });
        }

        function calculateCredits(durationSeconds) {
            // 1 credit per 15 SECONDS
            return durationSeconds / 15;
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

        async function requestBreakdown(taskId) {
            try {
                const response = await fetch('/api/breakdown', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ taskId })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Reload tasks to get updated breakdown
                    await loadTasks();
                }
            } catch (error) {
                console.error('Breakdown failed:', error);
            }
        }

        function toggleSubtasks(taskIndex) {
            const task = tasks[taskIndex];
            const container = document.querySelector(`#task-${taskIndex} .subtasks-container`);
            const expandBtn = document.querySelector(`#task-${taskIndex} .expand-btn`);
            
            if (!container) return;
            
            if (container.classList.contains('expanded')) {
                container.classList.remove('expanded');
                expandBtn.textContent = '▼';
            } else {
                container.classList.add('expanded');
                expandBtn.textContent = '▲';
            }
        }

        function toggleSubtask(taskIndex, sectionIndex, subtaskIndex) {
            const task = tasks[taskIndex];
            if (!task.sections || !task.sections[sectionIndex]) return;
            
            const subtask = task.sections[sectionIndex].items[subtaskIndex];
            subtask.done = !subtask.done;
            
            // Check if all subtasks in all sections are done
            let allDone = true;
            for (const section of task.sections) {
                for (const item of section.items) {
                    if (!item.done) {
                        allDone = false;
                        break;
                    }
                }
                if (!allDone) break;
            }
            
            task.done = allDone;
            saveTasks();
            renderTasks();
        }

        function formatTime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }

        function formatDuration(seconds) {
            if (seconds < 60) return `${seconds}s`;
            const m = Math.floor(seconds / 60);
            if (m < 60) return `${m}m`;
            const h = Math.floor(m / 60);
            const rm = m % 60;
            return `${h}h ${rm}m`;
        }

        function renderTasks() {
            const tasksList = document.getElementById('tasksList');
            
            if (tasks.length === 0) {
                tasksList.innerHTML = '<div class="empty-state">No tasks yet. Add one above!</div>';
                return;
            }

            tasksList.innerHTML = '';
            tasks.forEach((task, index) => {
                const taskDiv = document.createElement('div');
                taskDiv.className = 'task-item';
                taskDiv.id = `task-${index}`;
                
                const hasSubtasks = task.sections && task.sections.length > 0;
                const subtasksCount = hasSubtasks ? 
                    task.sections.reduce((sum, sec) => sum + sec.items.length, 0) : 0;
                
                let subtasksHTML = '';
                if (hasSubtasks) {
                    subtasksHTML = '<div class="subtasks-container">';
                    
                    task.sections.forEach((section, sIdx) => {
                        subtasksHTML += `<div class="section-title">${escapeHtml(section.title)}</div>`;
                        
                        section.items.forEach((subtask, stIdx) => {
                            subtasksHTML += `
                                <div class="subtask-item ${subtask.done ? 'done' : ''}" onclick="toggleSubtask(${index}, ${sIdx}, ${stIdx})">
                                    <div class="subtask-checkbox ${subtask.done ? 'checked' : ''}"></div>
                                    <div class="subtask-text">${escapeHtml(subtask.task)}</div>
                                    <div class="subtask-time">${formatDuration(subtask.expectedTime)}</div>
                                </div>
                            `;
                        });
                    });
                    
                    subtasksHTML += '</div>';
                } else if (task.needsBreakdown) {
                    subtasksHTML = '<div class="subtasks-container"><div class="breakdown-status loading">⏳ Breaking down task...</div></div>';
                }
                
                taskDiv.innerHTML = `
                    <div class="task-header">
                        <div class="task-main">
                            <span class="task-checkbox">${task.done ? '✓' : '○'}</span>
                            <span class="task-text">${escapeHtml(task.task)}</span>
                        </div>
                        <div class="task-actions">
                            ${hasSubtasks ? `<button class="expand-btn" onclick="toggleSubtasks(${index})">▼</button>` : ''}
                            <button class="delete-btn" onclick="deleteTask(${index})">×</button>
                        </div>
                    </div>
                    ${subtasksHTML}
                `;
                
                tasksList.appendChild(taskDiv);
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function addTask() {
            const input = document.getElementById('taskInput');
            const taskText = input.value.trim();
            
            if (taskText) {
                const newTask = {
                    task: taskText,
                    done: false,
                    expectedTime: 0,
                    actualTime: 0,
                    createdAt: new Date().toISOString(),
                    needsBreakdown: true,  // Flag for breakdown
                    sections: null,
                    subtasks: []
                };
                
                tasks.push(newTask);
                await saveTasks();
                await loadTasks();  // Reload to get the task ID
                
                // Find the newly added task and request breakdown
                const addedTask = tasks.find(t => t.task === taskText && t.needsBreakdown);
                if (addedTask && addedTask.id) {
                    requestBreakdown(addedTask.id);
                }
                
                input.value = '';
                input.focus();
            }
        }

        function deleteTask(index) {
            if (confirm(`Delete task: "${tasks[index].task}"?`)) {
                tasks.splice(index, 1);
                saveTasks();
                renderTasks();
            }
        }

        async function endSession() {
            if (!sessionStartTime) return;
            
            const sessionDuration = Math.floor((Date.now() - sessionStartTime) / 1000);
            const tasksCompleted = tasks.filter(t => t.done).length;
            
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
            } catch (error) {
                console.error('Failed to save session:', error);
            }
            
            showCongratsModal(sessionDuration, tasksCompleted);
            
            sessionRunning = false;
            sessionStartTime = null;
            currentSessionId = null;
            clearInterval(timerInterval);
            
            document.getElementById('startBtn').textContent = 'Start Session';
            document.getElementById('startBtn').classList.remove('hidden');
            document.getElementById('stopBtn').classList.add('hidden');
            document.getElementById('finishBtn').classList.add('hidden');
            
            const display = document.getElementById('timerDisplay');
            display.classList.remove('running');
            display.textContent = '00:00:00';
        }

        function showCongratsModal(duration, tasksCompleted) {
            document.getElementById('modalDuration').textContent = formatTime(duration);
            document.getElementById('modalTasksCompleted').textContent = tasksCompleted;
            document.getElementById('creditsEarned').textContent = creditsEarned.toFixed(2);
            
            const modal = document.getElementById('congratsModal');
            modal.classList.add('show');
        }

        async function closeCongratsModal() {
            const walletInput = document.getElementById('walletInput');
            const walletAddress = walletInput.value.trim();
            
            if (!walletAddress) {
                alert('⚠️ Please enter a wallet address!');
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
                    alert(`🎉 Success! ${creditsEarned.toFixed(2)} credits sent!`);
                    
                    const modal = document.getElementById('congratsModal');
                    modal.classList.remove('show');
                    
                    walletInput.value = '';
                    creditsEarned = 0;
                }
            } catch (error) {
                console.error('Credit transfer error:', error);
            } finally {
                continueBtn.disabled = false;
                continueBtn.textContent = 'Continue';
            }
        }

        function updateTimer() {
            if (!sessionRunning) return;
            const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
            document.getElementById('timerDisplay').textContent = formatTime(elapsed);
        }

        function startSession() {
            if (tasks.length === 0) {
                alert('⚠️ Add at least one task first!');
                return;
            }
            
            sessionRunning = true;
            
            if (!sessionStartTime) {
                sessionStartTime = Date.now();
                currentSessionId = 'session_' + Date.now();
            }
            
            document.getElementById('startBtn').classList.add('hidden');
            document.getElementById('stopBtn').classList.remove('hidden');
            document.getElementById('finishBtn').classList.remove('hidden');
            
            const display = document.getElementById('timerDisplay');
            display.classList.add('running');
            
            timerInterval = setInterval(updateTimer, 1000);
        }

        function stopSession() {
            sessionRunning = false;
            clearInterval(timerInterval);
            
            document.getElementById('startBtn').textContent = 'Continue Session';
            document.getElementById('startBtn').classList.remove('hidden');
            document.getElementById('stopBtn').classList.add('hidden');
            document.getElementById('finishBtn').classList.add('hidden');
            
            document.getElementById('timerDisplay').classList.remove('running');
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
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return None
        
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        
        if 'session_token' in cookies:
            return cookies['session_token'].value
        return None
    
    def get_current_user(self):
        token = self.get_session_token()
        if not token:
            return None
        return get_current_user_from_token(token)
    
    def require_auth(self):
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
            
            # Use task_service to get tasks
            tasks = get_user_tasks(user_id, archived=False)
            
            self.wfile.write(json.dumps(tasks, cls=JSONEncoder).encode())
        
        elif self.path.startswith('/api/rewards'):
            user_id = self.require_auth()
            if not user_id:
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Use completion_service to get reward history
            rewards = get_reward_history(user_id)
            
            self.wfile.write(json.dumps({'rewards': rewards}, cls=JSONEncoder).encode())
            
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
                
                # Use auth_service to register
                success, message, user_id = register_user(username, password)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': success,
                    'message': message
                }).encode())
                
            except Exception as e:
                print(f"❌ Registration error: {e}")
                self.send_error(500)
                
        elif self.path == '/api/login':
            try:
                data = json.loads(post_data)
                username = data.get('username', '').strip()
                password = data.get('password', '')
                
                # Use auth_service to login
                success, message, user_id = login_user(username, password)
                
                if not success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': message
                    }).encode())
                    return
                
                # Create session
                session_token = create_session(user_id)
                
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
                
                # Use task_service to save all tasks
                success = save_user_tasks(user_id, tasks)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': success}).encode())
                
            except Exception as e:
                print(f"❌ Error saving tasks: {e}")
                self.send_error(500)
        
        elif self.path == '/api/breakdown':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                data = json.loads(post_data)
                task_id = data.get('taskId')
                
                # Use breakdown_service to break down task
                success, message, breakdown_result = request_breakdown(user_id, task_id)
                
                if not success:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': message
                    }).encode())
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'sections': breakdown_result.get('sections', []),
                    'taskType': breakdown_result.get('taskType'),
                    'paceMultiplier': breakdown_result.get('paceMultiplier')
                }).encode())
                
            except Exception as e:
                print(f"❌ Breakdown error: {e}")
                self.send_error(500)
                
        elif self.path == '/api/session':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                session_data = json.loads(post_data)
                session_data['userId'] = user_id
                sessions_collection.insert_one(session_data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"Error saving session: {e}")
                self.send_error(500)
                
        elif self.path == '/api/tasks-complete':
            # Complete a task with evaluation and rewards
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                data = json.loads(post_data)
                task_id = data.get('taskId')
                wallet_address = data.get('walletAddress')
                
                # Update wallet if provided
                if wallet_address:
                    update_user_wallet(user_id, wallet_address)
                
                # Complete task with reward evaluation
                result = complete_task_with_reward(user_id, task_id)
                
                self.send_response(200 if result['success'] else 400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                print(f"❌ Task completion error: {e}")
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
                
                # Update wallet
                update_user_wallet(user_id, wallet_address)
                
                print(f"💰 Wallet updated: {wallet_address}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'credits': credits,
                    'walletAddress': wallet_address,
                    'message': 'Wallet updated successfully'
                }).encode())
                
            except Exception as e:
                print(f"❌ Error updating wallet: {e}")
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
        print(f"🤖 Task Breakdown: Enabled")
        
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
