import json
import time
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:5000"
TOKEN = "eternitylabsadmin"

payloads = [
    {"team": [], "player": ["Drake Thomas", "Jarran Reed", "Dareke Young", "Khyiris Tonga", "Jack Westover", "Christian Barmore", "Eric Saubert", "Brady Russell", "Nick Emmanwori", "Ernest Jones"], "market": ["1St Reception (Yards)", "Rush + Rec Yards", "Fg Made", "Completion Percentage", "Fantasy Points", "Missed Fg", "1St Drive Pass Yards", "Team 1St Td Scorer", "25+ Rush Yards In Each Half", "Solo Tackles"]},
    {"team": [], "player": ["Milton Williams", "Christian Elliss", "Robbie Ouzts", "Hunter Henry", "DeMario Douglas", "DeMarcus Lawrence", "Tyrice Knight", "Drake Maye", "TreVeyon Henderson", "Jaxon Smith-Njigba"], "market": ["1H Targets", "100+ Pass Yards In Each Half", "Defensive Ints", "25+ Pass Yards In Each Quarter", "1St Attempt Completions", "1Q Pass Tds", "Game Longest Punt Return", "50+ Rush Yards In Each Half", "Game High Rec Yards", "1St Pass Td (Yards)"]},
    {"team": [], "player": ["Harold Landry III", "Marcus Jones", "Josh Jobe"], "market": ["50+ Pass Yards In Each Quarter", "1St To 20+ Rush Yards", "Receiving Tds", "Kicking Points", "1St 10+ Yard Rush Of Game", "Pass Yards", "1Q Most Rec Yards", "Game Longest Rush", "Completions", "1St Sack Taken"]},
    {"team": [], "player": ["AJ Barner", "Sam Darnold", "Leonard Williams", "Coby Bryant", "Boye Mafe", "Craig Woodson", "Andy Borregales", "Carlton Davis", "Uchenna Nwosu", "Elijah Arroyo"], "market": ["Targets", "Rush Attempt Or Target Each Drive 1H", "Pass Tds", "1H Pass Tds", "1Q Pass Yards", "Completions In 1St 5 Attempts", "Rush Yards", "1H Rec Yards", "50+ Rec Yards In Each Half", "Rush Attempts"]}
]

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    
    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e)

print("Running validation tests...")

# Clear Cache
print("Clearing cache...")
status, _ = make_request("DELETE", "/cache/clear")
print(f"Cache Clear Status: {status}")

for i, p in enumerate(payloads):
    start = time.time()
    status, content = make_request("POST", "/cache/batch", p)
    duration = time.time() - start
    print(f"Payload {i+1}: Status {status}, Time: {duration:.4f}s")
    if status != 200:
        print(f"Response: {content}")
