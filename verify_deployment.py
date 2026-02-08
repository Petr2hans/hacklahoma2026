#!/usr/bin/env python3
"""
Deployment Verification Script
Checks that all services and integrations are working correctly
"""

import sys
import json
from datetime import datetime

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_imports():
    """Verify all required imports are available"""
    print_section("Checking Imports")
    
    imports = {
        'pymongo': 'MongoDB driver',
        'solana': 'Solana blockchain library',
        'solders': 'Solana signers library',
        'google.generativeai': 'Google Gemini API',
        'httpx': 'HTTP client',
    }
    
    failed = []
    for module, description in imports.items():
        try:
            __import__(module)
            print(f"✓ {module:30} ({description})")
        except ImportError as e:
            print(f"✗ {module:30} - {e}")
            failed.append(module)
    
    return len(failed) == 0

def check_modules():
    """Verify all custom modules exist and can be imported"""
    print_section("Checking Custom Modules")
    
    modules = [
        'db',
        'config',
        'auth_service',
        'task_service',
        'breakdown_service',
        'completion_service',
        'gemini_client',
        'parsers',
        'prompts',
        'sol',
        'pace',
        'credit'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}.py")
        except ImportError as e:
            print(f"✗ {module}.py - {e}")
            failed.append(module)
    
    return len(failed) == 0

def check_environment():
    """Check environment variables"""
    print_section("Checking Environment Variables")
    
    required_vars = {
        'MONGODB_URI': 'MongoDB connection string',
        'MONGODB_DB': 'MongoDB database name',
        'GEMINI_API_KEY': 'Google Gemini API key',
    }
    
    optional_vars = {
        'token_address': 'Solana token mint address',
        'sol_key': 'Solana treasury keypair',
        'PORT': 'Server port',
        'HOST': 'Server host',
    }
    
    import os
    
    failed = []
    missing = []
    
    # Check required vars
    for var, description in required_vars.items():
        if var in os.environ:
            value = os.environ[var]
            shows = value[:30] + '...' if len(value) > 30 else value
            print(f"✓ {var:20} = {shows}")
        else:
            print(f"✗ {var:20} - MISSING")
            missing.append(var)
            failed.append(var)
    
    # Check optional vars
    print()
    for var, description in optional_vars.items():
        if var in os.environ:
            value = os.environ[var]
            shows = value[:30] + '...' if len(value) > 30 else value
            print(f"✓ {var:20} = {shows}")
        else:
            print(f"⊘ {var:20} - not set (optional)")
    
    if missing:
        print(f"\n⚠️  Missing required environment variables: {', '.join(missing)}")
        print("   Copy .env.example to .env and fill in the values")
    
    return len(failed) == 0

def check_mongodb():
    """Test MongoDB connection"""
    print_section("Checking MongoDB Connection")
    
    try:
        from db import get_client
        client = get_client()
        
        # Try to ping the server
        info = client.server_info()
        print(f"✓ Connected to MongoDB")
        print(f"  Version: {info.get('version', 'unknown')}")
        
        # List databases
        db_names = client.list_database_names()
        print(f"  Available databases: {', '.join(db_names[:5])}")
        
        # Check our database
        db = client['todo_app']
        collections = db.list_collection_names()
        print(f"  Collections in 'todo_app': {', '.join(collections) if collections else 'none'}")
        
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed")
        print(f"  Error: {str(e)}")
        print(f"\n  Troubleshooting:")
        print(f"  1. Ensure MONGODB_URI is set correctly")
        print(f"  2. Check MongoDB Atlas cluster is running")
        print(f"  3. Verify IP whitelist (should include your IP or 0.0.0.0)")
        return False

def check_gemini():
    """Test Gemini API connection"""
    print_section("Checking Gemini API Connection")
    
    try:
        from gemini_client import get_gemini_client
        client = get_gemini_client()
        
        # Try a simple request
        response = client.generate_content("What is 2+2?")
        if response.text:
            print(f"✓ Connected to Gemini API")
            print(f"  Test response: {response.text[:50]}...")
            return True
        else:
            print(f"✗ Gemini returned empty response")
            return False
            
    except Exception as e:
        print(f"✗ Gemini API connection failed")
        print(f"  Error: {str(e)}")
        print(f"\n  Troubleshooting:")
        print(f"  1. Ensure GEMINI_API_KEY is set correctly")
        print(f"  2. Check your API key has Generative Language API enabled")
        print(f"  3. Verify you have quota remaining on your API")
        return False

def check_solana():
    """Test Solana connection"""
    print_section("Checking Solana Connection")
    
    try:
        from solana.rpc.api import Client
        from solana.rpc.commitment import Confirmed
        
        # Connect to devnet
        client = Client("https://api.devnet.solana.com", commitment=Confirmed)
        
        # Get cluster version
        response = client.get_version()
        if response.value:
            print(f"✓ Connected to Solana devnet")
            print(f"  Solana version: {response.value.solana_version}")
            return True
        else:
            print(f"✗ Solana returned empty response")
            return False
            
    except Exception as e:
        print(f"✗ Solana connection failed")
        print(f"  Error: {str(e)}")
        print(f"\n  Note: This is optional for development")
        print(f"  You can test without Solana initially")
        return False

def check_services():
    """Test service modules"""
    print_section("Checking Service Modules")
    
    try:
        from auth_service import hash_password, verify_password
        pwd = "testpassword"
        hashed = hash_password(pwd)
        if verify_password(pwd, hashed):
            print(f"✓ auth_service - password hashing works")
        else:
            print(f"✗ auth_service - password verification failed")
            return False
            
        from task_service import create_task
        print(f"✓ task_service - imported successfully")
        
        from breakdown_service import request_breakdown
        print(f"✓ breakdown_service - imported successfully")
        
        from completion_service import complete_task_with_reward
        print(f"✓ completion_service - imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Service module check failed")
        print(f"  Error: {str(e)}")
        return False

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("  Deployment Verification Script")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    results = {
        'imports': check_imports(),
        'modules': check_modules(),
        'environment': check_environment(),
        'services': check_services(),
        'mongodb': check_mongodb(),
        'gemini': check_gemini(),
        'solana': check_solana(),
    }
    
    print_section("Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {check.title()}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Your deployment is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
