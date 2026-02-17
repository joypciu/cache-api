import sqlite3
import time

def analyze_payload():
    payload = {
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
    
    conn = sqlite3.connect('sports_data.db')
    cursor = conn.cursor()
    
    print("=== Analyzing Teams (NEW LOGIC) ===")
    start_time = time.time()
    for team in payload["team"]:
        # Check exact match first (Fast)
        cursor.execute("SELECT id FROM teams WHERE name = ? COLLATE NOCASE OR abbreviation = ? COLLATE NOCASE", (team, team))
        if cursor.fetchone():
            print(f"[FOUND-EXACT] '{team}'")
            continue
            
        # Check PREFIX match (Simulating the fix)
        # Note: Using % at end only
        cursor.execute("SELECT id FROM teams WHERE name LIKE ?", (f"{team}%",))
        if cursor.fetchone():
            print(f"[FOUND-PREFIX] '{team}'")
            continue
            
        print(f"[MISSING] '{team}' -> Fast fail (No wildcard scan)")
        
    print(f"\nTeam Check Time: {time.time() - start_time:.4f}s")
    
    print("\n=== Analyzing Players (NEW LOGIC) ===")
    start_time = time.time()
    for player in payload["player"]:
        cursor.execute("SELECT id FROM players WHERE name = ? COLLATE NOCASE", (player,))
        if cursor.fetchone():
            print(f"[FOUND-EXACT] '{player}'")
            continue
            
        cursor.execute("SELECT id FROM players WHERE name LIKE ?", (f"{player}%",))
        if cursor.fetchone():
             print(f"[FOUND-PREFIX] '{player}'")
             continue
            
        print(f"[MISSING] '{player}' -> Fast fail (No wildcard scan)")

    print(f"\nPlayer Check Time: {time.time() - start_time:.4f}s")

    print("\n=== Analyzing Markets (NEW LOGIC) ===")
    start_time = time.time()
    for market in payload["market"]:
        market_search_term = market.lower().replace(" ", "").replace("_", "")
        cursor.execute("SELECT id FROM markets WHERE LOWER(REPLACE(REPLACE(name, ' ', ''), '_', '')) = ?", (market_search_term,))
        if cursor.fetchone():
             print(f"[FOUND-STRIPPED] '{market}'")
             continue
        
        # Prefix only
        cursor.execute("SELECT id FROM markets WHERE name LIKE ?", (f"{market}%",))
        if cursor.fetchone():
             print(f"[FOUND-PREFIX] '{market}'")
             continue
             
        print(f"[MISSING] '{market}' -> Fast fail")

    print(f"\nMarket Check Time: {time.time() - start_time:.4f}s")
    conn.close()

if __name__ == "__main__":
    analyze_payload()
