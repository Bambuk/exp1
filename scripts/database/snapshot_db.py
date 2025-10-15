#!/usr/bin/env python3
"""
Database snapshot creation script.
Creates full dumps of production and test databases using pg_dump.
"""

import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime
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


def get_database_size(connection_params: dict, database_name: str) -> float:
    """Get database size in MB."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Connect to postgres database to get size
        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"SELECT pg_database_size('{database_name}')")
        size_bytes = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Convert bytes to MB
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def get_table_count(connection_params: dict, database_name: str) -> int:
    """Get number of tables in database."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database=database_name,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """
        )

        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return count
    except Exception:
        return 0


def create_database_dump(
    connection_params: dict, database_name: str, output_file: Path
) -> bool:
    """Create database dump using Python psycopg2."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        print(f"   📦 Creating dump for {database_name}...")

        # Connect to database
        conn = psycopg2.connect(
            host=connection_params["host"],
            port=connection_params["port"],
            user=connection_params["user"],
            password=connection_params["password"],
            database=database_name,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cursor.fetchall()]

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"-- Database dump for {database_name}\n")
            f.write(f"-- Generated on {datetime.now().isoformat()}\n\n")
            f.write("SET statement_timeout = 0;\n")
            f.write("SET lock_timeout = 0;\n")
            f.write("SET idle_in_transaction_session_timeout = 0;\n")
            f.write("SET client_encoding = 'UTF8';\n")
            f.write("SET standard_conforming_strings = on;\n")
            f.write("SELECT pg_catalog.set_config('search_path', 'public', false);\n")
            f.write("SET check_function_bodies = false;\n")
            f.write("SET xmloption = content;\n")
            f.write("SET client_min_messages = warning;\n")
            f.write("SET row_security = off;\n\n")

            # Dump each table
            for table in tables:
                f.write(f"-- Table: {table}\n")
                f.write(f'DROP TABLE IF EXISTS "{table}" CASCADE;\n')

                # Get table structure
                cursor.execute(
                    f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """
                )
                columns = cursor.fetchall()

                if columns:
                    f.write(f'CREATE TABLE "{table}" (\n')
                    col_defs = []
                    for col_name, data_type, is_nullable, col_default in columns:
                        nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                        default = f" DEFAULT {col_default}" if col_default else ""
                        col_defs.append(
                            f'    "{col_name}" {data_type}{default} {nullable}'
                        )
                    f.write(",\n".join(col_defs))
                    f.write("\n);\n\n")

                    # Get table data
                    cursor.execute(f'SELECT * FROM "{table}"')
                    rows = cursor.fetchall()

                    if rows:
                        f.write(f"-- Data for table {table}\n")

                        # Process rows in batches of 1000
                        batch_size = 1000
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i : i + batch_size]

                            # Build batch insert
                            batch_values = []
                            for row in batch:
                                # Escape values
                                escaped_row = []
                                for value in row:
                                    if value is None:
                                        escaped_row.append("NULL")
                                    elif isinstance(value, str):
                                        escaped_value = value.replace("'", "''")
                                        escaped_row.append(f"'{escaped_value}'")
                                    elif hasattr(
                                        value, "isoformat"
                                    ):  # datetime objects
                                        escaped_row.append(f"'{value.isoformat()}'")
                                    else:
                                        escaped_row.append(str(value))

                                batch_values.append(f"({', '.join(escaped_row)})")

                            # Write batch insert
                            f.write(
                                f'INSERT INTO "{table}" VALUES {", ".join(batch_values)};\n'
                            )

                        f.write("\n")

        cursor.close()
        conn.close()

        print(f"   ✅ Dump created: {output_file}")
        return True
    except Exception as e:
        print(f"   ❌ Error creating dump for {database_name}: {e}")
        return False


def create_snapshot(include_prod: bool = True, include_test: bool = True) -> bool:
    """Create database snapshot."""
    print("📸 Creating database snapshot...")

    # Create snapshots directory
    snapshots_dir = project_root / ".snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    # Generate timestamp for snapshot folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_dir = snapshots_dir / f"snapshot_{timestamp}"
    snapshot_dir.mkdir(exist_ok=True)

    print(f"📁 Snapshot directory: {snapshot_dir}")

    # Parse database URLs
    prod_params = parse_database_url(settings.DATABASE_URL_SYNC)
    test_params = parse_database_url(
        settings.DATABASE_URL_SYNC.replace("radiator", "radiator_test")
    )

    metadata = {"timestamp": datetime.now().isoformat(), "databases": {}}

    success = True

    # Create production database dump
    if include_prod:
        print(f"🔄 Processing production database: {prod_params['database']}")
        prod_dump_file = snapshot_dir / "radiator.sql"

        if create_database_dump(prod_params, prod_params["database"], prod_dump_file):
            # Get database info
            size_mb = get_database_size(prod_params, prod_params["database"])
            table_count = get_table_count(prod_params, prod_params["database"])

            metadata["databases"]["radiator"] = {
                "size_mb": round(size_mb, 2),
                "tables_count": table_count,
                "dump_file": "radiator.sql",
            }
        else:
            success = False

    # Create test database dump
    if include_test:
        print(f"🔄 Processing test database: {test_params['database']}")
        test_dump_file = snapshot_dir / "radiator_test.sql"

        if create_database_dump(test_params, test_params["database"], test_dump_file):
            # Get database info
            size_mb = get_database_size(test_params, test_params["database"])
            table_count = get_table_count(test_params, test_params["database"])

            metadata["databases"]["radiator_test"] = {
                "size_mb": round(size_mb, 2),
                "tables_count": table_count,
                "dump_file": "radiator_test.sql",
            }
        else:
            success = False

    # Save metadata
    metadata_file = snapshot_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"📄 Metadata saved: {metadata_file}")

    if success:
        # Create tar.gz archive
        print("🗜️  Creating compressed archive...")
        archive_path = snapshot_dir.parent / f"{snapshot_dir.name}.tar.gz"

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(snapshot_dir, arcname=snapshot_dir.name)

        # Get archive size
        archive_size_mb = archive_path.stat().st_size / (1024 * 1024)

        # Remove uncompressed directory
        import shutil

        shutil.rmtree(snapshot_dir)

        print(f"✅ Snapshot created successfully: {archive_path}")
        print(f"📊 Snapshot contains:")
        for db_name, info in metadata["databases"].items():
            print(
                f"   • {db_name}: {info['size_mb']} MB, {info['tables_count']} tables"
            )
        print(f"🗜️  Compressed size: {archive_size_mb:.1f} MB")
    else:
        print("❌ Snapshot creation failed!")

    return success


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Create database snapshots")
    parser.add_argument(
        "--prod-only",
        action="store_true",
        help="Create snapshot only for production database",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Create snapshot only for test database",
    )

    args = parser.parse_args()

    # Determine which databases to include
    include_prod = not args.test_only
    include_test = not args.prod_only

    if args.prod_only and args.test_only:
        print("❌ Cannot specify both --prod-only and --test-only")
        sys.exit(1)

    print("🚀 Starting database snapshot creation")
    print(f"   Production DB: {'✅' if include_prod else '❌'}")
    print(f"   Test DB: {'✅' if include_test else '❌'}")
    print()

    success = create_snapshot(include_prod=include_prod, include_test=include_test)

    if success:
        print("🎉 Snapshot creation completed successfully!")
        sys.exit(0)
    else:
        print("💥 Snapshot creation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
