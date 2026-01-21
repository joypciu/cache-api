# Cache API with Redis Caching

A high-performance FastAPI-based cache normalization service for sports betting data with Redis caching layer and token-based authentication.

## Features

- **🔒 Token Authentication**: Secure API access with Bearer token authentication
- **🚀 Redis Caching**: 10-100x faster response times for cached queries
- **RESTful API** for cache lookups
- **Flexible queries** supporting market, team, player, and league parameters
- **SQLite database** with comprehensive sports data (teams, players, leagues, markets)
- **Automated deployment** via GitHub Actions with Redis setup
- **Systemd service** management with auto-recovery
- **Cache management** endpoints for statistics and invalidation
- **Graceful fallback** to direct database queries if Redis is unavailable

## Quick Start

### 1. Authentication Setup

Before using the API, configure your authentication tokens:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your API token
# API_TOKEN=your-secure-token-here
```

**Generate a secure token:**

```bash
# Using Python
python -c "import secrets; print(f'API_TOKEN={secrets.token_urlsafe(32)}')"
```

See [AUTH_GUIDE.md](AUTH_GUIDE.md) for detailed authentication documentation.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
python main.py
```

## API Documentation

The API documentation is available at `/docs`.

- **Public View**: `https://cache-api.eternitylabs.co/docs`
  - Shows only public endpoints (cache lookups, batch queries).
- **Admin View**: `https://cache-api.eternitylabs.co/docs?admin_token=eternitylabsadmin`
  - Authenticates the browser session.
  - Shows all endpoints including admin management tools.
  - Sets a secure cookie valid for 1 hour.

## API Endpoints

**Note:** All endpoints except `/` require authentication via the `Authorization: Bearer <token>` header.

### Cache Query Endpoint

**GET /cache** 🔒

Retrieve normalized cache entries with Redis caching.

**Headers:**

```
Authorization: Bearer your-api-token-here
```

**Parameters:**

- `market` (optional): Market type (e.g., "moneyline", "spread", "total")
- `team` (optional): Team name to look up
- `player` (optional): Player name to look up
- `sport` (optional): Sport name - **required when searching by team or league only**
- `league` (optional): League name to look up

**Cache Behavior:**

- **First Request**: Cache MISS → Queries SQLite database → Stores result in Redis
- **Subsequent Requests**: Cache HIT → Returns data from Redis (10-100x faster)
- **Auto-Expiration**: Cache entries expire after CACHE_TTL seconds (default: 3600)
- **Graceful Fallback**: If Redis is unavailable, queries go directly to database

**Search Modes:**

1. **Team only**: Returns all matching teams with their players (sport required)
2. **Player only**: Returns all matching players with their team info
3. **League only**: Returns league with all its teams (sport required)
4. **Team + Player**: Returns only the specified player from the specified team (most specific)
5. **Market**: Returns market information and applicable sports

**Examples:**

```bash
# Look up a team (sport is required)
curl -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache?team=Lakers&sport=Basketball"

# Look up a league with all its teams
curl -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache?league=Premier%20League&sport=Soccer"

# Look up a player
curl -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache?player=LeBron%20James"

# Look up a specific player on a specific team (most precise)
curl -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache?player=Kylian%20Mbappé&team=Real%20Madrid%20CF"

# Look up a market
curl -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache?market=moneyline"
```

### Batch Query Endpoints

**POST /cache/batch** 🔒

Query multiple independent items in a single request. Each item is searched for independently.

**Body:**

```json
{
  "team": ["Lakers", "Warriors"],
  "player": ["LeBron James", "Stephen Curry"],
  "market": ["moneyline", "total"],
  "sport": "Basketball"
}
```

**POST /cache/batch/precision** 🔒

Query multiple specific combinations (precision queries) in a batch.

**Body:**

```json
{
  "queries": [
    { "team": "Lakers", "player": "LeBron James", "sport": "Basketball" },
    { "team": "Warriors", "sport": "Basketball" },
    { "player": "Messi", "sport": "Soccer" }
  ]
}
```

### Cache Management Endpoints

**Note**: These endpoints require the **Admin API Token**.

**GET /cache/stats** 🔒 (Admin)

Get detailed cache statistics including Redis status, memory usage, and key count.

```bash
curl -H "Authorization: Bearer your-api-token-here" \
  http://142.44.160.36:8001/cache/stats
```

**DELETE /cache/clear** 🔒

Clear all cache entries from Redis.

```bash
curl -X DELETE \
  -H "Authorization: Bearer your-api-token-here" \
  http://142.44.160.36:8001/cache/clear
```

