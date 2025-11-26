# MultinotesAI Deployment Guide

This directory contains all configuration files needed to deploy MultinotesAI in production.

## Files Overview

| File | Description |
|------|-------------|
| `nginx.conf` | Nginx reverse proxy configuration with SSL, rate limiting |
| `supervisor.conf` | Supervisor process manager configuration |
| `gunicorn.conf.py` | Gunicorn WSGI server configuration |
| `Dockerfile` | Docker container build instructions |
| `docker-compose.yml` | Docker Compose multi-container setup |
| `deploy.sh` | Automated deployment script |

## Deployment Options

### Option 1: Traditional Server Deployment

1. **Prerequisites**
   - Ubuntu 22.04 LTS or similar
   - Python 3.11+
   - MySQL 8.0+
   - Redis 7+
   - Nginx
   - Supervisor

2. **Setup Steps**
   ```bash
   # Clone repository
   git clone https://github.com/your-org/multinotesai.git /var/www/multinotesai

   # Create virtual environment
   python3 -m venv /var/www/multinotesai/venv
   source /var/www/multinotesai/venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with production values

   # Run migrations
   python manage.py migrate

   # Collect static files
   python manage.py collectstatic

   # Copy configuration files
   cp deployment/nginx.conf /etc/nginx/sites-available/multinotesai
   ln -s /etc/nginx/sites-available/multinotesai /etc/nginx/sites-enabled/
   cp deployment/supervisor.conf /etc/supervisor/conf.d/multinotesai.conf

   # Start services
   supervisorctl reread
   supervisorctl update
   systemctl reload nginx
   ```

### Option 2: Docker Deployment

1. **Prerequisites**
   - Docker 24+
   - Docker Compose 2+

2. **Setup Steps**
   ```bash
   # Clone repository
   git clone https://github.com/your-org/multinotesai.git
   cd multinotesai

   # Configure environment
   cp .env.example .env
   # Edit .env with production values

   # Build and start containers
   cd deployment
   docker-compose up -d --build

   # Run migrations
   docker-compose exec backend python manage.py migrate

   # View logs
   docker-compose logs -f
   ```

## SSL Certificate Setup

Using Let's Encrypt:

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d multinotesai.com -d www.multinotesai.com -d api.multinotesai.com

# Auto-renewal (add to crontab)
0 12 * * * /usr/bin/certbot renew --quiet
```

## Environment Variables

Required environment variables (see `.env.example` for full list):

```bash
# Core
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=multinotesai.com,api.multinotesai.com

# Database
DB_NAME=multinotesai
DB_USER=multinotesai
DB_PASSWORD=secure-password
DB_HOST=localhost

# Redis
REDIS_URL=redis://localhost:6379/0

# Razorpay
RAZORPAY_KEY_ID=rzp_live_xxx
RAZORPAY_KEY_SECRET=xxx
RAZORPAY_WEBHOOK_SECRET=xxx

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=noreply@multinotesai.com
SMTP_PASSWORD=xxx

# AWS S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_BUCKET=multinotesai-production
```

## Monitoring & Maintenance

### Health Checks
- HTTP: `curl http://localhost:8000/health/`
- Services: `supervisorctl status`
- Docker: `docker-compose ps`

### Logs
- Nginx: `/var/log/nginx/multinotesai_*.log`
- Gunicorn: `/var/log/multinotesai/gunicorn*.log`
- Celery: `/var/log/multinotesai/celery*.log`
- Docker: `docker-compose logs [service]`

### Backup
```bash
# Database backup
mysqldump -u root -p multinotesai > backup.sql

# Media files backup
tar -czvf media_backup.tar.gz /var/www/multinotesai/backend/media/
```

### Scaling
- Increase Gunicorn workers in `gunicorn.conf.py`
- Scale Celery workers: `supervisorctl restart celery_worker`
- Docker: `docker-compose up -d --scale celery_worker=4`

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check if Gunicorn is running: `supervisorctl status gunicorn`
   - Check socket permissions: `ls -la /var/run/multinotesai/`

2. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check Nginx static file path

3. **Database connection error**
   - Verify MySQL is running: `systemctl status mysql`
   - Check credentials in `.env`

4. **Celery tasks not running**
   - Check Redis: `redis-cli ping`
   - Check Celery logs: `supervisorctl tail celery_worker`

## Security Checklist

- [ ] SSL certificate installed and auto-renewal configured
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` set
- [ ] Database credentials secured
- [ ] Firewall configured (only 80, 443 open)
- [ ] Admin panel restricted to specific IPs
- [ ] Regular security updates applied
- [ ] Backup strategy implemented
