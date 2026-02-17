#!/bin/bash

# VPS Deployment Script for Cache API
# This script automates the deployment process on the VPS

set -e  # Exit on error

echo "=========================================="
echo "Cache API VPS Deployment Script"
echo "=========================================="
echo ""

# Configuration
SERVICE_NAME="cache-api"
SERVICE_DIR="/home/ubuntu/services/cache-api"
VENV_DIR="$SERVICE_DIR/venv"
SERVICE_FILE="cache-api.service"
REPO_URL="https://github.com/joypciu/cache-api.git"

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
    print_info "First time setup - cloning repository..."
    git clone "$REPO_URL" .
    print_success "Repository cloned"
else
    print_info "Updating repository..."
    git fetch origin
    git reset --hard origin/main
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
pip install --upgrade pip
pip install -r requirements.txt --upgrade
print_success "Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
        print_info "Please edit .env file with your configuration"
    else
        print_error ".env.example not found"
    fi
else
    print_success ".env file already exists"
fi

# Install systemd service
print_info "Installing systemd service..."
sudo cp "$SERVICE_FILE" "/etc/systemd/system/$SERVICE_FILE"
sudo systemctl daemon-reload
print_success "Systemd service installed"

# Kill any existing process on port 5000
print_info "Checking for existing process on port 5000..."
sudo fuser -k 5000/tcp 2>/dev/null || true

# Enable and restart service
print_info "Starting $SERVICE_NAME service..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Wait for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "$SERVICE_NAME service is running"
else
    print_error "$SERVICE_NAME service failed to start"
    print_info "Checking logs..."
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    exit 1
fi

# Verify API is responding
print_info "Verifying API is responding..."
if curl -f http://localhost:5000/health &> /dev/null; then
    print_success "API is responding on port 8001"
else
    print_error "API is not responding"
fi

# Show status
echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo ""

# Service status
print_info "Service Status:"
sudo systemctl status "$SERVICE_NAME" --no-pager | head -n 10

echo ""

# Redis status
print_info "Redis Status:"
sudo systemctl status redis-server --no-pager | head -n 5

echo ""

# Port status
print_info "Port 8001 Status:"
sudo netstat -tlnp | grep :8001 || echo "Port not listening"

echo ""

# Cache statistics
print_info "Cache Statistics:"
curl -s http://localhost:8001/cache/stats | python3 -m json.tool 2>/dev/null || echo "Could not fetch cache stats"

echo ""
echo "=========================================="
print_success "Deployment completed successfully!"
echo "=========================================="
echo ""
print_info "Useful commands:"
echo "  View logs:         sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart service:   sudo systemctl restart $SERVICE_NAME"
echo "  Check status:      sudo systemctl status $SERVICE_NAME"
echo "  Clear cache:       curl -X DELETE http://localhost:8001/cache/clear"
echo ""
