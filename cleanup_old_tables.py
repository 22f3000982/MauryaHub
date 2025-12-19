#!/usr/bin/env python3
"""
Cleanup script to drop old tables after successful migration
"""

import psycopg2
import os

# Set DATABASE_URL
os.environ['DATABASE_URL'] = 'postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres'

def cleanup_old_tables():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        
        print("Starting cleanup of old tables...")
        
        # Tables to drop
        old_tables = ['pyqs', 'notes', 'assignments']
        
        for table in old_tables:
            print(f"Dropping table: {table}")
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"✓ Dropped {table}")
        
        # Commit changes
        conn.commit()
        
        print("\n=== Cleanup completed successfully! ===")
        print("Old tables (pyqs, notes, assignments) have been removed.")
        print("Data is now available in new tables (quiz1, quiz2, endterm).")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Cleanup failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    cleanup_old_tables()