#!/usr/bin/env python3
"""
Database restore script.
Restores databases from snapshots created by snapshot_db.py.
"""

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings


def parse_database_url(database_url: str) -> dict:
    """Parse database URL to extract connection parameters."""
    parsed = urlparse(database_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") if parsed.path else "radiator",
    }


def list_snapshots() -> list:
    """List all available snapshots."""
    snapshots_dir = project_root / ".snapshots"

    if not snapshots_dir.exists():
        return []

    snapshots = []

    # Check for tar.gz archives first
    for archive_file in sorted(snapshots_dir.glob("snapshot_*.tar.gz"), reverse=True):
        try:
            # Extract metadata from archive
            with tarfile.open(archive_file, "r:gz") as tar:
                # Find metadata.json file in the archive
                metadata_member = None
                for member in tar.getmembers():
                    if member.name.endswith("/metadata.json"):
                        metadata_member = member
                        break

                if metadata_member:
                    metadata_file = tar.extractfile(metadata_member)
                    if metadata_file:
                        metadata = json.load(metadata_file)
                        snapshots.append(
                            {
                                "name": archive_file.stem,
                                "path": archive_file,
                                "metadata": metadata,
                                "is_archive": True,
                            }
                        )
                    else:
                        raise Exception("Could not extract metadata file")
                else:
                    raise Exception("Metadata file not found in archive")
        except Exception as e:
            print(f"Warning: Could not read metadata from {archive_file}: {e}")
            # If metadata is corrupted, still include the snapshot
            snapshots.append(
                {
                    "name": archive_file.stem,
                    "path": archive_file,
                    "metadata": {"timestamp": "unknown", "databases": {}},
                    "is_archive": True,
                }
            )

    # Check for uncompressed directories (legacy support)
    for snapshot_dir in sorted(snapshots_dir.iterdir(), reverse=True):
        if snapshot_dir.is_dir() and snapshot_dir.name.startswith("snapshot_"):
            metadata_file = snapshot_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    snapshots.append(
                        {
                            "name": snapshot_dir.name,
                            "path": snapshot_dir,
                            "metadata": metadata,
                            "is_archive": False,
                        }
                    )
                except Exception:
                    # If metadata is corrupted, still include the snapshot
                    snapshots.append(
                        {
                            "name": snapshot_dir.name,
                            "path": snapshot_dir,
                            "metadata": {"timestamp": "unknown", "databases": {}},
                            "is_archive": False,
                        }
                    )

    return snapshots


def display_snapshots(snapshots: list):
    """Display available snapshots in a formatted table."""
    if not snapshots:
        print("📭 No snapshots found in .snapshots/ directory")
        return

    print("📸 Available snapshots:")
    print("=" * 80)
    print(f"{'#':<3} {'Snapshot Name':<25} {'Created':<20} {'Databases':<20}")
    print("=" * 80)

    for i, snapshot in enumerate(snapshots, 1):
        timestamp = snapshot["metadata"].get("timestamp", "unknown")
        if timestamp != "unknown":
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        databases = list(snapshot["metadata"].get("databases", {}).keys())
        db_str = ", ".join(databases) if databases else "none"

        print(f"{i:<3} {snapshot['name']:<25} {timestamp:<20} {db_str:<20}")

    print("=" * 80)


def select_snapshot(snapshots: list) -> dict:
    """Interactive snapshot selection."""
    if not snapshots:
        return None

    while True:
        try:
            choice = input(
                f"\nSelect snapshot (1-{len(snapshots)}) or 'q' to quit: "
            ).strip()

            if choice.lower() == "q":
                return None

            index = int(choice) - 1
            if 0 <= index < len(snapshots):
                return snapshots[index]
            else:
                print(f"❌ Please enter a number between 1 and {len(snapshots)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled")
            return None


def terminate_database_connections(connection_params: dict, database_name: str) -> bool:
    """Terminate all active connections to the database."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{database_name}' AND pid <> pg_backend_pid()
        """
        )

        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(
            f"   ⚠️  Warning: Could not terminate connections to {database_name}: {e}"
        )
        return False


def drop_database(connection_params: dict, database_name: str) -> bool:
    """Drop database if it exists."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")

        cursor.close()
        conn.close()
        print(f"   ✅ Dropped database: {database_name}")
        return True
    except Exception as e:
        print(f"   ❌ Error dropping database {database_name}: {e}")
        return False


def create_database(connection_params: dict, database_name: str) -> bool:
    """Create database."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE {database_name}")

        cursor.close()
        conn.close()
        print(f"   ✅ Created database: {database_name}")
        return True
    except Exception as e:
        print(f"   ❌ Error creating database {database_name}: {e}")
        return False


def restore_database(
    connection_params: dict, database_name: str, dump_file: Path
) -> bool:
    """Restore database from SQL dump file using psql."""
    try:
        import subprocess

        print(f"   📦 Restoring {database_name} from {dump_file.name}...")

        # Build psql command
        cmd = [
            "psql",
            "-h",
            connection_params["host"],
            "-p",
            str(connection_params["port"]),
            "-U",
            connection_params["user"],
            "-d",
            database_name,
            "-f",
            str(dump_file),
            "-q",  # quiet mode
        ]

        # Set password via environment variable
        env = os.environ.copy()
        if connection_params["password"]:
            env["PGPASSWORD"] = connection_params["password"]

        # Run psql
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"   ❌ Error restoring database: {result.stderr}")
            return False

        print(f"   ✅ Restored database: {database_name}")
        return True

    except Exception as e:
        print(f"   ❌ Error restoring database {database_name}: {e}")
        return False


