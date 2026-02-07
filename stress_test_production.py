import json
import time
import urllib.request
import urllib.error
import random
import concurrent.futures
import string

BASE_URL = "http://localhost:5000"
TOKEN = "eternitylabsadmin"

# Test Data Pools
TEAMS = ["Lakers", "Warriors", "Yankees", "Cowboys", "Real Madrid", "Man City", "Chiefs", "Celtics", "Dodgers", "Eagles", "Liverpool", "Arsenal", "Barcelona", "PSG", "Bayern Munich", "Bulls", "Heat", "Nuggets", "Suns", "Bucks"]
PLAYERS = ["LeBron James", "Stephen Curry", "Patrick Mahomes", "Lionel Messi", "Cristiano Ronaldo", "Shohei Ohtani", "Aaron Judge", "Luka Doncic", "Giannis Antetokounmpo", "Kevin Durant", "Nikola Jokic", "Jayson Tatum", "Harry Kane", "Kylian Mbappe", "Erling Haaland"]
MARKETS = ["Moneyline", "Spread", "Total", "Anytime Touchdown", "Player Points", "Player Assists", "Player Rebounds", "First Goalscorer", "Correct Score", "Both Teams to Score", "Over/Under 2.5 Goals"]

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))

def generate_batch_payload(miss_ratio=0.5):
    """Generate a payload with a mix of hits and misses"""
    payload = {
        "team": [],
        "player": [],
        "market": []
    }
    
    # Add Teams
    for _ in range(random.randint(5, 15)):
        if random.random() > miss_ratio:
            payload["team"].append(random.choice(TEAMS))
        else:
            payload["team"].append(generate_random_string(10))
            
    # Add Players
    for _ in range(random.randint(5, 15)):
        if random.random() > miss_ratio:
            payload["player"].append(random.choice(PLAYERS))
        else:
            payload["player"].append(generate_random_string(12))
            
    # Add Markets
    for _ in range(random.randint(3, 8)):
        if random.random() > miss_ratio:
            payload["market"].append(random.choice(MARKETS))
        else:
            payload["market"].append(generate_random_string(15))
            
    return payload

def generate_precision_payload(count=10):
    queries = []
    for _ in range(count):
        q = {}
        if random.random() > 0.5:
            q["team"] = random.choice(TEAMS) if random.random() > 0.3 else generate_random_string()
        if random.random() > 0.5:
            q["player"] = random.choice(PLAYERS) if random.random() > 0.3 else generate_random_string()
        if random.random() > 0.7:
            q["market"] = random.choice(MARKETS)
        queries.append(q)
    return {"queries": queries}

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    
    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.data = json_data
        
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=30) as response:
            duration = time.time() - start
            return response.status, duration, len(response.read())
    except urllib.error.HTTPError as e:
        return e.code, 0, 0
    except Exception as e:
        print(f"Request Error: {e}")
        return 0, 0, 0

def run_stress_test(num_requests=100, concurrency=10, test_type="batch"):
    print(f"\n--- Starting {test_type.upper()} Stress Test ---")
    print(f"Requests: {num_requests}, Concurrency: {concurrency}")
    
    times = []
    statuses = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for _ in range(num_requests):
            if test_type == "batch":
                payload = generate_batch_payload()
                endpoint = "/cache/batch"
            else:
                payload = generate_precision_payload()
                endpoint = "/cache/batch/precision"
                
            futures.append(executor.submit(make_request, "POST", endpoint, payload))
            
        for future in concurrent.futures.as_completed(futures):
            status, duration, size = future.result()
            if status not in statuses:
                statuses[status] = 0
            statuses[status] += 1
            if status == 200:
                times.append(duration)
                
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        p95 = sorted(times)[int(len(times) * 0.95)]
        
        print(f"Results:")
        print(f"  Total Successful: {len(times)}/{num_requests}")
        print(f"  Avg Time: {avg_time:.4f}s")
        print(f"  Min Time: {min_time:.4f}s")
        print(f"  Max Time: {max_time:.4f}s")
        print(f"  95th %%ile: {p95:.4f}s")
        print(f"  Requests/Sec: {len(times) / sum(times) * concurrency:.2f}")
    else:
        print("No successful requests.")
        
    print(f"Status Codes: {statuses}")

if __name__ == "__main__":
    # 1. Clear Cache
    print("Clearing cache to force DB hits...")
    make_request("DELETE", "/cache/clear")
    
    # 2. Batch Stress Test (High Miss Rate)
    run_stress_test(num_requests=200, concurrency=20, test_type="batch")
    
    # 3. Precision Stress Test
    run_stress_test(num_requests=200, concurrency=20, test_type="precision")
    
    # 4. Extreme Spike
    print("\n--- EXTREME SPIKE (50 Concurrent) ---")
    run_stress_test(num_requests=500, concurrency=50, test_type="batch")
