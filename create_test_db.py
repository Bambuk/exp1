#!/usr/bin/env python3
"""
Script to create test database for radiator tests.
Run this script to create the radiator_test database.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

def create_test_database():
    """Create test database if it doesn't exist."""
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': '12345',
        'database': 'postgres'  # Connect to default postgres database first
    }
    
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if test database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'radiator_test'")
        exists = cursor.fetchone()
        
        if exists:
            print("Database 'radiator_test' already exists.")
        else:
            # Create test database
            cursor.execute("CREATE DATABASE radiator_test")
            print("Database 'radiator_test' created successfully.")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Error creating test database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def drop_test_database():
    """Drop test database if it exists."""
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': '12345',
        'database': 'postgres'  # Connect to default postgres database first
    }
    
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if test database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'radiator_test'")
        exists = cursor.fetchone()
        
        if exists:
            # Drop test database
            cursor.execute("DROP DATABASE radiator_test")
            print("Database 'radiator_test' dropped successfully.")
        else:
            print("Database 'radiator_test' does not exist.")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Error dropping test database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage test database for radiator")
    parser.add_argument("--drop", action="store_true", help="Drop test database instead of creating it")
    
    args = parser.parse_args()
    
    if args.drop:
        drop_test_database()
    else:
        create_test_database()
