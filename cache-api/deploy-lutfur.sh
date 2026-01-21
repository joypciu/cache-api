#!/bin/bash

# VPS Deployment Script for Lutfur Cache API Service
# This script automates the deployment process on the VPS

set -e  # Exit on error

echo "=========================================="
echo "Lutfur Cache API VPS Deployment Script"
echo "=========================================="
echo ""

# Configuration
SERVICE_NAME="lutfur"
SERVICE_DIR="/home/ubuntu/services/lutfur"
VENV_DIR="$SERVICE_DIR/venv"
SERVICE_FILE="lutfur.service"
REPO_URL="https://github.com/joypciu/cache-api.git"
REPO_BRANCH="lutfur"
SERVICE_PORT=6002

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if running as correct user
if [ "$USER" != "ubuntu" ]; then
    print_error "This script should be run as the ubuntu user"
    exit 1
fi

# Check if Redis is installed
print_info "Checking Redis installation..."
if ! command -v redis-server &> /dev/null; then
    print_info "Redis not found. Installing Redis..."
    sudo apt update
    sudo apt install redis-server -y
    print_success "Redis installed"
else
    print_success "Redis is already installed"
fi

# Start and enable Redis
print_info "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify Redis is working
if redis-cli ping &> /dev/null; then
    print_success "Redis is running and responding"
else
    print_error "Redis is not responding"
    exit 1
fi

# Create service directory if it doesn't exist
if [ ! -d "$SERVICE_DIR" ]; then
    print_info "Creating service directory..."
    sudo mkdir -p "$SERVICE_DIR"
    sudo chown -R ubuntu:ubuntu /home/ubuntu/services
    print_success "Service directory created"
fi

# Navigate to service directory
cd "$SERVICE_DIR"

# Check if this is first time setup or update
if [ ! -d ".git" ]; then
    print_info "First time setup - cloning repository (lutfur branch)..."
    git clone -b "$REPO_BRANCH" "$REPO_URL" .
    print_success "Repository cloned"
else
    print_info "Updating repository..."
    git fetch origin "$REPO_BRANCH"
    git reset --hard origin/"$REPO_BRANCH"
    print_success "Repository updated"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment and install dependencies
print_info "Installing/updating Python dependencies..."
source venv/bin/activate
cd cache-api
pip install --upgrade pip
pip install -r requirements.txt
deactivate
print_success "Dependencies installed"

# Create systemd service file
print_info "Installing systemd service..."
sudo tee /etc/systemd/system/"$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Lutfur Cache API Service
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$SERVICE_DIR/cache-api
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="REDIS_HOST=localhost"
Environment="REDIS_PORT=6379"
Environment="CACHE_TTL=3600"
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF
print_success "Service file created"

# Reload systemd
print_info "Reloading systemd daemon..."
sudo systemctl daemon-reload
print_success "Systemd daemon reloaded"

# Enable and start service
print_info "Enabling and starting $SERVICE_NAME service..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
print_success "Service started"

# Wait a moment for service to start
sleep 3

# Check service status
print_info "Checking service status..."
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "$SERVICE_NAME service is running!"
    sudo systemctl status "$SERVICE_NAME" --no-pager | head -15
else
    print_error "$SERVICE_NAME service failed to start"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    exit 1
fi

# Check if firewall needs port opened
print_info "Checking firewall configuration..."
if sudo ufw status | grep -q "Status: active"; then
    if ! sudo ufw status | grep -q "$SERVICE_PORT"; then
        print_info "Opening port $SERVICE_PORT in firewall..."
        sudo ufw allow "$SERVICE_PORT/tcp"
        print_success "Port $SERVICE_PORT opened"
    else
        print_success "Port $SERVICE_PORT already open"
    fi
else
    print_info "UFW firewall not active"
fi

# Test the service
print_info "Testing service endpoint..."
sleep 2
if curl -s http://localhost:$SERVICE_PORT/ > /dev/null; then
    print_success "Service is responding on port $SERVICE_PORT!"
else
    print_error "Service is not responding on port $SERVICE_PORT"
fi

echo ""
print_success "=========================================="
print_success "Deployment completed successfully!"
print_success "=========================================="
echo ""
echo "Service Name: $SERVICE_NAME"
echo "Service Directory: $SERVICE_DIR"
echo "Port: $SERVICE_PORT"
echo "Status: sudo systemctl status $SERVICE_NAME"
echo "Logs: sudo journalctl -u $SERVICE_NAME -f"
echo "Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
print_success "Service is now running at http://localhost:$SERVICE_PORT"
