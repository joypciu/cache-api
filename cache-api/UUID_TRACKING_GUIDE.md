# UUID Login Tracking

## Overview

The Cache API now supports UUID-based authentication with comprehensive tracking of login attempts. Every UUID login is automatically tracked with geo-location data for security and analytics purposes.

## Features

- **UUID Authentication**: Accept login requests using UUID credentials
- **Automatic Tracking**: Every login attempt is logged automatically
- **Geo-Location Detection**: IP-based geo-location tracking including:
  - Country and country code
  - Region/state
  - City
  - Latitude and longitude
  - Timezone
  - ISP information
- **Admin Dashboard**: Admin-only endpoint to view all tracking logs
- **Privacy Aware**: Handles private/localhost IPs gracefully

## Endpoints

### 1. UUID Login Endpoint

**POST** `/auth/uuid`

Authenticates users via UUID and tracks the login attempt.

**No authentication required** - This IS the authentication endpoint.

**Request Body:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "authenticated": true,
  "message": "Login successful - UUID authenticated",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "tracking": {
    "status": "success",
    "message": "UUID login attempt tracked",
    "record_id": 123,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "ip_address": "203.0.113.42",
    "geo_location": {
      "country": "United States",
      "country_code": "US",
      "region": "California",
      "city": "San Francisco",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timezone": "America/Los_Angeles",
      "isp": "Example ISP"
    }
  }
}
```

**Example cURL:**
```bash
curl -X POST "http://localhost:8001/auth/uuid" \
  -H "Content-Type: application/json" \
  -d '{"uuid": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Example JavaScript:**
```javascript
const response = await fetch('http://localhost:8001/auth/uuid', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    uuid: '550e8400-e29b-41d4-a716-446655440000'
  })
});

const data = await response.json();
console.log(data.tracking.geo_location);
```

### 2. Admin: View UUID Login Logs

**GET** `/admin/uuid-logs`

Retrieve tracked UUID login attempts. **Admin authentication required.**

**Headers:**
```
Authorization: Bearer eternitylabsadmin
```

**Query Parameters:**
- `uuid` (optional): Filter logs by specific UUID
- `limit` (optional): Maximum records to return (1-1000, default: 100)
- `offset` (optional): Number of records to skip for pagination (default: 0)

**Response (200 OK):**
```json
{
  "total": 500,
  "limit": 100,
  "offset": 0,
  "count": 100,
  "logs": [
    {
      "id": 123,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "ip_address": "203.0.113.42",
      "timestamp": "2026-01-20 10:30:15",
      "geo_location": {
        "country": "United States",
        "country_code": "US",
        "region": "California",
        "city": "San Francisco",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timezone": "America/Los_Angeles",
        "isp": "Example ISP"
      },
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
    }
  ]
}
```

**Example cURL - Get all logs:**
```bash
curl -X GET "http://localhost:8001/admin/uuid-logs" \
  -H "Authorization: Bearer eternitylabsadmin"
```

**Example cURL - Filter by UUID:**
```bash
curl -X GET "http://localhost:8001/admin/uuid-logs?uuid=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer eternitylabsadmin"
```

**Example cURL - Pagination:**
```bash
curl -X GET "http://localhost:8001/admin/uuid-logs?limit=50&offset=100" \
  -H "Authorization: Bearer eternitylabsadmin"
```

## Database Schema

The tracking system uses a separate SQLite database (`uuid_tracking.db`) with the following schema:

```sql
CREATE TABLE uuid_login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    country TEXT,
    country_code TEXT,
    region TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    timezone TEXT,
    isp TEXT,
    user_agent TEXT,
    geo_data_raw TEXT
);

-- Indexes for performance
CREATE INDEX idx_uuid ON uuid_login_attempts(uuid);
CREATE INDEX idx_timestamp ON uuid_login_attempts(timestamp);
```

## Tracked Information

For each UUID login attempt, the following information is captured:

1. **UUID**: The UUID used for authentication
2. **IP Address**: Client IP (with proxy support via X-Forwarded-For header)
3. **Timestamp**: Exact date and time of login attempt
4. **Geo-Location**:
   - Country and country code
   - Region/state
   - City
   - Latitude and longitude coordinates
   - Timezone
   - ISP (Internet Service Provider)
5. **User Agent**: Browser/client information
6. **Raw Geo Data**: Complete JSON response from geo-location service

## Geo-Location Service

The system uses **ip-api.com** (free tier) for geo-location lookups:
- **Rate Limit**: 45 requests per minute
- **No API key required**
- **Privacy**: Private IPs (localhost, 192.168.x.x, etc.) are handled gracefully

For production environments with higher traffic, consider upgrading to:
- ip-api.com Pro ($13/month for 1M requests)
- MaxMind GeoIP2 (offline database)
- IPinfo.io
- ipgeolocation.io

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Database initialization:**
The tracking database is automatically created when the first UUID login occurs.

## Security Considerations

- **Admin Access**: Only users with the admin token can view tracking logs
- **Data Retention**: Consider implementing log rotation/cleanup for old records
- **Privacy**: Be transparent about tracking with your users
- **IP Privacy**: Localhost and private IPs are marked as such without external lookup

## Example Use Cases

### 1. Security Monitoring
Track suspicious login patterns from specific UUIDs or locations:
```bash
# Get all logins for a specific UUID
curl -X GET "http://localhost:8001/admin/uuid-logs?uuid=SUSPICIOUS-UUID" \
  -H "Authorization: Bearer eternitylabsadmin"
```

### 2. Geographic Analytics
Analyze where your users are logging in from to optimize service locations.

### 3. Compliance
Maintain audit logs for security compliance requirements.

### 4. Fraud Detection
Identify unusual login patterns (e.g., same UUID from multiple countries in short time).

## Testing

**Test UUID login:**
```bash
# Login with a UUID
curl -X POST "http://localhost:8001/auth/uuid" \
  -H "Content-Type: application/json" \
  -d '{"uuid": "test-uuid-12345"}'

# View the tracking log (admin only)
curl -X GET "http://localhost:8001/admin/uuid-logs?uuid=test-uuid-12345" \
  -H "Authorization: Bearer eternitylabsadmin"
```

## Future Enhancements

Potential improvements for this feature:

- [ ] UUID validation/verification against a database
- [ ] Rate limiting per UUID or IP
- [ ] Automatic blocking of suspicious patterns
- [ ] Email notifications for admin on suspicious activity
- [ ] Export logs to CSV/JSON
- [ ] Integration with SIEM systems
- [ ] Two-factor authentication for UUIDs
- [ ] Configurable retention policies
