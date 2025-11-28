# Scaling Guide - MultinotesAI

This guide provides comprehensive strategies and instructions for scaling the MultinotesAI platform to handle increased traffic and user growth.

**Last Updated**: 2025-11-26
**Version**: 2.0.0

---

## Table of Contents
- [Overview](#overview)
- [Scaling Strategies](#scaling-strategies)
- [Horizontal Scaling](#horizontal-scaling)
- [Database Scaling](#database-scaling)
- [Redis Scaling](#redis-scaling)
- [CDN Configuration](#cdn-configuration)
- [Load Balancer Setup](#load-balancer-setup)
- [Auto-Scaling](#auto-scaling)
- [Performance Optimization](#performance-optimization)
- [Capacity Planning](#capacity-planning)

---

## Overview

### Current Architecture (Single Server)
```
                                  ┌──────────────┐
                                  │   Internet   │
                                  └──────┬───────┘
                                         │
                                  ┌──────▼───────┐
                                  │    Nginx     │
                                  └──────┬───────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
             ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐
             │  Gunicorn    │    │    MySQL     │    │    Redis     │
             │  (Django)    │    │  Database    │    │   Cache      │
             └──────┬───────┘    └──────────────┘    └──────┬───────┘
                    │                                        │
             ┌──────▼───────┐                         ┌──────▼───────┐
             │    Celery    │◄────────────────────────┤  Celery Msg  │
             │   Workers    │                         │    Broker    │
             └──────────────┘                         └──────────────┘
```

### Target Architecture (Scaled)
```
                             ┌──────────────┐
                             │   Internet   │
                             └──────┬───────┘
                                    │
                             ┌──────▼───────┐
                             │   Route 53   │  (DNS)
                             └──────┬───────┘
                                    │
                             ┌──────▼───────┐
                             │  CloudFront  │  (CDN)
                             └──────┬───────┘
                                    │
                             ┌──────▼───────┐
                             │     ALB      │  (Load Balancer)
                             └──────┬───────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
         ┌──────────▼─────────┐         ┌──────────▼─────────┐
         │  Web Server 1      │         │  Web Server 2      │
         │  Nginx + Gunicorn  │         │  Nginx + Gunicorn  │
         └──────────┬─────────┘         └──────────┬─────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │               │               │
          ┌─────────▼────────┐ ┌───▼────┐ ┌────────▼──────┐
          │  RDS (MySQL)     │ │  S3    │ │ ElastiCache   │
          │  Multi-AZ        │ │ Files  │ │  (Redis)      │
          │  Read Replicas   │ └────────┘ │  Cluster      │
          └──────────────────┘            └───────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │     Celery    │
                                          │    Workers    │
                                          │   (Auto-scale)│
                                          └───────────────┘
```

### Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU Usage | >70% for 10 min | Scale up application servers |
| Memory Usage | >80% for 10 min | Scale up application servers |
| Request Rate | >1000 req/s | Add application servers |
| Database CPU | >80% | Add read replicas |
| Redis Memory | >80% | Scale up Redis instance |
| Celery Queue | >1000 tasks | Add Celery workers |
| Response Time p95 | >1s | Investigate and scale |

---

## Scaling Strategies

### Vertical Scaling (Scale Up)
**Pros**: Simple, no code changes
**Cons**: Limited by hardware, single point of failure

**When to Use**:
- Quick fix for immediate issues
- Database scaling
- Cache scaling

**Implementation**:
```bash
# AWS EC2: Change instance type
aws ec2 modify-instance-attribute \
  --instance-id i-1234567890abcdef0 \
  --instance-type t3.xlarge

# RDS: Change instance class
aws rds modify-db-instance \
  --db-instance-identifier multinotesai-db \
  --db-instance-class db.r5.xlarge \
  --apply-immediately
```

### Horizontal Scaling (Scale Out)
**Pros**: Better fault tolerance, unlimited scaling
**Cons**: Requires architecture changes, complexity

**When to Use**:
- Long-term growth
- High availability requirements
- Geographic distribution

---

## Horizontal Scaling

### 1. Application Server Scaling

#### A. Prepare Application for Horizontal Scaling

**Make Application Stateless**:
```python
# ❌ BAD - Using in-memory sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# ✅ GOOD - Using database or Redis sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
# or
SESSION_ENGINE = 'redis_sessions.session'
```

**Shared File Storage (S3)**:
```python
# Already configured in settings.py ✓
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

**Shared Cache (Redis)**:
```python
# Already configured in settings.py ✓
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
    }
}
```

#### B. Create Application Server Image

**Option 1: Docker Image**
```bash
# Build Docker image:
docker build -t multinotesai/backend:2.0.0 .

# Push to registry:
docker tag multinotesai/backend:2.0.0 your-registry/multinotesai/backend:2.0.0
docker push your-registry/multinotesai/backend:2.0.0
```

**Option 2: AMI (AWS)**
```bash
# Create AMI from existing instance:
aws ec2 create-image \
  --instance-id i-1234567890abcdef0 \
  --name "multinotesai-web-v2.0.0" \
  --description "MultinotesAI web server v2.0.0"

# Launch new instances from AMI:
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --count 2 \
  --instance-type t3.large \
  --key-name multinotesai-key \
  --security-group-ids sg-0abcdef1234567890 \
  --subnet-id subnet-0abcdef1234567890
```

#### C. Deploy Multiple Instances

**Using Docker Compose (Manual)**
```yaml
# docker-compose.yml
version: '3.8'

services:
  web1:
    image: multinotesai/backend:2.0.0
    ports:
      - "8001:8000"
    environment:
      - SERVER_ID=web1

  web2:
    image: multinotesai/backend:2.0.0
    ports:
      - "8002:8000"
    environment:
      - SERVER_ID=web2

  web3:
    image: multinotesai/backend:2.0.0
    ports:
      - "8003:8000"
    environment:
      - SERVER_ID=web3
```

**Using Kubernetes**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multinotesai-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: multinotesai
      tier: web
  template:
    metadata:
      labels:
        app: multinotesai
        tier: web
    spec:
      containers:
      - name: web
        image: multinotesai/backend:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "False"
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: host
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: multinotesai-web
spec:
  selector:
    app: multinotesai
    tier: web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

```bash
# Apply deployment:
kubectl apply -f deployment.yaml

# Scale deployment:
kubectl scale deployment multinotesai-web --replicas=5

# Check status:
kubectl get pods
kubectl get services
```

### 2. Gunicorn Worker Configuration

**Per-Server Configuration**:
```python
# gunicorn.conf.py

import multiprocessing

# Number of worker processes
# Formula: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = 'gthread'

# Threads per worker
threads = 2

# Maximum requests per worker (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100

# Timeout
timeout = 60

# Keep-alive
keepalive = 5

# Logging
accesslog = '/var/log/multinotesai/gunicorn-access.log'
errorlog = '/var/log/multinotesai/gunicorn-error.log'
loglevel = 'info'

# Process naming
proc_name = 'multinotesai'

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048
```

### 3. Session Management for Multiple Servers

**Use Database-Backed Sessions**:
```python
# settings.py

# Option 1: Database sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Option 2: Cached database sessions (faster)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Option 3: Redis sessions (fastest, recommended)
# Install: pip install django-redis-sessions
SESSION_ENGINE = 'redis_sessions.session'
SESSION_REDIS = {
    'host': REDIS_HOST,
    'port': 6379,
    'db': 1,
    'password': REDIS_PASSWORD,
    'prefix': 'session',
    'socket_timeout': 5,
}
```

---

## Database Scaling

### 1. Vertical Scaling (Quick Fix)

```bash
# AWS RDS: Increase instance size
aws rds modify-db-instance \
  --db-instance-identifier multinotesai-db \
  --db-instance-class db.r5.2xlarge \
  --apply-immediately

# Increase storage:
aws rds modify-db-instance \
  --db-instance-identifier multinotesai-db \
  --allocated-storage 500 \
  --apply-immediately
```

### 2. Read Replicas (Horizontal Scaling)

**Create Read Replica**:
```bash
# AWS RDS:
aws rds create-db-instance-read-replica \
  --db-instance-identifier multinotesai-db-read-1 \
  --source-db-instance-identifier multinotesai-db \
  --db-instance-class db.r5.xlarge \
  --availability-zone us-east-1b

# Create additional replicas:
aws rds create-db-instance-read-replica \
  --db-instance-identifier multinotesai-db-read-2 \
  --source-db-instance-identifier multinotesai-db \
  --db-instance-class db.r5.xlarge \
  --availability-zone us-east-1c
```

**Configure Django for Read Replicas**:
```python
# settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_env_variable('DB_NAME'),
        'USER': get_env_variable('DB_USER'),
        'PASSWORD': get_env_variable('DB_PASSWORD'),
        'HOST': get_env_variable('DB_HOST'),  # Primary/writer
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'CONN_MAX_AGE': 60,
    },
    'read_replica_1': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_env_variable('DB_NAME'),
        'USER': get_env_variable('DB_USER'),
        'PASSWORD': get_env_variable('DB_PASSWORD'),
        'HOST': get_env_variable('DB_READ_REPLICA_1_HOST'),
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 60,
    },
    'read_replica_2': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_env_variable('DB_NAME'),
        'USER': get_env_variable('DB_USER'),
        'PASSWORD': get_env_variable('DB_PASSWORD'),
        'HOST': get_env_variable('DB_READ_REPLICA_2_HOST'),
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 60,
    },
}

# Database router for read/write splitting
DATABASE_ROUTERS = ['backend.routers.ReadReplicaRouter']
```

**Create Database Router**:
```python
# backend/routers.py

import random

class ReadReplicaRouter:
    """
    A router to control database read operations to read replicas
    and all writes to the primary database.
    """

    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly selected read replica.
        """
        return random.choice(['read_replica_1', 'read_replica_2'])

    def db_for_write(self, model, **hints):
        """
        Writes always go to primary.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects in the same database.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Migrations only run on primary database.
        """
        return db == 'default'
```

**Force Write to Primary**:
```python
# When you need to ensure read-after-write consistency:
from django.db import transaction

# Force read from primary:
User.objects.using('default').get(id=user_id)

# In a transaction (automatically uses primary):
with transaction.atomic():
    user = User.objects.get(id=user_id)  # Uses 'default'
    user.email = 'new@email.com'
    user.save()
```

### 3. Connection Pooling

**Install PgBouncer/ProxySQL**:
```bash
# For MySQL, use ProxySQL:
sudo apt-get install proxysql

# Configure ProxySQL:
sudo nano /etc/proxysql.cnf
```

```ini
# /etc/proxysql.cnf
datadir="/var/lib/proxysql"

admin_variables=
{
    admin_credentials="admin:admin"
    mysql_ifaces="0.0.0.0:6032"
}

mysql_variables=
{
    threads=4
    max_connections=2048
    default_query_delay=0
    default_query_timeout=36000000
    have_compress=true
    poll_timeout=2000
    interfaces="0.0.0.0:6033"
    default_schema="information_schema"
    stacksize=1048576
    server_version="5.7.0"
    connect_timeout_server=3000
    monitor_username="monitor"
    monitor_password="monitor"
    monitor_history=600000
    monitor_connect_interval=60000
    monitor_ping_interval=10000
    ping_interval_server_msec=120000
    ping_timeout_server=500
    commands_stats=true
    sessions_sort=true
    connect_retries_on_failure=10
}

mysql_servers =
(
    {
        address="db.primary.internal"
        port=3306
        hostgroup=0  # writer
        max_connections=200
    },
    {
        address="db.read1.internal"
        port=3306
        hostgroup=1  # reader
        max_connections=200
    },
    {
        address="db.read2.internal"
        port=3306
        hostgroup=1  # reader
        max_connections=200
    }
)

mysql_users =
(
    {
        username = "multinotesai"
        password = "password"
        default_hostgroup = 0
        max_connections=200
        active = 1
    }
)

mysql_query_rules =
(
    {
        rule_id=1
        active=1
        match_digest="^SELECT.*FOR UPDATE$"
        destination_hostgroup=0  # writer
        apply=1
    },
    {
        rule_id=2
        active=1
        match_digest="^SELECT"
        destination_hostgroup=1  # readers
        apply=1
    }
)
```

```bash
# Start ProxySQL:
sudo systemctl start proxysql
sudo systemctl enable proxysql

# Update Django settings to use ProxySQL:
DB_HOST=127.0.0.1
DB_PORT=6033
```

### 4. Database Query Optimization

**Add Indexes**:
```python
# In your models:
class Prompt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'folder']),
        ]
```

**Use Select Related and Prefetch Related**:
```python
# ❌ BAD - N+1 queries
prompts = Prompt.objects.all()
for prompt in prompts:
    print(prompt.user.email)  # Extra query per prompt!

# ✅ GOOD - Single query with JOIN
prompts = Prompt.objects.select_related('user', 'folder').all()
for prompt in prompts:
    print(prompt.user.email)  # No extra query

# ✅ GOOD - For many-to-many or reverse foreign keys
users = User.objects.prefetch_related('prompts').all()
```

**Use Raw SQL for Complex Queries**:
```python
from django.db import connection

def get_user_stats():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.email, COUNT(p.id) as prompt_count
            FROM authentication_customuser u
            LEFT JOIN coreapp_prompt p ON p.user_id = u.id
            GROUP BY u.id
        """)
        return cursor.fetchall()
```

### 5. Database Partitioning

**Partition Large Tables**:
```sql
-- Partition prompts table by date:
ALTER TABLE coreapp_prompt
PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Partition by hash for better distribution:
ALTER TABLE coreapp_document
PARTITION BY HASH(user_id)
PARTITIONS 4;
```

---

## Redis Scaling

### 1. Vertical Scaling

```bash
# AWS ElastiCache: Increase node size
aws elasticache modify-cache-cluster \
  --cache-cluster-id multinotesai-redis \
  --cache-node-type cache.r5.xlarge \
  --apply-immediately
```

### 2. Redis Cluster (Horizontal Scaling)

**Create Redis Cluster**:
```bash
# AWS ElastiCache:
aws elasticache create-replication-group \
  --replication-group-id multinotesai-redis-cluster \
  --replication-group-description "MultinotesAI Redis Cluster" \
  --engine redis \
  --cache-node-type cache.r5.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --multi-az-enabled

# Self-hosted:
# Install Redis on 6 nodes (3 masters, 3 replicas)
redis-cli --cluster create \
  10.0.1.1:6379 10.0.1.2:6379 10.0.1.3:6379 \
  10.0.1.4:6379 10.0.1.5:6379 10.0.1.6:6379 \
  --cluster-replicas 1
```

**Configure Django for Redis Cluster**:
```python
# Install redis-py-cluster:
# pip install redis-py-cluster

# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            'redis://10.0.1.1:6379/0',
            'redis://10.0.1.2:6379/0',
            'redis://10.0.1.3:6379/0',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS': 'rediscluster.connection.ClusterConnectionPool',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'skip_full_coverage_check': True,
            },
        },
    }
}
```

### 3. Redis Sentinel (High Availability)

```bash
# Configure Redis Sentinel:
# sentinel.conf
port 26379
sentinel monitor multinotesai-master 10.0.1.1 6379 2
sentinel down-after-milliseconds multinotesai-master 5000
sentinel failover-timeout multinotesai-master 10000
sentinel parallel-syncs multinotesai-master 1

