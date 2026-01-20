# Redis Sync Service

Automated synchronization service that keeps Redis cache in sync with the SQLite database.

## Overview

The sync service monitors the database for changes to alias tables and automatically updates Redis:
- **Additions**: New aliases in DB are pushed to Redis
- **Updates**: Modified aliases in DB are updated in Redis
- **Deletions**: Removed aliases from DB are deleted from Redis
- **Sync Interval**: Every 2 minutes

## Quick Start

### Run Continuous Sync (Default)
```powershell
cd f:\cacheFile\cache-api
python sync_redis.py
```

This will run the sync service continuously, checking for changes every 2 minutes.

### Run Single Sync (One-Time)
```powershell
python sync_redis.py --once
```

This will perform a single sync operation and exit.

## Features

### 1. Automatic Synchronization
- Syncs all alias tables: `team_aliases`, `player_aliases`, `league_aliases`, `market_aliases`
- Detects additions, updates, and deletions
- Runs every 2 minutes in continuous mode

### 2. Redis Key Structure
```
alias:team:{alias_name} -> [team_id1, team_id2, ...]
alias:player:{alias_name} -> [player_id1, player_id2, ...]
alias:league:{alias_name} -> [league_id1, league_id2, ...]
alias:market:{alias_name} -> [market_id1, market_id2, ...]
```

### 3. Change Detection
The service tracks:
- **Added**: New aliases that exist in DB but not in Redis
- **Updated**: Existing aliases with different ID mappings
- **Deleted**: Aliases that exist in Redis but not in DB

### 4. Logging
Each sync cycle displays:
```
[2026-01-05 14:30:00] Starting sync...
✓ Sync complete:
  - Total aliases: 1234
  - Added: 5
  - Updated: 2
  - Deleted: 1
```

## Configuration

### Environment Variables
```powershell
# Optional - defaults shown
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_DB = "0"
$env:REDIS_PASSWORD = $null
```

### Change Sync Interval
Edit `sync_redis.py`:
```python
# Default: 120 seconds (2 minutes)
SYNC_INTERVAL = 120

# Change to 5 minutes:
SYNC_INTERVAL = 300

# Change to 30 seconds:
SYNC_INTERVAL = 30
```

## Usage Examples

### Example 1: Start Sync Service
```powershell
cd f:\cacheFile\cache-api
python sync_redis.py
```

Output:
```
============================================================
Redis Alias Sync Service
============================================================
Database: f:\cacheFile\cache-api\sports_data.db
Redis: localhost:6379
Sync interval: 120 seconds (2 minutes)
Started at: 2026-01-05 14:30:00
============================================================

[2026-01-05 14:30:00] Starting sync...
✓ Sync complete:
  - Total aliases: 1234
  - Added: 150
  - Updated: 0
  - Deleted: 0

[2026-01-05 14:32:00] Starting sync...
✓ Sync complete:
  - Total aliases: 1234
  - Added: 0
  - Updated: 0
  - Deleted: 0
  - No changes detected
```

### Example 2: Run One-Time Sync
```powershell
python sync_redis.py --once
```

Output:
```
Running one-time sync...
[2026-01-05 14:30:00] Starting sync...
✓ Sync complete:
  - Total aliases: 1234
  - Added: 150
  - Updated: 0
  - Deleted: 0
Done.
```

### Example 3: Stop Sync Service
Press `Ctrl+C` in the terminal:
```
^C
⏹  Sync service stopped by user
```

## Integration with Cache API

The sync service works alongside your FastAPI cache application:

### Recommended Setup
1. **Terminal 1**: Redis Server
   ```powershell
   F:\cacheFile\redis\redis-server.exe
   ```

2. **Terminal 2**: Sync Service
   ```powershell
   cd f:\cacheFile\cache-api
   python sync_redis.py
   ```

3. **Terminal 3**: FastAPI Server
   ```powershell
   cd f:\cacheFile\cache-api
   python main.py
   ```

### Workflow
1. User adds/updates/deletes aliases in database
2. Sync service detects changes within 2 minutes
3. Redis is updated automatically
4. Cache API uses updated Redis data
5. Old cache entries expire naturally (1-hour TTL)

## Testing

### Test 1: Add New Alias
```powershell
# Add to database
sqlite3 sports_data.db "INSERT INTO team_aliases (team_id, alias) VALUES (1, 'rmcf')"

# Wait up to 2 minutes
# Check sync output for "Added: 1"

# Verify in Redis
F:\cacheFile\redis\redis-cli.exe GET alias:team:rmcf
# Should return: ["1"]
```

