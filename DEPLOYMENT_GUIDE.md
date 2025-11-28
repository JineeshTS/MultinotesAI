# MultinotesAI Production Deployment Guide

This guide will help you deploy MultinotesAI to production step by step.

---

## What You Need Before Starting

Before deploying, you need to sign up for these services:

### Required Accounts (Must Have)

| Service | Purpose | Sign Up Link | Cost |
|---------|---------|--------------|------|
| **DigitalOcean** | Hosting your app | https://digitalocean.com | ~$24/month |
| **Domain Name** | Your website address | Namecheap, GoDaddy, etc. | ~$12/year |

### API Keys You Need

| Service | Purpose | Get It From |
|---------|---------|-------------|
| **Together AI** | AI chat models | https://together.ai |
| **Google Gemini** | AI features | https://makersuite.google.com/app/apikey |
| **Razorpay** | Payments | https://razorpay.com (for India) |
| **AWS S3** | File storage | https://aws.amazon.com |
| **Google OAuth** | Login with Google | https://console.cloud.google.com |
| **SMTP Email** | Sending emails | Gmail or SendGrid |

---

## Step 1: Create DigitalOcean Account

1. Go to https://digitalocean.com
2. Click "Sign Up"
3. Create account with email or Google
4. Add a payment method (credit card)

---

## Step 2: Create a Droplet (Server)

1. Click **"Create"** → **"Droplets"**
2. Choose these settings:

   | Setting | What to Select |
   |---------|----------------|
   | Region | Choose closest to your users (e.g., Bangalore for India) |
   | Image | **Docker on Ubuntu 22.04** (from Marketplace tab) |
   | Size | **Basic** → **Regular** → **$24/mo** (4GB RAM, 2 CPUs) |
   | Authentication | **Password** (create a strong password and save it!) |
   | Hostname | `multinotesai-server` |

3. Click **"Create Droplet"**
4. Wait 1-2 minutes for it to be ready
5. **Copy the IP address** shown (looks like: `143.198.xxx.xxx`)

---

## Step 3: Connect to Your Server

### On Windows:
1. Download **PuTTY** from https://putty.org
2. Open PuTTY
3. Enter your Droplet IP address
4. Click "Open"
5. Login as: `root`
6. Enter your password

### On Mac/Linux:
1. Open Terminal
2. Type: `ssh root@YOUR_IP_ADDRESS`
3. Enter your password

---

## Step 4: Upload Your Code to Server

Once connected to your server, run these commands one by one:

```bash
# 1. Install Git
apt update && apt install -y git

# 2. Clone your repository (replace with your actual repo URL)
cd /home
git clone https://github.com/YOUR_USERNAME/MultinotesAI.git
cd MultinotesAI

# 3. Switch to the correct branch
git checkout claude/review-wbs-tasks-01Xda3wVEXMSLiVfQfZEXAQR
```

---

## Step 5: Create Environment File

Run this command to create your environment file:

```bash
nano /home/MultinotesAI/.env
```

Copy and paste the following, then **replace all the placeholder values** with your actual values:

```
# =============================================================================
# DJANGO CORE SETTINGS
# =============================================================================
SECRET_KEY=generate-a-random-50-character-string-here
DEBUG=False
ALLOWED_HOSTS=YOUR_DOMAIN.com,www.YOUR_DOMAIN.com,YOUR_IP_ADDRESS

# Frontend URL
FRONTEND_URL=https://YOUR_DOMAIN.com

# =============================================================================
# DATABASE (No changes needed - Docker handles this)
# =============================================================================
DB_NAME=multinotesai
DB_USER=multinotesai
DB_PASSWORD=CHOOSE_A_STRONG_PASSWORD_HERE
DB_HOST=mysql
DB_PORT=3306
DB_ROOT_PASSWORD=CHOOSE_ANOTHER_STRONG_PASSWORD

# =============================================================================
# REDIS (No changes needed)
# =============================================================================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# =============================================================================
# AWS S3 - For file uploads
# =============================================================================
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY
AWS_BUCKET=your-bucket-name
AWS_DEFAULT_REGION=ap-south-1

# =============================================================================
# EMAIL - For sending verification emails
# =============================================================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# =============================================================================
# RAZORPAY - For payments
# =============================================================================
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your-razorpay-secret
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret

# =============================================================================
# GOOGLE LOGIN
# =============================================================================
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://YOUR_DOMAIN.com/auth/google/callback

# =============================================================================
# AI API KEYS
# =============================================================================
TOGETHER_API_KEY=your-together-api-key
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# =============================================================================
# SECURITY (Leave as is for production)
# =============================================================================
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOW_ALL=False
CORS_ALLOWED_ORIGINS=https://YOUR_DOMAIN.com,https://www.YOUR_DOMAIN.com
CSRF_TRUSTED_ORIGINS=https://YOUR_DOMAIN.com,https://www.YOUR_DOMAIN.com

# =============================================================================
# MONITORING
# =============================================================================
LOG_LEVEL=INFO
SENTRY_DSN=
ENVIRONMENT=production
APP_VERSION=2.0.0
```

**To save the file:**
- Press `Ctrl + X`
- Press `Y` to confirm
- Press `Enter`

---

## Step 6: Create Nginx Configuration

```bash
nano /home/MultinotesAI/deployment/nginx.conf
```

Paste this (replace YOUR_DOMAIN.com):

