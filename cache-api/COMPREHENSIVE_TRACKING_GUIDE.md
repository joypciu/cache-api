# Comprehensive Request Tracking System

## Overview

The API now includes a comprehensive tracking system that monitors every aspect of user requests and responses. This system automatically detects and logs:

- **URL Access Patterns**: Which URLs are accessed and how many times
- **Null Value Detection**: Every null parameter or field in requests/responses
- **Rate Limit Tracking**: Usage statistics per user/client
- **Request/Response Data**: Complete request and response information
- **Performance Metrics**: Response times and error rates

## Features

### 1. URL Access Tracking

Every URL endpoint is tracked with:
- Total access count
- Last access timestamp
- Access frequency statistics

**Access via**: `GET /admin/url-stats`

**Example Response**:
```json
{
  "status": "success",
  "total_unique_urls": 45,
  "total_accesses": 15234,
  "top_urls": [
    {
      "path": "/cache",
      "access_count": 8542,
      "last_accessed": "2026-01-21 05:30:15"
    }
  ]
}
```

### 2. Null Value Detection and Logging

**Automatically detects and logs null values in**:
- Query parameters (e.g., `?team=null` or `?player=`)
- Request body fields (JSON)
- Response body fields (JSON)
- Nested objects and arrays

**Features**:
- Recursive detection in nested JSON structures
- Field path tracking (e.g., `data.team.players[0].name`)
- Separate logging for request vs response nulls
- Context preservation for debugging

**Access via**: `GET /admin/null-logs`

**Example Response**:
```json
{
  "status": "success",
  "total_records": 234,
  "logs": [
    {
      "id": 234,
      "request_id": 1523,
      "timestamp": "2026-01-21 05:30:15",
      "path": "/cache",
      "client_ip": "203.0.113.42",
      "null_type": "response_field",
      "field_name": "data",
      "field_path": "data.team",
      "context": {
        "location": "json_body",
        "field": "team",
        "path": "data.team",
        "value": null
      }
    }
  ]
}
```

### 3. Rate Limit Tracking

**Tracks per-client usage**:
- Request counts per time window (default: 60 minutes)
- Endpoint-specific usage
- Client identification (IP or API token)
- Historical usage patterns

**Access via**: `GET /admin/rate-limits`

**Example Response (All Clients)**:
```json
{
  "status": "success",
  "stats": [
    {
      "client_identifier": "12ab...cd34",
      "total_requests": 1250,
      "endpoints_accessed": 5,
      "last_request": "2026-01-21 05:30:15"
    }
  ]
}
```

**Example Response (Specific Client)**:
```json
{
  "status": "success",
  "filter": {"client_identifier": "12ab...cd34"},
  "stats": [
    {
      "endpoint": "/cache",
      "total_requests": 890,
      "windows": 15,
      "last_request": "2026-01-21 05:30:15"
    }
  ]
}
```

### 4. Enhanced Request/Response Logging

**Each request is logged with**:
- HTTP method and path
- Query parameters
- Request headers (with sensitive data redacted)
- Request body
- Client IP address
- User agent
- API token used (masked)
- Response status code
- Response body
- Response time (milliseconds)
- Error messages (if any)
- **NEW**: Null parameter flags and details
- **NEW**: Request data summary
- **NEW**: Rate limit information

**Access via**: `GET /admin/request-logs`

### 5. Request Statistics

**Aggregated statistics include**:
- Total request count
- Requests by HTTP method
- Requests by status code
- Top 10 endpoints
- Average response time
- Total error count

**Access via**: `GET /admin/request-stats`

## Database Schema

### Tables

#### 1. `api_requests` (Enhanced)
Main request/response tracking table.

**New Columns**:
- `has_null_params` (INTEGER): 1 if request has null values, 0 otherwise
- `null_params_details` (TEXT): JSON with null parameter details
- `has_null_response` (INTEGER): 1 if response has null values, 0 otherwise
- `null_response_details` (TEXT): JSON with null response details
- `api_token` (TEXT): Masked API token used for the request
- `request_data_summary` (TEXT): Human-readable summary of requested data

#### 2. `url_access_counts` (New)
Tracks URL access frequency.

**Columns**:
- `id`: Primary key
- `path`: URL path (unique)
- `access_count`: Total number of accesses
- `last_accessed`: Timestamp of last access

#### 3. `rate_limit_tracking` (New)
Tracks rate limit usage per client.

**Columns**:
- `id`: Primary key
- `client_identifier`: Client IP or API token (masked)
- `endpoint`: API endpoint accessed
- `request_count`: Number of requests in current window
- `window_start`: Start of current rate limit window
- `last_request`: Timestamp of last request
- `is_blocked`: Whether client is currently blocked

#### 4. `null_value_logs` (New)
Dedicated table for null value tracking.

**Columns**:
- `id`: Primary key
- `request_id`: Foreign key to api_requests
- `timestamp`: When null was detected
- `path`: Request path where null was found
- `client_ip`: Client IP address
- `null_type`: 'request_parameter' or 'response_field'
- `field_name`: Name of the null field
- `field_path`: Full path to the field (e.g., 'data.team.name')
- `context`: JSON with additional context

## API Endpoints

