import sqlite3

# Connect to the database
conn = sqlite3.connect('sports_data.db')
cursor = conn.cursor()

# Remove basketball logos from non-basketball sports
cursor.execute("""
    UPDATE teams 
    SET logo = NULL 
    WHERE logo LIKE '%fiba_eutobasket%' 
    AND sport_id != (SELECT id FROM sports WHERE name = 'Basketball')
""")

rows_affected = cursor.rowcount
print(f"Removed basketball logos from {rows_affected} non-basketball teams")

# Commit the changes
conn.commit()

# Verify the fix
cursor.execute("""
    SELECT COUNT(*) 
    FROM teams t
    LEFT JOIN sports s ON t.sport_id = s.id
    WHERE t.logo LIKE '%fiba_eutobasket%' 
    AND s.name != 'Basketball'
""")

remaining = cursor.fetchone()[0]
print(f"Remaining non-basketball teams with basketball logos: {remaining}")

# Show basketball teams that still have logos
cursor.execute("""
    SELECT COUNT(*) 
    FROM teams t
    LEFT JOIN sports s ON t.sport_id = s.id
    WHERE t.logo LIKE '%fiba_eutobasket%' 
    AND s.name = 'Basketball'
""")

basketball_count = cursor.fetchone()[0]
print(f"Basketball teams with logos: {basketball_count}")

conn.close()
