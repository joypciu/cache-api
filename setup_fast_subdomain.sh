#!/bin/bash

# Setup script for non-proxied cache-api-fast subdomain
# This script configures Nginx and Let's Encrypt SSL for cache-api-fast.eternitylabs.co

set -e

DOMAIN="cache-api-fast.eternitylabs.co"
# EMAIL="admin@eternitylabs.co" # Default email for Let's Encrypt
APP_PORT=5000

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' 

echo -e "${GREEN}Starting setup for $DOMAIN...${NC}"

# 1. Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Please run as root or with sudo${NC}"
  exit 1
fi

# 2. Check for Certbot
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# 3. Create Nginx Configuration (HTTP only first for Certbot)
echo "Creating Nginx configuration..."

cat > /etc/nginx/sites-available/cache-api-fast <<EOL
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeouts for long searches (as requested)
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
EOL

# 4. Enable the site
echo "Enabling site..."
ln -sf /etc/nginx/sites-available/cache-api-fast /etc/nginx/sites-enabled/

# 5. Test and Reload Nginx
echo "Testing Nginx config..."
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
else
    echo -e "${RED}Nginx config test failed.${NC}"
    exit 1
fi

# 6. Obtain SSL Certificate
echo "Obtaining SSL certificate with Certbot..."
echo "NOTE: This requires $DOMAIN to point to this server's IP and NOT be proxied (Grey Cloud in Cloudflare)"

certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect

# 7. Final Reload (Certbot usually does this, but to be sure)
systemctl reload nginx

echo -e "${GREEN}Setup complete! $DOMAIN is now serving HTTPS and pointing to port $APP_PORT${NC}"
