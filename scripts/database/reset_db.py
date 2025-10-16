#!/usr/bin/env python3
"""Database reset script - completely recreate database from scratch."""

import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings


def reset_database(environment: str = "development") -> None:
    """Reset database completely."""
    print(f"🔄 Resetting {environment} database...")

    # Set environment
    os.environ["ENVIRONMENT"] = environment

    # Get database URL
    db_url = settings.DATABASE_URL_SYNC
    print(f"📊 Database URL: {db_url}")

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Drop all tables
                print("🗑️  Dropping all tables...")

                # Get all table names
                result = conn.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name != 'alembic_version';
                """
                    )
                )

                tables = [row[0] for row in result]

                if tables:
                    print(f"   Found {len(tables)} tables to drop: {', '.join(tables)}")

                    # Drop tables with CASCADE to handle dependencies
                    for table in tables:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                        print(f"   ✅ Dropped table: {table}")
                else:
                    print("   No tables to drop")

                # Drop alembic_version table
                conn.execute(text('DROP TABLE IF EXISTS "alembic_version" CASCADE;'))
                print("   ✅ Dropped alembic_version table")

                # Commit the transaction
                trans.commit()
                print("✅ Database reset completed successfully")

            except Exception as e:
                trans.rollback()
                print(f"❌ Error during reset: {e}")
                raise

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    return True


def recreate_database(environment: str = "development") -> None:
    """Recreate database with fresh migrations."""
    print(f"🔄 Recreating {environment} database...")

    # Reset database
    if not reset_database(environment):
        return False

    # Run migrations
    print("📋 Running fresh migrations...")
    try:
        result = subprocess.run(
            ["python3", "scripts/database/migrate_db.py", "--env", environment],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        print("✅ Database recreated successfully")
        print("📝 Migration output:")
        print(result.stdout)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print("📝 Error output:")
        print(e.stderr)
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Database reset script")
    parser.add_argument(
        "--env",
        choices=["development", "test", "production"],
        default="development",
        help="Environment to reset",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Reset and recreate database with fresh migrations",
    )
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.force:
        print(f"⚠️  WARNING: This will completely reset the {args.env} database!")
        print("   All data will be lost!")

        if args.recreate:
            print("   Database will be recreated with fresh migrations.")

        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Operation cancelled")
            sys.exit(0)

    print(f"🚀 Starting database reset for {args.env} environment")

    if args.recreate:
        success = recreate_database(args.env)
    else:
        success = reset_database(args.env)

    if success:
        print("🎉 Database reset completed successfully!")
        sys.exit(0)
    else:
        print("💥 Database reset failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
