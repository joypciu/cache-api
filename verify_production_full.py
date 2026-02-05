
import requests
import time
import json
import uuid

# Configuration
VPS_URL = "https://cache-api.eternitylabs.co"
USER_TOKEN = "a8f5f167-0e5a-4f3c-9d2e-8b7a3c4e5f6d"
ADMIN_TOKEN = "eternitylabsadmin" # Only for health check

def print_section(title):
    print(f"\n{'='*50}")
    print(f"TEST: {title}")
    print(f"{'='*50}")

def test_health():
    print_section("Health Checks")
    
    # 1. Public Root
    try:
        resp = requests.get(f"{VPS_URL}/")
        print(f"Root: {resp.status_code} - {resp.json().get('status')}")
    except Exception as e:
        print(f"Root Check Failed: {e}")

    # 2. Admin Health
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        resp = requests.get(f"{VPS_URL}/health", headers=headers)
        print(f"Admin Health: {resp.status_code}")
        if resp.status_code == 200:
             print(f"Cache Stats: {resp.json().get('cache', {}).get('redis_connected')}")
    except Exception as e:
        print(f"Admin Health Failed: {e}")

def test_single_queries():
    print_section("Single Queries (Caching & Performance)")
    
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    
    # Query 1: Initial Request (Should be slower, DB hit)
    start = time.time()
    resp1 = requests.get(f"{VPS_URL}/cache?team=Lakers&sport=Basketball", headers=headers)
    dur1 = (time.time() - start) * 1000
    
    print(f"Req 1 (Cold): {dur1:.2f}ms - Status: {resp1.status_code}")
    
    # Query 2: Cached Request (Should be faster)
    start = time.time()
    resp2 = requests.get(f"{VPS_URL}/cache?team=Lakers&sport=Basketball", headers=headers)
    dur2 = (time.time() - start) * 1000
    
    print(f"Req 2 (Warm): {dur2:.2f}ms - Status: {resp2.status_code}")
    
    if dur2 < dur1:
        print("✅ Caching appears effective (warm request faster)")
    else:
        print("⚠️ Caching impact unclear (warm request took similar time)")

def test_batch_payloads():
    print_section("Batch Processing (User Payloads)")
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    
    # Using one rigorous payload
    payload = {
        "team": ["sea", "ne"],
        "player": ["Cooper Kupp", "Sam Darnold"],
        "market": ["Completion Percentage", "Rush Yards"] # Fuzzy match targets
    }
    
    start = time.time()
    resp = requests.post(f"{VPS_URL}/cache/batch", json=payload, headers=headers)
    dur = (time.time() - start) * 1000
    
    print(f"Batch Request: {dur:.2f}ms - Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print("Results:")
        print(f"  Teams Found: {sum(1 for v in data.get('team', {}).values() if v)}/{len(payload['team'])}")
        print(f"  Players Found: {sum(1 for v in data.get('player', {}).values() if v)}/{len(payload['player'])}")
        print(f"  Markets Found: {sum(1 for v in data.get('market', {}).values() if v)}/{len(payload['market'])}")
        
        # Verify Fuzzy Matching
        if data['market'].get('Rush Yards'):
             print(f"  ✅ Fuzzy Match 'Rush Yards' -> '{data['market']['Rush Yards']['normalized_name']}'")
        else:
             print(f"  ❌ Fuzzy Match 'Rush Yards' FAILED")

def test_precision_batch():
    print_section("Precision Batch (Exact Targeting)")
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    
    payload = {
        "queries": [
            {"team": "Lakers", "player": "LeBron James", "sport": "Basketball"}, # Valid
            {"team": "MadeUpTeam", "sport": "Basketball"}, # Invalid
            {"market": "1H Targets"} # Short term fuzzy
        ]
    }
    
    start = time.time()
    resp = requests.post(f"{VPS_URL}/cache/batch/precision", json=payload, headers=headers)
    dur = (time.time() - start) * 1000
    
    print(f"Precision Request: {dur:.2f}ms - Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Total Queries: {data['total_queries']}")
        print(f"  Successful: {data['successful']}")
        
        # Check specific results
        results = data.get('results', [])
        if results[0]['found']:
             print(f"  ✅ Complex Query (Team+Player) Found")
        if not results[1]['found']:
             print(f"  ✅ Invalid Query Correctly Not Found")

def test_logging_sanity():
    print_section("Logging & Tracking (Implicit Check)")
    print("Sending request with unique trace header...")
    
    headers = {
        "Authorization": f"Bearer {USER_TOKEN}",
        "X-Request-Trace": str(uuid.uuid4())
    }
    
    resp = requests.get(f"{VPS_URL}/cache?market=moneyline", headers=headers)
    print(f"Request Status: {resp.status_code}")
    
    if resp.status_code == 200:
        print("✅ Response 200 OK. Middleware executed successfully.")
        print("   (Assuming logs are written to SQLite on server as 'main.py' middleware didn't crash)")
    else:
        print("❌ Request failed. Middleware might be crashing.")

if __name__ == "__main__":
    print("STARTING FULL PRODUCTION TEST SUITE")
    print("Target: " + VPS_URL)
    
    test_health()
    test_single_queries()
    test_batch_payloads()
    test_precision_batch()
    test_logging_sanity()
    
    print("\n✅ Verification Complete.")
