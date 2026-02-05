"""
Database Viewer for Request Tracking System
View all tracked data directly from the SQLite database
"""

import sqlite3
from datetime import datetime
import os

DB_PATH = "request_tracking.db"

def check_db_exists():
    """Check if database file exists"""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print(f"Current directory: {os.getcwd()}")
        return False
    return True

def view_null_logs(limit=10):
    """View NULL value detection logs"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("NULL VALUE LOGS")
    print("="*80)
    
    cursor.execute("""
        SELECT id, request_id, null_type, field_name, path, 
               field_path, timestamp, client_ip
        FROM null_value_logs
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    if not rows:
        print("\nNo NULL values detected yet.")
    else:
        for row in rows:
            print(f"\n[{row[0]}] {row[6]}")  # ID and timestamp
            print(f"  Request ID: {row[1]}")
            print(f"  Type: {row[2]}")
            print(f"  Field: {row[3]}")
            print(f"  URL Path: {row[4]}")
            print(f"  Field Path: {row[5] or 'N/A'}")
            print(f"  Client: {row[7] or 'N/A'}")
    
    # Get summary
    cursor.execute("SELECT COUNT(*) FROM null_value_logs")
    total = cursor.fetchone()[0]
    print(f"\nTotal NULL values logged: {total}")
    
    conn.close()

def view_url_stats():
    """View URL access statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("URL ACCESS STATISTICS")
    print("="*80)
    
    cursor.execute("""
        SELECT path, access_count, last_accessed
        FROM url_access_counts
        ORDER BY access_count DESC
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("\nNo URL accesses tracked yet.")
    else:
        total_accesses = 0
        for row in rows:
            print(f"\n{row[0]}")
            print(f"  Accesses: {row[1]}")
            print(f"  Last: {row[2]}")
            total_accesses += row[1]
        
        print(f"\nTotal URLs: {len(rows)}")
        print(f"Total Accesses: {total_accesses}")
    
    conn.close()

def view_rate_limits():
    """View rate limit tracking"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("RATE LIMIT TRACKING")
    print("="*80)
    
    cursor.execute("""
        SELECT client_identifier, endpoint, request_count, window_start, last_request
        FROM rate_limit_tracking
        ORDER BY request_count DESC
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("\nNo rate limit data yet.")
    else:
        # Mask client IDs for privacy
        for row in rows:
            client_id = row[0]
            if len(client_id) > 8:
                masked = client_id[:4] + "..." + client_id[-4:]
            else:
                masked = "***"
            
            print(f"\nClient: {masked}")
            print(f"  Endpoint: {row[1]}")
            print(f"  Requests: {row[2]}")
            print(f"  Window: {row[3]}")
            print(f"  Last: {row[4]}")
        
        # Get summary by client
        cursor.execute("""
            SELECT client_identifier, COUNT(DISTINCT endpoint) as endpoints,
                   SUM(request_count) as total_requests
            FROM rate_limit_tracking
            GROUP BY client_identifier
            ORDER BY total_requests DESC
        """)
        
        print("\n" + "-"*80)
        print("Summary by Client:")
        for row in cursor.fetchall():
            client_id = row[0]
            if len(client_id) > 8:
                masked = client_id[:4] + "..." + client_id[-4:]
            else:
                masked = "***"
            print(f"  {masked}: {row[2]} requests across {row[1]} endpoints")
    
    conn.close()

def view_recent_requests(limit=10):
    """View recent API requests"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("RECENT REQUESTS")
    print("="*80)
    
    cursor.execute("""
        SELECT id, method, path, response_status, 
               response_time_ms, has_null_params, client_ip, timestamp
        FROM api_requests
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    if not rows:
        print("\nNo requests logged yet.")
    else:
        for row in rows:
            null_indicator = " [HAS NULLs]" if row[5] else ""
            print(f"\n[{row[0]}] {row[1]} {row[2]}{null_indicator}")
            print(f"  Status: {row[3]} | Time: {row[4]:.2f}ms")
            print(f"  Client: {row[6]}")
            print(f"  Time: {row[7]}")
    
    conn.close()

