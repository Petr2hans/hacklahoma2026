"""
🚀 UNIFIED FOCUS APP - Complete Integration
Combines: Authentication + To-Do + Gemini Breakdown + Solana Payments
Ready for Render deployment!
"""

import http.server
import socketserver
import json
import os
import webbrowser
import threading
import hashlib
import secrets
import asyncio
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Dict, Any, List

# Import your existing modules
from workers_breakdown import breakdown_one_task, ensure_profile
from sol import send_study_reward
from config import (
    MONGODB_URI, DB_NAME, 
    TASKS_COLLECTION, SESSIONS_COLLECTION,
    KEY_USER_ID, KEY_TASK, KEY_DONE, KEY_SUBTASKS,
    KEY_NEEDS_BREAKDOWN, KEY_ARCHIVED, KEY_EXPECTED, KEY_ACTUAL
)

PORT = int(os.environ.get('PORT', 8000))

# Session storage (in-memory)
sessions = {}  # {session_token: user_id}

print("="*60)
print("🚀 UNIFIED FOCUS APP STARTING...")
print("="*60)
print(f"🔍 Connecting to MongoDB...")

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    
    db = client[DB_NAME]
    tasks_collection = db[TASKS_COLLECTION]
    sessions_collection = db[SESSIONS_COLLECTION]
    users_collection = db['users']
    credit_transfers_collection = db['credit_transfers']
    
    # Create indexes
    tasks_collection.create_index(KEY_ARCHIVED)
    tasks_collection.create_index(KEY_USER_ID)
    tasks_collection.create_index(KEY_NEEDS_BREAKDOWN)
    sessions_collection.create_index(KEY_USER_ID)
    users_collection.create_index('username', unique=True)
    credit_transfers_collection.create_index(KEY_USER_ID)
    credit_transfers_collection.create_index('status')
    
    print("✅ Connected to MongoDB Atlas")
    print(f"📊 Database: {DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    raise

# Auth helpers
def hash_password(password):
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password, hashed):
    try:
        salt, pwd_hash = hashed.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except:
        return False

def create_session(user_id):
    token = secrets.token_urlsafe(32)
    sessions[token] = str(user_id)
    return token