# Start Sentinel on 3+ nodes:
redis-sentinel /etc/redis/sentinel.conf
```

**Configure Django for Sentinel**:
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://multinotesai-master/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.SentinelClient',
            'SENTINELS': [
                ('10.0.1.10', 26379),
                ('10.0.1.11', 26379),
                ('10.0.1.12', 26379),
            ],
            'SENTINEL_KWARGS': {
                'password': 'sentinel_password',
            },
        },
    }
}
```

### 4. Redis Memory Optimization

```bash
# Configure Redis for optimal memory usage:
redis-cli CONFIG SET maxmemory 4gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Enable compression:
redis-cli CONFIG SET rdbcompression yes

# Optimize save intervals:
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

---

## CDN Configuration

### CloudFront (AWS)

**Create CloudFront Distribution**:
```bash
# Create distribution:
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

**cloudfront-config.json**:
```json
{
  "CallerReference": "multinotesai-2025-11-26",
  "Comment": "MultinotesAI CDN",
  "Enabled": true,
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "multinotesai-api",
        "DomainName": "api.multinotesai.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          }
        }
      },
      {
        "Id": "multinotesai-s3",
        "DomainName": "multinotesai-bucket.s3.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "multinotesai-api",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "all"},
      "Headers": {
        "Quantity": 3,
        "Items": ["Authorization", "Accept", "Accept-Language"]
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 3600,
    "MaxTTL": 86400,
    "Compress": true
  },
  "CacheBehaviors": {
    "Quantity": 2,
    "Items": [
      {
        "PathPattern": "/static/*",
        "TargetOriginId": "multinotesai-api",
        "ViewerProtocolPolicy": "redirect-to-https",
        "MinTTL": 31536000,
        "DefaultTTL": 31536000,
        "MaxTTL": 31536000,
        "Compress": true
      },
      {
        "PathPattern": "/media/*",
        "TargetOriginId": "multinotesai-s3",
        "ViewerProtocolPolicy": "redirect-to-https",
        "MinTTL": 86400,
        "DefaultTTL": 604800,
        "MaxTTL": 31536000,
        "Compress": true
      }
    ]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/abc123",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "Aliases": {
    "Quantity": 1,
    "Items": ["cdn.multinotesai.com"]
  }
}
```

