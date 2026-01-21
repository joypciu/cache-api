"""
Request-Response Tracking Module
Logs all incoming API requests and outgoing responses for monitoring and debugging.
"""

import sqlite3
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

# Database file path for request tracking
REQUEST_TRACKING_DB_PATH = os.path.join(os.path.dirname(__file__), "request_tracking.db")


def init_request_tracking_db():
    """Initialize the request-response tracking database"""
    conn = sqlite3.connect(REQUEST_TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    # Create request-response tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            query_params TEXT,
            client_ip TEXT,
            user_agent TEXT,
            headers TEXT,
            request_body TEXT,
            response_status INTEGER,
            response_body TEXT,
            response_time_ms REAL,
            error_message TEXT
        )
    """)
    
    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON api_requests(timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_path 
        ON api_requests(path)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status 
        ON api_requests(response_status)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_ip 
        ON api_requests(client_ip)
    """)
    
    conn.commit()
    conn.close()
    print(f"Request tracking database initialized at: {REQUEST_TRACKING_DB_PATH}")


def log_api_request(
    method: str,
    path: str,
    query_params: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    request_body: Optional[str] = None,
    response_status: Optional[int] = None,
    response_body: Optional[str] = None,
    response_time_ms: Optional[float] = None,
    error_message: Optional[str] = None
) -> int:
    """
    Log an API request-response pair to the tracking database.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path/endpoint
        query_params: Query parameters as string
        client_ip: Client IP address
        user_agent: User agent string
        headers: Request headers as dictionary
        request_body: Request body as string
        response_status: HTTP response status code
        response_body: Response body as string
        response_time_ms: Response time in milliseconds
        error_message: Error message if any
        
    Returns:
        Record ID of the inserted log entry
    """
    # Initialize DB if it doesn't exist
    if not os.path.exists(REQUEST_TRACKING_DB_PATH):
        init_request_tracking_db()
    
    conn = sqlite3.connect(REQUEST_TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Convert headers dict to JSON string
        headers_json = json.dumps(headers) if headers else None
        
        # Insert tracking record
        cursor.execute("""
            INSERT INTO api_requests 
            (method, path, query_params, client_ip, user_agent, headers, 
             request_body, response_status, response_body, response_time_ms, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            method,
            path,
            query_params,
            client_ip,
            user_agent,
            headers_json,
            request_body,
            response_status,
            response_body,
            response_time_ms,
            error_message
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        return record_id
        
    except Exception as e:
        conn.rollback()
        print(f"Failed to log API request: {str(e)}")
        return -1
    finally:
        conn.close()


def get_request_logs(
    path: Optional[str] = None,
    method: Optional[str] = None,
    client_ip: Optional[str] = None,
    status_code: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Retrieve API request-response logs with optional filtering.
    
    Args:
        path: Filter by request path
        method: Filter by HTTP method
        client_ip: Filter by client IP
        status_code: Filter by response status code
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        Dictionary with logs and metadata
    """
    if not os.path.exists(REQUEST_TRACKING_DB_PATH):
        init_request_tracking_db()
        return {
            'status': 'success',
            'total_records': 0,
            'logs': []
        }
    
    conn = sqlite3.connect(REQUEST_TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Build dynamic query based on filters
        where_clauses = []
        params = []
        
        if path:
            where_clauses.append("path LIKE ?")
            params.append(f"%{path}%")
        
        if method:
            where_clauses.append("method = ?")
            params.append(method.upper())
        
        if client_ip:
            where_clauses.append("client_ip = ?")
            params.append(client_ip)
        
        if status_code:
            where_clauses.append("response_status = ?")
            params.append(status_code)
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM api_requests {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get records
        query = f"""
            SELECT id, timestamp, method, path, query_params, client_ip, 
                   user_agent, headers, request_body, response_status, 
                   response_body, response_time_ms, error_message
            FROM api_requests 
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(query, params)
        
        logs = []
        for row in cursor.fetchall():
            # Parse headers JSON
            headers = None
            if row[7]:
                try:
                    headers = json.loads(row[7])
                except:
                    headers = row[7]
            
            logs.append({
                'id': row[0],
                'timestamp': row[1],
                'method': row[2],
                'path': row[3],
                'query_params': row[4],
                'client_ip': row[5],
                'user_agent': row[6],
                'headers': headers,
                'request_body': row[8],
                'response_status': row[9],
                'response_body': row[10],
                'response_time_ms': row[11],
                'error_message': row[12]
            })
        
        return {
            'status': 'success',
            'total_records': total_count,
            'returned_records': len(logs),
            'limit': limit,
            'offset': offset,
            'logs': logs
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to retrieve request logs: {str(e)}',
            'logs': []
        }
    finally:
        conn.close()


def get_request_statistics() -> Dict[str, Any]:
    """
    Get statistics about API requests.
    
    Returns:
        Dictionary with various statistics
    """
    if not os.path.exists(REQUEST_TRACKING_DB_PATH):
        return {
            'status': 'error',
            'message': 'No tracking data available'
        }
    
    conn = sqlite3.connect(REQUEST_TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Total requests
        cursor.execute("SELECT COUNT(*) FROM api_requests")
        total_requests = cursor.fetchone()[0]
        
        # Requests by method
        cursor.execute("""
            SELECT method, COUNT(*) as count 
            FROM api_requests 
            GROUP BY method 
            ORDER BY count DESC
        """)
        by_method = [{'method': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Requests by status code
        cursor.execute("""
            SELECT response_status, COUNT(*) as count 
            FROM api_requests 
            WHERE response_status IS NOT NULL
            GROUP BY response_status 
            ORDER BY count DESC
        """)
        by_status = [{'status': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Top endpoints
        cursor.execute("""
            SELECT path, COUNT(*) as count 
            FROM api_requests 
            GROUP BY path 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_endpoints = [{'path': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Average response time
        cursor.execute("""
            SELECT AVG(response_time_ms) 
            FROM api_requests 
            WHERE response_time_ms IS NOT NULL
        """)
        avg_response_time = cursor.fetchone()[0]
        
        # Requests with errors
        cursor.execute("""
            SELECT COUNT(*) 
            FROM api_requests 
            WHERE error_message IS NOT NULL
        """)
        error_count = cursor.fetchone()[0]
        
        return {
            'status': 'success',
            'total_requests': total_requests,
            'by_method': by_method,
            'by_status_code': by_status,
            'top_endpoints': top_endpoints,
            'average_response_time_ms': round(avg_response_time, 2) if avg_response_time else 0,
            'error_count': error_count
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get statistics: {str(e)}'
        }
    finally:
        conn.close()