def restore_snapshot(
    snapshot: dict, include_prod: bool = True, include_test: bool = True
) -> bool:
    """Restore database from snapshot."""
    print(f"🔄 Restoring from snapshot: {snapshot['name']}")

    metadata = snapshot["metadata"]
    snapshot_path = snapshot["path"]

    # Extract archive if needed
    if snapshot.get("is_archive", False):
        print("📦 Extracting archive...")
        with tempfile.TemporaryDirectory() as temp_dir:
            with tarfile.open(snapshot_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Update snapshot_path to point to extracted directory
            # The archive contains a directory with the same name as the archive (without .tar extension)
            archive_name = snapshot["name"]
            if archive_name.endswith(".tar"):
                archive_name = archive_name[:-4]  # Remove .tar extension
            extracted_dir = Path(temp_dir) / archive_name
            return _restore_from_directory(
                extracted_dir, metadata, include_prod, include_test
            )
    else:
        return _restore_from_directory(
            snapshot_path, metadata, include_prod, include_test
        )


def _restore_from_directory(
    snapshot_dir: Path, metadata: dict, include_prod: bool, include_test: bool
) -> bool:
    """Restore database from extracted snapshot directory."""

    # Parse database URLs
    prod_params = parse_database_url(settings.DATABASE_URL_SYNC)
    test_params = parse_database_url(
        settings.DATABASE_URL_SYNC.replace("radiator", "radiator_test")
    )

    success = True

    # Restore production database
    if include_prod and "radiator" in metadata.get("databases", {}):
        print(f"🔄 Restoring production database: radiator")

        # Terminate connections
        terminate_database_connections(prod_params, "radiator")

        # Drop and recreate database
        if not drop_database(prod_params, "radiator"):
            success = False
        elif not create_database(prod_params, "radiator"):
            success = False
        else:
            # Restore from dump
            dump_file = snapshot_dir / "radiator.sql"
            if dump_file.exists():
                if not restore_database(prod_params, "radiator", dump_file):
                    success = False
            else:
                print(f"   ❌ Dump file not found: {dump_file}")
                success = False

    # Restore test database
    if include_test and "radiator_test" in metadata.get("databases", {}):
        print(f"🔄 Restoring test database: radiator_test")

        # Terminate connections
        terminate_database_connections(test_params, "radiator_test")

        # Drop and recreate database
        if not drop_database(test_params, "radiator_test"):
            success = False
        elif not create_database(test_params, "radiator_test"):
            success = False
        else:
            # Restore from dump
            dump_file = snapshot_dir / "radiator_test.sql"
            if dump_file.exists():
                if not restore_database(test_params, "radiator_test", dump_file):
                    success = False
            else:
                print(f"   ❌ Dump file not found: {dump_file}")
                success = False

    if success:
        print("✅ Snapshot restore completed successfully!")
    else:
        print("❌ Snapshot restore failed!")

    return success


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Restore database from snapshots")
    parser.add_argument(
        "--snapshot",
        help="Specific snapshot name to restore (skip interactive selection)",
    )
    parser.add_argument(
        "--prod-only", action="store_true", help="Restore only production database"
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Restore only test database"
    )
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument(
        "--list", action="store_true", help="List available snapshots and exit"
    )

    args = parser.parse_args()

    # List snapshots if requested
    if args.list:
        snapshots = list_snapshots()
        display_snapshots(snapshots)
        sys.exit(0)

    # Get available snapshots
    snapshots = list_snapshots()
    if not snapshots:
        print("❌ No snapshots found!")
        sys.exit(1)

    # Select snapshot
    if args.snapshot:
        snapshot = next((s for s in snapshots if s["name"] == args.snapshot), None)
        if not snapshot:
            print(f"❌ Snapshot '{args.snapshot}' not found!")
            sys.exit(1)
    else:
        display_snapshots(snapshots)
        snapshot = select_snapshot(snapshots)
        if not snapshot:
            print("❌ No snapshot selected")
            sys.exit(1)

    # Determine which databases to restore
    include_prod = not args.test_only
    include_test = not args.prod_only

    if args.prod_only and args.test_only:
        print("❌ Cannot specify both --prod-only and --test-only")
        sys.exit(1)

    # Show restore plan
    print(f"\n📋 Restore plan:")
    print(f"   Snapshot: {snapshot['name']}")
    print(f"   Production DB: {'✅' if include_prod else '❌'}")
    print(f"   Test DB: {'✅' if include_test else '❌'}")

    # Confirmation
    if not args.force:
        print(f"\n⚠️  WARNING: This will completely replace the selected databases!")
        print("   All current data will be lost!")

        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Operation cancelled")
            sys.exit(0)

    print(f"\n🚀 Starting database restore from {snapshot['name']}")

    success = restore_snapshot(
        snapshot, include_prod=include_prod, include_test=include_test
    )

    if success:
        print("🎉 Database restore completed successfully!")
        sys.exit(0)
    else:
        print("💥 Database restore failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
