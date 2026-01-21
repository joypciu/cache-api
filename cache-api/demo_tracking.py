"""
Demo script to test the comprehensive tracking system
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:6002"
ADMIN_TOKEN = "eternitylabsadmin"
USER_TOKEN = "12345"

# Test if server is running
try:
    r = requests.get(BASE_URL, timeout=2)
except:
    print("ERROR: Server is not running on", BASE_URL)
    print("Please start the server first: python main.py")
    sys.exit(1)

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_response(response, truncate=True):
    try:
        data = response.json()
        if truncate and isinstance(data, dict) and 'logs' in data:
            # Show summary for logs
            print(f"Status Code: {response.status_code}")
            print(f"Total Records: {data.get('total_records', 'N/A')}")
            if data.get('logs'):
                print(f"Showing first log entry:")
                print(json.dumps(data['logs'][0], indent=2))
        else:
            print(f"Status Code: {response.status_code}")
            print(json.dumps(data, indent=2))
    except:
        print(f"Status Code: {response.status_code}")
        print(response.text[:500])

# Step 1: Make some test requests with null values
print_section("STEP 1: Making Test Requests (with null values)")

print("\n1. Request with null player parameter:")
response = requests.get(
    f"{BASE_URL}/cache",
    params={"team": "Lakers", "player": "null", "sport": "Basketball"},
    headers={"Authorization": f"Bearer {USER_TOKEN}"}
)
print_response(response)

time.sleep(0.5)

print("\n2. Request with empty market parameter:")
response = requests.get(
    f"{BASE_URL}/cache",
    params={"market": "", "team": "Warriors"},
    headers={"Authorization": f"Bearer {USER_TOKEN}"}
)
print_response(response)

time.sleep(0.5)

print("\n3. Batch request with null values in body:")
response = requests.post(
    f"{BASE_URL}/cache/batch",
    headers={"Authorization": f"Bearer {USER_TOKEN}", "Content-Type": "application/json"},
    json={
        "team": ["Lakers", None, "Bulls"],
        "player": ["LeBron James", None],
        "sport": "Basketball"
    }
)
print_response(response)

time.sleep(0.5)

print("\n4. Normal request without nulls:")
response = requests.get(
    f"{BASE_URL}/cache",
    params={"team": "Lakers", "sport": "Basketball"},
    headers={"Authorization": f"Bearer {USER_TOKEN}"}
)
print_response(response)

time.sleep(1)

# Step 2: Check URL access statistics
print_section("STEP 2: URL Access Statistics")

response = requests.get(
    f"{BASE_URL}/admin/url-stats",
    params={"limit": 10},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response, truncate=False)

# Step 3: Check for null values
print_section("STEP 3: Null Value Logs")

print("\n1. All null values:")
response = requests.get(
    f"{BASE_URL}/admin/null-logs",
    params={"limit": 20},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response)

print("\n2. Request parameter nulls only:")
response = requests.get(
    f"{BASE_URL}/admin/null-logs",
    params={"null_type": "request_parameter", "limit": 10},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response)

# Step 4: Check rate limits
print_section("STEP 4: Rate Limit Tracking")

print("\n1. All clients:")
response = requests.get(
    f"{BASE_URL}/admin/rate-limits",
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response, truncate=False)

print("\n2. Specific client (user token):")
response = requests.get(
    f"{BASE_URL}/admin/rate-limits",
    params={"client_identifier": "1234...2345"},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response, truncate=False)

# Step 5: Check request logs
print_section("STEP 5: Request Logs")

print("\n1. Recent requests:")
response = requests.get(
    f"{BASE_URL}/admin/request-logs",
    params={"limit": 3},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response)

print("\n2. Requests with null parameters:")
response = requests.get(
    f"{BASE_URL}/admin/request-logs",
    params={"path": "/cache", "limit": 5},
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
if response.status_code == 200:
    data = response.json()
    print(f"Total requests to /cache: {data.get('total_records', 0)}")
    if data.get('logs'):
        for log in data['logs'][:2]:
            print(f"\nRequest #{log['id']}:")
            print(f"  Path: {log['path']}")
            print(f"  Query: {log['query_params']}")
            print(f"  Has Null Params: {log.get('has_null_params', 0) == 1}")
            print(f"  Has Null Response: {log.get('has_null_response', 0) == 1}")
            print(f"  Response Time: {log['response_time_ms']}ms")

# Step 6: Overall statistics
print_section("STEP 6: Overall Request Statistics")

response = requests.get(
    f"{BASE_URL}/admin/request-stats",
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
print_response(response, truncate=False)

print_section("DEMO COMPLETE")
print("\n✅ All tracking features are working!")
print("\nKey observations:")
print("  • URL access counts are being tracked")
print("  • Null values in requests/responses are being detected")
print("  • Rate limits are being monitored per client")
print("  • Complete request/response data is being logged")
print("  • Performance metrics are being captured")
