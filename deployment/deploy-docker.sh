#!/bin/bash
# =============================================================================
# MultinotesAI Docker Deployment Script
# Domain: multinotes.ai
# =============================================================================
# Run this script on your Hostinger VPS to deploy the application
# Usage: bash deploy-docker.sh
# =============================================================================

set -e  # Exit on any error

echo "========================================"
echo "  MultinotesAI Docker Deployment"
echo "  Domain: multinotes.ai"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use: sudo bash deploy-docker.sh)${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 1: Check if .env file exists
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 1: Checking environment file...${NC}"
if [ ! -f "../.env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please create .env file first:"
    echo "  cp ../.env.production ../.env"
    echo "  nano ../.env"
    echo "Then fill in your values and run this script again."
    exit 1
fi
echo -e "${GREEN}✓ .env file found${NC}"

# -----------------------------------------------------------------------------
# Step 2: Create necessary directories
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 2: Creating directories...${NC}"
mkdir -p certbot/conf certbot/www
mkdir -p /var/www/frontend
echo -e "${GREEN}✓ Directories created${NC}"

# -----------------------------------------------------------------------------
# Step 3: Build and start containers
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 3: Building and starting Docker containers...${NC}"
docker-compose down 2>/dev/null || true
docker-compose up -d --build

echo "Waiting for services to start (60 seconds)..."
sleep 60

# -----------------------------------------------------------------------------
# Step 4: Check if containers are running
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 4: Checking container status...${NC}"
docker-compose ps

# -----------------------------------------------------------------------------
# Step 5: Run database migrations
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 5: Running database migrations...${NC}"
docker-compose exec -T backend python manage.py migrate --noinput

# -----------------------------------------------------------------------------
# Step 6: Collect static files
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 6: Collecting static files...${NC}"
docker-compose exec -T backend python manage.py collectstatic --noinput

# -----------------------------------------------------------------------------
# Done!
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}========================================"
echo "  Deployment Complete!"
echo "========================================"
echo -e "${NC}"
echo "Next steps:"
echo "1. Point your domain DNS to this server's IP"
echo "2. Get SSL certificate (run: bash get-ssl.sh)"
echo "3. Build and deploy frontend (run: bash deploy-frontend.sh)"
echo ""
echo "To check logs: docker-compose logs -f"
echo "To restart: docker-compose restart"