### Test 2: Update Alias
```powershell
# Update in database
sqlite3 sports_data.db "UPDATE team_aliases SET team_id = 2 WHERE alias = 'rmcf'"

# Wait up to 2 minutes
# Check sync output for "Updated: 1"

# Verify in Redis
F:\cacheFile\redis\redis-cli.exe GET alias:team:rmcf
# Should return: ["2"]
```

### Test 3: Delete Alias
```powershell
# Delete from database
sqlite3 sports_data.db "DELETE FROM team_aliases WHERE alias = 'rmcf'"

# Wait up to 2 minutes
# Check sync output for "Deleted: 1"

# Verify in Redis
F:\cacheFile\redis\redis-cli.exe GET alias:team:rmcf
# Should return: (nil)
```

## Production Deployment

### Linux/Ubuntu VPS

#### 1. Create Systemd Service
```bash
sudo nano /etc/systemd/system/redis-sync.service
```

```ini
[Unit]
Description=Redis Alias Sync Service
After=network.target redis.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/cache-api
ExecStart=/usr/bin/python3 /path/to/cache-api/sync_redis.py
Restart=always
RestartSec=10
Environment=REDIS_HOST=localhost
Environment=REDIS_PORT=6379

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable redis-sync
sudo systemctl start redis-sync
```

#### 3. Check Status
```bash
sudo systemctl status redis-sync
```

#### 4. View Logs
```bash
sudo journalctl -u redis-sync -f
```

### Windows Service (using NSSM)

#### 1. Download NSSM
Download from: https://nssm.cc/download

#### 2. Install Service
```powershell
nssm install RedisSyncService "C:\Python313\python.exe" "f:\cacheFile\cache-api\sync_redis.py"
nssm set RedisSyncService AppDirectory "f:\cacheFile\cache-api"
nssm set RedisSyncService DisplayName "Redis Alias Sync Service"
nssm set RedisSyncService Description "Syncs database aliases to Redis every 2 minutes"
nssm set RedisSyncService Start SERVICE_AUTO_START
```

#### 3. Start Service
```powershell
nssm start RedisSyncService
```

#### 4. Check Status
```powershell
nssm status RedisSyncService
```

## Troubleshooting

### Issue: "Cannot connect to Redis"
**Solution**: Ensure Redis server is running
```powershell
F:\cacheFile\redis\redis-server.exe
```

### Issue: "No such table: team_aliases"
**Solution**: Ensure database exists and has alias tables
```powershell
python show_tables.py
```

### Issue: Changes not syncing
**Solution**: 
1. Check sync service is running
2. Wait up to 2 minutes for next sync cycle
3. Check database connection
4. Verify Redis connection

### Issue: Memory usage growing
**Solution**: Redis stores aliases permanently, but cache entries expire after 1 hour. To clear all data:
```powershell
F:\cacheFile\redis\redis-cli.exe FLUSHDB
```

## Monitoring

### Check Redis Alias Count
```powershell
F:\cacheFile\redis\redis-cli.exe KEYS alias:* | Measure-Object -Line
```

### View All Team Aliases in Redis
```powershell
F:\cacheFile\redis\redis-cli.exe KEYS alias:team:*
```

### Check Specific Alias
```powershell
F:\cacheFile\redis\redis-cli.exe GET alias:team:madrid
```

### Monitor Sync Service Logs
Watch the terminal output for sync statistics every 2 minutes.

## Best Practices

1. **Keep Service Running**: Use systemd (Linux) or NSSM (Windows) for automatic restart
2. **Monitor Logs**: Check sync output for errors
3. **Test Changes**: Verify database changes sync to Redis
4. **Backup Redis**: Use Redis persistence (RDB/AOF) if needed
5. **Adjust Interval**: Change `SYNC_INTERVAL` based on your update frequency

## Architecture

```
┌─────────────────┐
│  SQLite DB      │
│  (sports_data)  │
└────────┬────────┘
         │
         │ Every 2 minutes
         ↓
┌─────────────────┐
│  Sync Service   │
│  (sync_redis.py)│
└────────┬────────┘
         │
         │ Update aliases
         ↓
┌─────────────────┐       ┌─────────────────┐
│  Redis Cache    │←──────│  FastAPI App    │
│  (alias:*)      │       │  (main.py)      │
└─────────────────┘       └─────────────────┘
```

## Comparison with Cache

| Feature | Alias Sync | Query Cache |
|---------|-----------|-------------|
| Data | Alias mappings | Query results |
| Storage | Permanent in Redis | 1-hour TTL |
| Update | Every 2 minutes | On query |
| Key Pattern | `alias:type:name` | `cache:team_player:...` |
| Purpose | Fast lookup | Reduce DB load |

Both services work together for optimal performance!
