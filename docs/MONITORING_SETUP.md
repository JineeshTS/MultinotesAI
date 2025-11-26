# Monitoring Setup Guide - MultinotesAI

This guide provides comprehensive instructions for setting up monitoring, logging, and alerting for the MultinotesAI production environment.

**Last Updated**: 2025-11-26
**Version**: 2.0.0

---

## Table of Contents
- [Overview](#overview)
- [Sentry Setup](#sentry-setup)
- [Log Aggregation](#log-aggregation)
- [System Monitoring](#system-monitoring)
- [Application Monitoring](#application-monitoring)
- [Alerting Configuration](#alerting-configuration)
- [Key Metrics](#key-metrics)
- [Dashboard Templates](#dashboard-templates)
- [On-Call Setup](#on-call-setup)

---

## Overview

### Monitoring Stack
- **Error Tracking**: Sentry (already integrated in settings.py)
- **Log Aggregation**: ELK Stack, CloudWatch Logs, or Datadog
- **Metrics**: Prometheus + Grafana (recommended) or CloudWatch
- **Uptime Monitoring**: UptimeRobot, Pingdom, or StatusCake
- **APM**: Sentry Performance or New Relic

### Monitoring Objectives
- **Availability**: 99.9% uptime
- **Performance**: p95 response time <500ms
- **Error Rate**: <1% of total requests
- **Recovery Time**: <15 minutes for critical issues

---

## Sentry Setup

### 1. Create Sentry Account and Project

```bash
# Visit: https://sentry.io/signup/
# Create organization: "multinotesai"
# Create project: "multinotesai-backend" (Django)
```

### 2. Install Sentry SDK

Already included in requirements.txt:
```txt
sentry-sdk==1.40.0
```

### 3. Configuration

Sentry is already configured in `settings.py` (lines 622-666). Verify configuration:

```python
# backend/settings.py

SENTRY_DSN = get_env_variable('SENTRY_DSN')

if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
            ),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,
        release='2.0.0',
        environment='production',
        send_default_pii=False,
    )
```

### 4. Add Sentry DSN to Environment

```bash
# Add to .env file:
SENTRY_DSN=https://[your_sentry_key]@[sentry_instance].ingest.sentry.io/[project_id]
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=2.0.0
```

### 5. Test Sentry Integration

```python
# Django shell:
python manage.py shell

from sentry_sdk import capture_exception, capture_message

# Test error capture:
try:
    1 / 0
except Exception as e:
    capture_exception(e)

# Test message capture:
capture_message("Sentry test message", level="info")

# Check Sentry dashboard to verify events received
```

### 6. Configure Sentry Alerts

#### a) High Error Rate Alert
```yaml
# Sentry UI: Alerts > Create Alert Rule

When: Error count
Condition: is greater than 50
In: 1 hour
For: production environment
Then: Send notification to #alerts Slack channel
And: Email devops@multinotesai.com
```

#### b) New Issue Alert
```yaml
When: A new issue is created
For: production environment
Filter: level equals error or fatal
Then: Send notification to #critical-alerts Slack channel
```

#### c) Performance Degradation Alert
```yaml
When: Transaction duration p95
Condition: is greater than 1000ms
In: 5 minutes
For: production environment
Then: Send notification to #performance Slack channel
```

### 7. Sentry Releases

Configure automatic release tracking:

```bash
# Install Sentry CLI:
npm install -g @sentry/cli
# or
curl -sL https://sentry.io/get-cli/ | bash

# Configure Sentry CLI:
cat > .sentryclirc << EOF
[defaults]
url = https://sentry.io/
org = multinotesai
project = multinotesai-backend

[auth]
token = your_auth_token_here
EOF

# Create release on deployment:
export SENTRY_RELEASE=$(sentry-cli releases propose-version)
sentry-cli releases new -p multinotesai-backend $SENTRY_RELEASE
sentry-cli releases set-commits $SENTRY_RELEASE --auto
sentry-cli releases finalize $SENTRY_RELEASE

# Add to deployment script:
# deployment/deploy.sh
```

### 8. Sentry Integrations

#### Slack Integration
```bash
# Sentry UI: Settings > Integrations > Slack
# Connect workspace
# Configure notification channels:
# - #alerts (general errors)
# - #critical-alerts (critical errors)
# - #performance (performance issues)
```

#### GitHub Integration
```bash
# Sentry UI: Settings > Integrations > GitHub
# Connect repository: multinotesai/MultinotesAI
# Enable:
# - Commit tracking
# - Issue linking
# - Pull request tracking
```

### 9. Sentry Performance Monitoring

Enable performance monitoring for key transactions:

```python
# In views or functions you want to track:
from sentry_sdk import start_transaction

def process_prompt(request):
    with start_transaction(op="task", name="process_prompt") as transaction:
        # Your code here
        with transaction.start_child(op="llm", description="Call TogetherAI"):
            result = call_llm_api()
        return result
```

### 10. Sentry User Feedback

Capture user context for better debugging:

```python
# In authentication middleware or view:
from sentry_sdk import set_user

set_user({
    "id": user.id,
    "email": user.email,
    "username": user.username,
    # Don't include sensitive data
})
```

---

## Log Aggregation

### Option 1: ELK Stack (Elasticsearch, Logstash, Kibana)

#### A. Install Elasticsearch

```bash
# Install Elasticsearch:
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
sudo apt-get install apt-transport-https
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt-get update && sudo apt-get install elasticsearch

# Configure Elasticsearch:
sudo nano /etc/elasticsearch/elasticsearch.yml
```

```yaml
# /etc/elasticsearch/elasticsearch.yml
cluster.name: multinotesai-logs
node.name: node-1
network.host: 127.0.0.1
http.port: 9200
discovery.type: single-node

# Security:
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
```

```bash
# Start Elasticsearch:
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch

# Verify running:
curl -X GET "localhost:9200/"
```

#### B. Install Logstash

```bash
# Install Logstash:
sudo apt-get install logstash

# Configure Logstash:
sudo nano /etc/logstash/conf.d/multinotesai.conf
```

```ruby
# /etc/logstash/conf.d/multinotesai.conf
input {
  file {
    path => "/var/log/multinotesai/gunicorn.log"
    type => "gunicorn"
    codec => json
  }

  file {
    path => "/var/log/nginx/access.log"
    type => "nginx-access"
  }

  file {
    path => "/var/log/nginx/error.log"
    type => "nginx-error"
  }

  file {
    path => "/var/log/multinotesai/celery.log"
    type => "celery"
  }
}

filter {
  if [type] == "nginx-access" {
    grok {
      match => { "message" => "%{NGINXACCESS}" }
    }
  }

  if [type] == "gunicorn" {
    json {
      source => "message"
    }
  }

  date {
    match => [ "timestamp", "ISO8601" ]
  }

  geoip {
    source => "clientip"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "multinotesai-%{+YYYY.MM.dd}"
    user => "elastic"
    password => "${ELASTIC_PASSWORD}"
  }
}
```

```bash
# Start Logstash:
sudo systemctl enable logstash
sudo systemctl start logstash
```

#### C. Install Kibana

```bash
# Install Kibana:
sudo apt-get install kibana

# Configure Kibana:
sudo nano /etc/kibana/kibana.yml
```

```yaml
# /etc/kibana/kibana.yml
server.port: 5601
server.host: "0.0.0.0"
elasticsearch.hosts: ["http://localhost:9200"]
elasticsearch.username: "elastic"
elasticsearch.password: "your_password"
```

```bash
# Start Kibana:
sudo systemctl enable kibana
sudo systemctl start kibana

# Access Kibana:
# http://your-server-ip:5601
```

#### D. Configure Kibana Dashboards

```bash
# Create index pattern:
# Kibana UI > Stack Management > Index Patterns
# Create pattern: multinotesai-*
# Time field: @timestamp

# Import dashboards:
# Kibana UI > Stack Management > Saved Objects > Import
```

---

### Option 2: AWS CloudWatch Logs

#### A. Install CloudWatch Agent

```bash
# Download CloudWatch agent:
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure CloudWatch agent:
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

#### B. Configure Log Groups

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/multinotesai/gunicorn.log",
            "log_group_name": "/multinotesai/gunicorn",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/multinotesai/nginx/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/multinotesai/nginx/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/multinotesai/celery.log",
            "log_group_name": "/multinotesai/celery",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

```bash
# Start CloudWatch agent:
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

#### C. Create CloudWatch Alarms

```bash
# High error rate alarm:
aws cloudwatch put-metric-alarm \
  --alarm-name multinotesai-high-error-rate \
  --alarm-description "Alert when error rate exceeds threshold" \
  --metric-name ErrorCount \
  --namespace MultinotesAI \
  --statistic Sum \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:region:account-id:multinotesai-alerts
```

---

### Option 3: Datadog

#### A. Install Datadog Agent

```bash
# Install Datadog agent:
DD_API_KEY=your_api_key DD_SITE="datadoghq.com" bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure agent:
sudo nano /etc/datadog-agent/datadog.yaml
```

```yaml
# /etc/datadog-agent/datadog.yaml
api_key: your_api_key
site: datadoghq.com
tags:
  - env:production
  - service:multinotesai
  - version:2.0.0

logs_enabled: true
```

#### B. Configure Log Collection

```bash
# Create log config:
sudo nano /etc/datadog-agent/conf.d/multinotesai.d/conf.yaml
```

```yaml
logs:
  - type: file
    path: /var/log/multinotesai/gunicorn.log
    service: multinotesai
    source: gunicorn

  - type: file
    path: /var/log/nginx/access.log
    service: nginx
    source: nginx

  - type: file
    path: /var/log/nginx/error.log
    service: nginx
    source: nginx
    log_processing_rules:
      - type: multi_line
        pattern: \d{4}-\d{2}-\d{2}
        name: new_log_start_with_date

  - type: file
    path: /var/log/multinotesai/celery.log
    service: celery
    source: celery
```

```bash
# Restart Datadog agent:
sudo systemctl restart datadog-agent
```

---

## System Monitoring

### Option 1: Prometheus + Grafana

#### A. Install Prometheus

```bash
# Create Prometheus user:
sudo useradd --no-create-home --shell /bin/false prometheus

# Download Prometheus:
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvf prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64

# Move files:
sudo mv prometheus /usr/local/bin/
sudo mv promtool /usr/local/bin/
sudo mkdir /etc/prometheus
sudo mkdir /var/lib/prometheus
sudo mv consoles /etc/prometheus/
sudo mv console_libraries /etc/prometheus/

# Create Prometheus config:
sudo nano /etc/prometheus/prometheus.yml
```

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'multinotesai-production'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']

  - job_name: 'mysql'
    static_configs:
      - targets: ['localhost:9104']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'celery'
    static_configs:
      - targets: ['localhost:9808']
```

```bash
# Create systemd service:
sudo nano /etc/systemd/system/prometheus.service
```

```ini
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file /etc/prometheus/prometheus.yml \
  --storage.tsdb.path /var/lib/prometheus/ \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries

[Install]
WantedBy=multi-user.target
```

```bash
# Set permissions:
sudo chown -R prometheus:prometheus /etc/prometheus
sudo chown -R prometheus:prometheus /var/lib/prometheus

# Start Prometheus:
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus

# Verify:
curl localhost:9090/metrics
```

#### B. Install Node Exporter

```bash
# Download Node Exporter:
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvf node_exporter-1.6.1.linux-amd64.tar.gz
sudo mv node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/

# Create systemd service:
sudo nano /etc/systemd/system/node_exporter.service
```

```ini
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
```

```bash
# Start Node Exporter:
sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
```

#### C. Install Grafana

```bash
# Install Grafana:
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana

# Start Grafana:
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Access Grafana:
# http://your-server-ip:3000
# Default login: admin/admin
```

#### D. Configure Grafana

```bash
# Add Prometheus data source:
# Grafana UI > Configuration > Data Sources > Add data source
# Select: Prometheus
# URL: http://localhost:9090
# Click: Save & Test
```

---

### Option 2: AWS CloudWatch

```bash
# Install CloudWatch agent (see Log Aggregation section)

# Configure metrics:
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/config.json
```

```json
{
  "metrics": {
    "namespace": "MultinotesAI",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          {"name": "cpu_usage_iowait", "rename": "CPU_IOWAIT", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "diskio": {
        "measurement": [
          {"name": "io_time", "unit": "Milliseconds"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": [
          {"name": "tcp_established", "rename": "TCP_CONNECTIONS", "unit": "Count"}
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
```

---

## Application Monitoring

### Django Prometheus Exporter

```bash
# Install django-prometheus:
pip install django-prometheus

# Add to INSTALLED_APPS:
# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

# Add to MIDDLEWARE (at top):
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Update database config:
DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.mysql',
        # ... rest of config
    }
}

# Add to urls.py:
urlpatterns = [
    path('', include('django_prometheus.urls')),
    # ... other URLs
]

# Restart application:
sudo systemctl restart gunicorn
```

```bash
# Verify metrics endpoint:
curl http://localhost:8000/metrics

# Metrics available:
# - django_http_requests_total
# - django_http_requests_latency_seconds
# - django_db_query_duration_seconds
# - django_db_new_connections_total
```

### Celery Prometheus Exporter

```bash
# Install celery-prometheus-exporter:
pip install celery-prometheus-exporter

# Start exporter:
celery-exporter --broker=$CELERY_BROKER_URL --port=9808

# Or as systemd service:
sudo nano /etc/systemd/system/celery-exporter.service
```

```ini
[Unit]
Description=Celery Prometheus Exporter
After=network.target

[Service]
Type=simple
User=celery
Environment="CELERY_BROKER_URL=redis://localhost:6379/0"
ExecStart=/usr/local/bin/celery-exporter --broker=$CELERY_BROKER_URL --port=9808
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# Start exporter:
sudo systemctl daemon-reload
sudo systemctl start celery-exporter
sudo systemctl enable celery-exporter
```

### Nginx Prometheus Exporter

```bash
# Enable Nginx stub_status:
sudo nano /etc/nginx/sites-available/multinotesai.conf
```

```nginx
server {
    listen 127.0.0.1:80;
    server_name localhost;

    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}
```

```bash
# Install nginx-prometheus-exporter:
wget https://github.com/nginxinc/nginx-prometheus-exporter/releases/download/v0.11.0/nginx-prometheus-exporter_0.11.0_linux_amd64.tar.gz
tar xvf nginx-prometheus-exporter_0.11.0_linux_amd64.tar.gz
sudo mv nginx-prometheus-exporter /usr/local/bin/

# Create systemd service:
sudo nano /etc/systemd/system/nginx-exporter.service
```

```ini
[Unit]
Description=Nginx Prometheus Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/nginx-prometheus-exporter -nginx.scrape-uri=http://localhost/nginx_status

[Install]
WantedBy=multi-user.target
```

```bash
# Start exporter:
sudo systemctl daemon-reload
sudo systemctl start nginx-exporter
sudo systemctl enable nginx-exporter
```

---

## Alerting Configuration

### Prometheus Alerting Rules

```bash
# Create alert rules:
sudo nano /etc/prometheus/alerts.yml
```

```yaml
groups:
  - name: multinotesai_alerts
    interval: 30s
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High HTTP error rate detected"
          description: "Error rate is {{ $value }} errors/sec on {{ $labels.instance }}"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, django_http_requests_latency_seconds_bucket) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API response time"
          description: "p95 response time is {{ $value }}s on {{ $labels.instance }}"

      # High CPU Usage
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}% on {{ $labels.instance }}"

      # Low Disk Space
      - alert: LowDiskSpace
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 85
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value }}% on {{ $labels.instance }}"

      # Service Down
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} on {{ $labels.instance }} is down"

      # Celery Queue Buildup
      - alert: CeleryQueueBuildup
        expr: celery_queue_length > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue buildup"
          description: "Celery queue has {{ $value }} pending tasks"

      # Database Connection Pool Exhaustion
      - alert: DBConnectionPoolExhaustion
        expr: django_db_connections_total - django_db_connections_closed_total > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "{{ $value }} active database connections"
```

```bash
# Update Prometheus config to include alerts:
sudo nano /etc/prometheus/prometheus.yml
```

```yaml
# Add to prometheus.yml:
rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093
```

### Install Alertmanager

```bash
# Download Alertmanager:
cd /tmp
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.linux-amd64.tar.gz
tar xvf alertmanager-0.26.0.linux-amd64.tar.gz
cd alertmanager-0.26.0.linux-amd64

# Move files:
sudo mv alertmanager /usr/local/bin/
sudo mv amtool /usr/local/bin/
sudo mkdir /etc/alertmanager
sudo mv alertmanager.yml /etc/alertmanager/

# Configure Alertmanager:
sudo nano /etc/alertmanager/alertmanager.yml
```

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    email_configs:
      - to: 'devops@multinotesai.com'
        from: 'alerts@multinotesai.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@multinotesai.com'
        auth_password: 'your_password'

  - name: 'critical'
    slack_configs:
      - channel: '#critical-alerts'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
    email_configs:
      - to: 'devops@multinotesai.com,cto@multinotesai.com'

  - name: 'warning'
    slack_configs:
      - channel: '#alerts'
        title: 'WARNING: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

```bash
# Create systemd service:
sudo nano /etc/systemd/system/alertmanager.service
```

```ini
[Unit]
Description=Alertmanager
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/alertmanager --config.file=/etc/alertmanager/alertmanager.yml

[Install]
WantedBy=multi-user.target
```

```bash
# Start Alertmanager:
sudo systemctl daemon-reload
sudo systemctl start alertmanager
sudo systemctl enable alertmanager

# Restart Prometheus:
sudo systemctl restart prometheus
```

---

## Key Metrics

### Application Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Request Rate | - | - |
| Error Rate | <1% | >5% for 5min |
| p50 Response Time | <200ms | - |
| p95 Response Time | <500ms | >1s for 5min |
| p99 Response Time | <1s | >2s for 5min |
| Active Users | - | - |
| Request Size | - | - |
| Response Size | - | - |

### System Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| CPU Usage | <70% | >80% for 10min |
| Memory Usage | <80% | >85% for 10min |
| Disk Usage | <80% | >85% for 5min |
| Network I/O | - | - |
| Load Average | <# of CPUs | >(# of CPUs * 2) |

### Database Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Connection Count | <100 | >150 |
| Query Duration p95 | <100ms | >500ms |
| Slow Queries | 0 | >10/min |
| Deadlocks | 0 | >1 |
| Replication Lag | <1s | >10s |

### Redis Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Memory Usage | <80% | >90% |
| Hit Rate | >90% | <80% |
| Connected Clients | <100 | >200 |
| Evicted Keys | 0 | >100/min |
| Commands/sec | - | - |

### Celery Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Queue Length | <100 | >1000 |
| Task Duration p95 | <5s | >30s |
| Task Failure Rate | <1% | >5% |
| Active Workers | ≥2 | <2 |
| Worker CPU | <80% | >90% |

---

## Dashboard Templates

### Grafana Dashboard: System Overview

```json
{
  "dashboard": {
    "title": "MultinotesAI - System Overview",
    "panels": [
      {
        "title": "CPU Usage",
        "targets": [
          {
            "expr": "100 - (avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
          }
        ]
      },
      {
        "title": "Disk Usage",
        "targets": [
          {
            "expr": "(1 - (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"})) * 100"
          }
        ]
      },
      {
        "title": "Network Traffic",
        "targets": [
          {
            "expr": "rate(node_network_receive_bytes_total[5m])",
            "legendFormat": "Receive"
          },
          {
            "expr": "rate(node_network_transmit_bytes_total[5m])",
            "legendFormat": "Transmit"
          }
        ]
      }
    ]
  }
}
```

### Grafana Dashboard: Application Performance

```json
{
  "dashboard": {
    "title": "MultinotesAI - Application Performance",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(django_http_requests_total[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(django_http_responses_total_by_status_total{status=~\"5..\"}[5m]))"
          }
        ]
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, django_http_requests_latency_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Database Queries",
        "targets": [
          {
            "expr": "rate(django_db_query_duration_seconds_count[5m])"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100"
          }
        ]
      },
      {
        "title": "Celery Queue Length",
        "targets": [
          {
            "expr": "celery_queue_length"
          }
        ]
      }
    ]
  }
}
```

---

## On-Call Setup

### 1. Create On-Call Rotation

```yaml
# Example rotation schedule:
Week 1: Engineer A
Week 2: Engineer B
Week 3: Engineer C
Week 4: Engineer D

# Backup: DevOps Manager
```

### 2. On-Call Responsibilities

- Monitor alerts (Slack, email, PagerDuty)
- Respond to incidents within 15 minutes
- Escalate critical issues
- Document incidents
- Perform post-mortems

### 3. Set Up PagerDuty (Optional)

```bash
# Sign up: https://www.pagerduty.com/
# Create service: MultinotesAI Production
# Configure escalation policy
# Integrate with Alertmanager, Sentry, etc.
```

### 4. Runbook for On-Call Engineers

See [DEPLOYMENT_RUNBOOK.md](./DEPLOYMENT_RUNBOOK.md) for troubleshooting procedures.

---

## Testing Monitoring Setup

```bash
# 1. Test Sentry:
python manage.py shell
from sentry_sdk import capture_exception
capture_exception(Exception("Test error"))

# 2. Test Prometheus metrics:
curl localhost:9090/api/v1/query?query=up

# 3. Test Alertmanager:
curl -XPOST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Test alert"}
  }]'

# 4. Test Slack notifications:
# Should receive alert in configured Slack channel

# 5. Load test to trigger alerts:
locust -f loadtest.py --host=https://api.multinotesai.com --users 1000 --spawn-rate 100
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Maintained By**: DevOps Team
**Contact**: devops@multinotesai.com
