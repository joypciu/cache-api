"""
Request Tracking Module
Tracks all API requests from non-admin users with session-based tracking.
Stores data in JSON format for easy analysis.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict
import asyncio
from pathlib import Path

# Directory to store tracking data
TRACKING_DIR = os.path.join(os.path.dirname(__file__), "request_logs")
SESSIONS_FILE = os.path.join(TRACKING_DIR, "sessions.json")
REQUESTS_FILE = os.path.join(TRACKING_DIR, "requests.json")

# In-memory session storage
active_sessions: Dict[str, Dict[str, Any]] = {}

def init_tracking():
    """Initialize tracking directory and files"""
    # Create directory if it doesn't exist
    os.makedirs(TRACKING_DIR, exist_ok=True)
    
    # Initialize sessions file if it doesn't exist
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'w') as f:
            json.dump({"sessions": {}}, f, indent=2)
    
    # Initialize requests file if it doesn't exist
    if not os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'w') as f:
            json.dump({"requests": []}, f, indent=2)
    
    # Load active sessions into memory
    load_sessions()
    
    print(f"Request tracking initialized. Logs directory: {TRACKING_DIR}")


def load_sessions():
    """Load sessions from file into memory"""
    global active_sessions
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r') as f:
                data = json.load(f)
                active_sessions = data.get("sessions", {})
    except Exception as e:
        print(f"Error loading sessions: {e}")
        active_sessions = {}


def save_sessions():
    """Save sessions from memory to file"""
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump({"sessions": active_sessions, "last_updated": datetime.now().isoformat()}, f, indent=2)
    except Exception as e:
        print(f"Error saving sessions: {e}")


def create_session(user_identifier: str, ip_address: str, user_agent: str, token_type: str) -> str:
    """
    Create a new session for a user.
    
    Args:
        user_identifier: UUID or username of the user
        ip_address: IP address of the client
        user_agent: User agent string
        token_type: Type of token used (admin or non-admin)
    
    Returns:
        Session ID
    """
    session_id = str(uuid.uuid4())
    
    session_data = {
        "session_id": session_id,
        "user_identifier": user_identifier,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "token_type": token_type,
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "request_count": 0
    }
    
    active_sessions[session_id] = session_data
    save_sessions()
    
    return session_id


def get_or_create_session(token: str, ip_address: str, user_agent: str, user_identifier: Optional[str] = None) -> str:
    """
    Get existing session or create a new one based on token and IP.
    
    Args:
        token: API token used
        ip_address: Client IP address
        user_agent: User agent string
        user_identifier: Optional user identifier (UUID)
    
    Returns:
        Session ID
    """
    # Determine token type
    from main import ADMIN_KEY
    token_type = "admin" if token == ADMIN_KEY else "non-admin"
    
    # Look for existing session with same token and IP
    for session_id, session in active_sessions.items():
        if session.get("ip_address") == ip_address and session.get("user_agent") == user_agent:
            # Update last activity
            session["last_activity"] = datetime.now().isoformat()
            save_sessions()
            return session_id
    
    # Create new session
    identifier = user_identifier or f"user_{len(active_sessions) + 1}"
    return create_session(identifier, ip_address, user_agent, token_type)


def track_request(
    session_id: str,
    method: str,
    path: str,
    query_params: Dict[str, Any],
    token: str,
    ip_address: str,
    user_agent: str,
    response_status: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    body_data: Optional[Dict[str, Any]] = None
):
    """
    Track an API request.
    
    Args:
        session_id: Session identifier
        method: HTTP method (GET, POST, etc.)
        path: Request path
        query_params: Query parameters
        token: API token used (will be masked for bearer tokens, shown as UUID for UUID auth)
        ip_address: Client IP address
        user_agent: User agent string
        response_status: HTTP response status code
        response_time_ms: Response time in milliseconds
        body_data: Request body data (for POST requests)
    """
    # Determine if this is an admin request
    from main import ADMIN_KEY
    is_admin = (token == ADMIN_KEY)
    
    # Only track non-admin requests (including UUID-based authentication)
    if is_admin:
        return
    
    # Update session request count
    if session_id in active_sessions:
        active_sessions[session_id]["request_count"] += 1
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        save_sessions()
    
    # Mask token appropriately and extract UUID if present
    uuid_value = None
    if token.startswith("uuid:"):
        # For UUID authentication, show the UUID
        token_display = token  # Show full "uuid:xxx"
        uuid_value = token[5:]  # Extract just the UUID part
    elif len(token) > 8:
        # For bearer tokens, mask the middle
        token_display = f"{token[:4]}...{token[-4:]}"
    else:
        token_display = "***"
    
    # Create request record
    request_record = {
        "request_id": str(uuid.uuid4()),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "path": path,
        "query_params": query_params,
        "body_data": body_data,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "token_masked": token_display,
        "uuid": uuid_value,  # UUID value (if UUID-based auth, otherwise null)
        "response_status": response_status,
        "response_time_ms": response_time_ms
    }
    
    # Append to requests file
    try:
        # Read existing requests
        with open(REQUESTS_FILE, 'r') as f:
            data = json.load(f)
        
        # Append new request
        data["requests"].append(request_record)
        data["last_updated"] = datetime.now().isoformat()
        data["total_requests"] = len(data["requests"])
        
        # Write back to file
        with open(REQUESTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
    except Exception as e:
        print(f"Error tracking request: {e}")


def get_request_logs(
    session_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    path_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve request logs with optional filtering.
    
    Args:
        session_id: Filter by session ID
        limit: Maximum number of records to return
        offset: Number of records to skip
        path_filter: Filter by request path (partial match)
    
    Returns:
        Dictionary with logs and metadata
    """
    try:
        with open(REQUESTS_FILE, 'r') as f:
            data = json.load(f)
        
        requests = data.get("requests", [])
        
        # Filter by session_id
        if session_id:
            requests = [r for r in requests if r.get("session_id") == session_id]
        
        # Filter by path
        if path_filter:
            requests = [r for r in requests if path_filter in r.get("path", "")]
        
        # Apply pagination
        total = len(requests)
        requests = requests[offset:offset + limit]
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(requests),
            "requests": requests
        }
    
    except Exception as e:
        print(f"Error retrieving request logs: {e}")
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "count": 0,
            "requests": [],
            "error": str(e)
        }


