# Quick Reference - Cache API Deployment

## Merge PR & Auto-Deploy (Easiest)

```bash
# 1. Go to GitHub
https://github.com/joypciu/cache-api/pull/12

# 2. Click "Merge pull request"
# 3. Confirm merge
# 4. GitHub Actions will automatically deploy to VPS
# 5. Check deployment status in Actions tab
```

## Manual VPS Deployment

```bash
# SSH to VPS
ssh ubuntu@YOUR_VPS_IP

# Navigate to service directory
cd /home/ubuntu/services/cache-api

# Pull latest changes
git fetch origin
git checkout add-sports-database  # or main after merge

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

## Quick Test Commands

```bash
# Health check
curl http://YOUR_VPS_IP:8001/health

# Cache stats
curl http://YOUR_VPS_IP:8001/cache/stats

# Test query
curl "http://YOUR_VPS_IP:8001/cache?team=Lakers&sport=Basketball"
```

## Service Management

```bash
# Restart service
sudo systemctl restart cache-api

# Check status
sudo systemctl status cache-api

# View logs
sudo journalctl -u cache-api -n 50
```

## Redis Management

```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping

# View cache keys
redis-cli KEYS 'cache:*'

# Clear all cache
curl -X DELETE http://localhost:8001/cache/clear
```

## Troubleshooting

```bash
# Service won't start
sudo journalctl -u cache-api -n 100
sudo fuser -k 8001/tcp
sudo systemctl restart cache-api

# Redis issues
sudo systemctl restart redis-server
redis-cli ping

# Check port
sudo netstat -tlnp | grep :8001
```

## Key Files

- `.env` - Environment configuration
- `deploy.sh` - Deployment automation script
- `VPS_SETUP.md` - Complete setup guide
- `DEPLOYMENT_SUMMARY.md` - What was changed
- `.github/workflows/deploy.yml` - CI/CD workflow

## Environment Variables (.env)

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
CACHE_TTL=3600
API_HOST=0.0.0.0
API_PORT=8001
```

## New Features in PR #12

✅ Redis caching (10-100x faster)
✅ League search support
✅ Cache management endpoints
✅ Automatic Redis installation
✅ Enhanced monitoring
✅ Graceful fallback to SQLite

## Support Documents

- [VPS_SETUP.md](VPS_SETUP.md) - Detailed setup instructions
- [REDIS_README.md](REDIS_README.md) - Redis-specific guide
- [README.md](README.md) - Complete API documentation
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - Changes overview
