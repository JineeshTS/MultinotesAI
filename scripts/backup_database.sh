#!/bin/bash
# =============================================================================
# Database Backup Script for MultinotesAI
# =============================================================================
#
# Usage:
#   ./backup_database.sh                    # Standard backup
#   ./backup_database.sh --full             # Full backup with binary logs
#   ./backup_database.sh --upload           # Backup and upload to S3
#   ./backup_database.sh --restore <file>   # Restore from backup
#
# Configuration:
#   Set environment variables or use .env file
#
# Prerequisites:
#   - MySQL client (mysqldump)
#   - AWS CLI (for S3 upload)
#   - gzip for compression
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

# Load environment variables
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Database settings
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-multinotesai}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Backup settings
BACKUP_DIR="${BACKUP_DIR:-/var/backups/multinotesai}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"

# S3 settings (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-backups/database}"

# Notification settings
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

send_notification() {
    local status="$1"
    local message="$2"

    # Send Slack notification
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\":\"[MultinotesAI Backup] $status: $message\"}" \
            > /dev/null 2>&1 || true
    fi

    # Send email notification
    if [[ -n "$ADMIN_EMAIL" ]]; then
        echo "$message" | mail -s "[MultinotesAI Backup] $status" "$ADMIN_EMAIL" 2>/dev/null || true
    fi
}

check_dependencies() {
    local missing=""

    if ! command -v mysqldump &> /dev/null; then
        missing="$missing mysqldump"
    fi

    if ! command -v gzip &> /dev/null; then
        missing="$missing gzip"
    fi

    if [[ -n "$missing" ]]; then
        log_error "Missing dependencies:$missing"
        exit 1
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
        chmod 700 "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# =============================================================================
# Backup Functions
# =============================================================================

perform_backup() {
    local backup_type="${1:-standard}"
    local start_time=$(date +%s)

    log_info "Starting $backup_type backup of database: $DB_NAME"

    # Build mysqldump options
    local dump_opts="--single-transaction --routines --triggers --events"

    if [[ "$backup_type" == "full" ]]; then
        dump_opts="$dump_opts --master-data=2 --flush-logs"
    fi

    # Perform backup
    if [[ -n "$DB_PASSWORD" ]]; then
        MYSQL_PWD="$DB_PASSWORD" mysqldump \
            -h "$DB_HOST" \
            -P "$DB_PORT" \
            -u "$DB_USER" \
            $dump_opts \
            "$DB_NAME" > "$BACKUP_FILE"
    else
        mysqldump \
            -h "$DB_HOST" \
            -P "$DB_PORT" \
            -u "$DB_USER" \
            $dump_opts \
            "$DB_NAME" > "$BACKUP_FILE"
    fi

    # Compress backup
    log_info "Compressing backup..."
    gzip -f "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"

    # Calculate backup size and duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local size=$(du -h "$BACKUP_FILE" | cut -f1)

    log_info "Backup completed: $BACKUP_FILE"
    log_info "Size: $size, Duration: ${duration}s"

    echo "$BACKUP_FILE"
}

upload_to_s3() {
    local backup_file="$1"

    if [[ -z "$S3_BUCKET" ]]; then
        log_warn "S3 bucket not configured, skipping upload"
        return 0
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed, cannot upload to S3"
        return 1
    fi

    log_info "Uploading to S3: s3://$S3_BUCKET/$S3_PREFIX/"

    aws s3 cp "$backup_file" "s3://$S3_BUCKET/$S3_PREFIX/" \
        --storage-class STANDARD_IA

    log_info "Upload completed"
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    # Clean local backups
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

    local deleted=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS 2>/dev/null | wc -l)
    log_info "Deleted $deleted old local backups"

    # Clean S3 backups (if configured)
    if [[ -n "$S3_BUCKET" ]] && command -v aws &> /dev/null; then
        local cutoff_date=$(date -d "-$RETENTION_DAYS days" +%Y-%m-%d)

        aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/" | while read -r line; do
            file_date=$(echo "$line" | awk '{print $1}')
            file_name=$(echo "$line" | awk '{print $4}')

            if [[ "$file_date" < "$cutoff_date" ]]; then
                aws s3 rm "s3://$S3_BUCKET/$S3_PREFIX/$file_name"
                log_info "Deleted old S3 backup: $file_name"
            fi
        done
    fi
}

restore_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "WARNING: This will overwrite the current database!"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from: $backup_file"

    # Decompress if needed
    if [[ "$backup_file" == *.gz ]]; then
        log_info "Decompressing backup..."
        gunzip -c "$backup_file" > /tmp/restore_temp.sql
        backup_file="/tmp/restore_temp.sql"
    fi

    # Restore
    if [[ -n "$DB_PASSWORD" ]]; then
        MYSQL_PWD="$DB_PASSWORD" mysql \
            -h "$DB_HOST" \
            -P "$DB_PORT" \
            -u "$DB_USER" \
            "$DB_NAME" < "$backup_file"
    else
        mysql \
            -h "$DB_HOST" \
            -P "$DB_PORT" \
            -u "$DB_USER" \
            "$DB_NAME" < "$backup_file"
    fi

    # Cleanup temp file
    rm -f /tmp/restore_temp.sql

    log_info "Database restored successfully"
}

verify_backup() {
    local backup_file="$1"

    log_info "Verifying backup integrity..."

    # Check if file exists and is not empty
    if [[ ! -s "$backup_file" ]]; then
        log_error "Backup file is empty or does not exist"
        return 1
    fi

    # Check if it's a valid gzip file
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>/dev/null; then
            log_error "Backup file is corrupted"
            return 1
        fi
    fi

    # Check for SQL structure markers
    if [[ "$backup_file" == *.gz ]]; then
        if ! zgrep -q "CREATE TABLE" "$backup_file"; then
            log_warn "Backup may be incomplete (no CREATE TABLE statements found)"
        fi
    else
        if ! grep -q "CREATE TABLE" "$backup_file"; then
            log_warn "Backup may be incomplete (no CREATE TABLE statements found)"
        fi
    fi

    log_info "Backup verification passed"
    return 0
}

# =============================================================================
# Main Function
# =============================================================================

main() {
    local action="backup"
    local backup_type="standard"
    local upload=false
    local restore_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                backup_type="full"
                shift
                ;;
            --upload)
                upload=true
                shift
                ;;
            --restore)
                action="restore"
                restore_file="$2"
                shift 2
                ;;
            --cleanup)
                action="cleanup"
                shift
                ;;
            --verify)
                action="verify"
                restore_file="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --full              Full backup with binary logs"
                echo "  --upload            Upload backup to S3"
                echo "  --restore <file>    Restore from backup file"
                echo "  --cleanup           Clean up old backups"
                echo "  --verify <file>     Verify backup integrity"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check dependencies
    check_dependencies

    # Create backup directory
    create_backup_dir

    # Execute action
    case $action in
        backup)
            backup_file=$(perform_backup "$backup_type")

            if verify_backup "$backup_file"; then
                if [[ "$upload" == true ]]; then
                    upload_to_s3 "$backup_file"
                fi
                cleanup_old_backups
                send_notification "SUCCESS" "Backup completed: $(basename "$backup_file")"
            else
                send_notification "FAILED" "Backup verification failed"
                exit 1
            fi
            ;;
        restore)
            restore_backup "$restore_file"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        verify)
            verify_backup "$restore_file"
            ;;
    esac

    log_info "Operation completed successfully"
}

# Run main function
main "$@"
