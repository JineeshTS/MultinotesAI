#!/usr/bin/env python
"""
Automated Backup System for MultinotesAI.

This script provides:
- Database backups
- File storage backups
- S3 upload capability
- Backup rotation
- Notification on failure

Usage:
    python scripts/automated_backup.py database
    python scripts/automated_backup.py files
    python scripts/automated_backup.py full
    python scripts/automated_backup.py --help

Schedule with cron:
    0 2 * * * cd /path/to/project && python scripts/automated_backup.py full
"""

import os
import sys
import gzip
import shutil
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Configuration
class BackupConfig:
    """Backup configuration."""

    # Directories
    BACKUP_DIR = os.environ.get('BACKUP_DIR', '/var/backups/multinotesai')
    TEMP_DIR = '/tmp/multinotesai_backup'

    # Retention
    DAILY_RETENTION_DAYS = 7
    WEEKLY_RETENTION_WEEKS = 4
    MONTHLY_RETENTION_MONTHS = 12

    # S3 settings
    S3_ENABLED = os.environ.get('BACKUP_S3_ENABLED', 'false').lower() == 'true'
    S3_BUCKET = os.environ.get('BACKUP_S3_BUCKET', '')
    S3_PREFIX = os.environ.get('BACKUP_S3_PREFIX', 'backups/')

    # Notification settings
    NOTIFY_ON_FAILURE = True
    NOTIFY_EMAIL = os.environ.get('BACKUP_NOTIFY_EMAIL', '')

    # Database settings from environment
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'multinotesai')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

    # Files to backup
    MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/var/www/multinotesai/media')


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupManager:
    """Manage database and file backups."""

    def __init__(self, config=None):
        self.config = config or BackupConfig
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure backup directories exist."""
        Path(self.config.BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    def backup_database(self) -> Optional[str]:
        """
        Backup database using mysqldump.

        Returns:
            Path to backup file or None on failure
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"db_backup_{timestamp}.sql"
        backup_path = Path(self.config.TEMP_DIR) / backup_name
        compressed_path = Path(self.config.BACKUP_DIR) / f"{backup_name}.gz"

        logger.info(f"Starting database backup: {backup_name}")

        try:
            # Build mysqldump command
            cmd = [
                'mysqldump',
                '-h', self.config.DB_HOST,
                '-P', self.config.DB_PORT,
                '-u', self.config.DB_USER,
                f'-p{self.config.DB_PASSWORD}',
                '--single-transaction',
                '--quick',
                '--routines',
                '--triggers',
                self.config.DB_NAME,
            ]

            # Run mysqldump
            with open(backup_path, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True
                )

            # Compress backup
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed file
            backup_path.unlink()

            # Get file size
            size_mb = compressed_path.stat().st_size / (1024 * 1024)
            logger.info(f"Database backup completed: {compressed_path} ({size_mb:.2f} MB)")

            # Upload to S3 if enabled
            if self.config.S3_ENABLED:
                self._upload_to_s3(compressed_path)

            return str(compressed_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"Database backup failed: {e.stderr.decode()}")
            self._notify_failure("Database backup failed", str(e))
            return None

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            self._notify_failure("Database backup failed", str(e))
            return None

    def backup_files(self) -> Optional[str]:
        """
        Backup media files.

        Returns:
            Path to backup file or None on failure
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"files_backup_{timestamp}.tar.gz"
        backup_path = Path(self.config.BACKUP_DIR) / backup_name

        media_root = Path(self.config.MEDIA_ROOT)

        if not media_root.exists():
            logger.warning(f"Media directory not found: {media_root}")
            return None

        logger.info(f"Starting files backup: {backup_name}")

        try:
            # Create tar archive
            cmd = [
                'tar',
                '-czf', str(backup_path),
                '-C', str(media_root.parent),
                media_root.name
            ]

            subprocess.run(cmd, check=True, stderr=subprocess.PIPE)

            # Get file size
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Files backup completed: {backup_path} ({size_mb:.2f} MB)")

            # Upload to S3 if enabled
            if self.config.S3_ENABLED:
                self._upload_to_s3(backup_path)

            return str(backup_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"Files backup failed: {e.stderr.decode()}")
            self._notify_failure("Files backup failed", str(e))
            return None

        except Exception as e:
            logger.error(f"Files backup failed: {e}")
            self._notify_failure("Files backup failed", str(e))
            return None

    def full_backup(self) -> dict:
        """
        Perform full backup (database + files).

        Returns:
            Dict with backup results
        """
        logger.info("Starting full backup")

        results = {
            'timestamp': datetime.now().isoformat(),
            'database': None,
            'files': None,
            'success': True
        }

        # Database backup
        db_backup = self.backup_database()
        results['database'] = db_backup
        if not db_backup:
            results['success'] = False

        # Files backup
        files_backup = self.backup_files()
        results['files'] = files_backup
        if not files_backup:
            results['success'] = False

        # Rotate old backups
        self.rotate_backups()

        if results['success']:
            logger.info("Full backup completed successfully")
        else:
            logger.error("Full backup completed with errors")

        return results

    def rotate_backups(self):
        """Remove old backups based on retention policy."""
        logger.info("Rotating old backups")

        backup_dir = Path(self.config.BACKUP_DIR)
        now = datetime.now()

        # Get all backup files
        db_backups = sorted(backup_dir.glob('db_backup_*.sql.gz'))
        file_backups = sorted(backup_dir.glob('files_backup_*.tar.gz'))

        # Rotate database backups
        self._rotate_files(db_backups, now)

        # Rotate file backups
        self._rotate_files(file_backups, now)

    def _rotate_files(self, files: list, now: datetime):
        """Apply retention policy to backup files."""
        daily_cutoff = now - timedelta(days=self.config.DAILY_RETENTION_DAYS)
        weekly_cutoff = now - timedelta(weeks=self.config.WEEKLY_RETENTION_WEEKS)
        monthly_cutoff = now - timedelta(days=self.config.MONTHLY_RETENTION_MONTHS * 30)

        for file_path in files:
            try:
                # Extract date from filename
                filename = file_path.stem
                date_str = filename.split('_')[-2] + '_' + filename.split('_')[-1].split('.')[0]
                file_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')

                # Apply retention rules
                if file_date < monthly_cutoff:
                    # Delete very old backups
                    file_path.unlink()
                    logger.info(f"Deleted old backup: {file_path}")

                elif file_date < weekly_cutoff:
                    # Keep only monthly backups (1st of month)
                    if file_date.day != 1:
                        file_path.unlink()
                        logger.info(f"Deleted weekly backup: {file_path}")

                elif file_date < daily_cutoff:
                    # Keep only weekly backups (Sunday)
                    if file_date.weekday() != 6:
                        file_path.unlink()
                        logger.info(f"Deleted daily backup: {file_path}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse date from {file_path}: {e}")

    def _upload_to_s3(self, file_path: Path):
        """Upload backup file to S3."""
        if not self.config.S3_BUCKET:
            logger.warning("S3 bucket not configured")
            return

        try:
            import boto3

            s3 = boto3.client('s3')
            key = f"{self.config.S3_PREFIX}{file_path.name}"

            logger.info(f"Uploading to S3: s3://{self.config.S3_BUCKET}/{key}")

            s3.upload_file(
                str(file_path),
                self.config.S3_BUCKET,
                key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',  # Infrequent access
                    'ServerSideEncryption': 'AES256'
                }
            )

            logger.info(f"S3 upload completed: {key}")

        except ImportError:
            logger.warning("boto3 not installed, skipping S3 upload")

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")

    def _notify_failure(self, subject: str, message: str):
        """Send notification on backup failure."""
        if not self.config.NOTIFY_ON_FAILURE:
            return

        if not self.config.NOTIFY_EMAIL:
            logger.warning("Notification email not configured")
            return

        try:
            # Try to use Django's email
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
            import django
            django.setup()

            from django.core.mail import send_mail
            from django.conf import settings

            send_mail(
                subject=f"[ALERT] MultinotesAI Backup: {subject}",
                message=f"Backup failure notification:\n\n{message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.config.NOTIFY_EMAIL],
                fail_silently=True,
            )

            logger.info("Failure notification sent")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def list_backups(self) -> dict:
        """List all available backups."""
        backup_dir = Path(self.config.BACKUP_DIR)

        backups = {
            'database': [],
            'files': []
        }

        for f in sorted(backup_dir.glob('db_backup_*.sql.gz'), reverse=True):
            backups['database'].append({
                'name': f.name,
                'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })

        for f in sorted(backup_dir.glob('files_backup_*.tar.gz'), reverse=True):
            backups['files'].append({
                'name': f.name,
                'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })

        return backups

    def restore_database(self, backup_file: str) -> bool:
        """
        Restore database from backup.

        Args:
            backup_file: Path to backup file

        Returns:
            True on success
        """
        backup_path = Path(backup_file)

        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        logger.info(f"Restoring database from: {backup_path}")

        try:
            # Decompress if needed
            if backup_path.suffix == '.gz':
                temp_sql = Path(self.config.TEMP_DIR) / backup_path.stem
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_sql, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                sql_file = temp_sql
            else:
                sql_file = backup_path

            # Build mysql command
            cmd = [
                'mysql',
                '-h', self.config.DB_HOST,
                '-P', self.config.DB_PORT,
                '-u', self.config.DB_USER,
                f'-p{self.config.DB_PASSWORD}',
                self.config.DB_NAME,
            ]

            # Run restore
            with open(sql_file, 'r') as f:
                subprocess.run(cmd, stdin=f, check=True, stderr=subprocess.PIPE)

            # Cleanup temp file
            if backup_path.suffix == '.gz':
                sql_file.unlink()

            logger.info("Database restore completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Database restore failed: {e.stderr.decode()}")
            return False

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Automated backup system for MultinotesAI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Backup commands
    subparsers.add_parser('database', help='Backup database only')
    subparsers.add_parser('files', help='Backup files only')
    subparsers.add_parser('full', help='Full backup (database + files)')

    # Management commands
    subparsers.add_parser('list', help='List available backups')
    subparsers.add_parser('rotate', help='Rotate old backups')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('file', help='Backup file to restore')

    args = parser.parse_args()

    manager = BackupManager()

    if args.command == 'database':
        result = manager.backup_database()
        sys.exit(0 if result else 1)

    elif args.command == 'files':
        result = manager.backup_files()
        sys.exit(0 if result else 1)

    elif args.command == 'full':
        results = manager.full_backup()
        sys.exit(0 if results['success'] else 1)

    elif args.command == 'list':
        backups = manager.list_backups()
        print("\nDatabase Backups:")
        for b in backups['database'][:10]:
            print(f"  {b['name']} - {b['size_mb']} MB - {b['created']}")

        print("\nFile Backups:")
        for b in backups['files'][:10]:
            print(f"  {b['name']} - {b['size_mb']} MB - {b['created']}")

    elif args.command == 'rotate':
        manager.rotate_backups()

    elif args.command == 'restore':
        success = manager.restore_database(args.file)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
