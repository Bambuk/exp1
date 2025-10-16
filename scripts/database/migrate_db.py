#!/usr/bin/env python3
"""Database migration script with proper environment handling."""

import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings


def run_migration(environment: str = "development") -> None:
    """Run database migrations for specified environment."""
    print(f"🔄 Running migrations for {environment} environment...")

    # Set environment
    os.environ["ENVIRONMENT"] = environment

    # Get database URL
    db_url = settings.DATABASE_URL_SYNC
    print(f"📊 Database URL: {db_url}")

    # Check if database exists
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")

            # Check if alembic_version table exists
            result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                );
            """
                )
            )
            has_alembic = result.scalar()

            if has_alembic:
                print("📋 Alembic version table found")
            else:
                print("⚠️  Alembic version table not found - will be created")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # Run migrations
    try:
        # Use alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        print("✅ Migrations completed successfully")
        print("📝 Migration output:")
        print(result.stdout)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print("📝 Error output:")
        print(e.stderr)
        return False


def check_tables(environment: str = "development") -> None:
    """Check if tables exist after migration."""
    print(f"🔍 Checking tables in {environment} environment...")

    os.environ["ENVIRONMENT"] = environment
    db_url = settings.DATABASE_URL_SYNC

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            # List all tables
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
                )
            )

            tables = [row[0] for row in result]

            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table}")

            # Check for required tables
            required_tables = [
                "alembic_version",
                "tracker_tasks",
                "tracker_task_history",
                "tracker_sync_logs",
            ]

            missing_tables = [t for t in required_tables if t not in tables]

            if missing_tables:
                print(f"⚠️  Missing required tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables present")
                return True

    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "--env",
        choices=["development", "test", "production"],
        default="development",
        help="Environment to migrate",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check tables, don't run migrations",
    )

    args = parser.parse_args()

    print(f"🚀 Starting database migration for {args.env} environment")

    if args.check_only:
        success = check_tables(args.env)
    else:
        success = run_migration(args.env)
        if success:
            success = check_tables(args.env)

    if success:
        print("🎉 Database migration completed successfully!")
        sys.exit(0)
    else:
        print("💥 Database migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
