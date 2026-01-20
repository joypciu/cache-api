# VPS Setup Guide for Cache API with Redis

This guide provides step-by-step instructions for setting up the Cache API with Redis on a VPS using GitHub Actions.

## Prerequisites

- Ubuntu VPS (tested on Ubuntu 20.04/22.04)
- SSH access to the VPS
- GitHub repository access
- Domain or IP address for the VPS

## Initial VPS Setup (One-time)

### 1. Connect to Your VPS

```bash
ssh ubuntu@your-vps-ip
```

### 2. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Install Required System Packages

```bash
# Install Python, Redis, and other dependencies
sudo apt install -y python3 python3-pip python3-venv redis-server git net-tools

# Verify installations
python3 --version
redis-server --version
git --version
```

### 4. Configure Redis

```bash
# Enable Redis to start on boot
sudo systemctl enable redis-server

# Start Redis
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping  # Should return "PONG"

# Check Redis status
sudo systemctl status redis-server
```

### 5. Create Service Directory

```bash
# Create directory for the service
sudo mkdir -p /home/ubuntu/services/cache-api

# Change ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/services

# Navigate to the directory
cd /home/ubuntu/services/cache-api
```

### 6. Clone Repository

```bash
# Clone your repository (replace with your repo URL)
git clone https://github.com/joypciu/cache-api.git .

# Or if already cloned, pull latest changes
git pull origin main
```

### 7. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 8. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

**Example .env configuration:**

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Cache TTL (Time To Live) in seconds
CACHE_TTL=3600

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001

# API Authentication (REQUIRED)
# Generate a secure token for production
API_TOKEN=your-secure-production-token-here

# Optional: Additional tokens for different services
# API_TOKEN_1=token-for-service-1
# API_TOKEN_2=token-for-service-2
# API_TOKEN_3=token-for-service-3
```

**🔑 Generate a Secure API Token:**

```bash
# Option 1: Using Python
python3 -c "import secrets; print(f'API_TOKEN={secrets.token_urlsafe(32)}')"

# Option 2: Using OpenSSL
echo "API_TOKEN=$(openssl rand -base64 32)"

# Copy the generated token and paste it into your .env file
```

⚠️ **IMPORTANT:** 
- The API token is **required** for authentication
- Keep your production token **secret** - never commit it to Git
- Use different tokens for development and production
- Save your token securely - you'll need it to make API requests

### 9. Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp cache-api.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable cache-api

# Start the service
sudo systemctl start cache-api

# Check service status
sudo systemctl status cache-api
```

### 10. Verify API with Authentication

```bash
# Test with your API token (replace with your actual token from .env)
curl -H "Authorization: Bearer your-actual-token-here" \
  http://localhost:8001/health

# Expected response:
# {"status": "healthy", "cache": {...}}

# Test without token (should fail with 401)
curl http://localhost:8001/health

# Expected response:
# {"detail": "Not authenticated"}
```

**If authentication fails:**

```bash
# Check that API_TOKEN is set in .env
grep API_TOKEN .env

# Restart the service to reload environment variables
sudo systemctl restart cache-api

# Check logs for errors
sudo journalctl -u cache-api -n 50
```

### 11. Configure Firewall (if applicable)

```bash
# Allow port 8001 for the API
sudo ufw allow 8001/tcp

# Allow SSH (if not already allowed)
sudo ufw allow OpenSSH

# Enable firewall
sudo ufw enable

# Check firewall status
sudo ufw status
```

## GitHub Actions Setup

### 1. Configure API Token on VPS (Before First Deployment)

**\ud83d\udd11 IMPORTANT: Do this BEFORE pushing code with authentication enabled**

```bash
# SSH into your VPS
ssh ubuntu@your-vps-ip

# Navigate to service directory
cd /home/ubuntu/services/cache-api

# Edit .env file and add API token
nano .env

# Add this line with a secure token:
# API_TOKEN=your-secure-production-token-here
# Save and exit (Ctrl+X, Y, Enter)

# Verify token is set
grep API_TOKEN .env
```

\u26a0\ufe0f **Why do this first?**
- GitHub Actions will pull new code with authentication enabled
- Your existing `.env` file won't be overwritten
- The service will start with authentication working immediately

### 2. Add GitHub Secrets

Go to your GitHub repository \u2192 Settings \u2192 Secrets and variables \u2192 Actions

Add the following secrets:

- `VPS_HOST`: Your VPS IP address (e.g., `142.44.160.36`)
- `VPS_USERNAME`: SSH username (usually `ubuntu`)
- `VPS_SSH_KEY`: Your private SSH key
- `VPS_PORT`: SSH port (usually `22`)

### 3. Generate SSH Key (if needed)

On your local machine:

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "github-actions"

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@your-vps-ip

