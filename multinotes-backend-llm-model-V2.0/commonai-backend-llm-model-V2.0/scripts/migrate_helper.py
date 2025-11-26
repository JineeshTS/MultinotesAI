#!/usr/bin/env python
"""
Database Migration Helper for MultinotesAI.

This script provides:
- Safe migration execution
- Migration status checking
- Rollback capabilities
- Data migration helpers

Usage:
    python scripts/migrate_helper.py check
    python scripts/migrate_helper.py migrate
    python scripts/migrate_helper.py rollback <app> <migration>
    python scripts/migrate_helper.py status
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')


def setup_django():
    """Initialize Django."""
    import django
    django.setup()


def get_migration_status():
    """Get current migration status for all apps."""
    from django.core.management import call_command
    from io import StringIO

    output = StringIO()
    call_command('showmigrations', '--list', stdout=output)
    return output.getvalue()


def get_pending_migrations():
    """Get list of pending migrations."""
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connection

    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

    return [
        f"{migration.app_label}.{migration.name}"
        for migration, _ in plan
    ]


def check_migrations():
    """Check for pending migrations."""
    setup_django()

    pending = get_pending_migrations()

    if pending:
        print(f"⚠️  Found {len(pending)} pending migrations:")
        for migration in pending:
            print(f"   - {migration}")
        return 1
    else:
        print("✓ All migrations are applied.")
        return 0


def run_migrations(dry_run=False, app=None):
    """Run database migrations."""
    setup_django()

    from django.core.management import call_command

    pending = get_pending_migrations()

    if not pending:
        print("✓ No pending migrations.")
        return 0

    print(f"Found {len(pending)} pending migrations:")
    for migration in pending:
        print(f"   - {migration}")

    if dry_run:
        print("\n[DRY RUN] Would apply the above migrations.")
        return 0

    print("\nApplying migrations...")

    try:
        # Create backup before migration
        backup_before_migrate()

        # Run migrations
        if app:
            call_command('migrate', app, verbosity=2)
        else:
            call_command('migrate', verbosity=2)

        print("\n✓ Migrations applied successfully.")
        return 0

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("Consider rolling back using: python scripts/migrate_helper.py rollback")
        return 1


def rollback_migration(app, migration):
    """Rollback to a specific migration."""
    setup_django()

    from django.core.management import call_command

    print(f"Rolling back {app} to {migration}...")

    try:
        call_command('migrate', app, migration, verbosity=2)
        print(f"\n✓ Rolled back to {app}.{migration}")
        return 0
    except Exception as e:
        print(f"\n✗ Rollback failed: {e}")
        return 1


def backup_before_migrate():
    """Create a database backup before migration."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = PROJECT_ROOT / 'backups' / 'migrations'
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_file = backup_dir / f"pre_migration_{timestamp}.sql"

    print(f"Creating backup: {backup_file}")

    # Get database settings
    from django.conf import settings
    db = settings.DATABASES['default']

    if 'mysql' in db['ENGINE'].lower():
        cmd = [
            'mysqldump',
            '-h', db['HOST'],
            '-P', str(db['PORT']),
            '-u', db['USER'],
            f"-p{db['PASSWORD']}",
            '--single-transaction',
            '--quick',
            db['NAME'],
        ]

        try:
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
            print(f"✓ Backup created: {backup_file}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Backup failed: {e}")
            # Continue with migration even if backup fails

    elif 'postgresql' in db['ENGINE'].lower():
        cmd = [
            'pg_dump',
            '-h', db['HOST'],
            '-p', str(db['PORT']),
            '-U', db['USER'],
            '-d', db['NAME'],
            '-f', str(backup_file),
        ]

        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        try:
            subprocess.run(cmd, env=env, check=True, stderr=subprocess.PIPE)
            print(f"✓ Backup created: {backup_file}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Backup failed: {e}")


def show_status():
    """Show detailed migration status."""
    setup_django()

    print("=" * 60)
    print("Migration Status")
    print("=" * 60)

    status = get_migration_status()
    print(status)

    print("=" * 60)
    print("Pending Migrations")
    print("=" * 60)

    pending = get_pending_migrations()
    if pending:
        for migration in pending:
            print(f"  [ ] {migration}")
    else:
        print("  (none)")


def make_migrations(app=None, dry_run=False, empty=False, name=None):
    """Create new migrations."""
    setup_django()

    from django.core.management import call_command

    args = []
    kwargs = {'verbosity': 2}

    if app:
        args.append(app)

    if dry_run:
        kwargs['dry_run'] = True

    if empty:
        kwargs['empty'] = True

    if name:
        kwargs['name'] = name

    print("Checking for model changes...")
    call_command('makemigrations', *args, **kwargs)


def squash_migrations(app, start_migration, end_migration=None):
    """Squash migrations for an app."""
    setup_django()

    from django.core.management import call_command

    print(f"Squashing migrations for {app}...")

    args = [app, start_migration]
    if end_migration:
        args.append(end_migration)

    call_command('squashmigrations', *args, verbosity=2)


def validate_models():
    """Validate models without creating migrations."""
    setup_django()

    from django.core.management import call_command

    print("Validating models...")

    try:
        call_command('check')
        print("✓ Models are valid.")
        return 0
    except Exception as e:
        print(f"✗ Model validation failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Database migration helper for MultinotesAI'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Check command
    subparsers.add_parser('check', help='Check for pending migrations')

    # Status command
    subparsers.add_parser('status', help='Show migration status')

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    migrate_parser.add_argument('--app', help='Specific app to migrate')

    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to a migration')
    rollback_parser.add_argument('app', help='App name')
    rollback_parser.add_argument('migration', help='Migration name to rollback to')

    # Makemigrations command
    make_parser = subparsers.add_parser('makemigrations', help='Create new migrations')
    make_parser.add_argument('--app', help='Specific app')
    make_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    make_parser.add_argument('--empty', action='store_true', help='Create empty migration')
    make_parser.add_argument('--name', help='Migration name')

    # Squash command
    squash_parser = subparsers.add_parser('squash', help='Squash migrations')
    squash_parser.add_argument('app', help='App name')
    squash_parser.add_argument('start', help='Start migration')
    squash_parser.add_argument('--end', help='End migration')

    # Validate command
    subparsers.add_parser('validate', help='Validate models')

    args = parser.parse_args()

    if args.command == 'check':
        sys.exit(check_migrations())

    elif args.command == 'status':
        show_status()

    elif args.command == 'migrate':
        sys.exit(run_migrations(dry_run=args.dry_run, app=args.app))

    elif args.command == 'rollback':
        sys.exit(rollback_migration(args.app, args.migration))

    elif args.command == 'makemigrations':
        make_migrations(
            app=args.app,
            dry_run=args.dry_run,
            empty=args.empty,
            name=args.name
        )

    elif args.command == 'squash':
        squash_migrations(args.app, args.start, args.end)

    elif args.command == 'validate':
        sys.exit(validate_models())

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
