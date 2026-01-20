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

def search_teams(search_term, cursor):
    """Search for teams using regex and fuzzy matching"""
    print(f"\nSearching for teams matching '{search_term}'...")
    print("📋 Querying main table: 'teams' (not 'team_aliases')\n")
    
    # Get all teams from MAIN table (teams) with league information
    cursor.execute("""
        SELECT t.id, t.name, l.name as league_name
        FROM teams t
        LEFT JOIN leagues l ON t.league_id = l.id
    """)
    all_teams = cursor.fetchall()
    print(f"Found {len(all_teams)} teams in main table.\n")
    
    if not all_teams:
        print("No teams found in database!")
        return []
    
    matches = []
    search_lower = search_term.lower()
    
    for team_id, team_name, league_name in all_teams:
        team_lower = team_name.lower()
        score = 0
        
        # Exact match
        if search_lower == team_lower:
            score = 1.0
        # Contains the search term
        elif search_lower in team_lower:
            score = 0.9
        # Search term contains team name words
        elif any(word in search_lower for word in team_lower.split() if len(word) > 2):
            score = 0.8
        # Regex pattern match (word boundaries)
        elif re.search(r'\b' + re.escape(search_lower) + r'\b', team_lower):
            score = 0.85
        else:
            # Fuzzy similarity
            score = similarity_score(search_term, team_name)
        
        if score > 0.4:  # Threshold for showing results
            matches.append((score, team_id, team_name, league_name or 'N/A'))
    
    # Sort by score (highest first)
    matches.sort(reverse=True, key=lambda x: x[0])
    
    return matches

def check_existing_alias(alias, cursor):
    """Check if alias already exists"""
    cursor.execute("SELECT team_id FROM team_aliases WHERE alias = ?", (alias,))
    result = cursor.fetchone()
    return result

def insert_alias(alias, team_id, cursor, conn):
    """Insert new alias into team_aliases table"""
    try:
        cursor.execute("""
            INSERT INTO team_aliases (alias, team_id)
            VALUES (?, ?)
        """, (alias, team_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 70)
    print(" TEAM ALIAS MANAGER ".center(70, "="))
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Get alias name
        print("\nStep 1: Enter the alias name")
        print("-" * 70)
        alias_name = input("Enter alias name: ").strip()
        
        if not alias_name:
            print("Error: Alias name cannot be empty!")
            return
        
        # Check if alias already exists
        existing = check_existing_alias(alias_name, cursor)
        if existing:
            cursor.execute("SELECT name FROM teams WHERE id = ?", (existing[0],))
            team = cursor.fetchone()
            print(f"\n⚠ Warning: This alias already exists for team: {team[0]}")
            overwrite = input("Do you want to replace it? (yes/no): ").strip().lower()
            if overwrite != 'yes':
                print("Operation cancelled.")
                return
            cursor.execute("DELETE FROM team_aliases WHERE alias = ?", (alias_name,))
            conn.commit()
            print("Existing alias removed.")
        
        # Step 2: Search for team
        print("\nStep 2: Search for the team")
        print("-" * 70)
        team_search = input("Enter team name (can be partial/misspelled): ").strip()
        
        if not team_search:
            print("Error: Team name cannot be empty!")
            return
        
        # Search teams
        matches = search_teams(team_search, cursor)
        
        if not matches:
            print("\n❌ No teams found matching your search!")
            print("Try using different keywords or check your spelling.")
            return
        
        # Display matches
        print("\n" + "=" * 90)
        print(" SEARCH RESULTS ".center(90, "="))
        print("=" * 90)
        print(f"{'#':<4} {'Score':<8} {'Team Name':<35} {'League':<25} {'ID':<10}")
        print("-" * 90)
        
        display_limit = min(10, len(matches))  # Show top 10 matches
        for idx, (score, team_id, team_name, league_name) in enumerate(matches[:display_limit], 1):
            score_bar = "█" * int(score * 10)
            print(f"{idx:<4} {score:.2f} {score_bar:<10} {team_name:<35} {league_name:<25} {team_id:<10}")
        
        if len(matches) > display_limit:
            print(f"\n... and {len(matches) - display_limit} more results (showing top {display_limit})")
        
        # Step 3: Select team
        print("\n" + "=" * 70)
        print("Step 3: Select the correct team")
        print("-" * 70)
        
        while True:
            try:
                selection = input(f"Enter number (1-{display_limit}) or 'q' to quit: ").strip()
                if selection.lower() == 'q':
                    print("Operation cancelled.")
                    return
                
                selection_num = int(selection)
                if 1 <= selection_num <= display_limit:
                    selected_team = matches[selection_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {display_limit}")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        score, team_id, team_name, league_name = selected_team
        
        # Step 4: Confirm and insert
        print("\n" + "=" * 70)
        print(" CONFIRMATION ".center(70, "="))
        print("=" * 70)
        print(f"Alias:     {alias_name}")
        print(f"Team:      {team_name}")
        print(f"League:    {league_name}")
        print(f"Team ID:   {team_id}")
        print("-" * 70)
        
        confirm = input("\nAdd this alias? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            if insert_alias(alias_name, team_id, cursor, conn):
                print("\n✅ SUCCESS! Alias added successfully!")
                print(f"   '{alias_name}' → {team_name} (ID: {team_id})")
                
                # Show total aliases for this team
                cursor.execute("SELECT COUNT(*) FROM team_aliases WHERE team_id = ?", (team_id,))
                count = cursor.fetchone()[0]
                print(f"\n   This team now has {count} alias(es) total.")
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
        print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
