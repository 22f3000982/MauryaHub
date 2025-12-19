#!/usr/bin/env python3
"""
Migration script to transfer data from old table names to new table names:
- pyqs -> quiz1
- notes -> quiz2  
- assignments -> endterm
"""

import psycopg2
import os

# Set DATABASE_URL
os.environ['DATABASE_URL'] = 'postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres'

def migrate_table_data():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        
        print("Starting data migration from old table names to new table names...")
        
        # Migration mappings
        migrations = [
            ('pyqs', 'quiz1'),
            ('notes', 'quiz2'),
            ('assignments', 'endterm')
        ]
        
        for old_table, new_table in migrations:
            print(f"\nMigrating {old_table} -> {new_table}")
            
            # Copy all data from old table to new table
            cur.execute(f"""
                INSERT INTO {new_table} (id, course_id, name, yt_link, watch_count, sort_order)
                SELECT id, course_id, name, yt_link, watch_count, sort_order 
                FROM {old_table}
            """)
            
            # Get count of migrated records
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            count = cur.fetchone()[0]
            print(f"✓ Migrated {count} records to {new_table}")
        
        # Commit all changes
        conn.commit()
        
        print("\n=== Migration Summary ===")
        for old_table, new_table in migrations:
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            count = cur.fetchone()[0]
            print(f"{new_table}: {count} records")
        
        cur.close()
        conn.close()
        
        print("\nData migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    migrate_table_data()