#!/usr/bin/env python3
"""
Data Migration Script: SQLite to PostgreSQL
This script migrates all data from your existing SQLite database to PostgreSQL
"""

import sqlite3
import psycopg2
import psycopg2.extras
import os
import sys
from datetime import datetime

def get_sqlite_connection():
    """Connect to SQLite database"""
    if not os.path.exists('database.db'):
        print("ERROR: database.db not found!")
        return None
    return sqlite3.connect('database.db')

def get_postgresql_connection(database_url):
    """Connect to PostgreSQL database"""
    try:
        if database_url.startswith('postgres://'):
            # Fix for newer psycopg2 versions
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"ERROR connecting to PostgreSQL: {e}")
        return None

def migrate_table(sqlite_cur, pg_cur, table_name, columns):
    """Migrate a single table from SQLite to PostgreSQL"""
    try:
        # Get all data from SQLite
        sqlite_cur.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            print(f"  No data found in {table_name}")
            return 0
        
        # Clear existing data in PostgreSQL table
        pg_cur.execute(f"DELETE FROM {table_name}")
        
        # Insert data into PostgreSQL
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        pg_cur.executemany(insert_query, rows)
        
        print(f"  Migrated {len(rows)} records to {table_name}")
        return len(rows)
        
    except Exception as e:
        print(f"  ERROR migrating {table_name}: {e}")
        return 0

def reset_sequences(pg_cur, tables_with_serial):
    """Reset PostgreSQL sequences after data migration"""
    for table in tables_with_serial:
        try:
            pg_cur.execute(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}), true)")
            print(f"  Reset sequence for {table}")
        except Exception as e:
            print(f"  WARNING: Could not reset sequence for {table}: {e}")

def main():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration Script")
    print("=" * 60)
    
    # Get PostgreSQL connection string
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        print("Please set your PostgreSQL connection string:")
        print("Example: postgresql://username:password@host:port/database")
        sys.exit(1)
    
    # Connect to databases
    print("Connecting to databases...")
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        sys.exit(1)
    
    pg_conn = get_postgresql_connection(database_url)
    if not pg_conn:
        sqlite_conn.close()
        sys.exit(1)
    
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()
    
    print("✓ Connected to both databases")
    
    # Define tables and their columns (excluding auto-increment id)
    tables_to_migrate = {
        'courses': ['id', 'name'],
        'pyqs': ['id', 'course_id', 'name', 'yt_link', 'watch_count', 'sort_order'],
        'notes': ['id', 'course_id', 'name', 'yt_link', 'watch_count', 'sort_order'],
        'assignments': ['id', 'course_id', 'name', 'yt_link', 'watch_count', 'sort_order'],
        'resources': ['id', 'course_id', 'name', 'yt_link', 'watch_count', 'sort_order'],
        'extra_stuff': ['id', 'course_id', 'name', 'link'],
        'feedback': ['id', 'username', 'feedback', 'created_at']
    }
    
    # Add sort_order column to tables that might not have it
    for table in ['pyqs', 'notes', 'assignments']:
        try:
            sqlite_cur.execute(f"ALTER TABLE {table} ADD COLUMN sort_order INTEGER DEFAULT 0")
            sqlite_conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    print("\nStarting migration...")
    total_records = 0
    
    try:
        for table_name, columns in tables_to_migrate.items():
            print(f"Migrating {table_name}...")
            
            # Check if table exists in SQLite
            sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not sqlite_cur.fetchone():
                print(f"  Table {table_name} not found in SQLite, skipping...")
                continue
            
            # Check which columns actually exist in SQLite
            sqlite_cur.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [col[1] for col in sqlite_cur.fetchall()]
            
            # Only migrate columns that exist in both databases
            columns_to_migrate = [col for col in columns if col in existing_columns]
            
            if not columns_to_migrate:
                print(f"  No matching columns found for {table_name}, skipping...")
                continue
            
            count = migrate_table(sqlite_cur, pg_cur, table_name, columns_to_migrate)
            total_records += count
        
        # Reset sequences for tables with SERIAL columns
        print("\nResetting sequences...")
        reset_sequences(pg_cur, ['courses', 'pyqs', 'notes', 'assignments', 'resources', 'extra_stuff', 'feedback'])
        
        # Commit all changes
        pg_conn.commit()
        
        print(f"\n✓ Migration completed successfully!")
        print(f"✓ Total records migrated: {total_records}")
        print(f"✓ Timestamp: {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"\nERROR during migration: {e}")
        pg_conn.rollback()
        sys.exit(1)
    
    finally:
        sqlite_cur.close()
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()
    
    print("\nMigration completed. You can now use the PostgreSQL version of your app!")
    print("Don't forget to:")
    print("1. Set the DATABASE_URL environment variable on Render")
    print("2. Replace app.py with app_postgresql.py")
    print("3. Redeploy your application")

if __name__ == "__main__":
    main()