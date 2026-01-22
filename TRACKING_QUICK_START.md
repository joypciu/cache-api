# Request Tracking Implementation - Quick Start

## ✅ What Was Implemented

I've implemented a complete **request tracking system** for non-admin users with session-based tracking and JSON storage.

## 📁 Files Created

1. **cache-api/request_tracking.py** - Core tracking module
2. **cache-api/REQUEST_TRACKING_README.md** - Complete documentation
3. **test_request_tracking.py** - Test script to verify functionality
4. **view_tracking_data.py** - Interactive viewer for tracking data

## 📁 Files Modified

1. **cache-api/main.py** - Added middleware and admin endpoints

## 🎯 Key Features

### 1. Automatic Session Tracking
- Sessions are created automatically based on IP address and user agent
- Each session gets a unique ID
- Sessions persist across requests and server restarts

### 2. Request Logging (Non-Admin Only)
- All non-admin requests are automatically tracked
- Captured data includes:
  - Request method, path, and query parameters
  - IP address and user agent
  - Response status and time (in milliseconds)
  - Timestamp
  - Session ID

### 3. JSON Storage
All data is stored in human-readable JSON files:
- `cache-api/request_logs/sessions.json` - Active sessions
- `cache-api/request_logs/requests.json` - All logged requests

### 4. Admin Endpoints
New endpoints for viewing tracking data (admin-only):
- `GET /admin/request-logs` - View all request logs
- `GET /admin/sessions` - View all active sessions
- `GET /admin/sessions/{session_id}` - View specific session details
- `POST /admin/sessions/cleanup` - Clean up old sessions

## 🚀 How to Use

### Step 1: Start the API Server
```bash
cd cache-api
python main.py
```

### Step 2: Make Some Non-Admin Requests
```bash
# Using non-admin token (12345)
curl -H "Authorization: Bearer 12345" \
  "http://localhost:6002/cache?team=Lakers&sport=Basketball"
```

### Step 3: View Tracking Data

#### Option A: Use the Admin API
```bash
# View all sessions
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions"

# View request logs
curl -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/request-logs?limit=10"
```

#### Option B: Use the Interactive Viewer
```bash
python view_tracking_data.py
```

#### Option C: View JSON Files Directly
```bash
# Sessions
cat cache-api/request_logs/sessions.json

# Requests
cat cache-api/request_logs/requests.json
```

### Step 4: Run Tests (Optional)
```bash
python test_request_tracking.py
```

## 📊 Example Data

### Session Data (sessions.json)
```json
{
  "sessions": {
    "abc-123-def-456": {
      "session_id": "abc-123-def-456",
      "user_identifier": "user_1",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0...",
      "token_type": "non-admin",
      "created_at": "2026-01-22T10:00:00",
      "last_activity": "2026-01-22T10:30:15",
      "request_count": 25
    }
  }
}
```

### Request Data (requests.json)
```json
{
  "requests": [
    {
      "request_id": "xyz-789",
      "session_id": "abc-123-def-456",
      "timestamp": "2026-01-22T10:30:15",
      "method": "GET",
      "path": "/cache",
      "query_params": {"team": "Lakers", "sport": "Basketball"},
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0...",
      "token_masked": "1234...5678",
      "response_status": 200,
      "response_time_ms": 45.2
    }
  ]
}
```

## 🔒 Security Features

✅ **Admin requests are NOT tracked** - Only non-admin users are monitored
✅ **API tokens are masked** - Only first 4 and last 4 characters shown
✅ **Admin-only access** - All tracking endpoints require admin token
✅ **Automatic cleanup** - Old sessions can be cleared with cleanup endpoint

## 📈 Use Cases

- **Monitor API usage** - See what non-admin users are requesting
- **Track user behavior** - Analyze request patterns and frequency
- **Debug issues** - Review request history for troubleshooting
- **Security auditing** - Track who accessed what and when
- **Performance analysis** - Analyze response times and slow endpoints

## 🔄 Maintenance

### Clean Up Old Sessions
```bash
# Clean sessions older than 7 days (default)
curl -X POST -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions/cleanup"

# Clean sessions older than 30 days
curl -X POST -H "Authorization: Bearer eternitylabsadmin" \
  "http://localhost:6002/admin/sessions/cleanup?days_old=30"
```

### Backup Tracking Data
```bash
# Create backup directory
mkdir -p backups

# Backup tracking data
cp -r cache-api/request_logs backups/request_logs_$(date +%Y%m%d)
```

## 📝 Notes

- Sessions are identified by IP + User Agent combination
- Response times are in milliseconds
- All timestamps use ISO 8601 format
- JSON files are automatically created on first use
- Data persists across server restarts

## 🎉 Summary

You now have a complete request tracking system that:
- ✅ Automatically tracks all non-admin user requests
- ✅ Creates and manages sessions
- ✅ Stores data in easy-to-read JSON format
- ✅ Provides admin endpoints for viewing data
- ✅ Includes test and viewer scripts
- ✅ Respects admin privacy (admin requests not tracked)
