"""
Completion & Reward Service
Handles task completion, credit evaluation, pace multiplier updates, and Solana rewards
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any

from db import get_client
from pace import update_pace_multiplier
from auth_service import get_user_by_id, update_user_tokens, get_profiles_collection
from task_service import get_task_by_id, update_task

# Try to import Solana reward function
try:
    from sol import send_study_reward
    SOLANA_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Solana integration not available: {e}")
    SOLANA_AVAILABLE = False

def get_transfers_collection():
    """Get credit transfers collection from MongoDB"""
    client = get_client()
    return client['todo_app']['credit_transfers']

def now_iso() -> str:
    """Get current time in ISO format"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def evaluate_task_completion(user_id: str, task_id: str) -> Dict[str, Any]:
    """
    Evaluate task completion:
    1. Calculate time ratio (actual / expected)
    2. Determine if credit earned (ratio <= 1.0)
    3. Update pace multiplier
    4. Return evaluation result
    """
    task = get_task_by_id(user_id, task_id)
    if not task:
        raise ValueError("Task not found")
    
    # Get task times
    expected = task.get('expectedTotalTime', 0)
    actual = task.get('actualTotalTime', 0)
    task_type = task.get('taskType', 'other')
    
    if expected <= 0:
        raise ValueError("Expected time not set in task")
    
    # Calculate ratio and credit
    ratio = actual / expected if expected > 0 else 0
    credit_earned = ratio <= 1.0  # User earned credit if they beat or met expected time
    
    # Update pace multiplier
    try:
        profiles_col = get_profiles_collection()
        profile = profiles_col.find_one({"_id": user_id})
        
        if not profile:
            profile = {"_id": user_id, "paceByType": {}, "createdAt": now_iso()}
        
        profile = update_pace_multiplier(profile, task_type, ratio, lr=0.15)
        profiles_col.update_one({"_id": user_id}, {"$set": profile}, upsert=True)
        
        new_multiplier = profile["paceByType"].get(task_type, {}).get("multiplier", 1.0)
    except Exception as e:
        print(f"⚠️ Error updating pace multiplier: {e}")
        new_multiplier = 1.0
    
    return {
        "taskId": task_id,
        "creditEarned": credit_earned,
        "actualTime": actual,
        "expectedTime": expected,
        "ratio": round(ratio, 3),
        "taskType": task_type,
        "newMultiplier": round(new_multiplier, 3)
    }

def complete_task_with_reward(user_id: str, task_id: str) -> Dict[str, Any]:
    """
    Complete a task end-to-end:
    1. Evaluate task
    2. Determine reward amount
    3. Send Solana reward if earned
    4. Update task and user records
    5. Return result
    """
    try:
        # Get task
        task = get_task_by_id(user_id, task_id)
        if not task:
            return {
                "success": False,
                "message": "Task not found",
                "data": None
            }
        
        # Evaluate completion
        eval_result = evaluate_task_completion(user_id, task_id)
        
        # Determine reward
        reward_amount = 5.0 if eval_result["creditEarned"] else 0.0
        
        # Try to send reward
        reward_status = "none"
        reward_tx_hash = None
        reward_error = None
        
        if reward_amount > 0:
            try:
                user = get_user_by_id(user_id)
                if user and user.get('walletAddress'):
                    # Send reward synchronously (blocking)
                    if SOLANA_AVAILABLE:
                        try:
                            tx_hash = asyncio.run(send_study_reward(user['walletAddress'], reward_amount))
                            if tx_hash:
                                reward_status = "pending"
                                reward_tx_hash = tx_hash
                                print(f"✅ Reward sent: {reward_amount} SOL → {user['walletAddress']}")
                        except Exception as e:
                            reward_error = str(e)
                            print(f"⚠️ Failed to send Solana reward: {e}")
                            reward_status = "failed"
                    else:
                        # Just log the reward for later processing
                        reward_status = "pending"
                else:
                    reward_status = "no_wallet"
            except Exception as e:
                print(f"⚠️ Error during reward sending: {e}")
                reward_error = str(e)
                reward_status = "failed"
        
        # Update task
        task_updates = {
            'status': 'completed',
            'completedAt': now_iso(),
            'done': True,
            'creditEarned': eval_result["creditEarned"],
            'rewardAmount': reward_amount,
            'rewardSent': reward_status == "pending" or reward_status == "confirmed"
        }
        
        updated_task = update_task(user_id, task_id, task_updates)
        
        # Log reward transfer
        if reward_amount > 0:
            try:
                transfers_col = get_transfers_collection()
                transfers_col.insert_one({
                    'userId': user_id,
                    'taskId': task_id,
                    'amount': reward_amount,
                    'walletAddress': task.get('walletAddress') or get_user_by_id(user_id).get('walletAddress'),
                    'txHash': reward_tx_hash,
                    'status': reward_status,
                    'error': reward_error,
                    'createdAt': now_iso()
                })
            except Exception as e:
                print(f"⚠️ Error logging transfer: {e}")
        
        # Update user stats
        try:
            update_user_tokens(user_id, reward_amount)
        except Exception as e:
            print(f"⚠️ Error updating user tokens: {e}")
        
        # Generate feedback message
        if eval_result["creditEarned"]:
            if eval_result["ratio"] < 0.5:
                feedback = "🚀 Wow! You crushed this! Way faster than expected!"
            elif eval_result["ratio"] < 0.9:
                feedback = "🎉 Great job! You finished faster than expected!"
            else:
                feedback = "💪 Nice work! You completed this on time!"
        else:
            feedback = "💪 Keep practicing! Next time will be faster. Track your pace multiplier!"
        
        return {
            "success": True,
            "message": "Task completed successfully",
            "data": {
                "taskId": task_id,
                "creditEarned": eval_result["creditEarned"],
                "feedback": feedback,
                "rewardAmount": reward_amount,
                "rewardStatus": reward_status,
                "rewardTxHash": reward_tx_hash,
                "actualTime": eval_result["actualTime"],
                "expectedTime": eval_result["expectedTime"],
                "timeRatio": eval_result["ratio"],
                "taskType": eval_result["taskType"],
                "newPaceMultiplier": eval_result["newMultiplier"],
                "completedAt": now_iso()
            }
        }
    
    except Exception as e:
        print(f"❌ Error in complete_task_with_reward: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": None
        }

def get_reward_history(user_id: str, limit: int = 50) -> list:
    """Get user's reward/transfer history"""
    try:
        transfers_col = get_transfers_collection()
        transfers = list(
            transfers_col.find({"userId": user_id})
            .sort("createdAt", -1)
            .limit(limit)
        )
        
        # Convert ObjectIds to strings
        for t in transfers:
            t["_id"] = str(t.get("_id", ""))
        
        return transfers
    except Exception as e:
        print(f"⚠️ Error fetching reward history: {e}")
        return []

def get_total_rewards(user_id: str) -> float:
    """Get total rewards earned by user"""
    try:
        transfers_col = get_transfers_collection()
        result = list(transfers_col.aggregate([
            {"$match": {"userId": user_id, "status": {"$in": ["confirmed", "pending"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]))
        
        return result[0]["total"] if result else 0.0
    except Exception as e:
        print(f"⚠️ Error calculating total rewards: {e}")
        return 0.0
