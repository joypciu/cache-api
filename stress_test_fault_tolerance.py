
import os
import time
import concurrent.futures
import random
import string
from fastapi.testclient import TestClient

# Mock Env Vars
os.environ["ADMIN_API_TOKEN"] = "eternitylabsadmin"
os.environ["API_TOKEN"] = "a8f5f167-0e5a-4f3c-9d2e-8b7a3c4e5f6d"

from main import app

# Initialize Client
client = TestClient(app)

ADMIN_KEY = "eternitylabsadmin"
USER_KEY = "a8f5f167-0e5a-4f3c-9d2e-8b7a3c4e5f6d"

# Configuration
TOTAL_REQUESTS = 300  # Number of requests per test
CONCURRENT_WORKERS = 20 # Number of simulateous users

def run_stress_test(endpoint, headers, payload=None, method="GET"):
    """Runs a stress test against a single endpoint"""
    print(f"\n🚀 Starting Stress Test: {endpoint} [{method}]")
    print(f"   Workers: {CONCURRENT_WORKERS}, Total Requests: {TOTAL_REQUESTS}")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    errors = []

    def make_request():
        try:
            if method == "GET":
                resp = client.get(endpoint, headers=headers)
            else:
                resp = client.post(endpoint, json=payload, headers=headers)
            
            # We treat 200, 404 (Not Found) as "Success" in terms of server stability
            # 500 is a crash/failure
            if resp.status_code in [200, 404]:
                return True, resp.status_code
            else:
                return False, resp.status_code
        except Exception as e:
            return False, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(make_request) for _ in range(TOTAL_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            is_success, status = future.result()
            if is_success:
                success_count += 1
            else:
                fail_count += 1
                errors.append(status)

    duration = time.time() - start_time
    rps = TOTAL_REQUESTS / duration
    
    print(f"🏁 Finished in {duration:.2f}s ({rps:.2f} req/s)")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")
    
    if fail_count > 0:
        print(f"   ⚠️ Error Codes: {list(set(errors))[:5]}")
    
    return fail_count == 0

def stress_test_suite():
    print("=== 🔥 API STRESS & FAULT TOLERANCE TEST 🔥 ===")
    
    # 1. Simple Cache Lookup (High Volume)
    # Testing DB connection limits and tracking overhead
    run_stress_test(
        "/cache?team=Lakers&sport=Basketball", 
        {"Authorization": f"Bearer {USER_KEY}"}
    )

    # 2. Batch Query (Heavy Computation)
    # Testing thread pool limits in cache_db.py
    batch_payload = {
        "team": ["Lakers", "Warriors", "Bulls", "Heat", "Knicks"],
        "player": ["LeBron James", "Stephen Curry"],
        "market": ["moneyline", "spread"]
    }
    run_stress_test(
        "/cache/batch", 
        {"Authorization": f"Bearer {USER_KEY}"},
        payload=batch_payload,
        method="POST"
    )

    # 3. Precision Batch (Complex Logic)
    precision_payload = {
        "queries": [
            {"team": "Lakers", "player": "LeBron James", "sport": "Basketball"},
            {"team": "Warriors", "sport": "Basketball"}
        ] * 5 # Inflate the size
    }
    run_stress_test(
        "/cache/batch/precision", 
        {"Authorization": f"Bearer {USER_KEY}"},
        payload=precision_payload,
        method="POST"
    )

    # 4. Invalid/Random Input (Fuzzing)
    # Testing if server crashes on bad input
    random_str = ''.join(random.choices(string.ascii_letters, k=50))
    run_stress_test(
        f"/cache?team={random_str}&sport=Basketball", 
        {"Authorization": f"Bearer {USER_KEY}"}
    )

    # 5. Admin Stats (Concurrent Admin Access)
    # Testing if tracking logic breaks when admin is mixed in
    run_stress_test(
        "/cache/stats", 
        {"Authorization": f"Bearer {ADMIN_KEY}"}
    )

if __name__ == "__main__":
    stress_test_suite()
