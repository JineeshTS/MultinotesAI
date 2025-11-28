#!/bin/bash
# =============================================================================
# Get SSL Certificate for multinotes.ai
# =============================================================================
# Run this AFTER your DNS is pointing to this server
# Usage: bash get-ssl.sh
# =============================================================================

set -e

echo "========================================"
echo "  Getting SSL Certificate"
echo "  Domain: multinotes.ai"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use: sudo bash get-ssl.sh)"
    exit 1
fi

# Stop nginx temporarily to free port 80
echo "Stopping nginx temporarily..."
docker-compose stop nginx 2>/dev/null || true

# Create directories
mkdir -p certbot/conf certbot/www

# Get certificate
echo "Getting SSL certificate from Let's Encrypt..."
echo "Please enter your email when prompted."
echo ""

docker run -it --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d multinotes.ai -d www.multinotes.ai \
    --agree-tos

# Start nginx with SSL
echo "Starting nginx with SSL..."
docker-compose up -d nginx

echo ""
echo "========================================"
echo "  SSL Certificate Installed!"
echo "========================================"
echo ""
echo "Your site is now available at:"
echo "  https://multinotes.ai"
echo "  https://www.multinotes.ai"