### Admin Endpoints (Require Admin Token)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/request-logs` | GET | View all request/response logs |
| `/admin/request-stats` | GET | View aggregated request statistics |
| `/admin/null-logs` | GET | View all detected null values |
| `/admin/rate-limits` | GET | View rate limit usage per client |
| `/admin/url-stats` | GET | View URL access statistics |
| `/admin/uuid-logs` | GET | View UUID login tracking logs |

### Query Parameters

#### `/admin/request-logs`
- `path`: Filter by request path (partial match)
- `method`: Filter by HTTP method (GET, POST, etc.)
- `client_ip`: Filter by client IP
- `status_code`: Filter by response status
- `limit`: Max records (1-1000, default: 100)
- `offset`: Pagination offset

#### `/admin/null-logs`
- `path`: Filter by request path
- `null_type`: Filter by type ('request_parameter' or 'response_field')
- `limit`: Max records (1-1000, default: 100)
- `offset`: Pagination offset

#### `/admin/rate-limits`
- `client_identifier`: Filter by specific client

#### `/admin/url-stats`
- `limit`: Max URLs to return (1-1000, default: 100)

## How It Works

### Automatic Tracking Middleware

All tracking happens automatically through FastAPI middleware. For every request:

1. **Request Phase**:
   - Captures request details (method, path, params, headers, body)
   - Extracts client IP (with proxy support)
   - Detects null values in parameters
   - Identifies API token (masked for security)
   - Generates request summary

2. **Processing Phase**:
   - Request is processed normally
   - Response is captured

3. **Response Phase**:
   - Detects null values in response
   - Calculates response time
   - Updates URL access count
   - Tracks rate limit usage
   - Logs everything to database
   - Records null values separately if found

### Null Value Detection

The system uses recursive algorithms to detect null values:

```python
# Detects nulls in:
- Query params: ?team=null, ?player=
- JSON fields: {"team": null}
- Nested objects: {"data": {"team": null}}
- Arrays: {"players": [null, "Smith"]}
- Deep nesting: {"a": {"b": {"c": null}}}
```

For each null found, it logs:
- Field name
- Full path to the field
- Location (query, request body, response)
- Context information

### Rate Limit Tracking

Rate limits are tracked per client per endpoint:

```python
# Example tracking:
Client "12ab...cd34" on endpoint "/cache":
- Window 1 (12:00-13:00): 45 requests
- Window 2 (13:00-14:00): 67 requests
- Total: 112 requests across 2 windows
```

## Use Cases

### 1. Debugging Null Responses
Find all requests that returned null data:
```bash
GET /admin/null-logs?null_type=response_field
```

### 2. Monitoring Popular Endpoints
See which endpoints are most used:
```bash
GET /admin/url-stats?limit=10
```

### 3. Tracking User Activity
View all requests from a specific client:
```bash
GET /admin/request-logs?client_ip=203.0.113.42
```

### 4. Detecting Null Parameters
Find requests with missing/null parameters:
```bash
GET /admin/null-logs?null_type=request_parameter
```

### 5. Rate Limit Analysis
Check which clients are making the most requests:
```bash
GET /admin/rate-limits
```

### 6. Performance Monitoring
View response times and error rates:
```bash
GET /admin/request-stats
```

## Security

- Admin endpoints require admin API token
- API tokens are masked in logs (shows first 4 and last 4 chars only)
- Authorization headers are redacted in logs
- Large request/response bodies are truncated (max 10KB)
- Database uses indexes for efficient querying

## Performance Considerations

- Logging happens after response is sent (non-blocking)
- Failed logging doesn't affect request processing
- Indexes on all frequently-queried columns
- Automatic data truncation for large payloads
- Efficient recursive null detection algorithms

## Example Workflows

### Workflow 1: Investigating Failed Requests
```bash
# 1. Find all failed requests
GET /admin/request-logs?status_code=500

# 2. Check if nulls were involved
GET /admin/null-logs?path=/cache

# 3. View detailed request data
GET /admin/request-logs?path=/cache&limit=50
```

### Workflow 2: Monitoring API Usage
```bash
# 1. Check most accessed URLs
GET /admin/url-stats?limit=20

# 2. View rate limits for top clients
GET /admin/rate-limits

# 3. Get overall statistics
GET /admin/request-stats
```

### Workflow 3: Null Value Investigation
```bash
# 1. Find all null values in responses
GET /admin/null-logs?null_type=response_field

# 2. Filter by specific endpoint
GET /admin/null-logs?path=/cache/batch

# 3. Check related requests
GET /admin/request-logs?path=/cache/batch
```

## Migration Notes

### Existing Databases
The system automatically adds new columns and tables when initialized. Existing data is preserved.

### Backward Compatibility
All existing endpoints continue to work. The new tracking features are completely transparent to users.

## Summary

This comprehensive tracking system provides complete visibility into:
- ✅ **URL access patterns** - Track which endpoints are used and how often
- ✅ **Null value detection** - Automatically find and log every null parameter/field
- ✅ **Rate limit tracking** - Monitor usage per client/user
- ✅ **Complete request/response data** - Full audit trail of all API activity
- ✅ **Performance metrics** - Response times and error tracking
- ✅ **Security logging** - All access attempts with client information

All tracking happens automatically with zero configuration needed. Just use the admin endpoints to view the data!