**Configure Django for CDN**:
```python
# settings.py
if not DEBUG:
    # Serve static files from CDN
    STATIC_URL = 'https://cdn.multinotesai.com/static/'

    # Configure CloudFront for S3
    AWS_S3_CUSTOM_DOMAIN = 'cdn.multinotesai.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
```

---

## Load Balancer Setup

### AWS Application Load Balancer

**Create ALB**:
```bash
# Create load balancer:
aws elbv2 create-load-balancer \
  --name multinotesai-alb \
  --subnets subnet-12345678 subnet-87654321 \
  --security-groups sg-12345678 \
  --scheme internet-facing \
  --type application

# Create target group:
aws elbv2 create-target-group \
  --name multinotesai-web \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-12345678 \
  --health-check-protocol HTTP \
  --health-check-path /health/ \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Register targets:
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:region:account-id:targetgroup/multinotesai-web/abc123 \
  --targets Id=i-1234567890abcdef0 Id=i-0fedcba9876543210

# Create listener:
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/multinotesai-alb/abc123 \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:region:account-id:certificate/abc123 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account-id:targetgroup/multinotesai-web/abc123
```

**ALB Stickiness (Session Affinity)**:
```bash
# Enable sticky sessions:
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:region:account-id:targetgroup/multinotesai-web/abc123 \
  --attributes Key=stickiness.enabled,Value=true Key=stickiness.type,Value=lb_cookie Key=stickiness.lb_cookie.duration_seconds,Value=86400
```

