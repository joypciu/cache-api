"""
Add critical indexes to improve query performance
Run this once to add indexes to the database
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'cache-api', 'sports_data.db')

def add_indexes():
    """Add indexes for frequently queried columns"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Adding indexes to improve performance...")
    
    indexes = [
        # Alias tables - most critical for lookups
        ("idx_player_aliases_alias_lower", "player_aliases", "(LOWER(alias))"),
        ("idx_team_aliases_alias_lower", "team_aliases", "(LOWER(alias))"),
        ("idx_league_aliases_alias_lower", "league_aliases", "(LOWER(alias))"),
        ("idx_market_aliases_alias_lower", "market_aliases", "(LOWER(alias))"),
        
        # Foreign key indexes for JOINs
        ("idx_players_team_id", "players", "(team_id)"),
        ("idx_players_league_id", "players", "(league_id)"),
        ("idx_players_sport_id", "players", "(sport_id)"),
        ("idx_teams_league_id", "teams", "(league_id)"),
        ("idx_teams_sport_id", "teams", "(sport_id)"),
        ("idx_leagues_sport_id", "leagues", "(sport_id)"),
        
        # Name lookup indexes
        ("idx_players_name_lower", "players", "(LOWER(name))"),
        ("idx_teams_name_lower", "teams", "(LOWER(name))"),
        ("idx_leagues_name_lower", "leagues", "(LOWER(name))"),
        ("idx_sports_name_lower", "sports", "(LOWER(name))"),
        
        # Additional team lookups
        ("idx_teams_nickname_lower", "teams", "(LOWER(nickname))"),
        ("idx_teams_abbreviation_lower", "teams", "(LOWER(abbreviation))"),
    ]
    
    for idx_name, table, columns in indexes:
        try:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {columns}"
            cursor.execute(sql)
            print(f"✓ Created index: {idx_name}")
        except Exception as e:
            print(f"✗ Error creating {idx_name}: {e}")
    
    conn.commit()
    
    # Analyze the database for better query optimization
    print("\nAnalyzing database...")
    cursor.execute("ANALYZE")
    conn.commit()
    
    print("\n✅ Indexes created successfully!")
    print("\nVerifying indexes...")
    
    # Show all indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
    indexes = cursor.fetchall()
    print(f"\nTotal indexes in database: {len(indexes)}")
    
    conn.close()

if __name__ == "__main__":
    add_indexes()
