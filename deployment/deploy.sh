#!/bin/bash
# =============================================================================
# Deployment Script for MultinotesAI
# =============================================================================
#
# Usage:
#   ./deploy.sh                    # Full deployment
#   ./deploy.sh --quick            # Quick deployment (skip migrations)
#   ./deploy.sh --rollback         # Rollback to previous version
#
# Prerequisites:
#   - SSH access to server
#   - Git repository cloned
#   - Python virtual environment
#   - Supervisor and Nginx installed
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

APP_NAME="multinotesai"
APP_USER="www-data"
APP_DIR="/var/www/multinotesai"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="/var/log/multinotesai"
RUN_DIR="/var/run/multinotesai"
BACKUP_DIR="${APP_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# =============================================================================
# Deployment Functions
# =============================================================================

create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p ${LOG_DIR}
    mkdir -p ${RUN_DIR}
    mkdir -p ${BACKUP_DIR}
    mkdir -p ${BACKEND_DIR}/staticfiles
    mkdir -p ${BACKEND_DIR}/media
    chown -R ${APP_USER}:${APP_USER} ${LOG_DIR}
    chown -R ${APP_USER}:${APP_USER} ${RUN_DIR}
    chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
}

backup_database() {
    log_info "Backing up database..."
    source ${BACKEND_DIR}/.env 2>/dev/null || true

    if [[ -n "${DB_NAME:-}" ]]; then
        mysqldump -u ${DB_USER:-root} -p${DB_PASSWORD:-} ${DB_NAME} > \
            ${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql 2>/dev/null || \
            log_warn "Database backup failed (might be first deploy)"
    fi
}

pull_latest_code() {
    log_info "Pulling latest code from repository..."
    cd ${APP_DIR}

    # Stash any local changes
    git stash 2>/dev/null || true

    # Pull latest changes
    git fetch origin
    git pull origin main
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    cd ${BACKEND_DIR}

    # Activate virtual environment
    source ${VENV_DIR}/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    pip install -r requirements.txt
}

run_migrations() {
    log_info "Running database migrations..."
    cd ${BACKEND_DIR}
    source ${VENV_DIR}/bin/activate

    python manage.py migrate --noinput
}

collect_static() {
    log_info "Collecting static files..."
    cd ${BACKEND_DIR}
    source ${VENV_DIR}/bin/activate

    python manage.py collectstatic --noinput
}

restart_services() {
    log_info "Restarting services..."

    # Restart supervisor processes
    supervisorctl reread
    supervisorctl update
    supervisorctl restart ${APP_NAME}:*

    # Reload Nginx
    nginx -t && systemctl reload nginx

    log_info "Services restarted successfully"
}

run_health_check() {
    log_info "Running health check..."
    sleep 5

    # Check if Gunicorn is running
    if pgrep -f "gunicorn.*${APP_NAME}" > /dev/null; then
        log_info "Gunicorn is running"
    else
        log_error "Gunicorn is not running!"
        exit 1
    fi

    # Check if Celery is running
    if pgrep -f "celery.*${APP_NAME}" > /dev/null; then
        log_info "Celery is running"
    else
        log_warn "Celery might not be running"
    fi

    # Check HTTP endpoint
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ | grep -q "200"; then
        log_info "HTTP health check passed"
    else
        log_error "HTTP health check failed!"
        exit 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 5)..."
    cd ${BACKUP_DIR}
    ls -t db_backup_*.sql 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
}

rollback() {
    log_warn "Rolling back to previous version..."
    cd ${APP_DIR}

    # Get previous commit
    PREVIOUS_COMMIT=$(git rev-parse HEAD~1)

    # Checkout previous commit
    git checkout ${PREVIOUS_COMMIT}

    # Restart services
    restart_services

    log_info "Rollback complete to ${PREVIOUS_COMMIT}"
}

# =============================================================================
# Main Deployment Flow
# =============================================================================

main() {
    log_info "Starting deployment for ${APP_NAME}..."
    log_info "Timestamp: ${TIMESTAMP}"

    check_root

    # Check for flags
    QUICK_DEPLOY=false
    ROLLBACK=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_DEPLOY=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    if [[ "$ROLLBACK" == true ]]; then
        rollback
        exit 0
    fi

    # Run deployment steps
    create_directories
    backup_database
    pull_latest_code
    install_dependencies

    if [[ "$QUICK_DEPLOY" == false ]]; then
        run_migrations
    fi

    collect_static
    restart_services
    run_health_check
    cleanup_old_backups

    log_info "Deployment completed successfully!"
}

# Run main function with all arguments
main "$@"