### Nginx Load Balancer (Self-Hosted)

```nginx
# /etc/nginx/nginx.conf

upstream multinotesai_backend {
    # Load balancing method:
    # - round_robin (default)
    # - least_conn
    # - ip_hash (sticky sessions)
    least_conn;

    # Backend servers:
    server 10.0.1.10:8000 weight=3 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 weight=3 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 weight=2 max_fails=3 fail_timeout=30s;
    server 10.0.1.13:8000 backup;  # Backup server

    # Health check (requires nginx-plus or module):
    # health_check interval=10 fails=3 passes=2 uri=/health/;

    # Keepalive connections:
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.multinotesai.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.multinotesai.com;

    # SSL configuration:
    ssl_certificate /etc/letsencrypt/live/api.multinotesai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.multinotesai.com/privkey.pem;

    # Proxy to backend:
    location / {
        proxy_pass http://multinotesai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts:
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering:
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # Keepalive:
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Static files (direct serve):
    location /static/ {
        alias /var/www/multinotesai/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint:
    location /health/ {
        access_log off;
        proxy_pass http://multinotesai_backend;
    }
}
```

---

## Auto-Scaling

### AWS Auto Scaling Group

**Create Launch Template**:
```bash
aws ec2 create-launch-template \
  --launch-template-name multinotesai-web-template \
  --version-description "v2.0.0" \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t3.large",
    "KeyName": "multinotesai-key",
    "SecurityGroupIds": ["sg-12345678"],
    "IamInstanceProfile": {"Name": "multinotesai-ec2-role"},
    "UserData": "IyEvYmluL2Jhc2gKY2QgL3Zhci93d3cvbXVsdGlub3Rlc2FpCmdpdCBwdWxsIG9yaWdpbiBtYWluCnN1ZG8gc3lzdGVtY3RsIHJlc3RhcnQgZ3VuaWNvcm4="
  }'
```

