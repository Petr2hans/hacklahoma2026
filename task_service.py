"""
Task Service
Handles task CRUD operations, subtask tracking, and task status management
"""

import time
from datetime import datetime
from bson import ObjectId
from db import get_client

def get_tasks_collection():
    """Get tasks collection from MongoDB"""
    client = get_client()
    return client['todo_app']['tasks']

def create_task(user_id, title, estimated_minutes=60):
    """Create a new task"""
    tasks_col = get_tasks_collection()
    
    try:
        task = {
            'userId': user_id,
            'task': title.strip(),
            'status': 'pending',
            'estimatedMinutes': estimated_minutes,
            'expectedTotalTime': 0,  # Will be set after breakdown
            'actualTotalTime': 0,
            'subtasks': [],
            'taskType': None,
            'paceMultiplier': 1.0,
            'needsBreakdown': True,
            'creditEarned': False,
            'rewardSent': False,
            'rewardAmount': 0.0,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'completedAt': None,
            'sections': None  # For backward compatibility
        }
        
        result = tasks_col.insert_one(task)
        task['_id'] = str(result.inserted_id)
        task['id'] = str(result.inserted_id)
        return task
        
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        return None

def get_user_tasks(user_id, archived=False):
    """Get all tasks for a user"""
    tasks_col = get_tasks_collection()
    
    try:
        query = {'userId': user_id, 'archived': archived}
        tasks = list(tasks_col.find(query).sort('createdAt', -1))
        
        # Convert ObjectIds to strings
        for task in tasks:
            task['_id'] = str(task['_id'])
            task['id'] = str(task['_id'])
        
        return tasks
    except Exception as e:
        print(f"❌ Error fetching tasks: {e}")
        return []

def get_task_by_id(user_id, task_id):
    """Get a specific task by ID"""
    tasks_col = get_tasks_collection()
    
    try:
        task = tasks_col.find_one({
            '_id': ObjectId(task_id),
            'userId': user_id
        })
        
        if task:
            task['_id'] = str(task['_id'])
            task['id'] = str(task['_id'])
        
        return task
    except:
        return None

def update_task(user_id, task_id, updates):
    """Update task with new data"""
    tasks_col = get_tasks_collection()
    
    try:
        result = tasks_col.find_one_and_update(
            {
                '_id': ObjectId(task_id),
                'userId': user_id
            },
            {'$set': updates},
            return_document=True
        )
        
        if result:
            result['_id'] = str(result['_id'])
            result['id'] = str(result['_id'])
        
        return result
    except Exception as e:
        print(f"❌ Error updating task: {e}")
        return None

def save_user_tasks(user_id, tasks):
    """Save all tasks for a user (bulk update) - for backward compatibility"""
    tasks_col = get_tasks_collection()
    
    try:
        # Delete old tasks
        tasks_col.delete_many({'userId': user_id, 'archived': False})
        
        # Insert new tasks
        for task in tasks:
            task_id = task.pop('id', None)
            task['userId'] = user_id
            task['archived'] = False
            task['done'] = bool(task.get('done', False))
            task['expectedTime'] = int(task.get('expectedTime', 0))
            task['actualTime'] = int(task.get('actualTime', 0))
            task['needsBreakdown'] = bool(task.get('needsBreakdown', True))
            task['sections'] = task.get('sections', None)
            task['subtasks'] = task.get('subtasks', [])
            task['status'] = task.get('status', 'pending')
            
            tasks_col.insert_one(task)
        
        return True
    except Exception as e:
        print(f"❌ Error saving tasks: {e}")
        return False

def mark_subtask_done(user_id, task_id, subtask_id=None, actual_time=0):
    """Mark a subtask as done and log time spent"""
    tasks_col = get_tasks_collection()
    
    try:
        task = get_task_by_id(user_id, task_id)
        if not task:
            return None
        
        # Update subtask if sections exist (from breakdown)
        if task.get('sections'):
            for section in task.get('sections', []):
                for item in section.get('items', []):
                    if item.get('id') == subtask_id:
                        item['done'] = True
                        item['actualTime'] = actual_time
                        item['completedAt'] = datetime.utcnow().isoformat() + 'Z'
            
            # Check if all subtasks are done
            all_done = True
            for section in task.get('sections', []):
                for item in section.get('items', []):
                    if not item.get('done'):
                        all_done = False
                        break
            
            # Update status
            new_status = 'ready_for_completion' if all_done else 'in_progress'
            
            # Calculate total actual time
            total_actual = 0
            for section in task.get('sections', []):
                for item in section.get('items', []):
                    total_actual += item.get('actualTime', 0)
            
            task_updates = {
                'sections': task.get('sections'),
                'status': new_status,
                'actualTotalTime': total_actual
            }
        else:
            # For non-breakdown tasks, just mark done
            task_updates = {
                'actualTotalTime': actual_time,
                'status': 'ready_for_completion',
                'done': True
            }
        
        return update_task(user_id, task_id, task_updates)
    
    except Exception as e:
        print(f"❌ Error marking subtask done: {e}")
        return None

def archive_task(user_id, task_id):
    """Archive a task (soft delete)"""
    tasks_col = get_tasks_collection()
    
    try:
        tasks_col.update_one(
            {'_id': ObjectId(task_id), 'userId': user_id},
            {'$set': {'archived': True, 'status': 'archived'}}
        )
        return True
    except:
        return False

def update_task_breakdown(user_id, task_id, breakdown_result):
    """Update task with breakdown results from Gemini"""
    tasks_col = get_tasks_collection()
    
    try:
        # Calculate expected total time
        expected_total = 0
        if breakdown_result.get('sections'):
            for section in breakdown_result.get('sections', []):
                for item in section.get('items', []):
                    expected_total += item.get('expectedTime', 0)
        
        updates = {
            'sections': breakdown_result.get('sections'),
            'subtasks': breakdown_result.get('subtasks', []),
            'taskType': breakdown_result.get('taskType', 'other'),
            'paceMultiplier': breakdown_result.get('paceMultiplier', 1.0),
            'expectedTotalTime': expected_total,
            'needsBreakdown': False,
            'status': 'ready',
            'breakdownAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return update_task(user_id, task_id, updates)
    except Exception as e:
        print(f"❌ Error updating task breakdown: {e}")
        return None

def complete_task(user_id, task_id):
    """Mark task as completed"""
    tasks_col = get_tasks_collection()
    
    try:
        updates = {
            'status': 'completed',
            'completedAt': datetime.utcnow().isoformat() + 'Z',
            'done': True
        }
        
        return update_task(user_id, task_id, updates)
    except Exception as e:
        print(f"❌ Error completing task: {e}")
        return None
