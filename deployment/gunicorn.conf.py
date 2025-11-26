"""
Gunicorn Configuration for MultinotesAI

This file configures Gunicorn for production deployment.
Usage: gunicorn -c gunicorn.conf.py backend.wsgi:application
"""

import multiprocessing
import os

# =============================================================================
# Server Socket
# =============================================================================

# Bind to Unix socket for better performance with Nginx
bind = os.getenv('GUNICORN_BIND', 'unix:/var/run/multinotesai/gunicorn.sock')

# Backlog - number of pending connections
backlog = 2048

# =============================================================================
# Worker Processes
# =============================================================================

# Number of worker processes
# Recommended: 2-4 x $(NUM_CORES)
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker class - gthread for I/O bound applications
worker_class = 'gthread'

# Threads per worker
threads = int(os.getenv('GUNICORN_THREADS', 4))

# Maximum concurrent connections per worker
worker_connections = 1000

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Timeout for worker processes
timeout = 300  # 5 minutes for long AI requests
graceful_timeout = 30
keepalive = 5

# =============================================================================
# Server Mechanics
# =============================================================================

# Daemonize the Gunicorn process (set to False for supervisor)
daemon = False

# PID file location
pidfile = '/var/run/multinotesai/gunicorn.pid'

# User and group to run workers as
user = os.getenv('GUNICORN_USER', 'www-data')
group = os.getenv('GUNICORN_GROUP', 'www-data')

# Change to this directory before starting
chdir = '/var/www/multinotesai/backend'

# Use tmpfs for worker temp directory (faster)
worker_tmp_dir = '/dev/shm'

# =============================================================================
# Logging
# =============================================================================

# Access log - "-" means stdout
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '/var/log/multinotesai/gunicorn_access.log')

# Error log - "-" means stderr
errorlog = os.getenv('GUNICORN_ERROR_LOG', '/var/log/multinotesai/gunicorn_error.log')

# Log level
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Capture stdout and stderr
capture_output = True

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# =============================================================================
# Process Naming
# =============================================================================

proc_name = 'multinotesai'

# =============================================================================
# SSL (if terminating SSL at Gunicorn instead of Nginx)
# =============================================================================

# Uncomment to enable SSL at Gunicorn level
# certfile = '/etc/letsencrypt/live/multinotesai.com/fullchain.pem'
# keyfile = '/etc/letsencrypt/live/multinotesai.com/privkey.pem'

# =============================================================================
# Server Hooks
# =============================================================================

def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    pass

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    pass

def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    pass

def pre_exec(server):
    """Called just before a new master process is forked."""
    pass

def child_exit(server, worker):
    """Called in the master process after a worker has exited."""
    pass

def worker_exit(server, worker):
    """Called in the worker process just after exiting."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    pass

def on_exit(server):
    """Called just before exiting Gunicorn."""
    pass
