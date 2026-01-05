# Cache API with Redis

Sports betting cache normalization service with Redis caching layer.

## Redis Setup

### Installation (Ubuntu/WSL)
```bash
sudo apt install redis-server -y
sudo service redis-server start
redis-cli ping  # Should return PONG
```

### Configuration
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Edit `.env` to customize Redis settings:
- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (if required)
- `CACHE_TTL`: Cache expiration time in seconds (default: 3600 = 1 hour)

## Installation

```bash
cd cache-api
pip install -r requirements.txt
```

## Running the API

```bash
# Development mode
python main.py

# Production mode with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Testing Redis Integration

```bash
# From project root
python test_redis_integration.py
```

## New API Endpoints

### Cache Management

**Get Cache Statistics**
```bash
GET /cache/stats
```

Returns Redis connection status, cache size, memory usage, etc.

**Clear All Cache**
```bash
DELETE /cache/clear
```

Clears all cached entries from Redis.

**Invalidate Specific Cache Entry**
```bash
DELETE /cache/invalidate?team=Lakers&sport=Basketball
```

Removes a specific cache entry.

### Cache Behavior

- **First Request**: Cache MISS → Queries SQLite database → Stores result in Redis
- **Subsequent Requests**: Cache HIT → Returns data from Redis (much faster)
- **Auto-Expiration**: Cache entries expire after CACHE_TTL seconds
- **Graceful Fallback**: If Redis is unavailable, queries go directly to database

### Performance Benefits

With Redis caching:
- **Faster Response Times**: 10-100x faster for cached queries
- **Reduced Database Load**: Fewer SQLite queries
- **Scalability**: Better handling of concurrent requests

## Monitoring

Check cache performance in logs:
```
✓ Cache HIT: cache:team:lakers:basketball:abc123def456
✗ Cache MISS: cache:player:messi:123abc456def
✓ Cache SET: cache:market:moneyline:789xyz (TTL: 3600s)
```

## Production Deployment

The systemd service will automatically use Redis if available. The API gracefully falls back to direct database queries if Redis is down.

To restart the service:
```bash
sudo systemctl restart cache-api
sudo systemctl status cache-api
```
