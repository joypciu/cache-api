"""
Request Tracking Module
Tracks all API requests from non-admin users with session-based tracking.
Stores data in SQLite database for reliability and concurrency.
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import geoip2.database

# Directory to store tracking data
TRACKING_DIR = os.path.join(os.path.dirname(__file__), "request_logs")
DB_FILE = os.path.join(TRACKING_DIR, "requests.db")
GEOIP_DB_PATH = os.path.join(os.path.dirname(__file__), "geoip", "GeoLite2-City.mmdb")

def get_location_from_ip(ip_address: str) -> Optional[str]:
    """Resolve IP address to city/country using GeoIP2."""
    if not os.path.exists(GEOIP_DB_PATH):
        return None
        
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.city(ip_address)
            city = response.city.name
            country = response.country.name
            
            if city and country:
                return f"{city}, {country}"
            elif country:
                return country
            return None
    except Exception:
        return None

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_tracking():
    """Initialize tracking directory and database schemas."""
    # Create directory if it doesn't exist
    os.makedirs(TRACKING_DIR, exist_ok=True)
    
    with get_db_connection() as conn:
        # Create sessions table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_identifier TEXT,
            ip_address TEXT,
            user_agent TEXT,
            token_type TEXT,
            created_at TEXT,
            last_activity TEXT,
            request_count INTEGER DEFAULT 0
        )
        ''')
        
        # Create requests table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            method TEXT,
            path TEXT,
            query_params TEXT,
            body_data TEXT,
            ip_address TEXT,
            user_agent TEXT,
            token_masked TEXT,
            uuid TEXT,
            response_status INTEGER,
            response_time_ms REAL,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        # Create indices for better query performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_session_id ON requests(session_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity)')
        
        # Create missing_items table for tracking data not found in cache/database
        conn.execute('''
        CREATE TABLE IF NOT EXISTS missing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            item_type TEXT,
            item_value TEXT,
            endpoint TEXT,
            query_params TEXT,
            first_seen TEXT,
            last_seen TEXT,
            occurrence_count INTEGER DEFAULT 1,
            UNIQUE(item_type, item_value, endpoint)
        )
        ''')
        
        # Create indices for missing items
        conn.execute('CREATE INDEX IF NOT EXISTS idx_missing_items_timestamp ON missing_items(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_missing_items_type ON missing_items(item_type)')

    print(f"Request tracking initialized. Database: {DB_FILE}")

def create_session(user_identifier: str, ip_address: str, user_agent: str, token_type: str) -> str:
    """
    Create a new session for a user.
    """
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    with get_db_connection() as conn:
        conn.execute('''
        INSERT INTO sessions (
            session_id, user_identifier, ip_address, user_agent, token_type, 
            created_at, last_activity, request_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (session_id, user_identifier, ip_address, user_agent, token_type, now, now))
    
    return session_id

def get_or_create_session(token: str, ip_address: str, user_agent: str, user_identifier: Optional[str] = None) -> str:
    """
    Get existing session or create a new one based on token and IP.
    """
    # Determine token type (attempt import, fallback to check)
    try:
        from main import ADMIN_KEY
        token_type = "admin" if token == ADMIN_KEY else "non-admin"
    except ImportError:
        token_type = "non-admin" 

    with get_db_connection() as conn:
        # Check for existing session matching IP and User Agent
        cursor = conn.execute('''
        SELECT session_id FROM sessions 
        WHERE ip_address = ? AND user_agent = ? 
        ORDER BY last_activity DESC LIMIT 1
        ''', (ip_address, user_agent))
        
        row = cursor.fetchone()
        
        if row:
            session_id = row['session_id']
            # Update last activity
            conn.execute('''
            UPDATE sessions SET last_activity = ? WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            return session_id

    # Create new session if not found
    identifier = user_identifier or f"user_unknown"
    return create_session(identifier, ip_address, user_agent, token_type)

def track_request(
    session_id: str,
    method: str,
    path: str,
    query_params: Dict[str, Any],
    token: str,
    ip_address: str,
    user_agent: str,
    response_status: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    body_data: Optional[Dict[str, Any]] = None,
    uuid: Optional[str] = None
):
    """
    Track an API request.
    """
    try:
        from main import ADMIN_KEY
        is_admin = (token == ADMIN_KEY)
    except ImportError:
        is_admin = False

    # Only track non-admin requests
    if is_admin:
        return

    # Mask token appropriately
    uuid_str = uuid
    if uuid_str is None:
        if token.startswith("uuid:"):
            token_display = token
            uuid_str = token[5:]
        elif len(token) > 8:
            token_display = f"{token[:4]}...{token[-4:]}"
        else:
            token_display = "***"
    else:
        # User requested to see the non-admin token (masked for security, but identifiable)
        if len(token) > 8:
            token_display = f"{token[:4]}...{token[-4:]}"
        else:
            token_display = token # Short tokens shown fully

    # Location lookup
    location = get_location_from_ip(ip_address)

    # Serialize complex types to JSON
    query_params_json = json.dumps(query_params) if query_params else "{}"
    body_data_json = json.dumps(body_data) if body_data else "{}"

    import uuid as uuid_lib # Safety alias
    request_id = str(uuid_lib.uuid4())
    timestamp = datetime.now().isoformat()

    try:
        with get_db_connection() as conn:
            # Add columns if they don't exist (Migration)
            try:
                conn.execute("ALTER TABLE requests ADD COLUMN location TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Insert request
            conn.execute('''
            INSERT INTO requests (
                request_id, session_id, timestamp, method, path, query_params,
                body_data, ip_address, user_agent, token_masked, uuid,
                response_status, response_time_ms, location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_id, session_id, timestamp, method, path, query_params_json,
                body_data_json, ip_address, user_agent, token_display, uuid_str,
                response_status, response_time_ms, location
            ))

            # Update session stats
            conn.execute('''
            UPDATE sessions
            SET request_count = request_count + 1, last_activity = ?
            WHERE session_id = ?
            ''', (timestamp, session_id))

    except Exception as e:
        print(f"Error tracking request: {e}")

def get_request_logs(
    session_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    path_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve request logs with optional filtering."""
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM requests WHERE 1=1"
            params = []
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            if path_filter:
                query += " AND path LIKE ?"
                params.append(f"%{path_filter}%")
                
            # Count total
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            total = conn.execute(count_query, params).fetchone()[0]
            
            # Get data (sort by timestamp DESC for logs)
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            requests = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON fields
            for req in requests:
                try:
                    req['query_params'] = json.loads(req['query_params'])
                    req['body_data'] = json.loads(req['body_data'])
                except:
                    pass

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(requests),
                "requests": requests
            }
    except Exception as e:
        print(f"Error retrieving request logs: {e}")
        return {"total": 0, "requests": [], "error": str(e)}