**Create Auto Scaling Group**:
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name multinotesai-asg \
  --launch-template LaunchTemplateName=multinotesai-web-template,Version='$Latest' \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --default-cooldown 300 \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --vpc-zone-identifier "subnet-12345678,subnet-87654321" \
  --target-group-arns arn:aws:elasticloadbalancing:region:account-id:targetgroup/multinotesai-web/abc123 \
  --tags Key=Name,Value=multinotesai-web,PropagateAtLaunch=true
```

**Create Scaling Policies**:
```bash
# Scale up policy:
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name multinotesai-asg \
  --policy-name scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0
  }'

# Scale down policy (automatic with target tracking)
```

### Kubernetes Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: multinotesai-web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: multinotesai-web
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

```bash
kubectl apply -f hpa.yaml

# Monitor autoscaling:
kubectl get hpa
kubectl describe hpa multinotesai-web-hpa
```

---

## Performance Optimization

### 1. Enable Caching

**Query Caching**:
```python
from django.core.cache import cache
from django.db.models import Prefetch

def get_user_prompts(user_id):
    cache_key = f'user_prompts_{user_id}'
    prompts = cache.get(cache_key)

    if prompts is None:
        prompts = list(
            Prompt.objects
            .filter(user_id=user_id)
            .select_related('user', 'folder')
            .order_by('-created_at')[:100]
        )
        cache.set(cache_key, prompts, 300)  # 5 minutes

    return prompts
