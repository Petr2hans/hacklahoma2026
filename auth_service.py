"""
Authentication Service
Handles user registration, login, session management, and password hashing
"""

import hashlib
import secrets
import time
from bson import ObjectId

from db import get_client

def get_users_collection():
    """Get users collection from MongoDB"""
    client = get_client()
    return client['todo_app']['users']

def get_profiles_collection():
    """Get user profiles collection from MongoDB"""
    client = get_client()
    return client['todo_app']['user_profiles']

def hash_password(password):
    """Hash password with salt for secure storage"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password, hashed):
    """Verify password against stored hash"""
    try:
        salt, pwd_hash = hashed.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except:
        return False

def register_user(username, password):
    """
    Register a new user
    Returns: (success: bool, message: str, user_id: str or None)
    """
    users_col = get_users_collection()
    
    # Validate input
    if len(username) < 3:
        return False, "Username must be at least 3 characters", None
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters", None
    
    # Check if username exists
    if users_col.find_one({'username': username}):
        return False, "Username already exists", None
    
    # Create user
    try:
        hashed_password = hash_password(password)
        result = users_col.insert_one({
            'username': username,
            'password': hashed_password,
            'walletAddress': None,
            'createdAt': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'totalCreditsEarned': 0,
            'totalTokensReceived': 0.0
        })
        
        user_id = str(result.inserted_id)
        
        # Create user profile
        profiles_col = get_profiles_collection()
        profiles_col.insert_one({
            '_id': user_id,
            'paceByType': {},
            'createdAt': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })
        
        print(f"✅ User registered: {username}")
        return True, "Account created successfully", user_id
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False, str(e), None

def login_user(username, password):
    """
    Login user
    Returns: (success: bool, message: str, user_id: str or None)
    """
    users_col = get_users_collection()
    
    user = users_col.find_one({'username': username})
    
    if not user or not verify_password(password, user['password']):
        return False, "Invalid username or password", None
    
    print(f"✅ User logged in: {username}")
    return True, "Login successful", str(user['_id'])

def get_user_by_id(user_id):
    """Get user document by ID"""
    users_col = get_users_collection()
    try:
        return users_col.find_one({'_id': ObjectId(user_id)})
    except:
        return None

def update_user_wallet(user_id, wallet_address):
    """Update user's Solana wallet address"""
    users_col = get_users_collection()
    try:
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'walletAddress': wallet_address}}
        )
        return True
    except:
        return False

def update_user_tokens(user_id, amount):
    """Update total tokens received by user"""
    users_col = get_users_collection()
    try:
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$inc': {
                    'totalTokensReceived': amount,
                    'totalCreditsEarned': 1
                }
            }
        )
        return True
    except:
        return False
