"""
Cache Database Module
Provides database access to sports data using SQLite with Redis caching.
"""

import sqlite3
import os
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from redis_cache import get_cached_data, set_cached_data

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "sports_data.db")


def get_db_connection():
    """Create and return a database connection with optimizations"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL")
    # Increase cache size (default is 2MB, set to 10MB)
    conn.execute("PRAGMA cache_size=-10000")
    # Use memory for temporary tables
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def normalize_key(value: str) -> str:
    """Normalize a string for cache lookup (lowercase, strip whitespace)"""
    if not value:
        return ""
    return value.lower().strip()


def get_league_priority(league_name: str) -> int:
    """
    Get sorting priority for leagues.
    Lower number = higher priority
    """
    if not league_name:
        return 999
    
    league_lower = league_name.lower()
    
    # Priority leagues
    if 'premier league' in league_lower and 'england' in league_lower:
        return 1
    elif 'la liga' in league_lower or ('liga' in league_lower and 'spain' in league_lower):
        return 2
    elif 'bundesliga' in league_lower or ('bundesliga' in league_lower and 'germany' in league_lower):
        return 3
    elif 'serie a' in league_lower or ('serie' in league_lower and 'italy' in league_lower):
        return 4
    elif 'ligue 1' in league_lower or ('ligue' in league_lower and 'france' in league_lower):
        return 5
    else:
        return 999  # All other leagues


def expand_sports_terms(text: str) -> str:
    """
    Expand common sports abbreviations for better fuzzy matching.
    """
    text = text.lower()
    replacements = {
        "rush ": "rushing ",
        "rec ": "receiving ",
        "tds": "touchdowns",
        "ints": "interceptions",
        "fg": "field goal",
        "xp": "extra point",
        "1h": "1st half",
        "2h": "2nd half",
        "1st": "1st", # ensure casing standard if needed, though we use lower()
        "yrds": "yards",
        "yds": "yards",
        "att": "attempts"
    }
    
    for abbr, full in replacements.items():
        if abbr in text:
            text = text.replace(abbr, full)
            
    return text

def get_cache_entry(
    market: Optional[str] = None,
    team: Optional[str] = None,
    player: Optional[str] = None,
    sport: Optional[str] = None,
    league: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve cache entry based on provided parameters.
    Uses Redis for caching with fallback to SQLite database.
    
    Relationships:
    - ONE-TO-MANY: Team → Players (one team has many players)
    - ONE-TO-ONE: Player → Team (each player belongs to exactly one team)
    - ONE-TO-MANY: League → Teams (one league has many teams)
    
    Args:
        market: Market type to look up
        team: Team name to look up (returns team with all its players)
        player: Player name to look up (returns player with their one team)
        sport: Sport name (required when searching by team)
        league: League name to look up (returns league with all its teams)
    
    Returns:
        Dictionary with cache entry data or None if not found
    """
    
    # Try to get from Redis cache first
    cached_result = get_cached_data(market=market, team=team, player=player, sport=sport, league=league)
    if cached_result is not None:
        return cached_result
    
    # Cache miss - query database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Special case: BOTH team AND player provided - search for player filtered by team
        if team and player:
            normalized_team = normalize_key(team)
            normalized_player = normalize_key(player)
            normalized_sport = normalize_key(sport) if sport else None
            
            # Search for player in BOTH player_aliases AND players table
            # 1. Check player_aliases
            cursor.execute("""
                SELECT DISTINCT player_id FROM player_aliases
                WHERE LOWER(alias) = ?
            """, (normalized_player,))
            player_ids_from_aliases = [row[0] for row in cursor.fetchall()]
            
            # 2. Check players table directly
            # Try exact match first (much faster)
            cursor.execute("""
                SELECT DISTINCT id FROM players
                WHERE name = ? COLLATE NOCASE
            """, (player.strip(),))
            player_ids_from_main = [row[0] for row in cursor.fetchall()]

            if not player_ids_from_main and len(normalized_player) > 2:
                # Fallback to slower partial match - Try prefix first (Index Friendly)
                cursor.execute("""
                    SELECT DISTINCT id FROM players
                    WHERE name LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                """, (f"{normalized_player}%", f"{normalized_player}%", f"{normalized_player}%"))
                player_ids_from_main = [row[0] for row in cursor.fetchall()]

                # STRICT PERFORMANCE MODE: Disabled full wildcard scan for players
                # Only prefix matching is allowed to prevent DB lockups during batch processing.
                # If specific fuzzy matching is needed, use a dedicated search endpoint or search service.


            
            player_ids = list(set(player_ids_from_aliases + player_ids_from_main))
            
            if not player_ids:
                return None
            
            # Search for team in BOTH team_aliases AND teams table
            # 1. Check team_aliases
            cursor.execute("""
                SELECT DISTINCT team_id FROM team_aliases
                WHERE LOWER(alias) = ?
            """, (normalized_team,))
            team_ids_from_aliases = [row[0] for row in cursor.fetchall()]
            
            # 2. Check teams table directly
            team_ids_from_main = []
            
            # Try exact match first
            if normalized_sport:
                cursor.execute("""
                    SELECT DISTINCT t.id FROM teams t
                    LEFT JOIN sports s ON t.sport_id = s.id
                    WHERE (t.name = ? COLLATE NOCASE OR t.abbreviation = ? COLLATE NOCASE)
                      AND LOWER(s.name) = ?
                """, (team.strip(), team.strip(), normalized_sport))
            else:
                cursor.execute("""
                    SELECT DISTINCT id FROM teams
                    WHERE name = ? COLLATE NOCASE OR abbreviation = ? COLLATE NOCASE
                """, (team.strip(), team.strip()))
            
            team_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            if not team_ids_from_main:
                # Fallback to slower partial match
                if normalized_sport:
                    cursor.execute("""
                        SELECT DISTINCT t.id FROM teams t
                        LEFT JOIN sports s ON t.sport_id = s.id
                        WHERE (LOWER(t.name) LIKE ? OR LOWER(t.nickname) LIKE ? OR LOWER(t.abbreviation) = ?)
                          AND LOWER(s.name) = ?
                    """, (f"%{normalized_team}%", f"%{normalized_team}%", normalized_team, normalized_sport))
                else:
                    cursor.execute("""
                        SELECT DISTINCT id FROM teams
                        WHERE LOWER(name) LIKE ? OR LOWER(nickname) LIKE ? OR LOWER(abbreviation) = ?
                    """, (f"%{normalized_team}%", f"%{normalized_team}%", normalized_team))
                
                team_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            team_ids = list(set(team_ids_from_aliases + team_ids_from_main))
            
            if not team_ids:
                return None
            
            # Search for player(s) matching player_id AND team_id, filtered by sport if provided
            placeholders_players = ','.join('?' * len(player_ids))
            placeholders_teams = ','.join('?' * len(team_ids))
            
            if normalized_sport:
                cursor.execute(f"""
                    SELECT p.id, p.name, p.first_name, p.last_name, p.position, p.number,
                           p.age, p.height, p.weight,
                           t.name as team_name, t.abbreviation, t.city,
                           l.name as league_name, s.name as sport_name
                    FROM players p
                    JOIN teams t ON p.team_id = t.id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN sports s ON p.sport_id = s.id
                    WHERE p.id IN ({placeholders_players})
                      AND p.team_id IN ({placeholders_teams})
                      AND LOWER(s.name) = ?
                    ORDER BY p.name
                """, (*player_ids, *team_ids, normalized_sport))
            else:
                cursor.execute(f"""
                    SELECT p.id, p.name, p.first_name, p.last_name, p.position, p.number,
                           p.age, p.height, p.weight,
                           t.name as team_name, t.abbreviation, t.city,
                           l.name as league_name, s.name as sport_name
                    FROM players p
                    JOIN teams t ON p.team_id = t.id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN sports s ON p.sport_id = s.id
                    WHERE p.id IN ({placeholders_players})
                      AND p.team_id IN ({placeholders_teams})
                    ORDER BY p.name
                """, (*player_ids, *team_ids))
            
            results = cursor.fetchall()
            if results:
                players_data = []
                
                for result in results:
                    players_data.append({
                        "id": result["id"],
                        "normalized_name": result["name"],
                        "first_name": result["first_name"],
                        "last_name": result["last_name"],
                        "position": result["position"],
                        "number": result["number"],
                        "age": result["age"],
                        "height": result["height"],
                        "weight": result["weight"],
                        "team": result["team_name"],
                        "team_abbreviation": result["abbreviation"],
                        "team_city": result["city"],
                        "league": result["league_name"],
                        "sport": result["sport_name"]
                    })
                
                result_data = {
                    "type": "player",
                    "query": {
                        "player": player,
                        "team": team,
                        "sport": sport
                    },
                    "players": players_data,
                    "player_count": len(players_data)
                }
                
                # Cache the result
                set_cached_data(result_data, market=market, team=team, player=player, sport=sport)
                return result_data
            else:
                # No player found in that specific team
                return None
        
        # Priority: team > player > market
        if team:
            normalized_team = normalize_key(team)
            normalized_sport = normalize_key(sport) if sport else None
            
            # Search in BOTH team_aliases AND teams table
            # 1. Check team_aliases table
            cursor.execute("""
                SELECT DISTINCT team_id FROM team_aliases
                WHERE LOWER(alias) = ?
            """, (normalized_team,))
            team_ids_from_aliases = [row[0] for row in cursor.fetchall()]
            
            # 2. Check teams table directly (name, nickname, abbreviation)
            team_ids_from_main = []
            
            # Try exact match first
            if normalized_sport:
                cursor.execute("""
                    SELECT DISTINCT t.id FROM teams t
                    LEFT JOIN sports s ON t.sport_id = s.id
                    WHERE (t.name = ? COLLATE NOCASE OR t.abbreviation = ? COLLATE NOCASE)
                      AND LOWER(s.name) = ?
                """, (team.strip(), team.strip(), normalized_sport))
            else:
                cursor.execute("""
                    SELECT DISTINCT id FROM teams
                    WHERE name = ? COLLATE NOCASE OR abbreviation = ? COLLATE NOCASE
                """, (team.strip(), team.strip()))
                
            team_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            # For short strings, SKIP fuzzy search to prevent performance kill (LIKE '%a%' matches everything)
            if not team_ids_from_main and len(normalized_team) > 2:
                if normalized_sport:
                    # Try prefix match first (Index Friendly)
                    cursor.execute("""
                        SELECT DISTINCT t.id FROM teams t
                        LEFT JOIN sports s ON t.sport_id = s.id
                        WHERE (t.name LIKE ? OR t.nickname LIKE ? OR t.abbreviation = ?)
                          AND LOWER(s.name) = ?
                    """, (f"{normalized_team}%", f"{normalized_team}%", normalized_team, normalized_sport))
                    team_ids_from_main = [row[0] for row in cursor.fetchall()]
                    
                    # STRICT PERFORMANCE MODE: Disabled full wildcard scan for teams
                    
                else:
                    # Try prefix match first (Index Friendly)
                    cursor.execute("""
                        SELECT DISTINCT id FROM teams
                        WHERE name LIKE ? OR nickname LIKE ? OR abbreviation = ?
                    """, (f"{normalized_team}%", f"{normalized_team}%", normalized_team))
                    team_ids_from_main = [row[0] for row in cursor.fetchall()]

                    # STRICT PERFORMANCE MODE: Disabled full wildcard scan for teams

            team_ids = list(set(team_ids_from_aliases + team_ids_from_main))
            
            if not team_ids:
                return None
            
            # Search for ALL teams matching team_id(s) AND sport (case-insensitive)
            placeholders = ','.join('?' * len(team_ids))
            
            if normalized_sport:
                cursor.execute(f"""
                    SELECT t.id, t.name, t.abbreviation, t.city, t.mascot, t.nickname,
                           l.name as league_name, s.name as sport_name
                    FROM teams t
                    LEFT JOIN leagues l ON t.league_id = l.id
                    LEFT JOIN sports s ON t.sport_id = s.id
                    WHERE t.id IN ({placeholders})
                      AND LOWER(s.name) = ?
                    ORDER BY t.name
                """, (*team_ids, normalized_sport))
            else:
                # Fallback if sport not provided (shouldn't happen due to API validation)
                cursor.execute(f"""
                    SELECT t.id, t.name, t.abbreviation, t.city, t.mascot, t.nickname,
                           l.name as league_name, s.name as sport_name
                    FROM teams t
                    LEFT JOIN leagues l ON t.league_id = l.id
                    LEFT JOIN sports s ON t.sport_id = s.id
                    WHERE t.id IN ({placeholders})
                    ORDER BY t.name
                """, tuple(team_ids))
            
            results = cursor.fetchall()
            if results:
                teams_data = []
                
                # Process each matching team
                for result in results:
                    team_id = result["id"]
                    
                    # Get all players for this team (ONE-TO-MANY relationship)
                    cursor.execute("""
                        SELECT p.id, p.name, p.first_name, p.last_name, p.position, 
                               p.number, p.age, p.height, p.weight
                        FROM players p
                        WHERE p.team_id = ?
                        ORDER BY p.name
                    """, (team_id,))
                    
                    players = [dict(row) for row in cursor.fetchall()]
                    
                    teams_data.append({
                        "id": result["id"],
                        "normalized_name": result["name"],
                        "abbreviation": result["abbreviation"],
                        "city": result["city"],
                        "mascot": result["mascot"],
                        "nickname": result["nickname"],
                        "league": result["league_name"],
                        "sport": result["sport_name"],
                        "players": players,
                        "player_count": len(players)
                    })
                
                # Sort teams by league priority
                teams_data.sort(key=lambda x: (get_league_priority(x.get("league", "")), x.get("normalized_name", "")))
                
                result_data = {
                    "type": "team",
                    "query": team,
                    "teams": teams_data,
                    "team_count": len(teams_data)
                }
                
                # Cache the result
                set_cached_data(result_data, market=market, team=team, player=player, sport=sport)
                return result_data
        
        if player:
            normalized_player = normalize_key(player)
            
            # Search in BOTH player_aliases AND players table
            # 1. Check player_aliases table
            cursor.execute("""
                SELECT DISTINCT player_id FROM player_aliases
                WHERE LOWER(alias) = ?
            """, (normalized_player,))
            player_ids_from_aliases = [row[0] for row in cursor.fetchall()]
            
            # 2. Check players table directly (name, first_name, last_name)
            # Try exact match first
            cursor.execute("""
                SELECT DISTINCT id FROM players
                WHERE name = ? COLLATE NOCASE
            """, (player.strip(),))
            player_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            if not player_ids_from_main and len(normalized_player) > 2:
                cursor.execute("""
                    SELECT DISTINCT id FROM players
                    WHERE LOWER(name) LIKE ? OR LOWER(first_name) LIKE ? OR LOWER(last_name) LIKE ?
                """, (f"%{normalized_player}%", f"%{normalized_player}%", f"%{normalized_player}%"))
                player_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            # Combine and deduplicate player IDs
            player_ids = list(set(player_ids_from_aliases + player_ids_from_main))
            
            if not player_ids:
                return None
            
            # Search for ALL players with matching player_id (case-insensitive)
            placeholders = ','.join('?' * len(player_ids))
            cursor.execute(f"""
                SELECT p.id, p.name, p.first_name, p.last_name, p.position, p.number,
                       p.age, p.height, p.weight,
                       t.name as team_name, l.name as league_name, s.name as sport_name
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN sports s ON p.sport_id = s.id
                WHERE p.id IN ({placeholders})
                ORDER BY p.name
            """, tuple(player_ids))
            
            results = cursor.fetchall()
            if results:
                players_data = []
                
                for result in results:
                    players_data.append({
                        "id": result["id"],
                        "normalized_name": result["name"],
                        "first_name": result["first_name"],
                        "last_name": result["last_name"],
                        "position": result["position"],
                        "number": result["number"],
                        "age": result["age"],
                        "height": result["height"],
                        "weight": result["weight"],
                        "team": result["team_name"],
                        "league": result["league_name"],
                        "sport": result["sport_name"]
                    })
                
                # Sort players by league priority
                players_data.sort(key=lambda x: (get_league_priority(x.get("league", "")), x.get("normalized_name", "")))
                
                result_data = {
                    "type": "player",
                    "query": player,
                    "players": players_data,
                    "player_count": len(players_data)
                }
                
                # Cache the result
                set_cached_data(result_data, market=market, team=team, player=player, sport=sport)
                return result_data
        
        if league:
            normalized_league = normalize_key(league)
            normalized_sport = normalize_key(sport) if sport else None
            
            # Search in BOTH league_aliases AND leagues table
            # 1. Check league_aliases table
            cursor.execute("""
                SELECT DISTINCT league_id FROM league_aliases
                WHERE LOWER(alias) = ?
            """, (normalized_league,))
            league_ids_from_aliases = [row[0] for row in cursor.fetchall()]
            
            # 2. Check leagues table directly
            league_ids_from_main = []
            
            # Try exact match first
            if normalized_sport:
                cursor.execute("""
                    SELECT DISTINCT l.id FROM leagues l
                    LEFT JOIN sports s ON l.sport_id = s.id
                    WHERE l.name = ? COLLATE NOCASE
                      AND LOWER(s.name) = ?
                """, (league.strip(), normalized_sport))
            else:
                cursor.execute("""
                    SELECT DISTINCT id FROM leagues
                    WHERE name = ? COLLATE NOCASE
                """, (league.strip(),))
            
            league_ids_from_main = [row[0] for row in cursor.fetchall()]

            if not league_ids_from_main:
                if normalized_sport:
                    cursor.execute("""
                        SELECT DISTINCT l.id FROM leagues l
                        LEFT JOIN sports s ON l.sport_id = s.id
                        WHERE LOWER(l.name) LIKE ?
                          AND LOWER(s.name) = ?
                    """, (f"%{normalized_league}%", normalized_sport))
                else:
                    cursor.execute("""
                        SELECT DISTINCT id FROM leagues
                        WHERE LOWER(name) LIKE ?
                    """, (f"%{normalized_league}%",))
                
                league_ids_from_main = [row[0] for row in cursor.fetchall()]
            
            # Combine and deduplicate league IDs
            league_ids = list(set(league_ids_from_aliases + league_ids_from_main))
            
            if not league_ids:
                return None
            
            # Search for ALL leagues matching league_id(s), filtered by sport if provided
            placeholders = ','.join('?' * len(league_ids))
            
            if normalized_sport:
                cursor.execute(f"""
                    SELECT l.id, l.name, s.name as sport_name
                    FROM leagues l
                    LEFT JOIN sports s ON l.sport_id = s.id
                    WHERE l.id IN ({placeholders})
                      AND LOWER(s.name) = ?
                    ORDER BY l.name
                """, (*league_ids, normalized_sport))
            else:
                cursor.execute(f"""
                    SELECT l.id, l.name, s.name as sport_name
                    FROM leagues l
                    LEFT JOIN sports s ON l.sport_id = s.id
                    WHERE l.id IN ({placeholders})
                    ORDER BY l.name
                """, tuple(league_ids))
            
            results = cursor.fetchall()
            if results:
                leagues_data = []
                
                # Process each matching league
                for result in results:
                    league_id = result["id"]
                    
                    # Get all teams for this league (ONE-TO-MANY relationship)
                    cursor.execute("""
                        SELECT t.id, t.name, t.abbreviation, t.city, t.mascot, t.nickname
                        FROM teams t
                        WHERE t.league_id = ?
                        ORDER BY t.name
                    """, (league_id,))
                    
                    teams = [dict(row) for row in cursor.fetchall()]
                    
                    leagues_data.append({
                        "id": result["id"],
                        "normalized_name": result["name"],
                        "sport": result["sport_name"],
                        "teams": teams,
                        "team_count": len(teams)
                    })
                
                # Sort leagues by priority
                leagues_data.sort(key=lambda x: (get_league_priority(x.get("normalized_name", "")), x.get("normalized_name", "")))
                
                result_data = {
                    "type": "league",
                    "query": league,
                    "leagues": leagues_data,
                    "league_count": len(leagues_data)
                }
                
                # Cache the result
                set_cached_data(result_data, market=market, team=team, player=player, sport=sport, league=league)
                return result_data
        
        if market:
            normalized_market = normalize_key(market)
            # Create a stripped version for robust matching (no spaces, no underscores)
            market_search_term = market.lower().replace(" ", "").replace("_", "")
            
            # First, try exact alias match (normalized)
            cursor.execute("""
                SELECT DISTINCT market_id FROM market_aliases
                WHERE LOWER(REPLACE(REPLACE(alias, ' ', ''), '_', '')) = ?
                LIMIT 1
            """, (market_search_term,))
            
            alias_result = cursor.fetchone()
            
            if alias_result:
                market_id = alias_result[0]
            else:
                # No exact alias match, try direct match on markets table
                # 1. Try exact stripped match
                cursor.execute("""
                    SELECT id FROM markets
                    WHERE LOWER(REPLACE(REPLACE(name, ' ', ''), '_', '')) = ?
                    LIMIT 1
                """, (market_search_term,))
                direct_result = cursor.fetchone()
                
                if direct_result:
                    market_id = direct_result[0]
                else:
                    # 2. Try fuzzy contain match (e.g. "Completion Percentage" -> "Player Passing Completion Percentage")
                    # We normalize the input first to ensure good matching
                    normalized_input = market.lower().strip()
                    
                    # Search 2a: Direct fuzzy on input (Prefix first)
                    cursor.execute("""
                        SELECT id FROM markets
                        WHERE name LIKE ?
                        ORDER BY LENGTH(name) ASC 
                        LIMIT 1
                    """, (f"{normalized_input}%",))
                    fuzzy_result = cursor.fetchone()
                    
                    if not fuzzy_result and len(normalized_input) > 3:
                        # STRICT PERFORMANCE MODE: Disabled full wildcard scan for markets
                        pass

                    if fuzzy_result:
                         market_id = fuzzy_result[0]
                    else:
                        # Search 2b: Expanded abbreviations (Rush -> Rushing, etc)
                        expanded_input = expand_sports_terms(normalized_input)
                        if expanded_input != normalized_input:
                            cursor.execute("""
                                SELECT id FROM markets
                                WHERE name LIKE ?
                                ORDER BY LENGTH(name) ASC
                                LIMIT 1
                            """, (f"{expanded_input}%",))
                            expanded_result = cursor.fetchone()
                            
                            if not expanded_result and len(expanded_input) > 3:
                                # STRICT PERFORMANCE MODE: Disabled full wildcard scan for markets
                                pass

                            if expanded_result:
                                market_id = expanded_result[0]
                            else:
                                return None
            
            # Search for market by resolved ID
            cursor.execute("""
                SELECT m.id, m.name, m.market_type_id
                FROM markets m
                WHERE m.id = ?
            """, (market_id,))
            
            result = cursor.fetchone()
            if result:
                # Get associated sports for this market
                cursor.execute("""
                    SELECT s.name
                    FROM market_sports ms
                    JOIN sports s ON ms.sport_id = s.id
                    WHERE ms.market_id = ?
                """, (result["id"],))
                sports = [row["name"] for row in cursor.fetchall()]
                
                result_data = {
                    "type": "market",
                    "query": market,
                    "normalized_name": result["name"],
                    "market_type_id": result["market_type_id"],
                    "sports": sports
                }
                
                # Cache the result
                set_cached_data(result_data, market=market, team=team, player=player, sport=sport)
                return result_data
        
        # No match found
        return None
        
    finally:
        conn.close()


