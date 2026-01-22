"""
Simple viewer for request tracking JSON files
Provides a formatted view of sessions and requests
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

# Paths to tracking files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_DIR = os.path.join(SCRIPT_DIR, "cache-api", "request_logs")
SESSIONS_FILE = os.path.join(TRACKING_DIR, "sessions.json")
REQUESTS_FILE = os.path.join(TRACKING_DIR, "requests.json")

def load_json_file(filepath):
    """Load and parse JSON file"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def format_timestamp(iso_timestamp):
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_timestamp

def view_sessions():
    """Display all active sessions"""
    print("\n" + "="*80)
    print("ACTIVE SESSIONS")
    print("="*80)
    
    data = load_json_file(SESSIONS_FILE)
    if not data:
        print("❌ No sessions file found or empty")
        return
    
    sessions = data.get("sessions", {})
    
    if not sessions:
        print("No active sessions")
        return
    
    print(f"\nTotal Sessions: {len(sessions)}")
    print(f"Last Updated: {data.get('last_updated', 'Unknown')}\n")
    
    for session_id, session in sessions.items():
        print("-" * 80)
        print(f"Session ID:      {session.get('session_id', 'N/A')}")
        print(f"User:            {session.get('user_identifier', 'N/A')}")
        print(f"IP Address:      {session.get('ip_address', 'N/A')}")
        print(f"Token Type:      {session.get('token_type', 'N/A')}")
        print(f"Created:         {format_timestamp(session.get('created_at', 'N/A'))}")
        print(f"Last Activity:   {format_timestamp(session.get('last_activity', 'N/A'))}")
        print(f"Request Count:   {session.get('request_count', 0)}")
        print(f"User Agent:      {session.get('user_agent', 'N/A')[:60]}...")

def view_requests(limit=20):
    """Display recent requests"""
    print("\n" + "="*80)
    print(f"REQUEST LOGS (Last {limit})")
    print("="*80)
    
    data = load_json_file(REQUESTS_FILE)
    if not data:
        print("❌ No requests file found or empty")
        return
    
    requests = data.get("requests", [])
    
    if not requests:
        print("No requests logged")
        return
    
    print(f"\nTotal Requests: {len(requests)}")
    print(f"Last Updated: {data.get('last_updated', 'Unknown')}\n")
    
    # Show most recent requests
    recent_requests = requests[-limit:] if len(requests) > limit else requests
    recent_requests.reverse()  # Show newest first
    
    for i, req in enumerate(recent_requests, 1):
        print("-" * 80)
        print(f"#{i} Request ID:     {req.get('request_id', 'N/A')}")
        print(f"   Timestamp:      {format_timestamp(req.get('timestamp', 'N/A'))}")
        print(f"   Method:         {req.get('method', 'N/A')} {req.get('path', 'N/A')}")
        
        # Query params
        query_params = req.get('query_params', {})
        if query_params:
            params_str = ", ".join([f"{k}={v}" for k, v in query_params.items()])
            print(f"   Params:         {params_str}")
        
        # Body data
        body_data = req.get('body_data')
        if body_data:
            print(f"   Body:           {json.dumps(body_data)[:60]}...")
        
        print(f"   IP Address:     {req.get('ip_address', 'N/A')}")
        print(f"   Session ID:     {req.get('session_id', 'N/A')}")
        print(f"   Response:       Status {req.get('response_status', 'N/A')} ({req.get('response_time_ms', 'N/A'):.2f}ms)")
        print(f"   Token:          {req.get('token_masked', 'N/A')}")

def view_statistics():
    """Display tracking statistics"""
    print("\n" + "="*80)
    print("TRACKING STATISTICS")
    print("="*80)
    
    sessions_data = load_json_file(SESSIONS_FILE)
    requests_data = load_json_file(REQUESTS_FILE)
    
    if not sessions_data or not requests_data:
        print("❌ Missing tracking files")
        return
    
    sessions = sessions_data.get("sessions", {})
    requests = requests_data.get("requests", [])
    
    # Count by token type
    admin_sessions = sum(1 for s in sessions.values() if s.get("token_type") == "admin")
    non_admin_sessions = len(sessions) - admin_sessions
    
    # Count requests by path
    path_counts = {}
    for req in requests:
        path = req.get("path", "unknown")
        path_counts[path] = path_counts.get(path, 0) + 1
    
    # Count requests by method
    method_counts = {}
    for req in requests:
        method = req.get("method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1
    
    print(f"\nTotal Active Sessions:     {len(sessions)}")
    print(f"  - Admin Sessions:        {admin_sessions}")
    print(f"  - Non-Admin Sessions:    {non_admin_sessions}")
    print(f"\nTotal Tracked Requests:    {len(requests)}")
    
    print(f"\nRequests by Method:")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"  {method:8s}: {count:4d}")
    
    print(f"\nTop Requested Paths:")
    for path, count in sorted(path_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {path:40s}: {count:4d}")
    
    # Average response time
    response_times = [r.get('response_time_ms', 0) for r in requests if r.get('response_time_ms')]
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        print(f"\nAverage Response Time:     {avg_response:.2f}ms")
        print(f"Min Response Time:         {min(response_times):.2f}ms")
        print(f"Max Response Time:         {max(response_times):.2f}ms")

def main():
    """Main viewer menu"""
    while True:
        print("\n" + "="*80)
        print("REQUEST TRACKING DATA VIEWER")
        print("="*80)
        print("\nOptions:")
        print("  1. View Active Sessions")
        print("  2. View Request Logs")
        print("  3. View Statistics")
        print("  4. View All")
        print("  0. Exit")
        
        choice = input("\nEnter your choice (0-4): ").strip()
        
        if choice == "1":
            view_sessions()
        elif choice == "2":
            limit_input = input("How many requests to show? (default 20): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 20
            view_requests(limit)
        elif choice == "3":
            view_statistics()
        elif choice == "4":
            view_statistics()
            view_sessions()
            view_requests()
        elif choice == "0":
            print("\nGoodbye!")
            break
        else:
            print("\n❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    # Check if tracking directory exists
    if not os.path.exists(TRACKING_DIR):
        print(f"\n❌ Tracking directory not found: {TRACKING_DIR}")
        print("\nThe tracking system hasn't created any data yet.")
        print("Start the API server and make some requests first.")
        exit(1)
    
    main()
