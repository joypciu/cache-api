# Request Tracking System

## Overview
This system tracks all non-admin user requests with session-based tracking and stores data in JSON format for easy analysis.

## Features

### 1. **Session Management**
- Automatic session creation based on IP address and user agent
- Session persistence across requests
- Session cleanup for old inactive sessions

### 2. **Request Tracking**
- Tracks all non-admin API requests automatically
- Records request details: method, path, query params, IP, response status, response time
- Stores data in JSON format for easy access and analysis

### 3. **Admin Endpoints**
All tracking data is accessible via admin-only endpoints (requires admin token).

## Files Created

1. **request_tracking.py** - Core tracking module
   - Session management
   - Request logging
   - JSON storage

2. **request_logs/** - Directory for tracking data
   - `sessions.json` - Active user sessions
   - `requests.json` - All tracked requests

## API Endpoints

### Admin Endpoints (Require Admin Token)

#### 1. Get Request Logs
```
GET /admin/request-logs
```

**Query Parameters:**
- `session_id` (optional) - Filter by session ID
- `path_filter` (optional) - Filter by request path
- `limit` (default: 100) - Maximum records to return
- `offset` (default: 0) - Pagination offset

**Example:**
```bash
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/request-logs?limit=50"
```

**Response:**
```json
{
  "total": 500,
  "limit": 50,
  "offset": 0,
  "count": 50,
  "requests": [
    {
      "request_id": "abc-123-def-456",
      "session_id": "xyz-789",
      "timestamp": "2026-01-22T10:30:15",
      "method": "GET",
      "path": "/cache",
      "query_params": {"team": "Lakers", "sport": "Basketball"},
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0...",
      "token_masked": "1234...5678",
      "response_status": 200,
      "response_time_ms": 45.2
    }
  ]
}
```

#### 2. Get Sessions Summary
```
GET /admin/sessions
```

**Example:**
```bash
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions"
```

**Response:**
```json
{
  "total_sessions": 25,
  "admin_sessions": 2,
  "non_admin_sessions": 23,
  "total_tracked_requests": 1500,
  "sessions": [
    {
      "session_id": "xyz-789",
      "user_identifier": "user_1",
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0...",
      "token_type": "non-admin",
      "created_at": "2026-01-22T08:00:00",
      "last_activity": "2026-01-22T10:30:15",
      "request_count": 45
    }
  ]
}
```

#### 3. Get Session Details
```
GET /admin/sessions/{session_id}
```

**Example:**
```bash
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions/xyz-789"
```

**Response:**
```json
{
  "session": {
    "session_id": "xyz-789",
    "user_identifier": "user_1",
    "ip_address": "203.0.113.42",
    "token_type": "non-admin",
    "created_at": "2026-01-22T08:00:00",
    "last_activity": "2026-01-22T10:30:15",
    "request_count": 45
  },
  "request_count": 45,
  "recent_requests": [
    {
      "request_id": "abc-123",
      "method": "GET",
      "path": "/cache",
      "timestamp": "2026-01-22T10:30:15"
    }
  ]
}
```

#### 4. Clean Up Old Sessions
```
POST /admin/sessions/cleanup?days_old=7
```

**Query Parameters:**
- `days_old` (default: 7) - Clear sessions older than this many days

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions/cleanup?days_old=7"
```

**Response:**
```json
{
  "status": "success",
  "message": "Sessions older than 7 days have been cleared"
}
```

## How It Works

### 1. Automatic Session Creation
When a non-admin user makes their first request:
- System checks IP + User Agent
- Creates a unique session ID
- Stores session info in `sessions.json`

### 2. Request Tracking
For each non-admin request:
- Middleware intercepts the request
- Records request details (method, path, params, etc.)
- Calculates response time
- Appends to `requests.json`
- Updates session last activity

### 3. Admin Access
Admins can:
- View all non-admin requests
- Filter by session or path
- See session statistics
- View individual session details
- Clean up old sessions

## Data Storage

### sessions.json Structure
```json
{
  "sessions": {
    "session-id-1": {
      "session_id": "session-id-1",
      "user_identifier": "user_1",
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0...",
      "token_type": "non-admin",
      "created_at": "2026-01-22T08:00:00",
      "last_activity": "2026-01-22T10:30:15",
      "request_count": 45
    }
  },
  "last_updated": "2026-01-22T10:30:15"
}
```

### requests.json Structure
```json
{
  "requests": [
    {
      "request_id": "unique-id",
      "session_id": "session-id-1",
      "timestamp": "2026-01-22T10:30:15",
      "method": "GET",
      "path": "/cache",
      "query_params": {"team": "Lakers"},
      "body_data": null,
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0...",
      "token_masked": "1234...5678",
      "response_status": 200,
      "response_time_ms": 45.2
    }
  ],
  "last_updated": "2026-01-22T10:30:15",
  "total_requests": 1500
}
```

## Security

- ✅ Only non-admin requests are tracked (admin requests are not logged)
- ✅ API tokens are masked in logs (shows first 4 and last 4 characters only)
- ✅ All tracking endpoints require admin authentication
- ✅ Sessions are automatically cleaned up after 7 days of inactivity

## Testing

### 1. Make a non-admin request:
```bash
curl -H "Authorization: Bearer 12345" \
  "http://localhost:6002/cache?team=Lakers&sport=Basketball"
```

### 2. View the tracked request:
```bash
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/request-logs?limit=1"
```

### 3. Check sessions:
```bash
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions"
```

## Notes

- Admin requests (using admin token) are **not tracked**
- Only authenticated requests are tracked (requires valid token)
- Sessions persist across server restarts (stored in JSON files)
- Response times are calculated in milliseconds
- All timestamps use ISO 8601 format