def get_all_teams() -> List[Dict[str, Any]]:
    """Get all teams from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT t.id, t.name, t.abbreviation, l.name as league_name, s.name as sport_name
            FROM teams t
            LEFT JOIN leagues l ON t.league_id = l.id
            LEFT JOIN sports s ON t.sport_id = s.id
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_players() -> List[Dict[str, Any]]:
    """Get all players from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT p.id, p.name, p.position, t.name as team_name, l.name as league_name, s.name as sport_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN sports s ON p.sport_id = s.id
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_markets() -> List[Dict[str, Any]]:
    """Get all markets from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT m.id, m.name, m.market_type_id
            FROM markets m
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_batch_cache_entries(
    teams: Optional[List[str]] = None,
    players: Optional[List[str]] = None,
    markets: Optional[List[str]] = None,
    sport: Optional[str] = None,
    leagues: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Batch query for multiple items across categories.
    Each item is searched independently within its category.
    Uses parallel processing for improved performance.
    
    Args:
        teams: List of team names to look up
        players: List of player names to look up
        markets: List of market types to look up
        sport: Sport context for team/league queries
        leagues: List of league names to look up
    
    Returns:
        Dictionary with categories containing item results:
        {
            "team": {"Lakers": {...}, "Warriors": null},
            "player": {"LeBron": {...}},
            "market": {"moneyline": {...}},
            "league": {"NBA": {...}}
        }
    """
    result = {}
    
    # Reduced max_workers to prevent CPU thrashing on 50% quota VPS
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        
        # Submit all team queries

        if teams:
            result["team"] = {}
            for team_name in teams:
                future = executor.submit(get_cache_entry, team=team_name, sport=sport)
                futures[future] = ("team", team_name)
        
        # Submit all player queries
        if players:
            result["player"] = {}
            for player_name in players:
                future = executor.submit(get_cache_entry, player=player_name)
                futures[future] = ("player", player_name)
        
        # Submit all market queries
        if markets:
            result["market"] = {}
            for market_name in markets:
                future = executor.submit(get_cache_entry, market=market_name)
                futures[future] = ("market", market_name)
        
        # Submit all league queries
        if leagues:
            result["league"] = {}
            for league_name in leagues:
                future = executor.submit(get_cache_entry, league=league_name, sport=sport)
                futures[future] = ("league", league_name)
        
        # Collect results as they complete
        for future in as_completed(futures):
            category, name = futures[future]
            try:
                entry = future.result()
                result[category][name] = entry
            except Exception as e:
                # Handle errors gracefully
                result[category][name] = None
    
    return result


