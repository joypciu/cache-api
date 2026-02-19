import sqlite3
import os

# Connect to the database
conn = sqlite3.connect('sports_data.db')
cursor = conn.cursor()

# Mapping of PNG filenames (without .png) to team names in the database
# BPL Cricket Teams (Bangladesh)
logo_mapping = {
    'Abahani_Ltd_Dhaka': 'Abahani Limited',
    'Brothers_Union': 'Brothers Union',
    'Chattogram_Royals': 'Chittagong Kings',
    'Dhaka_Capitals': 'Dhaka Capital',
    'Dhaka_Mohammedan': 'Mohammedan Sporting Club',
    'Fortis': 'Fortune Barishal',
    'Rajshahi_Warriors': 'Durbar Rajshahi',
    'Rangpur_Riders': 'Rangpur Riders',
    'Sylhet_Titans': 'Sylhet Strikers'
}

# Update the logo column for each team - ONLY for Cricket sport
updated_count = 0
for logo_filename, team_name in logo_mapping.items():
    logo_path = f'static/logo/team/cricket/bpl/{logo_filename}.png'
    
    # Update only teams in Cricket sport to avoid cross-sport contamination
    cursor.execute("""
        UPDATE teams 
        SET logo = ? 
        WHERE name = ?
        AND sport_id = (SELECT id FROM sports WHERE name = 'Cricket')
    """, (logo_path, team_name))
    
    rows_affected = cursor.rowcount
    updated_count += rows_affected
    print(f"Updated {rows_affected} team(s) for '{team_name}' with logo: {logo_path}")

# Commit the changes
conn.commit()
print(f"\nTotal teams updated: {updated_count}")

# Verify the updates
print("\nVerifying updates...")
cursor.execute("""
    SELECT t.name, t.logo, l.name as league
    FROM teams t
    LEFT JOIN leagues l ON t.league_id = l.id
    WHERE t.logo IS NOT NULL AND t.logo LIKE '%bpl%'
    ORDER BY t.name
    LIMIT 32
""")

results = cursor.fetchall()
for row in results:
    print(f"{row[0]:30} | {row[2]:30} | {row[1]}")

conn.close()