def get_session_summary() -> Dict[str, Any]:
    """Get summary of all active sessions."""
    try:
        with get_db_connection() as conn:
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            admin_sessions = conn.execute("SELECT COUNT(*) FROM sessions WHERE token_type = 'admin'").fetchone()[0]
            non_admin_sessions = total_sessions - admin_sessions
            total_requests = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            
            sessions_cursor = conn.execute("SELECT * FROM sessions ORDER BY last_activity DESC")
            sessions = [dict(row) for row in sessions_cursor.fetchall()]
            
            return {
                "total_sessions": total_sessions,
                "admin_sessions": admin_sessions,
                "non_admin_sessions": non_admin_sessions,
                "total_tracked_requests": total_requests,
                "sessions": sessions
            }
    except Exception as e:
        print(f"Error getting session summary: {e}")
        return {}

def get_session_details(session_id: str) -> Optional[Dict[str, Any]]:
    """Get details for a specific session."""
    try:
        with get_db_connection() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if not session:
                return None
            
            # We must convert row to dict
            session_dict = dict(session)
            
            # Get recent requests
            logs = get_request_logs(session_id=session_id, limit=10)
                
            return {
                "session": session_dict,
                "request_count": session_dict['request_count'],
                "recent_requests": logs['requests']
            }
    except Exception as e:
        print(f"Error getting session details: {e}")
        return None

