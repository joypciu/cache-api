#!/bin/bash

# Quick Start Script for Cache API with Redis
# This script sets up and starts the cache API with Redis caching

echo "======================================"
echo "Cache API - Quick Start with Redis"
echo "======================================"
echo ""

# Check if Redis is installed
echo "Checking Redis installation..."
if ! command -v redis-cli &> /dev/null; then
    echo "❌ Redis is not installed"
    echo "Installing Redis..."
    sudo apt install redis-server -y
else
    echo "✅ Redis is installed"
fi

# Start Redis service
echo ""
echo "Starting Redis service..."
sudo service redis-server start

# Check Redis connection
echo ""
echo "Testing Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running (PONG received)"
else
    echo "❌ Redis is not responding"
    echo "Try: sudo service redis-server restart"
    exit 1
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd "$(dirname "$0")/cache-api"
pip install -r requirements.txt --quiet

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env configuration file..."
    cp .env.example .env
    echo "✅ Created .env file with default settings"
else
    echo "✅ .env file already exists"
fi

# Run Redis integration test
echo ""
echo "Running Redis integration tests..."
cd ..
python test_redis_integration.py

# Ask if user wants to start the API
echo ""
read -p "Start the API server now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting Cache API on http://localhost:8001..."
    echo "Press Ctrl+C to stop"
    echo ""
    cd cache-api
    python main.py
fi