**DELETE /cache/invalidate** 🔒

Invalidate specific cache entry.

```bash
# Invalidate specific team cache
curl -X DELETE \
  -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache/invalidate?team=Lakers&sport=Basketball"

# Invalidate specific player cache
curl -X DELETE \
  -H "Authorization: Bearer your-api-token-here" \
  "http://142.44.160.36:8001/cache/invalidate?player=LeBron%20James"
```

**Response Format:**

**Team Search (returns all matching teams):**

```json
{
  "found": true,
  "data": {
    "type": "team",
    "query": "Barcelona",
    "teams": [
      {
        "id": "ABC123",
        "normalized_name": "FC Barcelona",
        "abbreviation": "BAR",
        "city": "Barcelona",
        "mascot": null,
        "nickname": "Barça",
        "league": "La Liga",
        "sport": "Soccer",
        "players": [...],
        "player_count": 25
      },
      {
        "id": "XYZ789",
        "normalized_name": "Barcelona SC",
        "abbreviation": "BSC",
        "city": "Guayaquil",
        "mascot": null,
        "nickname": "Los Toreros",
        "league": "Ecuador - Serie A",
        "sport": "Soccer",
        "players": [...],
        "player_count": 20
      }
    ],
    "team_count": 2
  },
  "query": {
    "market": null,
    "team": "Barcelona",
    "player": null,
    "sport": "Soccer"
  }
}
```

### Health Endpoints

**GET /health** 🔒 (Admin)

Health check endpoint with cache statistics for monitoring. Requires Admin Token.

```bash
curl -H "Authorization: Bearer your-api-token-here" \
  http://142.44.160.36:8001/health
```