def get_user_from_session(session_token):
    return sessions.get(session_token)

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# Async wrapper for Solana
def send_solana_credits_sync(wallet_address: str, credits: float):
    """Synchronous wrapper for async Solana send"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_study_reward(wallet_address, credits))
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Solana payment error: {e}")
        return None

# Load HTML templates
def load_template(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except:
        return f"<h1>Error: {filename} not found</h1>"

LOGIN_HTML = load_template('templates/login.html')
REGISTER_HTML = load_template('templates/register.html')
APP_HTML = load_template('templates/app.html')


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class UnifiedAppHandler(http.server.SimpleHTTPRequestHandler):
    
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
        return get_user_from_session(token)
    
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
            self.wfile.write(APP_HTML.encode())
            
        elif self.path == '/api/tasks':
            user_id = self.require_auth()
            if not user_id:
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get user's tasks
            tasks = list(tasks_collection.find(
                {KEY_USER_ID: user_id, KEY_ARCHIVED: False},
                {KEY_TASK: 1, KEY_DONE: 1, KEY_EXPECTED: 1, KEY_ACTUAL: 1,
                 'createdAt': 1, KEY_SUBTASKS: 1, KEY_NEEDS_BREAKDOWN: 1, 'taskType': 1}
            ).sort('_id', 1))
            
            for task in tasks:
                task['id'] = str(task['_id'])
                del task['_id']
                # Ensure subtasks exist
                if KEY_SUBTASKS not in task:
                    task[KEY_SUBTASKS] = []
            
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
                    'createdAt': now_iso()
                }).inserted_id
                
                # Create user profile for pace tracking
                ensure_profile(str(user_id))
                
                print(f"✅ New user registered: {username}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Account created successfully'
                }).encode())
                
            except Exception as e:
                print(f"❌ Registration error: {e}")
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
                print(f"❌ Login error: {e}")
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
                
                # Delete existing non-archived tasks
                tasks_collection.delete_many({KEY_USER_ID: user_id, KEY_ARCHIVED: False})
                
                # Insert tasks with userId
                for task in tasks:
                    task_id = task.pop('id', None)
                    task[KEY_USER_ID] = user_id
                    task[KEY_ARCHIVED] = False
                    task[KEY_DONE] = bool(task.get(KEY_DONE, False))
                    task[KEY_EXPECTED] = int(task.get(KEY_EXPECTED, 0))
                    task[KEY_ACTUAL] = int(task.get(KEY_ACTUAL, 0))
                    task[KEY_NEEDS_BREAKDOWN] = bool(task.get(KEY_NEEDS_BREAKDOWN, True))
                    task[KEY_SUBTASKS] = task.get(KEY_SUBTASKS, [])
                    
                    tasks_collection.insert_one(task)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
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
                
                # Get the task
                task = tasks_collection.find_one({
                    '_id': ObjectId(task_id),
                    KEY_USER_ID: user_id
                })
                
                if not task:
                    self.send_error(404)
                    return
                
                print(f"🤖 Breaking down task: {task.get(KEY_TASK)}")
                
                # ✅ CALL YOUR ACTUAL GEMINI BREAKDOWN!
                subtasks, task_type, pace = breakdown_one_task(user_id, task)
                
                # Calculate total expected time
                expected_total = sum(st[KEY_EXPECTED] for st in subtasks)
                
                # Update task with breakdown
                tasks_collection.update_one(
                    {'_id': ObjectId(task_id)},
                    {'$set': {
                        KEY_SUBTASKS: subtasks,
                        KEY_NEEDS_BREAKDOWN: False,
                        KEY_EXPECTED: expected_total,
                        'taskType': task_type,
                        'paceMultiplier': pace,
                        'breakdownAt': now_iso()
                    }}
                )
                
                print(f"✅ Breakdown complete: {len(subtasks)} subtasks, type: {task_type}, pace: {pace}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'subtasks': subtasks,
                    'taskType': task_type,
                    'expectedTime': expected_total
                }).encode())
                
            except Exception as e:
                print(f"❌ Breakdown error: {e}")
                import traceback
                traceback.print_exc()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': str(e)
                }).encode())
                
        elif self.path == '/api/session':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                session_data = json.loads(post_data)
                session_data[KEY_USER_ID] = user_id
                sessions_collection.insert_one(session_data)
                
                print(f"💾 Session saved: {session_data.get('sessionId')} - {session_data.get('creditsEarned')} credits")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                
            except Exception as e:
                print(f"❌ Error saving session: {e}")
                self.send_error(500)
                
        elif self.path == '/api/credit-transfer':
            user_id = self.get_current_user()
            if not user_id:
                self.send_error(401)
                return
            
            try:
                transfer_data = json.loads(post_data)
                wallet_address = transfer_data.get('walletAddress')
                credits = float(transfer_data.get('credits', 0))
                session_id = transfer_data.get('sessionId')
                
                # Save transfer record
                credit_record = {
                    KEY_USER_ID: user_id,
                    'walletAddress': wallet_address,
                    'credits': credits,
                    'sessionId': session_id,
                    'timestamp': now_iso(),
                    'status': 'pending',
                    'transactionHash': None
                }
                
                transfer_id = credit_transfers_collection.insert_one(credit_record).inserted_id
                
                print(f"💰 Attempting Solana transfer: {credits} tokens → {wallet_address[:6]}...")
                
                # ✅ ATTEMPT SOLANA TRANSFER
                tx_hash = send_solana_credits_sync(wallet_address, credits)
                
                if tx_hash:
                    # Update as completed
                    credit_transfers_collection.update_one(
                        {'_id': transfer_id},
                        {'$set': {
                            'status': 'completed',
                            'transactionHash': str(tx_hash),
                            'completedAt': now_iso()
                        }}
                    )
                    print(f"✅ Solana transfer complete: {tx_hash}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'credits': credits,
                        'walletAddress': wallet_address,
                        'transactionHash': str(tx_hash),
                        'message': f'Successfully sent {credits} tokens!'
                    }).encode())
                else:
                    # Mark as failed
                    credit_transfers_collection.update_one(
                        {'_id': transfer_id},
                        {'$set': {
                            'status': 'failed',
                            'error': 'Solana transfer failed',
                            'failedAt': now_iso()
                        }}
                    )
                    
                    print(f"❌ Solana transfer failed")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'Transfer failed - saved for manual processing'
                    }).encode())
                
            except Exception as e:
                print(f"❌ Error in credit transfer: {e}")
                import traceback
                traceback.print_exc()
                
                # Still save the record
                if 'transfer_id' in locals():
                    credit_transfers_collection.update_one(
                        {'_id': transfer_id},
                        {'$set': {
                            'status': 'error',
                            'error': str(e),
                            'failedAt': now_iso()
                        }}
                    )
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'Error: {str(e)}'
                }).encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass


def open_browser():
    webbrowser.open(f'http://localhost:{PORT}')


if __name__ == '__main__':
    with socketserver.TCPServer(("0.0.0.0", PORT), UnifiedAppHandler) as httpd:
        print("="*60)
        print(f"✨ UNIFIED FOCUS APP RUNNING")
        print("="*60)
        print(f"🌐 URL: http://localhost:{PORT}")
        print(f"📊 Database: {DB_NAME}")
        print(f"🤖 Gemini Breakdown: ENABLED")
        print(f"💰 Solana Payments: ENABLED")
        print(f"🔐 Authentication: ENABLED")
        print("="*60)
        
        if os.environ.get('PORT') is None:
            print("🌐 Opening browser...")
            threading.Timer(1.0, open_browser).start()
        
        print("\nPress Ctrl+C to stop\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            client.close()
