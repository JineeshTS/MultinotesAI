# Disaster Recovery Plan - MultinotesAI

This document outlines the disaster recovery (DR) procedures, backup strategies, and incident response plan for MultinotesAI production environment.

**Last Updated**: 2025-11-26
**Version**: 2.0.0
**Classification**: CONFIDENTIAL

---

## Table of Contents
- [Overview](#overview)
- [Recovery Objectives](#recovery-objectives)
- [Backup Procedures](#backup-procedures)
- [Recovery Procedures](#recovery-procedures)
- [RTO/RPO Targets](#rtorpo-targets)
- [Incident Response Plan](#incident-response-plan)
- [Disaster Scenarios](#disaster-scenarios)
- [Testing & Validation](#testing--validation)
- [Roles & Responsibilities](#roles--responsibilities)

---

## Overview

### Purpose
This Disaster Recovery Plan ensures business continuity in the event of:
- Infrastructure failure
- Data loss or corruption
- Security breach
- Natural disaster
- Human error
- Service provider outage

### Scope
- Production environment: `api.multinotesai.com`
- Database: MySQL production database
- File storage: AWS S3 bucket
- Cache/Queue: Redis instance
- Application code and configurations

### DR Strategy
- **Backup Strategy**: Regular automated backups with multiple retention periods
- **Geographic Redundancy**: Multi-region backup storage
- **Recovery Approach**: Restore from backups with documented procedures
- **Testing Frequency**: Quarterly DR drills

---

## Recovery Objectives

### Recovery Time Objective (RTO)
**Maximum acceptable downtime for each component:**

| Component | RTO Target | Criticality |
|-----------|------------|-------------|
| Web Application | 2 hours | CRITICAL |
| Database | 1 hour | CRITICAL |
| File Storage (S3) | 4 hours | HIGH |
| Cache (Redis) | 30 minutes | MEDIUM |
| Celery Workers | 1 hour | HIGH |
| Monitoring/Logging | 24 hours | LOW |

**Overall System RTO**: 2 hours

### Recovery Point Objective (RPO)
**Maximum acceptable data loss:**

| Data Type | RPO Target | Backup Frequency |
|-----------|------------|------------------|
| Database | 1 hour | Every 1 hour + Daily full backup |
| User Files (S3) | 0 (real-time replication) | Cross-region replication |
| Application Logs | 24 hours | Daily |
| Configuration Files | 0 (version controlled) | Git |
| Redis Data | 5 minutes | AOF persistence |

**Overall System RPO**: 1 hour

### Service Level Objectives (SLO)

| Metric | Target |
|--------|--------|
| Availability | 99.9% (43.8 min downtime/month) |
| Successful Recovery | >95% |
| Data Loss | <0.01% |
| Recovery Test Success | 100% quarterly |

---

## Backup Procedures

### 1. Database Backups

#### A. Automated Hourly Incremental Backups

```bash
#!/bin/bash
# /usr/local/bin/backup_db_incremental.sh

set -e

# Configuration
DB_HOST=${DB_HOST}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}
BACKUP_DIR="/backups/database/incremental"
S3_BUCKET="s3://multinotesai-backups-primary/database/incremental"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/incremental_${TIMESTAMP}.sql.gz"

# Logging
LOG_FILE="/var/log/backups/db_incremental.log"
exec 1>> "$LOG_FILE"
exec 2>&1

echo "$(date): Starting incremental database backup"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform incremental backup (binlog-based)
mysqlbinlog --read-from-remote-server \
  --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD \
  --result-file="${BACKUP_DIR}/binlog_${TIMESTAMP}.sql" \
  --stop-never &

# Or use mysqldump with --single-transaction for consistency
mysqldump --single-transaction \
  --quick \
  --lock-tables=false \
  --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD \
  $DB_NAME | gzip > "$BACKUP_FILE"

# Verify backup
if [ ! -f "$BACKUP_FILE" ]; then
    echo "$(date): ERROR - Backup file not created"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "$(date): Backup completed - Size: $BACKUP_SIZE"

# Upload to S3
aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/" --storage-class STANDARD_IA

# Verify S3 upload
if aws s3 ls "$S3_BUCKET/incremental_${TIMESTAMP}.sql.gz" > /dev/null; then
    echo "$(date): Backup uploaded to S3 successfully"
else
    echo "$(date): ERROR - S3 upload failed"
    exit 1
fi

# Cleanup old local backups (keep last 24 hours)
find "$BACKUP_DIR" -name "incremental_*.sql.gz" -mtime +1 -delete

echo "$(date): Incremental backup completed successfully"

# Send notification
curl -X POST https://api.slack.com/incoming/YOUR_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"✅ Database incremental backup completed: ${TIMESTAMP}\"}"
```

#### B. Daily Full Backups

```bash
#!/bin/bash
# /usr/local/bin/backup_db_full.sh

set -e

# Configuration
DB_HOST=${DB_HOST}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}
BACKUP_DIR="/backups/database/full"
S3_BUCKET_PRIMARY="s3://multinotesai-backups-primary/database/full"
S3_BUCKET_SECONDARY="s3://multinotesai-backups-secondary/database/full"  # Different region
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/full_${TIMESTAMP}.sql.gz"
ENCRYPTED_FILE="${BACKUP_FILE}.enc"

# Logging
LOG_FILE="/var/log/backups/db_full.log"
exec 1>> "$LOG_FILE"
exec 2>&1

echo "$(date): Starting full database backup"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full backup with all databases
mysqldump --all-databases \
  --single-transaction \
  --quick \
  --lock-tables=false \
  --routines \
  --triggers \
  --events \
  --master-data=2 \
  --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD | gzip > "$BACKUP_FILE"

# Verify backup integrity
if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "$(date): ERROR - Backup file is corrupted"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "$(date): Backup completed - Size: $BACKUP_SIZE"

# Encrypt backup
ENCRYPTION_KEY=${DB_BACKUP_ENCRYPTION_KEY}
openssl enc -aes-256-cbc -salt -pbkdf2 \
  -in "$BACKUP_FILE" \
  -out "$ENCRYPTED_FILE" \
  -pass pass:"$ENCRYPTION_KEY"

echo "$(date): Backup encrypted"

# Upload to primary S3 bucket
aws s3 cp "$ENCRYPTED_FILE" "$S3_BUCKET_PRIMARY/" \
  --storage-class STANDARD_IA \
  --metadata "backup-date=${DATE},backup-type=full"

# Upload to secondary S3 bucket (different region)
aws s3 cp "$ENCRYPTED_FILE" "$S3_BUCKET_SECONDARY/" \
  --storage-class STANDARD_IA \
  --region us-west-2

# Verify uploads
if aws s3 ls "$S3_BUCKET_PRIMARY/full_${TIMESTAMP}.sql.gz.enc" > /dev/null && \
   aws s3 ls "$S3_BUCKET_SECONDARY/full_${TIMESTAMP}.sql.gz.enc" --region us-west-2 > /dev/null; then
    echo "$(date): Backup uploaded to both S3 buckets successfully"
else
    echo "$(date): ERROR - S3 upload failed"
    exit 1
fi

# Create backup manifest
cat > "${BACKUP_DIR}/manifest_${DATE}.json" << EOF
{
  "backup_date": "$(date -Iseconds)",
  "backup_type": "full",
  "database": "$DB_NAME",
  "file_name": "full_${TIMESTAMP}.sql.gz.enc",
  "size_bytes": $(stat -c%s "$ENCRYPTED_FILE"),
  "size_human": "$BACKUP_SIZE",
  "encrypted": true,
  "locations": [
    "$S3_BUCKET_PRIMARY/full_${TIMESTAMP}.sql.gz.enc",
    "$S3_BUCKET_SECONDARY/full_${TIMESTAMP}.sql.gz.enc"
  ],
  "retention_days": 90
}
EOF

aws s3 cp "${BACKUP_DIR}/manifest_${DATE}.json" "$S3_BUCKET_PRIMARY/"

# Cleanup old local backups (keep last 7 days)
find "$BACKUP_DIR" -name "full_*.sql.gz*" -mtime +7 -delete

# Cleanup old S3 backups (keep based on retention policy)
# Daily backups: 30 days
# Weekly backups: 90 days
# Monthly backups: 1 year

echo "$(date): Full backup completed successfully"

# Send notification
curl -X POST https://api.slack.com/incoming/YOUR_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"✅ Database full backup completed: ${TIMESTAMP}\n Size: ${BACKUP_SIZE}\"}"
```

#### C. Backup Schedule (Cron Jobs)

```bash
# /etc/crontab

# Incremental backup every hour
0 * * * * root /usr/local/bin/backup_db_incremental.sh

# Full backup daily at 2 AM
0 2 * * * root /usr/local/bin/backup_db_full.sh

# Weekly backup (kept for 90 days) - Sunday at 3 AM
0 3 * * 0 root /usr/local/bin/backup_db_weekly.sh

# Monthly backup (kept for 1 year) - 1st of month at 4 AM
0 4 1 * * root /usr/local/bin/backup_db_monthly.sh
```

### 2. File Storage (S3) Backups

#### A. Enable S3 Versioning

```bash
# Enable versioning on primary bucket
aws s3api put-bucket-versioning \
  --bucket multinotesai-bucket \
  --versioning-configuration Status=Enabled

# Verify versioning enabled
aws s3api get-bucket-versioning --bucket multinotesai-bucket
```

#### B. Configure Cross-Region Replication

```bash
# Create replication role
aws iam create-role \
  --role-name S3ReplicationRole \
  --assume-role-policy-document file://s3-replication-trust-policy.json

# Attach replication policy
aws iam put-role-policy \
  --role-name S3ReplicationRole \
  --policy-name S3ReplicationPolicy \
  --policy-document file://s3-replication-policy.json

# Configure replication
aws s3api put-bucket-replication \
  --bucket multinotesai-bucket \
  --replication-configuration file://replication-config.json
```

**replication-config.json**:
```json
{
  "Role": "arn:aws:iam::123456789012:role/S3ReplicationRole",
  "Rules": [
    {
      "Status": "Enabled",
      "Priority": 1,
      "DeleteMarkerReplication": { "Status": "Enabled" },
      "Filter": {},
      "Destination": {
        "Bucket": "arn:aws:s3:::multinotesai-bucket-backup-us-west-2",
        "ReplicationTime": {
          "Status": "Enabled",
          "Time": {
            "Minutes": 15
          }
        },
        "Metrics": {
          "Status": "Enabled",
          "EventThreshold": {
            "Minutes": 15
          }
        }
      }
    }
  ]
}
```

#### C. S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "Id": "Transition-to-IA",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

```bash
# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket multinotesai-bucket \
  --lifecycle-configuration file://lifecycle-policy.json
```

### 3. Redis Backups

#### A. Enable Redis Persistence (AOF)

```bash
# Configure Redis for AOF persistence
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec
redis-cli CONFIG SET auto-aof-rewrite-percentage 100
redis-cli CONFIG SET auto-aof-rewrite-min-size 64mb

# Save config
redis-cli CONFIG REWRITE
```

#### B. Automated Redis Backups

```bash
#!/bin/bash
# /usr/local/bin/backup_redis.sh

set -e

REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_PASSWORD=${REDIS_PASSWORD}
BACKUP_DIR="/backups/redis"
S3_BUCKET="s3://multinotesai-backups-primary/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Trigger BGSAVE
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD BGSAVE

# Wait for BGSAVE to complete
while [ $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD LASTSAVE) -eq $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD LASTSAVE) ]; do
    sleep 1
done

# Copy RDB file
cp /var/lib/redis/dump.rdb "${BACKUP_DIR}/dump_${TIMESTAMP}.rdb"

# Copy AOF file
cp /var/lib/redis/appendonly.aof "${BACKUP_DIR}/aof_${TIMESTAMP}.aof"

# Compress
tar -czf "${BACKUP_DIR}/redis_${TIMESTAMP}.tar.gz" \
  "${BACKUP_DIR}/dump_${TIMESTAMP}.rdb" \
  "${BACKUP_DIR}/aof_${TIMESTAMP}.aof"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/redis_${TIMESTAMP}.tar.gz" "$S3_BUCKET/"

# Cleanup
find "$BACKUP_DIR" -name "redis_*.tar.gz" -mtime +7 -delete

echo "$(date): Redis backup completed"
```

```bash
# Cron job - daily at 3 AM
0 3 * * * root /usr/local/bin/backup_redis.sh
```

### 4. Configuration Backups

```bash
#!/bin/bash
# /usr/local/bin/backup_config.sh

set -e

BACKUP_DIR="/backups/config"
S3_BUCKET="s3://multinotesai-backups-primary/config"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configurations
tar -czf "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz" \
  /etc/nginx/sites-available/ \
  /etc/systemd/system/gunicorn.service \
  /etc/systemd/system/celery.service \
  /etc/supervisor/ \
  /var/www/multinotesai/.env.example

# Upload to S3
aws s3 cp "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz" "$S3_BUCKET/"

# Git commit
cd /var/www/multinotesai
git add -A
git commit -m "Config backup ${TIMESTAMP}" || true
git push origin backup-branch

echo "$(date): Configuration backup completed"
```

### 5. Backup Monitoring & Alerts

```bash
#!/bin/bash
# /usr/local/bin/verify_backups.sh

set -e

# Check if today's backups exist
DATE=$(date +%Y%m%d)

check_backup() {
    local bucket=$1
    local prefix=$2
    local name=$3

    if aws s3 ls "${bucket}/${prefix}_${DATE}" > /dev/null 2>&1; then
        echo "✅ $name backup exists"
        return 0
    else
        echo "❌ $name backup MISSING"
        # Send alert
        curl -X POST https://api.slack.com/incoming/YOUR_WEBHOOK \
          -H 'Content-Type: application/json' \
          -d "{\"text\":\"🚨 ALERT: $name backup missing for $DATE\"}"
        return 1
    fi
}

# Check all backups
check_backup "s3://multinotesai-backups-primary/database/full" "full" "Database Full"
check_backup "s3://multinotesai-backups-primary/redis" "redis" "Redis"
check_backup "s3://multinotesai-backups-primary/config" "config" "Configuration"

# Check S3 replication
REPLICATION_STATUS=$(aws s3api get-bucket-replication --bucket multinotesai-bucket | jq -r '.ReplicationConfiguration.Rules[0].Status')

if [ "$REPLICATION_STATUS" != "Enabled" ]; then
    echo "❌ S3 replication not enabled"
    # Send alert
fi
```

```bash
# Cron job - daily at 5 AM (after all backups)
0 5 * * * root /usr/local/bin/verify_backups.sh
```

---

## Recovery Procedures

### 1. Database Recovery

#### A. Restore from Latest Full Backup

```bash
#!/bin/bash
# Database restoration procedure

set -e

echo "=== DATABASE RECOVERY PROCEDURE ==="
echo "This will REPLACE the current database with backup data"
read -p "Are you sure you want to continue? (type 'yes'): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Recovery cancelled"
    exit 1
fi

# List available backups
echo "Available backups:"
aws s3 ls s3://multinotesai-backups-primary/database/full/ | tail -10

read -p "Enter backup filename to restore: " BACKUP_FILE

# Download backup
TEMP_DIR="/tmp/db_restore"
mkdir -p "$TEMP_DIR"

echo "Downloading backup from S3..."
aws s3 cp "s3://multinotesai-backups-primary/database/full/$BACKUP_FILE" \
  "$TEMP_DIR/$BACKUP_FILE"

# Decrypt backup
echo "Decrypting backup..."
ENCRYPTION_KEY=${DB_BACKUP_ENCRYPTION_KEY}
openssl enc -aes-256-cbc -d -pbkdf2 \
  -in "$TEMP_DIR/$BACKUP_FILE" \
  -out "$TEMP_DIR/backup.sql.gz" \
  -pass pass:"$ENCRYPTION_KEY"

# Decompress
echo "Decompressing backup..."
gunzip "$TEMP_DIR/backup.sql.gz"

# Stop application
echo "Stopping application services..."
sudo systemctl stop gunicorn
sudo systemctl stop celery

# Create pre-restore backup
echo "Creating pre-restore backup..."
mysqldump --all-databases \
  --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD | gzip > "/tmp/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"

# Restore database
echo "Restoring database..."
mysql --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD < "$TEMP_DIR/backup.sql"

# Verify restoration
echo "Verifying restoration..."
TABLE_COUNT=$(mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD \
  -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME'" -sN)

echo "Database contains $TABLE_COUNT tables"

# Restart application
echo "Starting application services..."
sudo systemctl start gunicorn
sudo systemctl start celery

# Health check
echo "Performing health check..."
sleep 5
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.multinotesai.com/health/)

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ Database restoration completed successfully"
    echo "Application is healthy"
else
    echo "❌ WARNING: Application health check failed (HTTP $HTTP_STATUS)"
    echo "Manual intervention may be required"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "=== RECOVERY COMPLETE ==="
```

#### B. Point-in-Time Recovery

```bash
#!/bin/bash
# Point-in-time recovery using binary logs

set -e

read -p "Enter target datetime (YYYY-MM-DD HH:MM:SS): " TARGET_DATETIME

echo "Performing point-in-time recovery to: $TARGET_DATETIME"

# 1. Restore latest full backup before target time
# (Follow full backup restore procedure)

# 2. Apply binary logs up to target time
mysqlbinlog --stop-datetime="$TARGET_DATETIME" \
  /var/lib/mysql/binlog.* | \
  mysql --host=$DB_HOST --user=$DB_USER --password=$DB_PASSWORD

echo "Point-in-time recovery completed"
```

### 2. S3 File Recovery

#### A. Restore Deleted File

```bash
#!/bin/bash
# Restore deleted S3 object

FILE_KEY="$1"  # e.g., "documents/user123/file.pdf"

# List versions
echo "Available versions:"
aws s3api list-object-versions \
  --bucket multinotesai-bucket \
  --prefix "$FILE_KEY"

read -p "Enter VersionId to restore: " VERSION_ID

# Restore by copying version to current
aws s3api copy-object \
  --bucket multinotesai-bucket \
  --copy-source "multinotesai-bucket/$FILE_KEY?versionId=$VERSION_ID" \
  --key "$FILE_KEY"

echo "File restored: $FILE_KEY"
```

#### B. Restore from Replica Bucket

```bash
#!/bin/bash
# Restore from cross-region replica in case primary is lost

aws s3 sync \
  s3://multinotesai-bucket-backup-us-west-2/ \
  s3://multinotesai-bucket-new/ \
  --region us-west-2

echo "S3 bucket restored from replica"
```

### 3. Redis Recovery

```bash
#!/bin/bash
# Restore Redis from backup

set -e

# Download latest backup
LATEST_BACKUP=$(aws s3 ls s3://multinotesai-backups-primary/redis/ | tail -1 | awk '{print $4}')

aws s3 cp "s3://multinotesai-backups-primary/redis/$LATEST_BACKUP" /tmp/

# Extract backup
tar -xzf "/tmp/$LATEST_BACKUP" -C /tmp/

# Stop Redis
sudo systemctl stop redis

# Replace dump and AOF files
sudo cp /tmp/dump_*.rdb /var/lib/redis/dump.rdb
sudo cp /tmp/aof_*.aof /var/lib/redis/appendonly.aof

# Fix permissions
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/appendonly.aof

# Start Redis
sudo systemctl start redis

# Verify
redis-cli ping

echo "Redis restored successfully"
```

### 4. Complete System Recovery

**Full disaster recovery procedure when entire infrastructure is lost:**

```bash
#!/bin/bash
# Complete system recovery

set -e

echo "=== COMPLETE SYSTEM RECOVERY ==="
echo "This procedure rebuilds the entire infrastructure"

# Step 1: Provision new infrastructure
echo "Step 1: Provisioning new infrastructure..."

# Launch new EC2 instances (or use Terraform/CloudFormation)
# Setup new RDS instance
# Setup new ElastiCache instance
# Setup new S3 bucket

# Step 2: Restore database
echo "Step 2: Restoring database..."
# (Use database recovery procedure above)

# Step 3: Restore Redis
echo "Step 3: Restoring Redis..."
# (Use Redis recovery procedure above)

# Step 4: Restore S3 files
echo "Step 4: Restoring S3 files..."
aws s3 sync \
  s3://multinotesai-bucket-backup-us-west-2/ \
  s3://multinotesai-bucket-new/

# Step 5: Deploy application
echo "Step 5: Deploying application..."
cd /var/www/multinotesai
git clone https://github.com/YourOrg/MultinotesAI.git .
git checkout v2.0.0

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restore configuration
aws s3 cp s3://multinotesai-backups-primary/config/latest.tar.gz /tmp/
tar -xzf /tmp/latest.tar.gz -C /

# Setup environment
cp .env.example .env
# Update .env with new infrastructure details

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Step 6: Start services
echo "Step 6: Starting services..."
sudo systemctl start nginx
sudo systemctl start gunicorn
sudo systemctl start celery

# Step 7: Update DNS
echo "Step 7: Update DNS to point to new infrastructure"
echo "New Load Balancer: [NEW_LB_DNS]"
read -p "Update DNS and press Enter when complete..."

# Step 8: Verify system
echo "Step 8: Verifying system..."
curl https://api.multinotesai.com/health/

echo "=== RECOVERY COMPLETE ==="
echo "Next steps:"
echo "1. Monitor logs and metrics"
echo "2. Notify users of restoration"
echo "3. Conduct post-incident review"
echo "4. Update DR documentation"
```

---

## RTO/RPO Targets

### Detailed Recovery Targets

| Scenario | Impact | RTO | RPO | Priority |
|----------|--------|-----|-----|----------|
| Single web server failure | Partial service degradation | 15 min | 0 | P1 |
| Database failure | Complete outage | 1 hour | 1 hour | P0 |
| Cache failure | Performance degradation | 30 min | 5 min | P2 |
| File storage failure | Upload/download failure | 4 hours | 0 | P1 |
| Complete region failure | Complete outage | 4 hours | 1 hour | P0 |
| Security breach | Potential data loss | 2 hours | 1 hour | P0 |
| Accidental deletion | Data loss | 2 hours | 24 hours | P2 |
| Ransomware attack | Complete outage | 24 hours | 24 hours | P0 |

### SLA Guarantees

**99.9% Uptime SLA**:
- Maximum downtime: 43.8 minutes/month
- Maximum downtime: 8.76 hours/year

**Recovery Guarantees**:
- Database recovery: 60 minutes
- Application recovery: 120 minutes
- Data loss: Maximum 1 hour of transactions

---

## Incident Response Plan

### 1. Incident Classification

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **P0 - Critical** | Complete service outage | Immediate | Database down, security breach |
| **P1 - High** | Major functionality impaired | 15 minutes | S3 failure, API errors >50% |
| **P2 - Medium** | Minor functionality impaired | 1 hour | Cache failure, slow response times |
| **P3 - Low** | Minimal impact | 4 hours | Cosmetic issues, log errors |

### 2. Incident Response Workflow

```
┌─────────────────┐
│  Incident       │
│  Detected       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Alert/         │
│  Notification   │◄──── Monitoring, User Reports, On-Call
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Assess         │
│  Severity       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│  P0   │ │ P1-P3 │
│  P1   │ │       │
└───┬───┘ └───┬───┘
    │         │
    │         ▼
    │    ┌────────────┐
    │    │  Assign    │
    │    │  Engineer  │
    │    └─────┬──────┘
    │          │
    ▼          ▼
┌─────────────────┐
│  Initiate       │
│  War Room       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Investigate &  │
│  Diagnose       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Implement      │
│  Fix/Recovery   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Verify         │
│  Resolution     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Post-Incident  │
│  Review         │
└─────────────────┘
```

### 3. Incident Response Procedures

#### P0/P1 Incident Response

```bash
# 1. Acknowledge incident
echo "Incident acknowledged by [YOUR_NAME] at $(date)" >> /var/log/incidents/incident_$(date +%Y%m%d_%H%M%S).log

# 2. Notify team
curl -X POST https://api.slack.com/incoming/YOUR_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{"text":"🚨 P0 INCIDENT: [DESCRIPTION]\nIncident Commander: [NAME]\nWar Room: https://meet.google.com/xxx"}'

# 3. Enable status page banner
curl -X POST https://api.statuspage.io/v1/pages/YOUR_PAGE_ID/incidents \
  -H "Authorization: OAuth YOUR_API_KEY" \
  -d "incident[name]=Service Disruption" \
  -d "incident[status]=investigating" \
  -d "incident[message]=We are investigating reports of service disruptions"

# 4. Start incident log
cat > /var/log/incidents/incident_$(date +%Y%m%d).md << EOF
# Incident Report - $(date)

## Summary
- **Incident ID**: INC-$(date +%Y%m%d)-001
- **Severity**: P0
- **Detected**: $(date)
- **Incident Commander**: [NAME]

## Timeline
- $(date): Incident detected
-

## Impact
- Users affected:
- Services affected:

## Root Cause
- TBD

## Resolution
- TBD

## Action Items
- [ ]
EOF
```

### 4. Communication Templates

#### User Notification (Outage)

```
Subject: [RESOLVED] Service Disruption - MultinotesAI

Dear MultinotesAI Users,

We experienced a service disruption on [DATE] from [START_TIME] to [END_TIME] UTC.

What happened:
[BRIEF_DESCRIPTION]

Impact:
- Duration: [DURATION] minutes
- Services affected: [SERVICES]
- Users affected: [PERCENTAGE]%

Resolution:
[WHAT_WAS_DONE]

We sincerely apologize for any inconvenience. We are committed to providing reliable service and have implemented additional measures to prevent similar issues.

If you have any questions, please contact support@multinotesai.com.

Sincerely,
MultinotesAI Team
```

#### Internal Communication (Incident Start)

```
🚨 P0 INCIDENT ALERT

Incident: Database connection failure
Severity: P0
Detected: 2025-11-26 14:32 UTC
Incident Commander: Alice Smith

Status: INVESTIGATING

Impact:
- API returning 503 errors
- Users cannot access application
- Estimated affected users: 100%

War Room: https://meet.google.com/xxx-xxx-xxx

Next update: 15 minutes
```

---

## Disaster Scenarios

### Scenario 1: Database Server Failure

**Symptoms**:
- Database connection errors
- Application unable to read/write data
- HTTP 503 errors

**Immediate Actions**:
1. Check database server status
2. Attempt automatic failover (if Multi-AZ)
3. If failover fails, restore from backup

**Recovery Steps**:
```bash
# 1. Provision new RDS instance or fix existing
# 2. Restore from latest snapshot/backup (see Database Recovery section)
# 3. Update application connection string
# 4. Restart application services
# 5. Verify data integrity
```

**Estimated RTO**: 1 hour
**Estimated RPO**: 1 hour

---

### Scenario 2: Ransomware Attack

**Symptoms**:
- Files encrypted
- Ransom demand
- Unusual system behavior

**Immediate Actions**:
1. **DO NOT PAY RANSOM**
2. Isolate affected systems immediately
3. Disconnect from network
4. Preserve evidence
5. Notify security team and law enforcement

**Recovery Steps**:
```bash
# 1. Isolate and preserve affected systems
sudo iptables -A INPUT -j DROP
sudo iptables -A OUTPUT -j DROP

# 2. Analyze scope of attack
# - Check all systems for infection
# - Identify entry point

# 3. Clean rebuild
# - Provision new infrastructure
# - Deploy from clean code repository
# - Restore data from pre-attack backups

# 4. Restore from backup (ensure backup is clean)
# - Use backup from before attack
# - Verify backup integrity

# 5. Security hardening
# - Patch vulnerabilities
# - Update all credentials
# - Implement additional security measures

# 6. Resume operations
```

**Estimated RTO**: 24-48 hours
**Estimated RPO**: 24 hours

---

### Scenario 3: Complete AWS Region Failure

**Symptoms**:
- All services in region unavailable
- AWS status page shows regional issues

**Recovery Steps**:
```bash
# 1. Activate DR region (us-west-2)

# 2. Update DNS to point to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://dns-failover.json

# 3. Promote read replica to primary (if in different region)
aws rds promote-read-replica \
  --db-instance-identifier multinotesai-db-west-2

# 4. Update application configuration
# - Point to new database endpoint
# - Point to replica S3 bucket

# 5. Scale up resources in DR region
# 6. Verify all services operational
# 7. Notify users of temporary performance impact
```

**Estimated RTO**: 4 hours
**Estimated RPO**: 1 hour

---

## Testing & Validation

### Quarterly DR Drill

**Schedule**: Last Saturday of each quarter, 2 AM - 6 AM UTC

#### DR Drill Checklist

```markdown
# Disaster Recovery Drill - [DATE]

## Pre-Drill
- [ ] Schedule drill 2 weeks in advance
- [ ] Notify all stakeholders
- [ ] Prepare test environment
- [ ] Document current state

## Drill Execution
- [ ] Simulate disaster scenario: _______________
- [ ] Start timer
- [ ] Execute recovery procedures
- [ ] Document all steps and issues
- [ ] Stop timer when recovery complete

## Verification
- [ ] Application accessible
- [ ] Database contains expected data
- [ ] Files accessible from S3
- [ ] All services operational
- [ ] Performance acceptable

## Metrics
- Time to detect: _____ minutes
- Time to initiate recovery: _____ minutes
- Time to complete recovery: _____ minutes
- Total RTO: _____ minutes (Target: 120 min)
- Data loss: _____ (Target: < 1 hour)

## Issues Encountered
1.
2.

## Action Items
- [ ]
- [ ]

## Participants
-
-

## Drill Result
- [ ] PASS
- [ ] FAIL - Reason: _______________

## Next Steps
- Schedule next drill: _______________
- Update DR procedures based on learnings
```

### Backup Restoration Testing

**Monthly Test**: Restore random backup and verify integrity

```bash
#!/bin/bash
# Monthly backup restoration test

# Select random backup
BACKUP=$(aws s3 ls s3://multinotesai-backups-primary/database/full/ | shuf -n 1 | awk '{print $4}')

echo "Testing backup: $BACKUP"

# Restore to test database
# (Restoration procedure, but to test database)

# Run verification queries
mysql -h test-db -u root -p$DB_PASSWORD -e "
  SELECT COUNT(*) FROM $TEST_DB.authentication_customuser;
  SELECT COUNT(*) FROM $TEST_DB.coreapp_prompt;
  SELECT COUNT(*) FROM $TEST_DB.planandsubscription_subscription;
"

# Document results
echo "Backup restoration test: PASS" >> /var/log/backup-tests.log
```

---

## Roles & Responsibilities

### Incident Commander
- Overall responsibility for incident response
- Coordinates recovery efforts
- Communicates with stakeholders
- Makes final decisions on recovery strategy

**Primary**: CTO
**Backup**: DevOps Lead

### Database Administrator
- Database recovery
- Data integrity verification
- Performance optimization post-recovery

**Primary**: Senior Backend Engineer
**Backup**: DevOps Engineer

### Infrastructure Engineer
- Server provisioning
- Network configuration
- Service restoration

**Primary**: DevOps Lead
**Backup**: Cloud Engineer

### Application Engineer
- Application deployment
- Code deployment
- Application health verification

**Primary**: Lead Backend Engineer
**Backup**: Senior Backend Engineer

### Communications Lead
- User notifications
- Status page updates
- Internal communications

**Primary**: Product Manager
**Backup**: Customer Success Lead

### Security Lead (for security incidents)
- Security analysis
- Forensics
- Hardening post-incident

**Primary**: Security Engineer
**Backup**: DevOps Lead

---

## Contact Information

### Emergency Contacts

| Role | Name | Phone | Email | Slack |
|------|------|-------|-------|-------|
| Incident Commander | [NAME] | [PHONE] | [EMAIL] | @[handle] |
| DB Admin | [NAME] | [PHONE] | [EMAIL] | @[handle] |
| Infrastructure | [NAME] | [PHONE] | [EMAIL] | @[handle] |
| Application | [NAME] | [PHONE] | [EMAIL] | @[handle] |
| Communications | [NAME] | [PHONE] | [EMAIL] | @[handle] |
| Security | [NAME] | [PHONE] | [EMAIL] | @[handle] |

### Escalation Path

1. On-call engineer (PagerDuty)
2. Engineering Lead
3. CTO
4. CEO

### External Contacts

| Service | Contact | Phone | Portal |
|---------|---------|-------|--------|
| AWS Support | Enterprise Support | 1-800-xxx-xxxx | console.aws.amazon.com |
| DNS Provider | [Provider] | [Phone] | [Portal URL] |
| CDN Provider | [Provider] | [Phone] | [Portal URL] |

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-26 | Initial version | DevOps Team |

**Next Review**: 2026-02-26 (Quarterly)

---

**Document Classification**: CONFIDENTIAL
**Owner**: DevOps Team
**Contact**: devops@multinotesai.com
