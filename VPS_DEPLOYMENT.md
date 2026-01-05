# VPS Deployment Guide for Redis Sync Service

This guide covers deploying the Redis sync service to an Ubuntu VPS.

## Prerequisites

- Ubuntu VPS with root/sudo access
- Python 3.8+ installed
- Redis server installed and running
- Git installed

## Quick Deployment

### 1. Connect to VPS
```bash
ssh root@142.44.160.36
# or
ssh your-username@142.44.160.36
```

### 2. Clone Repository
```bash
# Create directory
sudo mkdir -p /var/www
cd /var/www

# Clone repo
sudo git clone -b add-sports-database https://github.com/joypciu/cache-api.git
cd cache-api
```

### 3. Install Dependencies
```bash
# Install Python packages
sudo pip3 install redis hiredis

# Or use requirements.txt if available
# sudo pip3 install -r requirements.txt
```

### 4. Setup Environment
```bash
# Copy environment file
sudo cp .env.sync.example .env.sync

# Edit configuration
sudo nano .env.sync
```

Update `.env.sync`:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
DB_PATH=/var/www/cache-api/sports_data.db
SYNC_INTERVAL=120
LOG_LEVEL=INFO
LOG_FILE=/var/log/redis-sync/sync.log
```

### 5. Create Log Directory
```bash
sudo mkdir -p /var/log/redis-sync
sudo chown www-data:www-data /var/log/redis-sync
```

### 6. Install Systemd Service
```bash
# Copy service file
sudo cp redis-sync.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable redis-sync

# Start service
sudo systemctl start redis-sync
```

### 7. Verify Service
```bash
# Check status
sudo systemctl status redis-sync

# View logs
sudo journalctl -u redis-sync -f

# Or view log file
sudo tail -f /var/log/redis-sync/sync.log
```

## Service Management

### Start Service
```bash
sudo systemctl start redis-sync
```

### Stop Service
```bash
sudo systemctl stop redis-sync
```

### Restart Service
```bash
sudo systemctl restart redis-sync
```

### Check Status
```bash
sudo systemctl status redis-sync
```

### View Logs
```bash
# Systemd journal
sudo journalctl -u redis-sync -f

# Last 100 lines
sudo journalctl -u redis-sync -n 100

# Today's logs
sudo journalctl -u redis-sync --since today

# Log file (if configured)
sudo tail -f /var/log/redis-sync/sync.log
```

### Disable Service
```bash
sudo systemctl disable redis-sync
```

## Testing

### Test Single Sync
```bash
cd /var/www/cache-api
python3 sync_redis.py --once
```

### Check Redis Data
```bash
# Connect to Redis
redis-cli

# Check alias count
KEYS alias:*

# Check entity count
KEYS entity:*

# Get specific alias
GET alias:team:madrid

# Get specific entity
GET entity:team:1
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `REDIS_DB` | 0 | Redis database number |
| `REDIS_PASSWORD` | None | Redis password (if required) |
| `DB_PATH` | ./sports_data.db | Path to SQLite database |
| `SYNC_INTERVAL` | 120 | Sync interval in seconds |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | None | Path to log file (None = console only) |

### Change Sync Interval

Edit `/var/www/cache-api/.env.sync`:
```bash
# 1 minute
SYNC_INTERVAL=60

# 5 minutes
SYNC_INTERVAL=300

# 10 minutes
SYNC_INTERVAL=600
```

