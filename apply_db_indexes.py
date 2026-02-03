
import sqlite3
import os

# Use current directory or find the db
DB_PATH = "sports_data.db"
if not os.path.exists(DB_PATH):
    # Try absolute path if running from elsewhere, or assume relative to script
    DB_PATH = os.path.join(os.path.dirname(__file__), "sports_data.db")

def add_indexes():
    print(f"Connecting to {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    indexes_to_create = [
        ("idx_players_name_nocase", "CREATE INDEX IF NOT EXISTS idx_players_name_nocase ON players(name COLLATE NOCASE)"),
        ("idx_teams_name_nocase", "CREATE INDEX IF NOT EXISTS idx_teams_name_nocase ON teams(name COLLATE NOCASE)"),
        ("idx_leagues_name_nocase", "CREATE INDEX IF NOT EXISTS idx_leagues_name_nocase ON leagues(name COLLATE NOCASE)"),
        ("idx_markets_name_nocase", "CREATE INDEX IF NOT EXISTS idx_markets_name_nocase ON markets(name COLLATE NOCASE)")
    ]
    
    for idx_name, sql in indexes_to_create:
        print(f"Creating index {idx_name}...")
        try:
            cursor.execute(sql)
            print("Success.")
        except Exception as e:
            print(f"Failed: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_indexes()