```nginx
upstream backend {
    server backend:8000;
}

upstream websocket {
    server daphne:8001;
}

server {
    listen 80;
    server_name YOUR_DOMAIN.com www.YOUR_DOMAIN.com;

    # For SSL certificate verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN.com www.YOUR_DOMAIN.com;

    # SSL certificates (will be created later)
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API requests
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket connections
    location /ws/ {
        proxy_pass http://websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Static files
    location /static/ {
        alias /var/www/static/;
    }

    # Media files
    location /media/ {
        alias /var/www/media/;
    }

    # Health check
    location /health/ {
        proxy_pass http://backend;
    }

    # Frontend (root)
    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

Save with `Ctrl + X`, then `Y`, then `Enter`.

---

## Step 7: Create MySQL Init File

```bash
mkdir -p /home/MultinotesAI/deployment/mysql
nano /home/MultinotesAI/deployment/mysql/init.sql
```

Paste this:

```sql
-- Set character encoding
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS multinotesai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

Save the file.

---

## Step 8: Start the Application

```bash
cd /home/MultinotesAI/deployment

# Start all services
docker-compose up -d

# Wait about 2 minutes, then check if everything is running
docker-compose ps
```

You should see all services as "Up":
- `multinotesai-backend`
- `multinotesai-mysql`
- `multinotesai-redis`
- `multinotesai-nginx`
- `multinotesai-celery-worker`
- `multinotesai-celery-beat`
- `multinotesai-daphne`

---

## Step 9: Run Database Migrations

```bash
# Enter the backend container
docker-compose exec backend bash

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Exit container
exit
```

---

## Step 10: Point Your Domain to Server

1. Go to your domain registrar (Namecheap, GoDaddy, etc.)
2. Find **DNS Settings** or **Manage DNS**
3. Add these records:

   | Type | Host | Value | TTL |
   |------|------|-------|-----|
   | A | @ | YOUR_DROPLET_IP | 3600 |
   | A | www | YOUR_DROPLET_IP | 3600 |

4. Wait 5-30 minutes for DNS to propagate

---

## Step 11: Get Free SSL Certificate

```bash
cd /home/MultinotesAI/deployment

# Create certbot directories
mkdir -p certbot/conf certbot/www

# Get SSL certificate (replace YOUR_DOMAIN.com and YOUR_EMAIL)
docker run -it --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d YOUR_DOMAIN.com -d www.YOUR_DOMAIN.com \
    --email YOUR_EMAIL@example.com \
    --agree-tos --no-eff-email

# Restart nginx to use the certificate
docker-compose restart nginx
```

---

## Step 12: Deploy Frontend

### Option A: Host on Same Server

```bash
cd /home/MultinotesAI/multinotes-frontend-main/multinotes-frontend-main

# Create production environment file
nano .env.production
```

Add:
```
VITE_API_BASE_URL=https://YOUR_DOMAIN.com/api
VITE_WS_BASE_URL=wss://YOUR_DOMAIN.com/ws
VITE_GOOGLE_CLIENT_ID=your-google-client-id
```

Build and deploy:
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs

# Install dependencies and build
npm install
npm run build

# Copy to nginx serving directory
mkdir -p /var/www/frontend
cp -r dist/* /var/www/frontend/
```

### Option B: Host on Vercel (Easier)

1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "New Project"
4. Import your repository
5. Set the root directory to `multinotes-frontend-main/multinotes-frontend-main`
6. Add environment variables:
   - `VITE_API_BASE_URL` = `https://YOUR_DOMAIN.com/api`
   - `VITE_WS_BASE_URL` = `wss://YOUR_DOMAIN.com/ws`
   - `VITE_GOOGLE_CLIENT_ID` = your Google client ID
7. Click "Deploy"

---

## Step 13: Verify Everything Works

1. Visit `https://YOUR_DOMAIN.com` - You should see the login page
2. Try to register a new account
3. Check your email for verification
4. Log in and test the AI chat

---

## Troubleshooting

### Check Logs

```bash
cd /home/MultinotesAI/deployment

# See all logs
docker-compose logs

# See specific service logs
docker-compose logs backend
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f backend
```

### Restart Services

```bash
# Restart everything
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Common Issues

| Problem | Solution |
|---------|----------|
| "502 Bad Gateway" | Wait 2-3 minutes for backend to start, then refresh |
| "Connection refused" | Check if all containers are running: `docker-compose ps` |
| Email not sending | Verify SMTP credentials and check spam folder |
| Payments not working | Verify Razorpay keys and webhook URL |

---

## Monthly Maintenance

### Update SSL Certificate (Every 90 Days)

```bash
cd /home/MultinotesAI/deployment
docker-compose stop nginx
docker run -it --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -p 80:80 \
    certbot/certbot renew
docker-compose start nginx
```

### Backup Database

```bash
docker-compose exec mysql mysqldump -u multinotesai -p multinotesai > backup_$(date +%Y%m%d).sql
```

---

## Cost Summary

| Service | Monthly Cost |
|---------|--------------|
| DigitalOcean Droplet (4GB) | $24 |
| Domain Name | ~$1 (yearly $12) |
| Together AI | Pay as you go (~$5-50) |
| AWS S3 | Pay as you go (~$1-5) |
| Razorpay | 2% per transaction |
| **Total** | ~$30-80/month |

---

## Need Help?

If you get stuck, share:
1. The exact error message
2. Which step you're on
3. Output of `docker-compose logs`

Good luck with your launch! 🚀