def clear_old_sessions(days_old: int = 7):
    """Clear sessions older than specified days."""
    try:
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        with get_db_connection() as conn:
            conn.execute("DELETE FROM requests WHERE session_id IN (SELECT session_id FROM sessions WHERE last_activity < ?)", (cutoff_date,))
            conn.execute("DELETE FROM sessions WHERE last_activity < ?", (cutoff_date,))
            print(f"Cleared old sessions before {cutoff_date}")
    except Exception as e:
        print(f"Error clearing old sessions: {e}")

def track_missing_item(
    session_id: str,
    item_type: str,
    item_value: str,
    endpoint: str,
    query_params: Optional[Dict[str, Any]] = None
):
    """
    Track an item that was not found in cache or database.
    
    Args:
        session_id: Session identifier
        item_type: Type of missing item (e.g., 'market', 'team', 'player', 'league')
        item_value: The value that was searched for
        endpoint: The API endpoint that was called
        query_params: Query parameters from the request
    """
    try:
        timestamp = datetime.now().isoformat()
        query_params_json = json.dumps(query_params) if query_params else "{}"
        
        with get_db_connection() as conn:
            # Check if this item was already tracked
            cursor = conn.execute('''
            SELECT id, occurrence_count FROM missing_items 
            WHERE item_type = ? AND item_value = ? AND endpoint = ?
            ''', (item_type, item_value, endpoint))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                conn.execute('''
                UPDATE missing_items 
                SET last_seen = ?, occurrence_count = occurrence_count + 1, session_id = ?
                WHERE id = ?
                ''', (timestamp, session_id, existing['id']))
            else:
                # Insert new record
                conn.execute('''
                INSERT INTO missing_items (
                    session_id, timestamp, item_type, item_value, endpoint,
                    query_params, first_seen, last_seen, occurrence_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    session_id, timestamp, item_type, item_value, endpoint,
                    query_params_json, timestamp, timestamp
                ))
                
    except Exception as e:
        print(f"Error tracking missing item: {e}")

def get_missing_items(
    item_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = 'last_seen'  # 'last_seen', 'occurrence_count', 'first_seen'
) -> Dict[str, Any]:
    """
    Retrieve missing items with optional filtering.
    
    Args:
        item_type: Filter by item type (e.g., 'market', 'team', 'player')
        limit: Maximum number of results
        offset: Offset for pagination
        sort_by: Field to sort by
        
    Returns:
        Dictionary with missing items data
    """
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM missing_items WHERE 1=1"
            params = []
            
            if item_type:
                query += " AND item_type = ?"
                params.append(item_type)
            
            # Count total
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            total = conn.execute(count_query, params).fetchone()[0]
            
            # Sort
            valid_sorts = ['last_seen', 'occurrence_count', 'first_seen', 'timestamp']
            if sort_by not in valid_sorts:
                sort_by = 'last_seen'
            
            query += f" ORDER BY {sort_by} DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            items = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON fields
            for item in items:
                try:
                    item['query_params'] = json.loads(item['query_params'])
                except:
                    item['query_params'] = {}
            
            # Get summary statistics
            stats_cursor = conn.execute('''
            SELECT 
                item_type,
                COUNT(*) as count,
                SUM(occurrence_count) as total_occurrences
            FROM missing_items
            GROUP BY item_type
            ''')
            
            stats_by_type = {row['item_type']: {
                'unique_count': row['count'],
                'total_occurrences': row['total_occurrences']
            } for row in stats_cursor.fetchall()}
            
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "items": items,
                "stats_by_type": stats_by_type
            }
    except Exception as e:
        print(f"Error retrieving missing items: {e}")
        return {"total": 0, "items": [], "stats_by_type": {}, "error": str(e)}

def clear_missing_items(item_type: Optional[str] = None):
    """
    Clear missing items records.
    
    Args:
        item_type: If specified, only clear items of this type
    """
    try:
        with get_db_connection() as conn:
            if item_type:
                conn.execute("DELETE FROM missing_items WHERE item_type = ?", (item_type,))
                print(f"Cleared missing items of type: {item_type}")
            else:
                conn.execute("DELETE FROM missing_items")
                print("Cleared all missing items")
    except Exception as e:
        print(f"Error clearing missing items: {e}")

# Initialize tracking on module import
init_tracking()
