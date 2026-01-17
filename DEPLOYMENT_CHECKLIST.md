# Deployment Checklist - Cache API with Authentication

Use this checklist when deploying the authenticated Cache API to your VPS.

## Pre-Deployment (Do This First!) ⚠️

### [ ] 1. Configure API Token on VPS

**Why First?** The new code has authentication enabled. Configure the token BEFORE deploying so the API works immediately.

```bash
# SSH into VPS
ssh ubuntu@your-vps-ip

# Navigate to service directory
cd /home/ubuntu/services/cache-api

# Edit .env file
nano .env

# Add these lines:
API_TOKEN=your-secure-production-token-here

# Save and exit (Ctrl+X, Y, Enter)
```

**Generate a secure token:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Save this token securely** - you'll need it to make API requests!

### [ ] 2. Verify Token is Set

```bash
# Check token exists in .env
grep API_TOKEN .env

# Should output: API_TOKEN=your-token-value
```

## Deployment 🚀

### [ ] 3. Push Code to GitHub

```bash
# From your local machine
git add .
git commit -m "Add token-based authentication to cache API"
git push origin main
```

### [ ] 4. Monitor GitHub Actions

1. Go to your GitHub repository
2. Click **Actions** tab
3. Watch the deployment workflow
4. Wait for green checkmark ✅

### [ ] 5. Verify Service Restarted

```bash
# SSH into VPS
ssh ubuntu@your-vps-ip

# Check service status
sudo systemctl status cache-api

# Should show: active (running)
```

## Post-Deployment Testing ✅

### [ ] 6. Test Public Endpoint (No Auth)

```bash
curl http://your-vps-ip:8001/

# Expected: {"status": "online", "service": "Cache API", ...}
```

### [ ] 7. Test Protected Endpoint WITH Token

```bash
# Replace YOUR_TOKEN with actual token from .env
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-vps-ip:8001/health

# Expected: {"status": "healthy", "cache": {...}}
```

### [ ] 8. Test Protected Endpoint WITHOUT Token (Should Fail)

```bash
curl http://your-vps-ip:8001/health

# Expected: {"detail": "Not authenticated"}
```

### [ ] 9. Test Cache Query

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://your-vps-ip:8001/cache?team=Lakers&sport=Basketball"

# Expected: {"found": true, "data": {...}}
```

### [ ] 10. Test Cache Statistics

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-vps-ip:8001/cache/stats

# Expected: {"status": "connected", "keys_count": ..., ...}
```

## Verify in Postman 📮

### [ ] 11. Test in Postman

1. Open Postman
2. Create new request to: `http://your-vps-ip:8001/health`
3. Go to **Authorization** tab
4. Select **Type**: `Bearer Token`
5. **Token**: Paste your token (without "Bearer" prefix)
6. Click **Send**
7. Should get `200 OK` with health data

## Troubleshooting 🔧

### If Authentication Fails

```bash
# SSH into VPS
ssh ubuntu@your-vps-ip

# Check .env file has token
cd /home/ubuntu/services/cache-api
cat .env | grep API_TOKEN

# If missing, add it:
nano .env
# Add: API_TOKEN=your-token

# Restart service
sudo systemctl restart cache-api

# Check logs
sudo journalctl -u cache-api -n 50
```

### If Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u cache-api -n 100

# Common issues:
# - python-dotenv not installed: pip install python-dotenv
# - .env file missing: cp .env.example .env
# - No token set: Add API_TOKEN to .env
```

### If "No API tokens configured" Error

```bash
# This means API_TOKEN is not set in .env
cd /home/ubuntu/services/cache-api
nano .env

# Add:
API_TOKEN=your-secure-token-here

# Restart
sudo systemctl restart cache-api
```

## Security Checklist 🔒

### [ ] 12. Security Verification

- [ ] API token is long and random (32+ characters)
- [ ] Token is different from development token
- [ ] Token is not committed to Git
- [ ] .env file has proper permissions (600)
- [ ] Firewall allows port 8001
- [ ] Token is documented securely (password manager)

```bash
# Set proper .env permissions
chmod 600 /home/ubuntu/services/cache-api/.env

# Verify
ls -la /home/ubuntu/services/cache-api/.env
# Should show: -rw------- (600)
```

## Monitoring 📊

### [ ] 13. Set Up Monitoring

```bash
# Monitor logs in real-time
sudo journalctl -u cache-api -f

# Check Redis status
sudo systemctl status redis-server

# Monitor cache performance
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/cache/stats
```

## Success Criteria ✅

Deployment is successful when:

- ✅ GitHub Actions shows green checkmark
- ✅ Service is running: `sudo systemctl status cache-api`
- ✅ Public endpoint works: `curl http://vps-ip:8001/`
- ✅ Auth endpoint works WITH token
- ✅ Auth endpoint FAILS without token
- ✅ Cache queries return data
- ✅ Redis is connected and working

## Useful Commands

```bash
# View service status
sudo systemctl status cache-api

# Restart service
sudo systemctl restart cache-api

# View logs (last 50 lines)
sudo journalctl -u cache-api -n 50

# Follow logs in real-time
sudo journalctl -u cache-api -f

# Test with token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8001/health

# Check what's listening on port 8001
sudo netstat -tlnp | grep 8001
```

## Need Help?

See detailed documentation:
- [AUTH_GUIDE.md](AUTH_GUIDE.md) - Complete authentication guide
- [VPS_SETUP.md](VPS_SETUP.md) - VPS setup instructions
- [README.md](README.md) - API documentation
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - Deployment overview
