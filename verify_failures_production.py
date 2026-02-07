import urllib.request
import urllib.error
import json
import time

# Configuration
BASE_URL = "https://cache-api.eternitylabs.co"
ENDPOINT = "/cache/batch"
TOKEN = "a8f5f167-0e5a-4f3c-9d2e-8b7a3c4e5f6d"

# Payloads provided by the user
payloads = [
    {
        "team": [],
        "player": ["Drake Thomas", "Jarran Reed", "Dareke Young", "Khyiris Tonga", "Jack Westover", "Christian Barmore", "Eric Saubert", "Brady Russell", "Nick Emmanwori", "Ernest Jones"],
        "market": ["1St Reception (Yards)", "Rush + Rec Yards", "Fg Made", "Completion Percentage", "Fantasy Points", "Missed Fg", "1St Drive Pass Yards", "Team 1St Td Scorer", "25+ Rush Yards In Each Half", "Solo Tackles"]
    },
    {
        "team": [],
        "player": ["Milton Williams", "Christian Elliss", "Robbie Ouzts", "Hunter Henry", "DeMario Douglas", "DeMarcus Lawrence", "Tyrice Knight", "Drake Maye", "TreVeyon Henderson", "Jaxon Smith-Njigba"],
        "market": ["1H Targets", "100+ Pass Yards In Each Half", "Defensive Ints", "25+ Pass Yards In Each Quarter", "1St Attempt Completions", "1Q Pass Tds", "Game Longest Punt Return", "50+ Rush Yards In Each Half", "Game High Rec Yards", "1St Pass Td (Yards)"]
    },
    {
        "team": [],
        "player": ["Harold Landry III", "Marcus Jones", "Josh Jobe"],
        "market": ["50+ Pass Yards In Each Quarter", "1St To 20+ Rush Yards", "Receiving Tds", "Kicking Points", "1St 10+ Yard Rush Of Game", "Pass Yards", "1Q Most Rec Yards", "Game Longest Rush", "Completions", "1St Sack Taken"]
    },
    {
        "team": [],
        "player": ["AJ Barner", "Sam Darnold", "Leonard Williams", "Coby Bryant", "Boye Mafe", "Craig Woodson", "Andy Borregales", "Carlton Davis", "Uchenna Nwosu", "Elijah Arroyo"],
        "market": ["Targets", "Rush Attempt Or Target Each Drive 1H", "Pass Tds", "1H Pass Tds", "1Q Pass Yards", "Completions In 1St 5 Attempts", "Rush Yards", "1H Rec Yards", "50+ Rec Yards In Each Half", "Rush Attempts"]
    }
]

def run_test():
    url = f"{BASE_URL}{ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "VerificationScript/1.0"
    }

    print(f"Testing URL: {url}")
    print(f"Using Token: {TOKEN[:5]}...{TOKEN[-5:]}")
    print("-" * 60)

    success_count = 0
    
    for i, payload in enumerate(payloads, 1):
        print(f"\nTest #{i}")
        # Add default sport if needed, but user provided payloads without it. 
        # We will try sending exactly as provided.
        # If the API requires 'sport', we might need to add it, but let's test the failure case first.
        # Given the previous 504s, it's likely searching a massive DB without a sport filter or similar.
        
        # Injecting 'American Football' as a guess if these are NFL players (e.g. Sam Darnold, Drake Maye)
        # However, the prompt says "check all of the data... Mapping Failed". I'll stick to precise payload first.
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                duration = time.time() - start_time
                status = response.getcode()
                response_body = response.read().decode('utf-8')
                
                print(f"Status: {status} (Time: {duration:.2f}s)")
                try:
                    json_resp = json.loads(response_body)
                    # Summary of response
                    keys = list(json_resp.keys()) if isinstance(json_resp, dict) else "List"
                    data_len = len(json_resp.get('data', [])) if isinstance(json_resp, dict) and 'data' in json_resp else 'N/A'
                    print(f"Response: Valid JSON with {data_len} data items.")
                    success_count += 1
                except:
                    print(f"Response Body: {response_body[:200]}...")

        except urllib.error.HTTPError as e:
            duration = time.time() - start_time
            print(f"FAILED: HTTP {e.code} (Time: {duration:.2f}s)")
            print(f"Reason: {e.reason}")
            try:
                err_body = e.read().decode('utf-8')
                print(f"Error Body: {err_body}")
            except:
                pass
        except urllib.error.URLError as e:
            duration = time.time() - start_time
            print(f"FAILED: Connection Error (Time: {duration:.2f}s)")
            print(f"Reason: {e.reason}")
        except Exception as e:
            print(f"FAILED: Unexpected Error: {e}")

    print("-" * 60)
    print(f"Summary: {success_count}/{len(payloads)} passed.")

if __name__ == "__main__":
    run_test()