# Copy private key content for GitHub secret
cat ~/.ssh/id_rsa  # Copy this to VPS_SSH_KEY secret
```

### 4. Test GitHub Actions Deployment

**First, verify your VPS has the API token configured:**

```bash
# SSH to VPS and check
ssh ubuntu@your-vps-ip
cd /home/ubuntu/services/cache-api
grep API_TOKEN .env  # Should show your token
```

**Then push your code:**

```bash
# From your local machine
git add .
git commit -m "Add authentication to cache API"
git push origin main
```

The GitHub Actions workflow will automatically:

1. Check if Redis is installed (install if not)
2. Pull latest code (with authentication)
3. Install/update Python dependencies (including python-dotenv)
4. Update systemd service
5. Restart the API service
6. Verify deployment

**\u2705 Your existing `.env` file with API_TOKEN will NOT be overwritten!**

### 5. Verify Deployment with Authentication

After GitHub Actions completes:

```bash
# SSH into VPS
ssh ubuntu@your-vps-ip

# Test API with authentication
curl -H "Authorization: Bearer your-actual-token" \\\n  http://localhost:8001/health

# Check service logs
sudo journalctl -u cache-api -n 50

# View service status
sudo systemctl status cache-api
```

## Monitoring and Maintenance

### Check Service Status

```bash
# Check if service is running
sudo systemctl status cache-api

# View recent logs
sudo journalctl -u cache-api -n 50 --no-pager

# Follow logs in real-time
sudo journalctl -u cache-api -f
```

### Check Redis Status

```bash
# Check Redis service
sudo systemctl status redis-server

# Check Redis connection
redis-cli ping

# Get Redis info
redis-cli info

# Check cache keys
redis-cli KEYS 'cache:*'
```

### Check API Endpoints

```bash
# Health check (requires authentication)
curl -H "Authorization: Bearer your-token-here" \
  http://localhost:8001/health

# Cache statistics (requires authentication)
curl -H "Authorization: Bearer your-token-here" \
  http://localhost:8001/cache/stats

# Test query (requires authentication)
curl -H "Authorization: Bearer your-token-here" \
  "http://localhost:8001/cache?team=Lakers&sport=Basketball"

# Public endpoint (no auth required)
curl http://localhost:8001/
```

### Service Management Commands

```bash
# Start service
sudo systemctl start cache-api

# Stop service
sudo systemctl stop cache-api

# Restart service
sudo systemctl restart cache-api

# View service status
sudo systemctl status cache-api

# Enable service (start on boot)
sudo systemctl enable cache-api

# Disable service
sudo systemctl disable cache-api
```

### Clear Cache

```bash
# Via API (requires authentication)
curl -X DELETE \
  -H "Authorization: Bearer your-token-here" \
  http://localhost:8001/cache/clear

# Via Redis CLI (direct access, no auth needed)
redis-cli FLUSHDB
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u cache-api -n 100

# Check if port is already in use
sudo netstat -tlnp | grep :8001

# Kill process on port 8001
sudo fuser -k 8001/tcp

# Restart service
sudo systemctl restart cache-api
```

### Redis Connection Issues

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start Redis if stopped
sudo systemctl start redis-server

# Check Redis logs
sudo journalctl -u redis-server -n 50

# Test Redis connection
redis-cli ping
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/services/cache-api

# Fix permissions
chmod +x /home/ubuntu/services/cache-api/venv/bin/python
```

### Database Issues

```bash
# Check if database file exists
ls -la /home/ubuntu/services/cache-api/sports_data.db

# Check permissions
chmod 644 /home/ubuntu/services/cache-api/sports_data.db
```

## Performance Optimization

### Redis Memory Configuration

Edit Redis configuration:

```bash
sudo nano /etc/redis/redis.conf
```

Add or modify:

```conf
# Maximum memory to use
maxmemory 256mb

# Eviction policy when max memory reached
maxmemory-policy allkeys-lru

# Disable persistence if not needed (for pure cache)
save ""
appendonly no
```

Restart Redis:

```bash
sudo systemctl restart redis-server
```

### Monitor Resource Usage

```bash
# Check CPU and memory usage
htop

# Check disk usage
df -h

# Check Redis memory usage
redis-cli INFO memory
```

## Security Best Practices

1. **Firewall Configuration**: Only allow necessary ports
2. **SSH Key Authentication**: Disable password authentication
3. **Redis Password**: Set Redis password in production
4. **Regular Updates**: Keep system packages updated
5. **Log Monitoring**: Regularly check logs for suspicious activity

## Backup and Recovery

### Backup Database

```bash
# Backup SQLite database
cp /home/ubuntu/services/cache-api/sports_data.db ~/backups/sports_data_$(date +%Y%m%d).db

# Backup Redis data (if persistence enabled)
sudo cp /var/lib/redis/dump.rdb ~/backups/redis_$(date +%Y%m%d).rdb
```

### Automated Backups (Cron)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cp /home/ubuntu/services/cache-api/sports_data.db ~/backups/sports_data_$(date +\%Y\%m\%d).db
```

## Updating the Application

Updates are automatically deployed via GitHub Actions when you push to the main branch.

Manual update:

```bash
cd /home/ubuntu/services/cache-api
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart cache-api
```

## Support

For issues or questions:

- Check application logs: `sudo journalctl -u cache-api -n 100`
- Check Redis logs: `sudo journalctl -u redis-server -n 100`
- Review GitHub Actions workflow logs
- Check the API health endpoint: `curl http://localhost:8001/health`
