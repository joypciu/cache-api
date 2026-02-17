# Security Guide

This document outlines security best practices and configurations for the Cache API.

## 🔒 Security Features

### 1. Token-Based Authentication

The API uses Bearer token authentication for all endpoints (except root `/`).

**Two types of tokens:**
- **API Token** (`API_TOKEN`): Regular access to cache endpoints
- **Admin Token** (`ADMIN_API_TOKEN`): Full access including admin endpoints (stats, clear cache)

**Configuration:**
```bash
# In .env file
API_TOKEN=your-secure-random-token-here
ADMIN_API_TOKEN=your-secure-admin-token-here
```

**Generate secure tokens:**
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

### 2. Rate Limiting (DDoS Protection)

Built-in rate limiting protects against DDoS attacks and abuse.

**Default Configuration:**
- **60 requests per minute** per IP address
- Returns HTTP 429 (Too Many Requests) when exceeded

**Customize:**
```bash
# In .env file
RATE_LIMIT_PER_MINUTE=100  # Allow 100 requests/minute
```

**How it works:**
- Tracks requests per IP address in memory
- Automatically cleans old entries
- Applies to all authenticated endpoints
- For production with multiple servers, consider Redis-based rate limiting

### 3. Environment Variables

**Never commit sensitive data to Git!**

All sensitive configuration is stored in `.env` file which is:
- ✅ Listed in `.gitignore`
- ✅ Not tracked by Git
- ✅ Only exists on your server

**Required variables:**
```bash
# Authentication (REQUIRED)
API_TOKEN=<your-secure-token>
ADMIN_API_TOKEN=<your-admin-token>

# Redis (optional password)
REDIS_PASSWORD=<optional-redis-password>

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## 🛡️ Best Practices

### 1. Token Management

**DO:**
- ✅ Generate strong random tokens (32+ characters)
- ✅ Use different tokens for development and production
- ✅ Store tokens securely (password managers, secret vaults)
- ✅ Rotate tokens periodically
- ✅ Use HTTPS in production

**DON'T:**
- ❌ Hardcode tokens in source code
- ❌ Commit tokens to Git
- ❌ Share tokens in public channels
- ❌ Use simple/predictable tokens
- ❌ Reuse tokens across different services

### 2. Server Security

**Firewall Configuration:**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Block Redis from external access
sudo ufw deny 6379
sudo ufw allow from 127.0.0.1 to any port 6379
```

**Redis Security:**
```bash
# Set Redis password in /etc/redis/redis.conf
requirepass your_strong_redis_password

# Bind to localhost only
bind 127.0.0.1

# Disable dangerous commands
rename-command CONFIG ""
rename-command FLUSHALL ""
rename-command FLUSHDB ""
```

**File Permissions:**
```bash
# Protect .env file
chmod 600 /path/to/cache-api/.env
chown your-user:your-user /path/to/cache-api/.env

# Protect database
chmod 640 /path/to/cache-api/sports_data.db
```

### 3. HTTPS/SSL

**Always use HTTPS in production!**

Use a reverse proxy (Nginx/Apache) with Let's Encrypt SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Monitoring & Logging

**Monitor for suspicious activity:**
- Excessive failed authentication attempts
- Unusual traffic patterns
- High rate of 429 errors
- Unexpected admin endpoint access

**Check logs:**
```bash
# Service logs
sudo journalctl -u cache-api -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Filter for 401/429 errors
sudo grep "401\|429" /var/log/nginx/access.log
```

### 5. Database Security

**SQLite:**
- Set proper file permissions (640 or 600)
- Regular backups
- Keep database outside web-accessible directories

**For production with sensitive data:**
- Consider PostgreSQL/MySQL with encryption
- Use parameterized queries (already implemented)
- Enable database audit logging

## 🚨 Incident Response

### If Tokens Are Compromised

1. **Immediately rotate tokens:**
```bash
# Generate new tokens
python -c "import secrets; print(f'API_TOKEN={secrets.token_urlsafe(32)}')"
python -c "import secrets; print(f'ADMIN_API_TOKEN={secrets.token_urlsafe(32)}')"

# Update .env file
nano /path/to/cache-api/.env

# Restart service
sudo systemctl restart cache-api
```

2. **Review logs for unauthorized access:**
```bash
sudo journalctl -u cache-api --since "1 hour ago"
```

3. **Clear Redis cache if compromised:**
```bash
redis-cli FLUSHALL
```

### If Server Is Compromised

1. **Disconnect from network**
2. **Review all logs**
3. **Check for backdoors/malware**
4. **Rotate ALL credentials**
5. **Rebuild from clean backup if necessary**

## 📋 Security Checklist

Before deploying to production:

- [ ] Strong random tokens generated for both API_TOKEN and ADMIN_API_TOKEN
- [ ] `.env` file exists and has correct permissions (600 or 640)
- [ ] `.env` is in `.gitignore`
- [ ] No hardcoded credentials in source code
- [ ] Firewall configured (UFW/iptables)
- [ ] Redis password set (if exposed to network)
- [ ] HTTPS/SSL enabled with valid certificate
- [ ] Rate limiting configured appropriately
- [ ] Regular backups scheduled
- [ ] Monitoring/alerting configured
- [ ] File permissions set correctly
- [ ] All default passwords changed
- [ ] SSH key-based authentication (password auth disabled)
- [ ] Only necessary ports open
- [ ] Security headers configured in reverse proxy

## 🔄 Regular Maintenance

**Monthly:**
- Review access logs for anomalies
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Check for security updates: `sudo apt update && sudo apt upgrade`

**Quarterly:**
- Rotate API tokens
- Review and update firewall rules
- Audit user access and permissions

**Annually:**
- Security audit
- Penetration testing (if applicable)
- Update disaster recovery plan

## 📚 Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [Redis Security Guide](https://redis.io/docs/management/security/)
- [Let's Encrypt SSL/TLS](https://letsencrypt.org/)

## 🐛 Reporting Security Issues

If you discover a security vulnerability:
1. **DO NOT** create a public GitHub issue
2. Email security concerns to the maintainer
3. Include detailed description and steps to reproduce
4. Allow reasonable time for patch before public disclosure
