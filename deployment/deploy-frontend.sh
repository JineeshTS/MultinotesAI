#!/bin/bash
# =============================================================================
# Deploy Frontend for multinotes.ai
# =============================================================================
# Run this to build and deploy the React frontend
# Usage: bash deploy-frontend.sh
# =============================================================================

set -e

echo "========================================"
echo "  Deploying Frontend"
echo "  Domain: multinotes.ai"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use: sudo bash deploy-frontend.sh)"
    exit 1
fi

FRONTEND_DIR="../multinotes-frontend-main/multinotes-frontend-main"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "ERROR: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
fi

# Create production environment file
echo "Creating frontend environment file..."
cat > "$FRONTEND_DIR/.env.production" << 'EOF'
VITE_API_BASE_URL=https://www.multinotes.ai/api
VITE_WS_BASE_URL=wss://www.multinotes.ai/ws
EOF

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies
echo "Installing dependencies..."
npm install

# Build for production
echo "Building frontend for production..."
npm run build

# Copy to nginx serving directory
echo "Deploying to /var/www/frontend..."
rm -rf /var/www/frontend/*
cp -r dist/* /var/www/frontend/

# Set permissions
chown -R www-data:www-data /var/www/frontend 2>/dev/null || true

echo ""
echo "========================================"
echo "  Frontend Deployed!"
echo "========================================"
echo ""
echo "Your site is now live at:"
echo "  https://www.multinotes.ai"