Then restart service:
```bash
sudo systemctl restart redis-sync
```

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
sudo journalctl -u redis-sync -n 50
```

**Common issues:**
- Database file not found → Check `DB_PATH` in `.env.sync`
- Redis connection failed → Ensure Redis is running: `sudo systemctl status redis`
- Permission denied → Check file permissions: `sudo chown -R www-data:www-data /var/www/cache-api`

### No Syncs Happening

**Check service status:**
```bash
sudo systemctl status redis-sync
```

**Check if process is running:**
```bash
ps aux | grep sync_redis
```

**Manually test:**
```bash
cd /var/www/cache-api
python3 sync_redis.py --once
```

### High Memory Usage

**Check Redis memory:**
```bash
redis-cli INFO memory
```

**Clear cache if needed:**
```bash
redis-cli FLUSHDB
```

### Database Locked Error

- Ensure only one sync service is running
- Check for other processes accessing the database:
```bash
lsof /var/www/cache-api/sports_data.db
```

## Security Best Practices

### 1. Set Proper Permissions
```bash
sudo chown -R www-data:www-data /var/www/cache-api
sudo chmod 640 /var/www/cache-api/.env.sync
```

### 2. Use Redis Password
Edit `/etc/redis/redis.conf`:
```
requirepass your_strong_password_here
```

Update `.env.sync`:
```
REDIS_PASSWORD=your_strong_password_here
```

Restart Redis:
```bash
sudo systemctl restart redis
sudo systemctl restart redis-sync
```

### 3. Firewall Configuration
```bash
# Allow only local Redis connections
sudo ufw deny 6379
sudo ufw allow from 127.0.0.1 to any port 6379
```

## Monitoring

### Check Sync Statistics

View logs for sync summary:
```bash
sudo journalctl -u redis-sync | grep "sync complete"
```

### Monitor Redis Memory
```bash
redis-cli INFO memory | grep used_memory_human
```

### Check Last Sync Time
```bash
sudo journalctl -u redis-sync | grep "Full sync cycle complete" | tail -1
```

### Set Up Alerts

Create a monitoring script (`/usr/local/bin/check-sync.sh`):
```bash
#!/bin/bash
if ! systemctl is-active --quiet redis-sync; then
    echo "Redis sync service is down!" | mail -s "Alert: Redis Sync Down" admin@example.com
fi
```

Add to crontab:
```bash
*/5 * * * * /usr/local/bin/check-sync.sh
```

## Updating

### Pull Latest Changes
```bash
cd /var/www/cache-api
sudo git pull origin add-sports-database
sudo systemctl restart redis-sync
```

### Update Dependencies
```bash
sudo pip3 install --upgrade redis hiredis
sudo systemctl restart redis-sync
```

## Complete Setup Script

Save as `deploy-sync.sh`:
```bash
#!/bin/bash
set -e

echo "Installing Redis Sync Service..."

# Install dependencies
sudo pip3 install redis hiredis

# Create directories
sudo mkdir -p /var/log/redis-sync
sudo chown www-data:www-data /var/log/redis-sync

# Copy environment file
sudo cp .env.sync.example .env.sync

# Install systemd service
sudo cp redis-sync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable redis-sync
sudo systemctl start redis-sync

echo "✓ Redis Sync Service installed and started"
echo "Check status: sudo systemctl status redis-sync"
echo "View logs: sudo journalctl -u redis-sync -f"
```

Run with:
```bash
chmod +x deploy-sync.sh
sudo ./deploy-sync.sh
```

## Integration with Main API

Both services should run together:

1. **Redis Server** (port 6379)
2. **Redis Sync Service** (syncs DB → Redis)
3. **FastAPI Cache API** (port 8001)

All three work together:
- Sync service keeps Redis updated with database changes
- Cache API uses Redis for fast lookups
- Users query the Cache API

## Architecture on VPS

```
┌──────────────────┐
│  SQLite DB       │
│  sports_data.db  │
└────────┬─────────┘
         │
         │ Every 2 min
         ↓
┌──────────────────┐
│  Sync Service    │
│  (systemd)       │
└────────┬─────────┘
         │
         │ Update
         ↓
┌──────────────────┐       ┌──────────────────┐
│  Redis Server    │←──────│  FastAPI App     │
│  localhost:6379  │       │  0.0.0.0:8001    │
└──────────────────┘       └────────┬─────────┘
                                    │
                                    │ HTTP
                                    ↓
                           ┌──────────────────┐
                           │  Nginx Proxy     │
                           │  port 80/443     │
                           └──────────────────┘
```

## Support

For issues or questions:
- GitHub: https://github.com/joypciu/cache-api/issues
- Logs: `sudo journalctl -u redis-sync -f`
