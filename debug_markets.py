
import sqlite3

def check_markets():
    conn = sqlite3.connect('sports_data.db')
    cursor = conn.cursor()
    
    keywords = ["Completion", "Return", "Targets", "Rush", "Quarter", "Sack"]
    
    print("--- Searching for Keywords ---")
    for kw in keywords:
        cursor.execute(f"SELECT name FROM markets WHERE name LIKE ?", (f"%{kw}%",))
        results = cursor.fetchall()
        print(f"Keyword '{kw}': {len(results)} matches")
        for r in results[:5]:  # print first 5
            print(f"  - {r[0]}")

    print("\n--- Checking specific User Inputs ---")
    user_inputs = [
        "Completion Percentage",
        "Game Longest Punt Return", 
        "1H Targets"
    ]
    for ui in user_inputs:
        cursor.execute("SELECT name FROM markets WHERE name LIKE ?", (f"%{ui}%",))
        res = cursor.fetchone()
        if res:
            print(f"'{ui}' MATCH FOUND: {res[0]}")
        else:
            print(f"'{ui}' NO MATCH")

    print("\n--- Checking Aliases for 'Targets' ---")
    cursor.execute("SELECT alias, market_id FROM market_aliases WHERE alias LIKE '%Targets%' LIMIT 10")
    for r in cursor.fetchall():
        print(f"Alias: {r[0]} -> ID: {r[1]}")

if __name__ == "__main__":
    check_markets()