def get_precision_batch_cache_entries(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Precision batch query where each query can combine multiple parameters.
    Uses parallel processing for improved performance.
    
    Args:
        queries: List of query dictionaries, each with optional parameters:
                 team, player, market, sport, league
    
    Returns:
        Dictionary with results array and statistics:
        {
            "results": [
                {"query": {...}, "found": true, "data": {...}},
                {"query": {...}, "found": false, "data": null}
            ],
            "total_queries": 5,
            "successful": 3,
            "failed": 2
        }
    """
    results = []
    successful = 0
    failed = 0
    
    # Reduced max_workers to prevent CPU thrashing on 50% quota VPS
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        
        for idx, query_item in enumerate(queries):
            # Convert Pydantic model to dict if needed
            if hasattr(query_item, 'model_dump'):
                query_dict = query_item.model_dump(exclude_none=True)
            elif hasattr(query_item, 'dict'):
                query_dict = query_item.dict(exclude_none=True)
            else:
                query_dict = query_item
            
            # Submit query to executor
            future = executor.submit(
                get_cache_entry,
                team=query_dict.get("team"),
                player=query_dict.get("player"),
                market=query_dict.get("market"),
                sport=query_dict.get("sport"),
                league=query_dict.get("league")
            )
            futures[future] = (idx, query_dict)
        
        # Collect results in order
        results_dict = {}
        for future in as_completed(futures):
            idx, query_dict = futures[future]
            try:
                entry = future.result()
                if entry:
                    results_dict[idx] = {
                        "query": query_dict,
                        "found": True,
                        "data": entry
                    }
                else:
                    results_dict[idx] = {
                        "query": query_dict,
                        "found": False,
                        "data": None
                    }
            except Exception as e:
                results_dict[idx] = {
                    "query": query_dict,
                    "found": False,
                    "data": None
                }
        
        # Sort results by original order
        for idx in sorted(results_dict.keys()):
            result = results_dict[idx]
            results.append(result)
            if result["found"]:
                successful += 1
            else:
                failed += 1
    
    return {
        "results": results,
        "total_queries": len(queries),
        "successful": successful,
        "failed": failed
    }


