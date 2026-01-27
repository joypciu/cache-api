
import os
import sys

ETERNITY_LABS_FILE = "/etc/nginx/sites-available/eternitylabs"
CACHE_API_FAST_FILE = "/etc/nginx/sites-available/cache-api-fast"

# Paths
CF_CERT = "/home/ubuntu/eternitylabs_cf/ssl_cert.pem"
CF_KEY = "/home/ubuntu/eternitylabs_cf/ssl_key.key"
LE_CERT = "/etc/letsencrypt/live/cache-api-fast.eternitylabs.co/fullchain.pem"
LE_KEY = "/etc/letsencrypt/live/cache-api-fast.eternitylabs.co/privkey.pem"

def fix_eternity_labs():
    print(f"Fixing {ETERNITY_LABS_FILE}...")
    try:
        with open(ETERNITY_LABS_FILE, 'r') as f:
            content = f.read()
        
        # Check if it has the Let's Encrypt certs
        if LE_CERT in content:
            print("Found incorrect Let's Encrypt certs in eternitylabs file. Reverting to Cloudflare certs.")
            new_content = content.replace(LE_CERT, CF_CERT).replace(LE_KEY, CF_KEY)
            
            # Remove the "# managed by Certbot" comments if present
            new_content = new_content.replace("; # managed by Certbot", ";")
            
            with open(ETERNITY_LABS_FILE, 'w') as f:
                f.write(new_content)
            print("Fixed eternitylabs file.")
        else:
            print("eternitylabs file seems fine or doesn't match expected patterns.")
            
    except Exception as e:
        print(f"Error fixing eternitylabs: {e}")
        sys.exit(1)

def fix_cache_api_fast():
    print(f"Fixing {CACHE_API_FAST_FILE}...")
    try:
        with open(CACHE_API_FAST_FILE, 'r') as f:
            content = f.read()
            
        ssl_block = f"""
server {{
    listen 443 ssl; 
    listen [::]:443 ssl;
    http2 on;
    server_name cache-api-fast.eternitylabs.co;

    ssl_certificate {LE_CERT};
    ssl_certificate_key {LE_KEY};

    location / {{
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }}
}}
"""
        # Check if SSL block already exists
        if "listen 443" in content:
            print("SSL block already appears to exist in cache-api-fast.")
        else:
            print("Appending SSL block to cache-api-fast.")
            with open(CACHE_API_FAST_FILE, 'a') as f:
                f.write(ssl_block)

    except Exception as e:
        print(f"Error fixing cache-api-fast: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
        
    fix_eternity_labs()
    fix_cache_api_fast()
    print("Done. Please reload nginx.")
