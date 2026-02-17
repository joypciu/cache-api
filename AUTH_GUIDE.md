# Cache API Authentication Guide

## Overview

The Cache API is now protected with token-based authentication. All endpoints (except the root `/` endpoint) require a valid API token to access.

## Setup

### 1. Configure API Tokens

Copy the example environment file and set your tokens:

```bash
cp .env.example .env
```

Edit `.env` and set at least one API token:

```bash
# Primary API token (required)
API_TOKEN=your-secure-token-here
```

You can configure up to 4 different tokens for different clients:

```bash
API_TOKEN=sk_live_primary_token_123
API_TOKEN_1=sk_live_service_a_456
API_TOKEN_2=sk_live_service_b_789
API_TOKEN_3=sk_live_service_c_012
```

### 2. Generate Secure Tokens

For production, use strong random tokens. You can generate them using:

**Python:**
```python
import secrets
token = secrets.token_urlsafe(32)
print(f"API_TOKEN={token}")
```

**PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**OpenSSL:**
```bash
openssl rand -base64 32
```

### 3. Install Dependencies

Make sure to install the updated requirements:

```bash
pip install -r requirements.txt
```

## Using the API

### Authentication Header

All protected endpoints require the `Authorization` header with a Bearer token:

```
Authorization: Bearer your-api-token-here
```

### Examples

#### Using curl:

```bash
# Health check
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/health

# Get cache entry
curl -H "Authorization: Bearer your-api-token-here" \
  "http://localhost:8001/cache?team=Lakers&sport=Basketball"

# Batch query
curl -X POST \
  -H "Authorization: Bearer your-api-token-here" \
  -H "Content-Type: application/json" \
  -d '{"team": ["Lakers", "Warriors"], "sport": "Basketball"}' \
  http://localhost:8001/cache/batch
```

#### Using Postman:

**🔑 Best Practice: Set Token Once for All Requests**

Instead of adding the token to each individual request, set it **once at the collection level**:

1. Create or select a **Collection** for your Cache API requests
2. Click on the collection name → **Authorization** tab
3. Select **Type**: `Bearer Token`
4. In the **Token** field, paste your token value: `your-api-token-here`
5. Save the collection

**✅ Now ALL requests in this collection will automatically use this token!**

You never need to enter it again for any request in that collection - Postman remembers it.

---

**Method 1: Using Authorization Tab (Per-Request)**

If you prefer to set it per request:

1. Open your request in Postman
2. Go to the **Authorization** tab
3. Select **Type**: `Bearer Token`
4. In the **Token** field, paste your token value:
   ```
   your-api-token-here
   ```
   ⚠️ **Important**: Enter ONLY the token value, **NOT** "Bearer your-token". Postman adds "Bearer" automatically.
   
**Token Persistence**: Once set, the token stays saved with this request. You don't need to re-enter it for each query.

**Method 2: Using Headers Tab (Manual)**

1. Go to the **Headers** tab
2. Add a new header:
   - **Key**: `Authorization`
   - **Value**: `Bearer your-api-token-here`
   
   ⚠️ **Important**: When using Headers tab, you MUST include "Bearer " prefix.

**Example Request in Postman:**

- **URL**: `http://localhost:8001/cache`
- **Method**: `GET`
- **Authorization**: Bearer Token → `sk_live_a1b2c3d4e5f6g7h8i9j0`
- **Params**: 
  - `team`: `Lakers`
  - `sport`: `Basketball`

**Batch Request Example:**

- **URL**: `http://localhost:8001/cache/batch`
- **Method**: `POST`
- **Authorization**: Bearer Token → `sk_live_a1b2c3d4e5f6g7h8i9j0`
- **Body** (raw JSON):
  ```json
  {
    "team": ["Lakers", "Warriors"],
    "sport": "Basketball"
  }
  ```

#### Using Python requests:

```python
import requests

API_URL = "http://localhost:8001"
API_TOKEN = "your-api-token-here"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# Health check
response = requests.get(f"{API_URL}/health", headers=headers)
print(response.json())

# Get cache entry
params = {"team": "Lakers", "sport": "Basketball"}
response = requests.get(f"{API_URL}/cache", headers=headers, params=params)
print(response.json())

# Batch query
data = {
    "team": ["Lakers", "Warriors"],
    "sport": "Basketball"
}
response = requests.post(f"{API_URL}/cache/batch", headers=headers, json=data)
print(response.json())
```

#### Using JavaScript/TypeScript:

```javascript
const API_URL = "http://localhost:8001";
const API_TOKEN = "your-api-token-here";

const headers = {
    "Authorization": `Bearer ${API_TOKEN}`,
    "Content-Type": "application/json"
};

// Health check
fetch(`${API_URL}/health`, { headers })
    .then(res => res.json())
    .then(data => console.log(data));

// Get cache entry
fetch(`${API_URL}/cache?team=Lakers&sport=Basketball`, { headers })
    .then(res => res.json())
    .then(data => console.log(data));

// Batch query
fetch(`${API_URL}/cache/batch`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
        team: ["Lakers", "Warriors"],
        sport: "Basketball"
    })
})
    .then(res => res.json())
    .then(data => console.log(data));
```

## Protected Endpoints

All endpoints except `/` (root) require authentication:

- ✅ `GET /` - Public (health status)
- 🔒 `GET /health` - Requires auth
- 🔒 `GET /cache/stats` - Requires auth
- 🔒 `GET /cache` - Requires auth
- 🔒 `POST /cache/batch` - Requires auth
- 🔒 `POST /cache/batch/precision` - Requires auth
- 🔒 `DELETE /cache/clear` - Requires auth
- 🔒 `DELETE /cache/invalidate` - Requires auth

## Error Responses

### 401 Unauthorized
Returned when the token is invalid or missing:

```json
{
  "detail": "Invalid or expired API token"
}
```

### 500 Internal Server Error
Returned when no tokens are configured:

```json
{
  "detail": "No API tokens configured. Please set API_TOKEN in environment variables."
}
```

## Security Best Practices

1. **Never commit `.env` to version control** - it contains sensitive tokens
2. **Use different tokens for different environments** (development, staging, production)
3. **Rotate tokens regularly** - especially if they may have been compromised
4. **Use HTTPS in production** - to prevent token interception
5. **Keep tokens long and random** - at least 32 characters
6. **Monitor API usage** - track which tokens are being used
7. **Revoke compromised tokens immediately** - by removing them from `.env` and restarting the service

## Troubleshooting

### "No API tokens configured"

Make sure you have:
1. Created a `.env` file from `.env.example`
2. Set at least one `API_TOKEN=...` value
3. Restarted the API service after updating `.env`

### "Invalid or expired API token"

Check that:
1. The token in your request matches one of the tokens in `.env`
2. There are no extra spaces or characters in the token
3. You're using the correct Authorization header format: `Bearer <token>`

### Token not working after update

Restart the API service to reload environment variables:

```bash
# If running directly
python main.py

# If running as a service
sudo systemctl restart cache-api
```