**GET /** ✅ Public

Root endpoint showing service status and features (no authentication required).

```bash
curl http://142.44.160.36:8001/
```

## Local Development

### Prerequisites

- Python 3.8+
- Redis (optional but recommended for full feature testing)
- pip

### Setup

1. **Clone the repository:**

```bash
git clone https://github.com/joypciu/cache-api.git
cd cache-api
```

2. **Install Redis (optional):**

**Ubuntu/WSL:**

```bash
sudo apt install redis-server -y
sudo service redis-server start
redis-cli ping  # Should return "PONG"
```

**macOS:**

```bash
brew install redis
brew services start redis
```

**Windows:**
Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases)

3. **Create a virtual environment:**

```bash
python -m venv venv
```

4. **Activate virtual environment:**

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

5. **Install dependencies:**

```bash
pip install -r requirements.txt
```

6. **Configure environment (optional):**

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings (optional)
# Defaults work fine for local development
```

7. **Run the server:**

```bash
python main.py
```

The API will be available at `http://localhost:8001`

### Testing

```bash
# Test health endpoint
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/health

# Test cache statistics
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/stats

# Test team query
curl -H "Authorization: Bearer your-api-token-here" \
  "http://localhost:8001/cache?team=Lakers&sport=Basketball"

# Test player query
curl -H "Authorization: Bearer your-api-token-here" \
  "http://localhost:8001/cache?player=LeBron%20James"
```

## VPS Deployment

### Quick Deployment

For detailed step-by-step instructions, see [VPS_SETUP.md](VPS_SETUP.md).

### Automated Deployment via GitHub Actions

The repository includes a GitHub Actions workflow that automatically deploys to your VPS on every push to the `main` branch.

#### Prerequisites

1. Ubuntu VPS with SSH access
2. GitHub repository with this code

#### GitHub Secrets Configuration

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `VPS_HOST`: Your VPS IP address (e.g., `142.44.160.36`)
- `VPS_USERNAME`: SSH username (usually `ubuntu`)
- `VPS_SSH_KEY`: Your private SSH key content
- `VPS_PORT`: SSH port (usually `22`)

#### What the Workflow Does

When you push to the `main` branch, the GitHub Actions workflow will:

1. ✅ Check and install Redis if not present
2. ✅ Start and enable Redis service
3. ✅ Pull latest code from repository
4. ✅ Create `.env` file from `.env.example` if needed
5. ✅ Install/update Python dependencies
6. ✅ Update systemd service configuration
7. ✅ Restart the Cache API service
8. ✅ Verify deployment with health checks
9. ✅ Display service status and logs

### Manual Deployment Script

For manual deployment or troubleshooting, you can use the deployment script:

```bash
# On your VPS
cd /home/ubuntu/services/cache-api
chmod +x deploy.sh
./deploy.sh
```

This script will:

- Install Redis if not present
- Update code from repository
- Install dependencies
- Configure and restart services
- Verify everything is working

### Initial VPS Setup (One-time)

**Option 1: Use the automated deployment script**

1. SSH into your VPS:

```bash
ssh ubuntu@142.44.160.36
```

2. Create service directory:

```bash
mkdir -p /home/ubuntu/services/cache-api
cd /home/ubuntu/services/cache-api
```

3. Clone repository:

```bash
git clone https://github.com/joypciu/cache-api.git .
```

4. Run deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

**Option 2: Manual setup**

See [VPS_SETUP.md](VPS_SETUP.md) for detailed manual setup instructions.

### Deployment Verification

After deployment, verify the service is working:

```bash
# Check service status
sudo systemctl status cache-api

# Check Redis status
sudo systemctl status redis-server

# Test API health
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/health

# Check cache statistics
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/stats

# View logs
sudo journalctl -u cache-api -n 50
```

## Project Structure

```
cache-api/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions deployment workflow
├── main.py                      # FastAPI application with cache endpoints
├── cache_db.py                  # Database access layer with Redis integration
├── redis_cache.py              # Redis caching module
├── sports_data.db              # SQLite database with sports data
├── requirements.txt             # Python dependencies (includes redis)
├── cache-api.service           # Systemd service configuration
├── .env.example                # Environment variables template
├── deploy.sh                   # Manual deployment script for VPS
├── VPS_SETUP.md                # Detailed VPS setup guide
├── REDIS_README.md             # Redis-specific documentation
├── .gitignore                  # Git ignore patterns
└── README.md                   # This file
```

## Database

The application uses a SQLite database (`sports_data.db`) with Redis caching layer for optimal performance.

### Data Structure

- **Sports**: Various sports with leagues
- **Leagues**: Sports leagues with teams
- **Teams**: Team information including abbreviations, cities, mascots, nicknames
- **Players**: Player details with team and league associations
- **Markets**: Betting market types and associations
- **Aliases**: Alternative names for teams, players, leagues, and markets

### Database Relationships

- **ONE-TO-MANY**: League → Teams
  - One league can have many teams
  - When querying a league, all its teams are returned

- **ONE-TO-MANY**: Team → Players
  - One team can have many players
  - When querying a team, all its players are returned
- **ONE-TO-ONE**: Player → Team
  - Each player belongs to exactly one team
  - Players have a single `team_id` foreign key
  - Foreign key constraints ensure data integrity

### Redis Cache Layer

The Redis cache layer provides:

- **Fast Lookups**: 10-100x faster than SQLite queries
- **Automatic Expiration**: TTL-based cache invalidation (default: 1 hour)
- **Smart Keys**: Hierarchical cache keys for easy management
- **Cache Statistics**: Real-time monitoring of cache performance
- **Graceful Fallback**: Continues working if Redis is unavailable

Cache key patterns:

- `cache:team:<name>:<sport>:<hash>` - Team queries
- `cache:player:<name>:<hash>` - Player queries
- `cache:league:<name>:<sport>:<hash>` - League queries
- `cache:market:<name>:<hash>` - Market queries

### Query Functions

The `cache_db.py` module provides query functions for:

- **Team lookups**: By name, abbreviation, or nickname (with sport filter)
  - Returns all matching teams with their complete player rosters
  - Results are cached in Redis for fast subsequent access
- **Player lookups**: By full name (fuzzy matching)
  - Returns all players with that name and their team information
  - Cached for quick repeated queries
- **League lookups**: By league name (with sport filter)
  - Returns league with all teams
  - Cached with automatic expiration
- **Market lookups**: By market name
  - Returns market information and applicable sports
  - Cached for performance

## Monitoring & Logs

### Service Logs

View real-time logs:

```bash
# Follow logs in real-time
sudo journalctl -u cache-api -f

# View last 50 lines
sudo journalctl -u cache-api -n 50

# View logs with timestamps
sudo journalctl -u cache-api -n 50 --no-pager
```

### Service Status

Check service status:

```bash
# Cache API service
sudo systemctl status cache-api

# Redis service
sudo systemctl status redis-server
```

### Cache Monitoring

Monitor cache performance:

```bash
# Get cache statistics via API
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/stats

# Monitor Redis directly
redis-cli INFO
redis-cli INFO stats
redis-cli INFO memory

# View cache keys
redis-cli KEYS 'cache:*'

# Get specific cache entry
redis-cli GET "cache:team:lakers:basketball:abc123"
```

### Performance Monitoring

```bash
# Check port 8001
sudo netstat -tlnp | grep :8001

# Monitor Redis memory usage
redis-cli INFO memory | grep used_memory_human

# Count cache entries
redis-cli DBSIZE

# Monitor hit/miss ratio
redis-cli INFO stats | grep keyspace
```

### Service Management

Restart services:

```bash
# Restart Cache API
sudo systemctl restart cache-api

# Restart Redis
sudo systemctl restart redis-server

# Restart both
sudo systemctl restart cache-api redis-server
```

Stop/start services:

```bash
# Stop service
sudo systemctl stop cache-api

# Start service
sudo systemctl start cache-api
```

## Configuration

### Environment Variables

The application can be configured using environment variables in the `.env` file:

```bash
# Redis Configuration
REDIS_HOST=localhost          # Redis server hostname
REDIS_PORT=6379              # Redis port
REDIS_DB=0                   # Redis database number
REDIS_PASSWORD=              # Redis password (if required)

# Cache Configuration
CACHE_TTL=3600              # Cache expiration time in seconds (1 hour)

# API Configuration
API_HOST=0.0.0.0            # API host (0.0.0.0 for all interfaces)
API_PORT=8001               # API port
```

### Service Configuration

The systemd service (`cache-api.service`) includes:

- Automatic restart on failure
- Resource limits (512MB memory, 50% CPU)
- Dependency on Redis service
- Graceful fallback if Redis is unavailable
- Journal logging for troubleshooting

### Redis Configuration

For production environments, consider optimizing Redis:

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Recommended settings for cache use:
maxmemory 256mb                    # Limit memory usage
maxmemory-policy allkeys-lru       # Evict least recently used keys
save ""                            # Disable persistence (faster)
appendonly no                      # Disable append-only file
```

Restart Redis after changes:

```bash
sudo systemctl restart redis-server
```

## Port Configuration

The service runs on port **8001** by default. To change:

1. Update `.env` file: `API_PORT=<new_port>`
2. Update `cache-api.service` if needed
3. Update firewall rules: `sudo ufw allow <new_port>/tcp`
4. Restart service: `sudo systemctl restart cache-api`

## Performance Optimization

### Redis Performance

- **Memory Limit**: Set `maxmemory` to prevent Redis from using too much RAM
- **Eviction Policy**: Use `allkeys-lru` for cache workloads
- **Disable Persistence**: Set `save ""` and `appendonly no` for pure cache usage
- **Monitor Memory**: Check `redis-cli INFO memory` regularly

### API Performance

- **Cache TTL**: Adjust `CACHE_TTL` based on data freshness requirements
  - Higher TTL = Better performance, less fresh data
  - Lower TTL = More database queries, fresher data
- **Resource Limits**: Adjust systemd service limits based on workload
- **Connection Pooling**: Redis client uses connection pooling automatically

### Monitoring Performance

```bash
# Check cache hit/miss ratio
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/stats

# Monitor Redis performance
redis-cli --stat

# Check API response time
time curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache?team=Lakers&sport=Basketball
```

## Security

### Redis Security

For production, secure Redis:

1. **Set Password**:

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Add password
requirepass your_strong_password_here

# Update .env
REDIS_PASSWORD=your_strong_password_here
```

2. **Bind to Localhost** (if Redis is on same server):

```bash
# In redis.conf
bind 127.0.0.1
```

3. **Enable Protected Mode**:

```bash
# In redis.conf
protected-mode yes
```

### Firewall Configuration

```bash
# Allow API port
sudo ufw allow 8001/tcp

# Allow SSH
sudo ufw allow OpenSSH

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u cache-api -n 100

# Check if port is in use
sudo netstat -tlnp | grep :8001

# Kill process on port 8001
sudo fuser -k 8001/tcp

# Restart service
sudo systemctl restart cache-api
```

### Redis Connection Failed

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping

# Check Redis logs
sudo journalctl -u redis-server -n 50
```

### Cache Not Working

```bash
# Check cache stats
curl -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/stats

# Clear cache
curl -X DELETE \
  -H "Authorization: Bearer your-api-token-here" \
  http://localhost:8001/cache/clear

# Check Redis keys
redis-cli KEYS 'cache:*'
```

### High Memory Usage

```bash
# Check Redis memory
redis-cli INFO memory

# Clear all cache
redis-cli FLUSHDB

# Or via API
curl -X DELETE http://localhost:8001/cache/clear
```

## Port Configuration

The service runs on port **8001** by default (port 8000 is used by unified-odds service). To change:

1. Update `main.py` (line with `uvicorn.run`)
2. Update `deploy.yml` port check commands
3. Ensure firewall allows the new port

## License

Private - Internal Use Only
