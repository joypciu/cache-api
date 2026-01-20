import sqlite3
import re
import os
from difflib import SequenceMatcher

def get_db_connection():
    """Connect to the database"""
    db_path = os.path.join(os.path.dirname(__file__), 'cache-api', 'sports_data.db')
    if not os.path.exists(db_path):
        # Try current directory
        db_path = 'sports_data.db'
    return sqlite3.connect(db_path)

def similarity_score(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def search_players(search_term, cursor):
    """Search for players using regex and fuzzy matching"""
    print(f"\nSearching for players matching '{search_term}'...")
    print("📋 Querying main table: 'players' (not 'player_aliases')\n")
    
    # Get all players from MAIN table (players) with team and league information
    cursor.execute("""
        SELECT p.id, p.name, p.first_name, p.last_name, t.name as team_name, l.name as league_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN leagues l ON p.league_id = l.id
        ORDER BY p.name COLLATE NOCASE
    """)
    all_players = cursor.fetchall()
    print(f"Found {len(all_players)} players in main table.\n")
    
    if not all_players:
        print("No players found in database!")
        return []
    
    matches = []
    search_lower = search_term.lower().strip()
    search_parts = search_lower.split()
    
    for player_id, player_name, first_name, last_name, team_name, league_name in all_players:
        player_lower = player_name.lower()
        first_lower = (first_name or '').lower()
        last_lower = (last_name or '').lower()
        score = 0
        
        # Exact match (case-insensitive)
        if search_lower == player_lower:
            score = 1.0
        # Exact first name or last name match
        elif search_lower == first_lower or search_lower == last_lower:
            score = 0.95
        # Starts with search term (e.g., "crist" matches "Cristiano Ronaldo")
        elif player_lower.startswith(search_lower):
            score = 0.92
        # First name or last name starts with search term
        elif first_lower.startswith(search_lower) or last_lower.startswith(search_lower):
            score = 0.90
        # Contains the search term
        elif search_lower in player_lower:
            score = 0.88
        # Multi-word search: check if all parts match (e.g., "cristiano ronaldo")
        elif len(search_parts) > 1:
            all_parts_match = all(
                any(part in word.lower() for word in player_name.split())
                for part in search_parts
            )
            if all_parts_match:
                score = 0.93
        # Check if search matches first letter of first name + last name (e.g., "c ronaldo")
        elif len(search_parts) == 2:
            if (first_lower.startswith(search_parts[0]) and last_lower.startswith(search_parts[1])):
                score = 0.91
        # Single letter search: matches first letter of first or last name
        elif len(search_lower) == 1:
            if first_lower.startswith(search_lower) or last_lower.startswith(search_lower):
                score = 0.75
        # Word boundary match
        elif re.search(r'\b' + re.escape(search_lower), player_lower):
            score = 0.85
        # Any word in player name contains search term
        elif any(search_lower in word.lower() for word in player_name.split()):
            score = 0.82
        else:
            # Fuzzy similarity
            score = similarity_score(search_term, player_name)
        
        if score > 0.4:  # Threshold for showing results
            matches.append((score, player_id, player_name, team_name or 'N/A', league_name or 'N/A'))
    
    # Sort by score (highest first), then alphabetically by name (case-insensitive)
    matches.sort(key=lambda x: (-x[0], x[2].lower()))
    
    return matches

def check_existing_alias(alias, cursor):
    """Check if alias already exists"""
    cursor.execute("SELECT player_id FROM player_aliases WHERE alias = ?", (alias,))
    result = cursor.fetchone()
    return result

def insert_alias(alias, player_id, cursor, conn):
    """Insert new alias into player_aliases table"""
    try:
        cursor.execute("""
            INSERT INTO player_aliases (alias, player_id)
            VALUES (?, ?)
        """, (alias, player_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 90)
    print(" PLAYER ALIAS MANAGER ".center(90, "="))
    print("=" * 90)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Get alias name
        print("\nStep 1: Enter the alias name")
        print("-" * 90)
        alias_name = input("Enter alias name: ").strip()
        
        if not alias_name:
            print("Error: Alias name cannot be empty!")
            return
        
        # Check if alias already exists
        existing = check_existing_alias(alias_name, cursor)
        if existing:
            cursor.execute("SELECT name FROM players WHERE id = ?", (existing[0],))
            player = cursor.fetchone()
            print(f"\n⚠ Warning: This alias already exists for player: {player[0]}")
            overwrite = input("Do you want to replace it? (yes/no): ").strip().lower()
            if overwrite != 'yes':
                print("Operation cancelled.")
                return
            cursor.execute("DELETE FROM player_aliases WHERE alias = ?", (alias_name,))
            conn.commit()
            print("Existing alias removed.")
        
        # Step 2: Search for player
        print("\nStep 2: Search for the player")
        print("-" * 90)
        player_search = input("Enter player name (can be partial/misspelled): ").strip()
        
        if not player_search:
            print("Error: Player name cannot be empty!")
            return
        
        # Search players
        matches = search_players(player_search, cursor)
        
        if not matches:
            print("\n❌ No players found matching your search!")
            print("Try using different keywords or check your spelling.")
            return
        
        # Display matches
        print("\n" + "=" * 110)
        print(" SEARCH RESULTS ".center(110, "="))
        print("=" * 110)
        print(f"{'#':<4} {'Score':<8} {'Player Name':<30} {'Team':<25} {'League':<25} {'ID':<10}")
        print("-" * 110)
        
        display_limit = min(10, len(matches))  # Show top 10 matches
        for idx, (score, player_id, player_name, team_name, league_name) in enumerate(matches[:display_limit], 1):
            score_bar = "█" * int(score * 10)
            print(f"{idx:<4} {score:.2f} {score_bar:<10} {player_name:<30} {team_name:<25} {league_name:<25} {player_id:<10}")
        
        if len(matches) > display_limit:
            print(f"\n... and {len(matches) - display_limit} more results (showing top {display_limit})")
        
        # Step 3: Select player
        print("\n" + "=" * 90)
        print("Step 3: Select the correct player")
        print("-" * 90)
        
        while True:
            try:
                selection = input(f"Enter number (1-{display_limit}) or 'q' to quit: ").strip()
                if selection.lower() == 'q':
                    print("Operation cancelled.")
                    return
                
                selection_num = int(selection)
                if 1 <= selection_num <= display_limit:
                    selected_player = matches[selection_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {display_limit}")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        score, player_id, player_name, team_name, league_name = selected_player
        
        # Step 4: Confirm and insert
        print("\n" + "=" * 90)
        print(" CONFIRMATION ".center(90, "="))
        print("=" * 90)
        print(f"Alias:      {alias_name}")
        print(f"Player:     {player_name}")
        print(f"Team:       {team_name}")
        print(f"League:     {league_name}")
        print(f"Player ID:  {player_id}")
        print("-" * 90)
        
        confirm = input("\nAdd this alias? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            if insert_alias(alias_name, player_id, cursor, conn):
                print("\n✅ SUCCESS! Alias added successfully!")
                print(f"   '{alias_name}' → {player_name} (ID: {player_id})")
                
                # Show total aliases for this player
                cursor.execute("SELECT COUNT(*) FROM player_aliases WHERE player_id = ?", (player_id,))
                count = cursor.fetchone()[0]
                print(f"\n   This player now has {count} alias(es) total.")
            else:
                print("\n❌ Failed to add alias!")
        else:
            print("\nOperation cancelled.")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print("\n" + "=" * 90)

if __name__ == "__main__":
    main()
