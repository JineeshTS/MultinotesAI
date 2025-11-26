# Deployment Runbook - MultinotesAI

This runbook provides step-by-step instructions for deploying MultinotesAI to production. Follow each step carefully and verify completion before proceeding.

**Last Updated**: 2025-11-26
**Version**: 2.0.0
**Environment**: Production

---

## Table of Contents
- [Overview](#overview)
- [Pre-Deployment Preparation](#pre-deployment-preparation)
- [Pre-Deployment Checks](#pre-deployment-checks)
- [Deployment Process](#deployment-process)
- [Post-Deployment Verification](#post-deployment-verification)
- [Health Check Endpoints](#health-check-endpoints)
- [Monitoring Dashboard Access](#monitoring-dashboard-access)
- [Troubleshooting](#troubleshooting)
- [Emergency Rollback](#emergency-rollback)

---

## Overview

### Deployment Architecture
- **Application**: Django 5.0.2 with Gunicorn WSGI server
- **Web Server**: Nginx (reverse proxy, static files)
- **Database**: MySQL 8.0
- **Cache/Queue**: Redis 7.0
- **Task Queue**: Celery with Redis broker
- **File Storage**: AWS S3
- **Monitoring**: Sentry (errors), system logs

### Deployment Method
- **Primary**: Docker Compose (recommended)
- **Alternative**: Manual deployment with systemd

### Deployment Windows
- **Preferred**: Tuesday-Thursday, 2:00 AM - 4:00 AM UTC (low traffic)
- **Avoid**: Friday-Monday, holidays, high-traffic periods

---

## Pre-Deployment Preparation

### 1. Coordinate with Team
```bash
# Send deployment notification (at least 24 hours before):
Subject: [DEPLOYMENT NOTICE] MultinotesAI v2.0.0 - [Date/Time]

Team,

Deployment scheduled for: [Date] at [Time] UTC
Expected duration: 30-45 minutes
Expected downtime: 5-10 minutes (database migrations)

Changes:
- [Major feature 1]
- [Major feature 2]
- [Bug fixes]

Rollback plan: Available if issues occur
On-call engineer: [Name] - [Contact]
```

### 2. Verify Code Ready for Deployment
```bash
# Ensure you're on the correct branch:
git fetch --all
git checkout main  # or production branch
git pull origin main

# Verify latest commit:
git log -1 --oneline

# Verify all tests pass:
pytest --verbose --cov=.

# Verify no uncommitted changes:
git status
```

### 3. Create Release Tag
```bash
# Tag the release:
git tag -a v2.0.0 -m "Release v2.0.0 - Multi-LLM platform launch"
git push origin v2.0.0

# Verify tag created:
git tag -l "v2.0.0"
```

### 4. Backup Production Database
```bash
# SSH to production server:
ssh deploy@production-server

# Create manual backup before deployment:
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME | gzip > /backups/pre-deploy-$BACKUP_DATE.sql.gz

# Verify backup created:
ls -lh /backups/pre-deploy-$BACKUP_DATE.sql.gz

# Upload to S3 for safety:
aws s3 cp /backups/pre-deploy-$BACKUP_DATE.sql.gz s3://multinotesai-backups/database/pre-deploy/
```

### 5. Prepare Environment File
```bash
# Verify production .env file has all required variables:
cd /var/www/multinotesai

# Check environment variables (don't print secrets):
cat > check_env.py << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS',
    'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT',
    'REDIS_URL', 'CELERY_BROKER_URL',
    'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_BUCKET',
    'SENTRY_DSN',
    'TOGETHER_API_KEY', 'GEMINI_API_KEY', 'OPENAI_API_KEY',
    'RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET',
]

missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ Missing variables: {', '.join(missing)}")
    exit(1)
else:
    print("✓ All required environment variables present")
    print(f"DEBUG={os.getenv('DEBUG')}")
EOF

python check_env.py
rm check_env.py
```

---

## Pre-Deployment Checks

### Health Check Current System
```bash
# 1. Check current application status:
curl -I https://api.multinotesai.com/health/

# 2. Check all services running:
sudo systemctl status nginx
sudo systemctl status gunicorn  # or docker ps for Docker setup
sudo systemctl status celery
sudo systemctl status redis

# 3. Check database connectivity:
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT 1;" $DB_NAME

# 4. Check Redis connectivity:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD ping

# 5. Check S3 access:
aws s3 ls s3://multinotesai-bucket/ --profile production

# 6. Check disk space (need at least 10% free):
df -h

# 7. Check memory:
free -h

# 8. Check current error rate in Sentry:
# Visit: https://sentry.io/organizations/multinotesai/projects/
```

### Verify Dependencies
```bash
# Check Python version:
python --version  # Should be 3.11+

# Check pip version:
pip --version

# Check all services:
docker --version  # If using Docker
docker-compose --version
```

---

## Deployment Process

Choose your deployment method:
- **Method A**: [Docker Compose Deployment](#method-a-docker-compose-deployment) (Recommended)
- **Method B**: [Manual Deployment](#method-b-manual-deployment)

---

### Method A: Docker Compose Deployment

#### Step 1: Pull Latest Code
```bash
# SSH to production server:
ssh deploy@production-server

# Navigate to application directory:
cd /var/www/multinotesai

# Pull latest code:
git fetch --all
git checkout v2.0.0  # Use the tagged version

# Verify correct version:
git describe --tags
```

#### Step 2: Build Docker Images
```bash
# Build new images:
docker-compose build --no-cache

# Verify images built:
docker images | grep multinotesai
```

#### Step 3: Run Database Migrations (Zero-Downtime)
```bash
# Run migrations before deploying new code:
docker-compose run --rm web python manage.py migrate --plan

# Review migration plan, then execute:
docker-compose run --rm web python manage.py migrate

# Verify migrations applied:
docker-compose run --rm web python manage.py showmigrations
```

#### Step 4: Collect Static Files
```bash
# Collect static files:
docker-compose run --rm web python manage.py collectstatic --noinput

# Verify static files:
ls -la /var/www/multinotesai/staticfiles/
```

#### Step 5: Deploy New Containers
```bash
# Stop old containers and start new ones:
docker-compose down

# Start new containers:
docker-compose up -d

# Verify all containers running:
docker-compose ps

# Expected output:
# NAME                STATUS              PORTS
# multinotesai_web    Up 10 seconds       0.0.0.0:8000->8000/tcp
# multinotesai_celery Up 10 seconds
# multinotesai_redis  Up 10 seconds       0.0.0.0:6379->6379/tcp
# multinotesai_db     Up 10 seconds       0.0.0.0:3306->3306/tcp
```

#### Step 6: Verify Container Health
```bash
# Check logs for errors:
docker-compose logs --tail=50 web
docker-compose logs --tail=50 celery

# Check web container health:
docker-compose exec web python manage.py check

# Test database connection:
docker-compose exec web python manage.py dbshell
# > SELECT 1;
# > exit;
```

---

### Method B: Manual Deployment

#### Step 1: Enable Maintenance Mode
```bash
# Put site in maintenance mode:
sudo cp /etc/nginx/sites-available/maintenance.conf /etc/nginx/sites-enabled/multinotesai.conf
sudo systemctl reload nginx

# Verify maintenance page showing:
curl -I https://api.multinotesai.com/
```

#### Step 2: Stop Application Services
```bash
# Stop Gunicorn:
sudo systemctl stop gunicorn

# Stop Celery:
sudo systemctl stop celery

# Verify services stopped:
sudo systemctl status gunicorn
sudo systemctl status celery
```

#### Step 3: Update Code
```bash
# Navigate to application directory:
cd /var/www/multinotesai

# Pull latest code:
git fetch --all
git checkout v2.0.0

# Activate virtual environment:
source venv/bin/activate

# Update dependencies:
pip install --upgrade pip
pip install -r multinotes-backend-llm-model-V2.0/commonai-backend-llm-model-V2.0/requirements.txt
```

#### Step 4: Run Database Migrations
```bash
# Navigate to Django project:
cd multinotes-backend-llm-model-V2.0/commonai-backend-llm-model-V2.0

# Check migrations plan:
python manage.py migrate --plan

# Run migrations:
python manage.py migrate

# Verify no unapplied migrations:
python manage.py showmigrations | grep "\[ \]"
```

#### Step 5: Collect Static Files
```bash
# Collect static files:
python manage.py collectstatic --noinput

# Verify static files collected:
ls -la staticfiles/
```

#### Step 6: Start Services
```bash
# Start Gunicorn:
sudo systemctl start gunicorn
sudo systemctl status gunicorn

# Start Celery:
sudo systemctl start celery
sudo systemctl status celery

# Verify services running:
ps aux | grep gunicorn
ps aux | grep celery
```

#### Step 7: Disable Maintenance Mode
```bash
# Restore normal nginx config:
sudo cp /etc/nginx/sites-available/multinotesai.conf /etc/nginx/sites-enabled/multinotesai.conf
sudo systemctl reload nginx

# Verify nginx config valid:
sudo nginx -t
```

---

## Post-Deployment Verification

### Immediate Checks (0-5 minutes)

#### 1. HTTP Status Check
```bash
# Check homepage:
curl -I https://api.multinotesai.com/
# Expected: HTTP/2 200

# Check health endpoint:
curl https://api.multinotesai.com/health/
# Expected: {"status": "healthy", "database": "connected", "cache": "connected"}

# Check API endpoint:
curl https://api.multinotesai.com/api/v1/status/
# Expected: {"version": "2.0.0", "status": "operational"}
```

#### 2. Application Logs
```bash
# Check Gunicorn logs (last 50 lines):
sudo tail -50 /var/log/multinotesai/gunicorn.log

# Check for errors:
sudo tail -100 /var/log/multinotesai/gunicorn.log | grep -i error

# For Docker:
docker-compose logs --tail=50 web
```

#### 3. Nginx Logs
```bash
# Check Nginx access log:
sudo tail -50 /var/log/nginx/access.log

# Check Nginx error log:
sudo tail -50 /var/log/nginx/error.log

# Check for 5xx errors:
sudo tail -100 /var/log/nginx/access.log | grep " 5[0-9][0-9] "
```

#### 4. Database Connection
```bash
# Test database query:
python manage.py dbshell
# Run query:
# > SELECT COUNT(*) FROM authentication_customuser;
# > exit;

# Or via Django shell:
python manage.py shell
# >>> from authentication.models import CustomUser
# >>> CustomUser.objects.count()
# >>> exit()
```

#### 5. Redis Connection
```bash
# Test Redis connection:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD ping
# Expected: PONG

# Test cache:
python manage.py shell
# >>> from django.core.cache import cache
# >>> cache.set('test_deploy', 'success', 60)
# >>> cache.get('test_deploy')
# Expected: 'success'
# >>> exit()
```

#### 6. Celery Tasks
```bash
# Check Celery workers:
celery -A backend inspect active

# Check Celery stats:
celery -A backend inspect stats

# Test async task:
python manage.py shell
# >>> from authentication.tasks import test_task  # Create a simple test task
# >>> result = test_task.delay()
# >>> result.get(timeout=10)
# >>> exit()
```

#### 7. S3 File Operations
```bash
# Test S3 upload:
python manage.py shell
# >>> from django.core.files.base import ContentFile
# >>> from django.core.files.storage import default_storage
# >>> path = default_storage.save('test_deploy.txt', ContentFile(b'Deployment test'))
# >>> url = default_storage.url(path)
# >>> print(url)  # Should return S3 presigned URL
# >>> default_storage.delete(path)
# >>> exit()
```

### Functional Tests (5-15 minutes)

#### 1. User Authentication
```bash
# Test user login:
curl -X POST https://api.multinotesai.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'

# Expected: {"access": "...", "refresh": "..."}
```

#### 2. API Endpoints
```bash
# Save access token:
TOKEN="your_access_token_here"

# Test protected endpoint:
curl -H "Authorization: Bearer $TOKEN" \
  https://api.multinotesai.com/api/v1/prompts/

# Test LLM models endpoint:
curl -H "Authorization: Bearer $TOKEN" \
  https://api.multinotesai.com/api/v1/llm-models/

# Test folders endpoint:
curl -H "Authorization: Bearer $TOKEN" \
  https://api.multinotesai.com/api/v1/folders/
```

#### 3. WebSocket Connection
```bash
# Test WebSocket connection (requires wscat):
npm install -g wscat

wscat -c "wss://api.multinotesai.com/ws/prompts/?token=$TOKEN"
# Should connect successfully
```

#### 4. Payment Integration
```bash
# Test Razorpay order creation:
curl -X POST https://api.multinotesai.com/api/v1/payments/create-order/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":1,"amount":999}'

# Expected: Order created response with Razorpay order ID
```

#### 5. File Upload
```bash
# Test file upload:
curl -X POST https://api.multinotesai.com/api/v1/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_document.pdf" \
  -F "title=Test Document"

# Expected: Document uploaded successfully
```

### Monitoring Checks (15-30 minutes)

#### 1. Sentry Errors
```bash
# Visit Sentry dashboard:
# https://sentry.io/organizations/multinotesai/projects/

# Check for new errors in last 30 minutes
# Acceptable: 0 critical errors, <5 warnings
```

#### 2. Response Times
```bash
# Monitor response times for 15 minutes:
for i in {1..30}; do
  curl -w "Time: %{time_total}s\n" -o /dev/null -s https://api.multinotesai.com/health/
  sleep 30
done

# Average should be <500ms
```

#### 3. Error Rate
```bash
# Check Nginx access logs for error rate:
sudo tail -1000 /var/log/nginx/access.log | awk '{print $9}' | sort | uniq -c | sort -rn

# Check for 5xx errors:
ERROR_COUNT=$(sudo tail -1000 /var/log/nginx/access.log | grep -c " 5[0-9][0-9] ")
TOTAL_COUNT=$(sudo wc -l < <(sudo tail -1000 /var/log/nginx/access.log))
ERROR_RATE=$(echo "scale=2; $ERROR_COUNT * 100 / $TOTAL_COUNT" | bc)

echo "Error rate: $ERROR_RATE%"
# Should be <1%
```

#### 4. Resource Usage
```bash
# Check CPU usage:
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}'
# Should be <70%

# Check memory usage:
free -h

# Check disk usage:
df -h
# Should have >10% free

# For Docker:
docker stats --no-stream
```

#### 5. Database Performance
```bash
# Check slow query log:
sudo tail -50 /var/log/mysql/slow-query.log

# Check active connections:
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SHOW STATUS LIKE 'Threads_connected';" $DB_NAME

# Check max connections used:
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SHOW STATUS LIKE 'Max_used_connections';" $DB_NAME
```

#### 6. Redis Performance
```bash
# Check Redis stats:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD INFO stats

# Check memory usage:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD INFO memory | grep used_memory_human

# Check connected clients:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD INFO clients
```

---

## Health Check Endpoints

### Primary Health Check
```bash
GET /health/
```

**Response (Healthy)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "connected",
    "cache": "connected",
    "celery": "running",
    "storage": "connected"
  }
}
```

**Response (Unhealthy)**:
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-26T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "error: connection refused",
    "cache": "connected",
    "celery": "warning: no workers",
    "storage": "connected"
  }
}
```

### API Status Check
```bash
GET /api/v1/status/
```

**Response**:
```json
{
  "version": "2.0.0",
  "status": "operational",
  "environment": "production",
  "uptime": 86400
}
```

### Database Health Check
```bash
# Create management command if not exists:
# management/commands/check_db.py

python manage.py check_db
```

### Celery Health Check
```bash
# Check Celery workers:
celery -A backend inspect ping

# Expected output:
# -> celery@worker1: OK
# pong
```

---

## Monitoring Dashboard Access

### Sentry (Error Tracking)
- **URL**: https://sentry.io/organizations/multinotesai/
- **Project**: multinotesai-backend
- **Access**: DevOps team, Team Leads
- **Key Metrics**:
  - Error rate (last 24h)
  - New issues
  - Unresolved issues
  - Performance (transaction throughput, p95/p99)

### Server Monitoring (Choose your tool)

#### Option 1: Grafana + Prometheus
- **URL**: https://monitoring.multinotesai.com/
- **Dashboards**:
  - System Overview
  - Application Performance
  - Database Metrics
  - Redis Metrics
  - Nginx Metrics

#### Option 2: AWS CloudWatch
- **URL**: https://console.aws.amazon.com/cloudwatch/
- **Metrics to Monitor**:
  - EC2 CPU/Memory
  - RDS connections/queries
  - ElastiCache operations
  - Application Load Balancer requests

#### Option 3: Datadog
- **URL**: https://app.datadoghq.com/
- **Dashboards**: MultinotesAI Production

### Log Aggregation

#### ELK Stack (Elasticsearch, Logstash, Kibana)
- **URL**: https://logs.multinotesai.com/
- **Logs Available**:
  - Application logs (Django)
  - Nginx access/error logs
  - Celery logs
  - System logs

#### CloudWatch Logs
- **URL**: https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups
- **Log Groups**:
  - /aws/ec2/multinotesai
  - /multinotesai/application
  - /multinotesai/nginx

---

## Troubleshooting

### Issue 1: Application Not Starting

**Symptoms**:
- HTTP 502 Bad Gateway
- Gunicorn not responding

**Diagnosis**:
```bash
# Check Gunicorn status:
sudo systemctl status gunicorn

# Check logs:
sudo journalctl -u gunicorn -n 100 --no-pager

# Check application logs:
sudo tail -100 /var/log/multinotesai/gunicorn.log
```

**Common Causes & Solutions**:

1. **Import Error**:
   ```bash
   # Check for Python errors:
   python manage.py check

   # Verify all dependencies installed:
   pip check
   ```

2. **Database Connection Failed**:
   ```bash
   # Test database connection:
   python manage.py dbshell

   # Verify environment variables:
   echo $DB_HOST $DB_PORT $DB_NAME

   # Check database server:
   sudo systemctl status mysql
   ```

3. **Port Already in Use**:
   ```bash
   # Find process using port 8000:
   sudo lsof -i :8000

   # Kill old process:
   sudo kill -9 <PID>

   # Restart Gunicorn:
   sudo systemctl restart gunicorn
   ```

---

### Issue 2: Database Migration Errors

**Symptoms**:
- Migration fails
- "No such table" errors
- Schema conflicts

**Diagnosis**:
```bash
# Check migration status:
python manage.py showmigrations

# Check for unapplied migrations:
python manage.py migrate --plan
```

**Solutions**:

1. **Fake Migration** (if already applied manually):
   ```bash
   python manage.py migrate <app_name> <migration_number> --fake
   ```

2. **Rollback Migration**:
   ```bash
   python manage.py migrate <app_name> <previous_migration_number>
   ```

3. **Reset Migrations** (DANGER - dev only):
   ```bash
   # DO NOT DO THIS IN PRODUCTION
   # Rollback to previous code version instead
   ```

---

### Issue 3: Static Files Not Loading

**Symptoms**:
- Missing CSS/JS
- 404 errors for static files

**Diagnosis**:
```bash
# Check static files directory:
ls -la /var/www/multinotesai/staticfiles/

# Check Nginx static file configuration:
sudo nginx -t
cat /etc/nginx/sites-enabled/multinotesai.conf | grep static
```

**Solutions**:
```bash
# Re-collect static files:
python manage.py collectstatic --noinput

# Verify Nginx configuration:
sudo nginx -t

# Reload Nginx:
sudo systemctl reload nginx

# Check file permissions:
sudo chown -R www-data:www-data /var/www/multinotesai/staticfiles/
sudo chmod -R 755 /var/www/multinotesai/staticfiles/
```

---

### Issue 4: Celery Workers Not Processing Tasks

**Symptoms**:
- Tasks stuck in queue
- Background jobs not executing

**Diagnosis**:
```bash
# Check Celery workers:
celery -A backend inspect active
celery -A backend inspect stats

# Check Celery status:
sudo systemctl status celery

# Check Celery logs:
sudo journalctl -u celery -n 100 --no-pager
```

**Solutions**:

1. **Restart Celery**:
   ```bash
   sudo systemctl restart celery
   sudo systemctl status celery
   ```

2. **Check Redis Connection**:
   ```bash
   redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD ping
   ```

3. **Purge Task Queue** (if stuck):
   ```bash
   celery -A backend purge
   ```

4. **Check Worker Count**:
   ```bash
   # Increase workers if needed:
   # Edit: /etc/systemd/system/celery.service
   # ExecStart=/path/to/celery -A backend worker --concurrency=8

   sudo systemctl daemon-reload
   sudo systemctl restart celery
   ```

---

### Issue 5: High Error Rate

**Symptoms**:
- Many 5xx errors in logs
- Sentry showing high error count

**Diagnosis**:
```bash
# Check error rate:
sudo tail -1000 /var/log/nginx/access.log | grep " 5[0-9][0-9] " | wc -l

# Check Sentry for error details:
# Visit: https://sentry.io/

# Check application logs:
sudo tail -200 /var/log/multinotesai/gunicorn.log | grep -i error
```

**Solutions**:

1. **Check Resource Usage**:
   ```bash
   # CPU/Memory:
   htop

   # Disk space:
   df -h

   # If resources maxed out, scale up or restart services
   ```

2. **Check Database**:
   ```bash
   # Connection count:
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SHOW STATUS LIKE 'Threads_connected';"

   # Slow queries:
   sudo tail -50 /var/log/mysql/slow-query.log
   ```

3. **Check External APIs**:
   ```bash
   # Test LLM APIs:
   curl https://api.together.xyz/v1/status
   curl https://generativelanguage.googleapis.com/v1beta/models
   ```

---

### Issue 6: Performance Degradation

**Symptoms**:
- Slow response times
- Timeouts
- High CPU/memory usage

**Diagnosis**:
```bash
# Check response times:
curl -w "Time: %{time_total}s\n" -o /dev/null -s https://api.multinotesai.com/

# Check system resources:
top
free -h
iostat

# Check slow queries:
sudo tail -50 /var/log/mysql/slow-query.log

# Check Redis memory:
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD INFO memory
```

**Solutions**:

1. **Scale Gunicorn Workers**:
   ```bash
   # Edit gunicorn config:
   # workers = (2 x CPU cores) + 1

   sudo systemctl restart gunicorn
   ```

2. **Enable Redis Cache**:
   ```bash
   # Verify cache working:
   python manage.py shell
   # >>> from django.core.cache import cache
   # >>> cache.set('test', 'value', 300)
   # >>> cache.get('test')
   ```

3. **Optimize Database**:
   ```bash
   # Analyze tables:
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "ANALYZE TABLE authentication_customuser, coreapp_prompt;"

   # Check for missing indexes:
   # Review Django queries with explain()
   ```

---

## Emergency Rollback

### When to Rollback
Initiate immediate rollback if:
- **Critical errors** affecting >50% of users
- **Data corruption** detected
- **Security vulnerability** discovered
- **Error rate >10%** for >5 minutes
- **Response time >5 seconds** for >5 minutes
- **Database issues** that can't be resolved quickly

### Quick Rollback Procedure (5-10 minutes)

#### Step 1: Announce Rollback
```bash
# Post to team channel:
"🚨 ROLLBACK INITIATED - Production deployment v2.0.0
Reason: [ISSUE]
ETA: 10 minutes
Status updates every 2 minutes"
```

#### Step 2: Enable Maintenance Mode
```bash
sudo cp /etc/nginx/sites-available/maintenance.conf /etc/nginx/sites-enabled/multinotesai.conf
sudo systemctl reload nginx
```

#### Step 3: Stop Services
```bash
# For Docker:
docker-compose down

# For systemd:
sudo systemctl stop gunicorn celery
```

#### Step 4: Rollback Code
```bash
cd /var/www/multinotesai

# Rollback to previous tag:
git checkout v1.9.0  # Previous stable version

# For Docker:
docker-compose build
docker-compose up -d

# For systemd:
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 5: Rollback Database (if needed)
```bash
# If migrations were run, rollback:
python manage.py migrate <app_name> <previous_migration_number>

# OR restore from backup:
gunzip < /backups/pre-deploy-YYYYMMDD_HHMMSS.sql.gz | \
  mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME
```

#### Step 6: Start Services
```bash
# For Docker:
docker-compose up -d

# For systemd:
sudo systemctl start gunicorn celery
sudo systemctl status gunicorn celery
```

#### Step 7: Disable Maintenance Mode
```bash
sudo cp /etc/nginx/sites-available/multinotesai.conf /etc/nginx/sites-enabled/multinotesai.conf
sudo systemctl reload nginx
```

#### Step 8: Verify Rollback
```bash
# Check version:
curl https://api.multinotesai.com/api/v1/status/
# Should show previous version

# Check health:
curl https://api.multinotesai.com/health/
# Should return healthy

# Monitor errors:
sudo tail -f /var/log/multinotesai/gunicorn.log
```

#### Step 9: Post-Rollback
```bash
# Announce completion:
"✅ ROLLBACK COMPLETE - Production stable on v1.9.0
Services verified healthy
Incident report: [LINK]
Post-mortem scheduled: [TIME]"

# Create incident report:
# Document: What happened, why, impact, resolution, prevention
```

---

## Post-Deployment Tasks

### Within 1 Hour
- [ ] Monitor Sentry for new errors
- [ ] Check response times in monitoring dashboard
- [ ] Verify all health checks passing
- [ ] Review application logs for warnings
- [ ] Check Celery task processing

### Within 24 Hours
- [ ] Review performance metrics vs. baseline
- [ ] Check user feedback/support tickets
- [ ] Verify backup completed successfully
- [ ] Update documentation if needed
- [ ] Tag Docker images (if applicable)

### Within 1 Week
- [ ] Conduct post-deployment review meeting
- [ ] Document lessons learned
- [ ] Update runbook based on experience
- [ ] Plan next iteration improvements

---

## Deployment Checklist

Use this quick checklist during deployment:

- [ ] Team notified (24h advance)
- [ ] Code tagged in Git
- [ ] Pre-deployment backup created
- [ ] Environment variables verified
- [ ] Tests passing
- [ ] Maintenance mode enabled (if needed)
- [ ] Services stopped
- [ ] Code updated to new version
- [ ] Dependencies installed
- [ ] Database migrations run
- [ ] Static files collected
- [ ] Services started
- [ ] Maintenance mode disabled
- [ ] Health checks verified
- [ ] API endpoints tested
- [ ] Error logs checked
- [ ] Monitoring dashboards checked
- [ ] Team notified (deployment complete)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Maintained By**: DevOps Team
**Contact**: devops@multinotesai.com
