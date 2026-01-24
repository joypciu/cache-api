# 🧪 Postman Testing Guide - Rate Limiting API

## 🚀 Quick Start

### 1. Start Server
```bash
cd e:/cache-test/cache-file/cache-api
python test_server.py
```

Server will run at: `http://localhost:6002`

---

## 🔑 Authentication

### Non-Admin Token
```
Bearer 12345
```
- Limited to rate limits
- Can access cache endpoints only

### Admin Token
```
Bearer eternitylabsadmin
```
- No rate limits
- Can access all endpoints including admin stats

---

## 📡 Test Endpoints

### 1. Health Check (No Auth Required)
```
Method: GET
URL: http://localhost:6002/
Headers: None
```

**Expected Response:**
```json
{
  "status": "online",
  "service": "Rate Limit Test API",
  "endpoints": {...},
  "auth": {...}
}
```

---

### 2. Cache Endpoint (200 req/min)
```
Method: GET
URL: http://localhost:6002/cache
Headers:
  Authorization: Bearer 12345
```

**Expected Response (Success):**
```json
{
  "status": "success",
  "endpoint": "/cache",
  "message": "Request successful",
  "data": {"sample": "data"}
}
```

**Expected Response (Rate Limited - after 200 requests):**
```json
{
  "error": "Rate limit exceeded",
  "limit": 200,
  "retry_after": 45
}
```

**Response Headers:**
```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 150
X-RateLimit-Reset: 1706098860
Retry-After: 45
```

---

### 3. Batch Endpoint (20 req/min)
```
Method: POST
URL: http://localhost:6002/cache/batch
Headers:
  Authorization: Bearer 12345
  Content-Type: application/json
Body: {}
```

**Expected Response (Success):**
```json
{
  "status": "success",
  "endpoint": "/cache/batch",
  "message": "Batch request successful"
}
```

**Expected Response (Rate Limited - after 20 requests):**
```json
{
  "error": "Rate limit exceeded",
  "limit": 20,
  "retry_after": 45
}
```

---

### 4. Precision Batch Endpoint (10 req/min)
```
Method: POST
URL: http://localhost:6002/cache/batch/precision
Headers:
  Authorization: Bearer 12345
  Content-Type: application/json
Body: {}
```

**Expected Response (Rate Limited - after 10 requests):**
```json
{
  "error": "Rate limit exceeded",
  "limit": 10,
  "retry_after": 45
}
```

---

## 👨‍💼 Admin Endpoints

### 5. Rate Limit Statistics
```
Method: GET
URL: http://localhost:6002/admin/rate-limits
Headers:
  Authorization: Bearer eternitylabsadmin
```

**Expected Response:**
```json
{
  "timestamp": 1706098800,
  "window_seconds": 60,
  "summary": {
    "total_clients": 2,
    "total_active_requests": 25,
    "limited_clients": 1
  },
  "clients": [
    {
      "identifier": "12345",
      "total_requests": 20,
      "status": "rate_limited",
      "endpoints": {
        "/cache": {
          "requests": 20,
          "limit": 200,
          "remaining": 180,
          "usage_percent": 10.0,
          "status": "normal"
        }
      }
    }
  ]
}
```

---

### 6. URL Access Statistics
```
Method: GET
URL: http://localhost:6002/admin/url-stats
Headers:
  Authorization: Bearer eternitylabsadmin
```

**Expected Response:**
```json
{
  "timestamp": 1706098800,
  "total_endpoints": 3,
  "total_requests": 50,
  "endpoints": [
    {
      "endpoint": "/cache",
      "total_requests": 30,
      "unique_clients": 2,
      "avg_requests_per_client": 15.0,
      "rate_limit": 200,
      "window_seconds": 60
    }
  ]
}
```

---

### 7. Request Statistics
```
Method: GET
URL: http://localhost:6002/admin/request-stats
Headers:
  Authorization: Bearer eternitylabsadmin
```

**Expected Response:**
```json
{
  "timestamp": 1706098800,
  "window_seconds": 60,
  "total_requests": 50,
  "total_clients": 2,
  "total_endpoints": 3,
  "by_endpoint": {
    "/cache": 30,
    "/cache/batch": 15,
    "/cache/batch/precision": 5
  },
  "status": {
    "normal": 1,
    "near_limit": 0,
    "rate_limited": 1
  }
}
```

---

## 🧪 Testing Scenarios

### Scenario 1: Normal Request Flow
1. Send GET to `/cache` with token `12345`
2. Check response status: `200 OK`
3. Check headers for rate limit info
4. Verify `X-RateLimit-Remaining` decreases

### Scenario 2: Hit Rate Limit
1. Use Postman Runner or send 21 requests to `/cache/batch`
2. First 20 should return `200 OK`
3. 21st request should return `429 Too Many Requests`
4. Verify `retry_after` in response

### Scenario 3: Admin Access
1. Use admin token `eternitylabsadmin`
2. Send requests to `/cache` (no limit)
3. Send 100+ requests - all should succeed
4. Check `/admin/rate-limits` to see stats

### Scenario 4: Unauthorized Access
1. Try `/cache` without Authorization header
2. Expected: `401 Unauthorized`
3. Try admin endpoint with non-admin token
4. Expected: `403 Forbidden`

---

## 📊 Postman Collection Template

```json
{
  "info": {
    "name": "Rate Limit API Tests",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "1. Health Check",
      "request": {
        "method": "GET",
        "url": "http://localhost:6002/"
      }
    },
    {
      "name": "2. Cache Endpoint",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer 12345"
          }
        ],
        "url": "http://localhost:6002/cache"
      }
    },
    {
      "name": "3. Admin - Rate Limits",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer eternitylabsadmin"
          }
        ],
        "url": "http://localhost:6002/admin/rate-limits"
      }
    }
  ]
}
```

---

## ✅ Checklist

- [ ] Server running on port 6002
- [ ] Redis running on port 6379
- [ ] Non-admin token works for cache endpoints
- [ ] Rate limiting triggers after limit exceeded
- [ ] 429 status code returned when limited
- [ ] Rate limit headers present in response
- [ ] Admin token bypasses rate limits
- [ ] Admin endpoints return statistics
- [ ] Unauthorized requests return 401
- [ ] Admin-only endpoints return 403 for non-admin

---

## 🐛 Troubleshooting

**Server won't start:**
```bash
# Check if port is in use
netstat -an | grep :6002

# Kill existing process
pkill -f test_server.py
```

**Redis errors:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
redis-server
```

**Database errors:**
```bash
# Recreate databases
cd e:/cache-test/cache-file/cache-api
rm -f uuid_tracking.db
python -c "from uuid_tracking import init_tracking_db; init_tracking_db()"
```