def get_session_summary() -> Dict[str, Any]:
    """
    Get summary of all active sessions.
    
    Returns:
        Dictionary with session statistics
    """
    total_sessions = len(active_sessions)
    admin_sessions = sum(1 for s in active_sessions.values() if s.get("token_type") == "admin")
    non_admin_sessions = total_sessions - admin_sessions
    
    # Get total request count
    try:
        with open(REQUESTS_FILE, 'r') as f:
            data = json.load(f)
            total_requests = len(data.get("requests", []))
    except:
        total_requests = 0
    
    return {
        "total_sessions": total_sessions,
        "admin_sessions": admin_sessions,
        "non_admin_sessions": non_admin_sessions,
        "total_tracked_requests": total_requests,
        "sessions": list(active_sessions.values())
    }


def get_session_details(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details for a specific session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session details or None if not found
    """
    session = active_sessions.get(session_id)
    if not session:
        return None
    
    # Get request count for this session
    logs = get_request_logs(session_id=session_id, limit=10000)
    
    return {
        "session": session,
        "request_count": logs["total"],
        "recent_requests": logs["requests"][:10]  # Last 10 requests
    }


def clear_old_sessions(days_old: int = 7):
    """
    Clear sessions older than specified days.
    
    Args:
        days_old: Number of days after which to clear sessions
    """
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    sessions_to_remove = []
    
    for session_id, session in active_sessions.items():
        last_activity = datetime.fromisoformat(session.get("last_activity", session.get("created_at")))
        if last_activity < cutoff_date:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del active_sessions[session_id]
    
    if sessions_to_remove:
        save_sessions()
        print(f"Cleared {len(sessions_to_remove)} old sessions")


# Initialize tracking on module import
init_tracking()
