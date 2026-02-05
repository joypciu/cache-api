
import requests
import time
import json
import uuid

# Configuration
VPS_URL = "https://cache-api.eternitylabs.co"
USER_TOKEN = "a8f5f167-0e5a-4f3c-9d2e-8b7a3c4e5f6d"
ADMIN_TOKEN = "eternitylabsadmin" 

# Payload 1 (Provided by user)
PAYLOAD_1 = {
  "team": [
    "sea",
    "ne"
  ],
  "player": [
    "Cooper Kupp",
    "Kyle Williams",
    "Nick Emmanwori",
    "Harold Landry III",
    "George Holani",
    "Cory Durden",
    "Khyiris Tonga",
    "Andy Borregales",
    "Robert Spillane",
    "Sam Darnold"
  ],
  "market": [
    "Completion Percentage",
    "Game Longest Punt Return",
    "1H Targets",
    "1St To 20+ Rush Yards",
    "1+ Fg Or Xp Made In Each Quarter",
    "Rush + Rec Yards",
    "1St 20+ Yard Reception Of Game",
    "10+ Rush Yards In Each Quarter",
    "Sacks Taken",
    "1St Sack Taken"
  ]
}

# Payload 2 (Provided by user)
PAYLOAD_2 = {
  "market": [
    "1St Drive Receptions",
    "1St Drive Rush Yards",
    "Rush Yards",
    "Missed Fg",
    "Ints Thrown",
    "50+ Pass Yards In Each Quarter",
    "Receiving Tds",
    "1+ Reception In Each Quarter",
    "First Td Scorer",
    "1St To 20+ Rec Yards"
  ]
}

# Payload 3 (User provided)
PAYLOAD_3 = {
  "player": [
    "Drake Thomas",
    "Jaxon Smith-Njigba",
    "Stefon Diggs",
    "Jake Bobo",
    "Rhamondre Stevenson",
    "Christian Gonzalez",
    "Eric Saubert",
    "Mack Hollins",
    "Leonard Taylor",
    "Craig Woodson"
  ],
  "market": [
    "Game High Rush Yards",
    "1H Pass Tds",
    "Tackles + Assists",
    "Completions",
    "Doinks",
    "1St Team Reception",
    "Fumbles Lost",
    "Longest Reception",
    "1St Drive Fg Or Xp Made",
    "1St Reception (Yards)"
  ]
}

# Payload 4 (2nd test provided by user)
PAYLOAD_4 = {
  "team": [
    "hanwha life challengers",
    "shifters",
    "Joint",
    "mythic",
    "Bronzet",
    "Fossa",
    "Navarrette",
    "ksu",
    "faze clan",
    "alt f4",
    "Kudermet",
    "Basilashvi",
    "Pagani",
    "Grabher",
    "Humbert"
  ],
  "player": [
    "Riccardo Orsolini",
    "Tiffany Hayes",
    "Yanni Gourde",
    "Cassandre Prosper",
    "Sonic",
    "Nicolas Bruna",
    "Maynter",
    "Jake Guentzel",
    "Erik Cernak",
    "Vaishnavi Adkar",
    "Adrien Rabiot",
    "Axel Tuanzebe",
    "Matt Scharff",
    "Darja Semenistaja",
    "Stephon Castle"
  ],
  "market": [
    "Avg Yards Per Punt",
    "50+ Rush Yards In Each Half",
    "1H Pass Tds",
    "Game High Rec Yards",
    "Rush + Rec Yards",
    "Double-Doubles",
    "Highest Checkout",
    "10+ Rush Yards In Each Quarter",
    "Rush + Rec Tds",
    "Holes 6-10 Strokes",
    "Points In First 5 Min.",
    "1St Sack Taken",
    "Receiving Tds",
    "Sacks Taken",
    "1Q Pts + Rebs + Asts"
  ]
}

def print_section(title):
    print(f"\n{'='*60}")
    print(f"TEST: {title}")
    print(f"{'='*60}")

def run_batch_test(name, payload):
    print_section(f"Batch Request: {name}")
    headers = {
        "Authorization": f"Bearer {USER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    start = time.time()
    try:
        resp = requests.post(f"{VPS_URL}/cache/batch", json=payload, headers=headers)
        dur = (time.time() - start) * 1000
        
        print(f"Status: {resp.status_code}")
        print(f"Time: {dur:.2f}ms")
        
        if resp.status_code == 200:
            data = resp.json()
            # Summarize results
            for category, items in data.items():
                if isinstance(items, dict):
                    found = sum(1 for v in items.values() if v)
                    total = len(items)
                    print(f"  - {category.upper()}: {found}/{total} found")
                    
                    # Print found markets for verification
                    if category == "market":
                        print("    Matches:")
                        for k, v in items.items():
                            if v:
                                normalized = v.get('normalized_name', 'Unknown')
                                print(f"      '{k}' -> '{normalized}'")
                            else:
                                pass # print(f"      '{k}' -> NULL")
        else:
            print(f"Error: {resp.text}")
            
    except Exception as e:
        print(f"Request Exception: {e}")

def verify_logging():
    print_section("Verifying server-side logging")
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    try:
        # Get recent logs
        resp = requests.get(f"{VPS_URL}/admin/logs?limit=5", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            total_logs = data.get('total', 0)
            print(f"Total Logs in DB: {total_logs}")
            
            recent = data.get('requests', [])
            if recent:
                print("Most recent log entry:")
                log = recent[0]
                print(f"  Method: {log.get('method')}")
                print(f"  Path: {log.get('path')}")
                print(f"  Status: {log.get('response_status')}")
                print(f"  User Agent: {log.get('user_agent')}")
                print(f"  UUID: {log.get('uuid')}")
                print("✅ LOGGING CONFIRMED ACTIVE")
            else:
                print("⚠️ No logs returned (Limit might be 0?)")
        else:
            print(f"Failed to fetch logs: {resp.status_code}")
            
    except Exception as e:
        print(f"Log verification failed: {e}")

if __name__ == "__main__":
    print(f"Testing VPS: {VPS_URL}")
    
    # 1. Run Functional Tests
    run_batch_test("Payload 1 (Original Failing)", PAYLOAD_1)
    run_batch_test("Payload 2 (Markets Only)", PAYLOAD_2)
    run_batch_test("Payload 3 (Mixed)", PAYLOAD_3)
    run_batch_test("Payload 4 (2nd Test - Large)", PAYLOAD_4)
    
    # 2. Check Logs (Proof of Lutfur's integration working)
    verify_logging()
    
    print("\n✅ Verification Suite Complete.")