def view_statistics():
    """View overall statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)
    
    # Total requests
    cursor.execute("SELECT COUNT(*) FROM api_requests")
    total_requests = cursor.fetchone()[0]
    
    # Average response time
    cursor.execute("SELECT AVG(response_time_ms) FROM api_requests")
    avg_response = cursor.fetchone()[0] or 0
    
    # Requests with errors
    cursor.execute("SELECT COUNT(*) FROM api_requests WHERE response_status >= 400")
    error_count = cursor.fetchone()[0]
    
    # Requests with NULLs
    cursor.execute("SELECT COUNT(*) FROM api_requests WHERE has_null_params = 1 OR has_null_response = 1")
    null_count_result = cursor.fetchone()
    null_count = null_count_result[0] if null_count_result else 0
    
    # Method breakdown
    cursor.execute("""
        SELECT method, COUNT(*) as count
        FROM api_requests
        GROUP BY method
        ORDER BY count DESC
    """)
    methods = cursor.fetchall()
    
    # Top endpoints
    cursor.execute("""
        SELECT path, COUNT(*) as count
        FROM api_requests
        GROUP BY path
        ORDER BY count DESC
        LIMIT 5
    """)
    top_endpoints = cursor.fetchall()
    
    print(f"\nTotal Requests: {total_requests}")
    print(f"Average Response Time: {avg_response:.2f}ms")
    print(f"Error Responses: {error_count}")
    print(f"Requests with NULLs: {null_count}")
    
    print("\nMethods:")
    for method, count in methods:
        print(f"  {method}: {count}")
    
    print("\nTop Endpoints:")
    for endpoint, count in top_endpoints:
        print(f"  {endpoint}: {count}")
    
    conn.close()

def export_data_to_csv():
    """Export all tracking data to CSV files"""
    import csv
    
    conn = sqlite3.connect(DB_PATH)
    
    # Export NULL logs
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM null_value_logs")
    with open('null_logs_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Request ID', 'Timestamp', 'Path', 'Client IP', 
                        'Type', 'Field', 'Field Path', 'Context'])
        writer.writerows(cursor.fetchall())
    print("\nExported: null_logs_export.csv")
    
    # Export URL stats
    cursor.execute("SELECT * FROM url_access_counts")
    with open('url_stats_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Path', 'Access Count', 'Last Accessed'])
        writer.writerows(cursor.fetchall())
    print("Exported: url_stats_export.csv")
    
    # Export rate limits
    cursor.execute("SELECT * FROM rate_limit_tracking")
    with open('rate_limits_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Client Identifier', 'Endpoint', 'Count', 'Window Start', 'Last Request', 'Is Blocked'])
        writer.writerows(cursor.fetchall())
    print("Exported: rate_limits_export.csv")
    
    # Export requests
    cursor.execute("SELECT * FROM api_requests")
    with open('requests_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Method', 'Endpoint', 'Status', 'Response Time', 
                        'Has NULLs', 'Client', 'Summary', 'Request Data', 
                        'Response Data', 'Created'])
        writer.writerows(cursor.fetchall())
    print("Exported: requests_export.csv")
    
    conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TRACKING DATABASE VIEWER")
    print("="*80)
    print(f"Database: {os.path.abspath(DB_PATH)}")
    
    if not check_db_exists():
        exit(1)
    
    # Show all data
    view_null_logs(10)
    view_url_stats()
    view_rate_limits()
    view_recent_requests(10)
    view_statistics()
    
    # Ask to export
    print("\n" + "="*80)
    print("Export Options:")
    print("  1. View data above (done)")
    print("  2. Export to CSV files")
    print("="*80)
    
    try:
        choice = input("\nExport to CSV? (y/n): ").strip().lower()
        if choice == 'y':
            export_data_to_csv()
            print("\nCSV files created in current directory.")
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    
    print("\n" + "="*80)
    print("Database verification complete!")
    print("="*80 + "\n")
