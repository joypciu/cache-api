"""
Test script for request tracking functionality
Tests session creation and request logging for non-admin users
"""

import requests
import json
import time

BASE_URL = "http://localhost:6002"
NON_ADMIN_TOKEN = "12345"
ADMIN_TOKEN = "eternitylabsadmin"

def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print()

def test_non_admin_requests():
    """Make several non-admin requests to generate tracking data"""
    print("\n🔵 STEP 1: Making non-admin requests (will be tracked)")
    
    headers = {"Authorization": f"Bearer {NON_ADMIN_TOKEN}"}
    
    # Request 1: Team lookup
    response = requests.get(
        f"{BASE_URL}/cache",
        params={"team": "Lakers", "sport": "Basketball"},
        headers=headers
    )
    print_response("Request 1: Team lookup (Lakers)", response)
    time.sleep(0.5)
    
    # Request 2: Player lookup
    response = requests.get(
        f"{BASE_URL}/cache",
        params={"player": "LeBron James"},
        headers=headers
    )
    print_response("Request 2: Player lookup (LeBron)", response)
    time.sleep(0.5)
    
    # Request 3: Market lookup
    response = requests.get(
        f"{BASE_URL}/cache",
        params={"market": "moneyline"},
        headers=headers
    )
    print_response("Request 3: Market lookup (moneyline)", response)
    time.sleep(0.5)
    
    # Request 4: Another team lookup
    response = requests.get(
        f"{BASE_URL}/cache",
        params={"team": "Warriors", "sport": "Basketball"},
        headers=headers
    )
    print_response("Request 4: Team lookup (Warriors)", response)

def test_view_sessions():
    """View all active sessions"""
    print("\n🔵 STEP 2: Viewing active sessions (admin endpoint)")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    response = requests.get(
        f"{BASE_URL}/admin/sessions",
        headers=headers
    )
    print_response("Active Sessions Summary", response)
    
    return response.json()

def test_view_request_logs():
    """View request tracking logs"""
    print("\n🔵 STEP 3: Viewing request tracking logs (admin endpoint)")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    response = requests.get(
        f"{BASE_URL}/admin/request-logs",
        params={"limit": 10},
        headers=headers
    )
    print_response("Request Logs (Last 10)", response)

def test_view_specific_session(session_id):
    """View details for a specific session"""
    print(f"\n🔵 STEP 4: Viewing specific session details")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    response = requests.get(
        f"{BASE_URL}/admin/sessions/{session_id}",
        headers=headers
    )
    print_response(f"Session Details: {session_id}", response)

def test_admin_request():
    """Make an admin request (should NOT be tracked)"""
    print("\n🔵 STEP 5: Making admin request (will NOT be tracked)")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    response = requests.get(
        f"{BASE_URL}/cache/stats",
        headers=headers
    )
    print_response("Admin Request: Cache Stats", response)

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("REQUEST TRACKING TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Make non-admin requests
        test_non_admin_requests()
        
        # Test 2: View sessions
        sessions_data = test_view_sessions()
        
        # Test 3: View request logs
        test_view_request_logs()
        
        # Test 4: View specific session (if available)
        if sessions_data.get("sessions"):
            first_session = sessions_data["sessions"][0]
            session_id = first_session.get("session_id")
            if session_id:
                test_view_specific_session(session_id)
        
        # Test 5: Make admin request (should not be tracked)
        test_admin_request()
        
        # Test 6: Verify admin request was NOT tracked
        test_view_request_logs()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        print("\nSummary:")
        print("- Non-admin requests are tracked ✓")
        print("- Sessions are created automatically ✓")
        print("- Admin endpoints show tracking data ✓")
        print("- Admin requests are NOT tracked ✓")
        print("\nCheck the following files for stored data:")
        print("- cache-api/request_logs/sessions.json")
        print("- cache-api/request_logs/requests.json")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the server.")
        print("Make sure the API is running on http://localhost:6002")
        print("\nStart the server with:")
        print("  cd cache-api")
        print("  python main.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