```

**View Caching**:
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
def public_prompts(request):
    prompts = Prompt.objects.filter(is_public=True)[:50]
    return render(request, 'prompts/public.html', {'prompts': prompts})
```

**Template Fragment Caching**:
```django
{% load cache %}
{% cache 500 sidebar request.user.id %}
    ... sidebar content ...
{% endcache %}
```

### 2. Database Connection Pooling

```python
# settings.py
DATABASES = {
    'default': {
        # ... other settings
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            # Connection pooling settings:
            'max_overflow': 10,
            'pool_size': 10,
            'pool_recycle': 3600,
        },
    }
}
```

### 3. Async Views (Django 4.1+)

```python
# For I/O bound operations:
from django.http import JsonResponse
import httpx

async def fetch_llm_response(request):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.together.xyz/v1/chat/completions',
            json={'model': 'meta-llama/Llama-3-70b', 'prompt': 'Hello'}
        )
        return JsonResponse(response.json())
```

### 4. Static File Compression

```nginx
# nginx.conf
http {
    # Gzip compression:
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # Brotli compression (if module installed):
    brotli on;
    brotli_comp_level 6;
    brotli_types text/plain text/css text/xml text/javascript
                 application/json application/javascript application/xml+rss;
}
```

---

## Capacity Planning

### Current Capacity (Single Server)

| Resource | Capacity | Usage (100 users) | Headroom |
|----------|----------|-------------------|----------|
| CPU (4 cores) | 100% | 40% | 60% → ~250 users |
| Memory (16GB) | 100% | 35% | 65% → ~450 users |
| Disk I/O | 1000 IOPS | 200 IOPS | 800 IOPS → ~500 users |
| Network | 1 Gbps | 200 Mbps | 800 Mbps → ~500 users |

**Bottleneck**: CPU → Can handle ~250 concurrent users

### Scaling Plan

| Users | Web Servers | DB Instance | Redis | Celery Workers |
|-------|-------------|-------------|-------|----------------|
| 0-500 | 1x t3.large | db.t3.large | cache.t3.medium | 2x t3.small |
| 500-2K | 2x t3.large | db.r5.xlarge | cache.r5.large | 4x t3.small |
| 2K-5K | 4x t3.xlarge | db.r5.2xlarge + 2 read replicas | cache.r5.xlarge | 8x t3.medium |
| 5K-10K | 8x t3.xlarge | db.r5.4xlarge + 4 read replicas | cache.r5.2xlarge cluster | 16x t3.medium |
| 10K+ | 15+ (auto-scale) | db.r5.8xlarge + 6+ read replicas | cache.r5.4xlarge cluster | 32+ (auto-scale) |

### Cost Estimation (AWS us-east-1)

| Tier | Users | Monthly Cost |
|------|-------|--------------|
| Starter | 0-500 | ~$300 |
| Growth | 500-2K | ~$800 |
| Scale | 2K-5K | ~$2,000 |
| Enterprise | 5K-10K | ~$5,000 |
| Massive | 10K+ | $10,000+ |

---

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Maintained By**: DevOps Team
**Contact**: devops@multinotesai.com
