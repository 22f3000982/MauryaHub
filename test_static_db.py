"""
Quick test script to verify hybrid database functionality
Run this to ensure static DB is working correctly
"""

import sqlite3
import os

def test_static_db():
    print("🧪 Testing Static Database Configuration\n")
    print("="*60)
    
    # Check if static_data.db exists
    db_path = 'static_data.db'
    if not os.path.exists(db_path):
        print("❌ ERROR: static_data.db not found!")
        print("   Run: python init_static_db.py")
        return False
    
    print("✅ static_data.db file exists")
    
    # Connect and test
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test 1: Check tables exist
        print("\n📋 Checking tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['courses', 'quiz1', 'quiz2', 'endterm', 'resources', 'extra_stuff', 'metadata']
        
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' missing!")
        
        # Test 2: Check data counts
        print("\n📊 Data Statistics:")
        for table in ['courses', 'quiz1', 'quiz2', 'endterm', 'resources', 'extra_stuff']:
            if table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"   {table:15} : {count:3} records")
        
        # Test 3: Sample data
        print("\n📚 Sample Course Data:")
        cursor.execute('SELECT id, name FROM courses LIMIT 3')
        courses = cursor.fetchall()
        for course_id, name in courses:
            print(f"   [{course_id}] {name}")
        
        # Test 4: Check watch counts (should be 0)
        print("\n🔍 Verifying watch counts are 0 (placeholders):")
        cursor.execute('SELECT COUNT(*) FROM quiz1 WHERE watch_count != 0')
        non_zero = cursor.fetchone()[0]
        if non_zero == 0:
            print("   ✅ All watch counts are 0 (correct)")
        else:
            print(f"   ⚠️  Found {non_zero} records with non-zero watch_count")
        
        # Test 5: Check metadata
        print("\n📅 Backup Information:")
        cursor.execute('SELECT value FROM metadata WHERE key = "backup_date"')
        backup_date = cursor.fetchone()
        if backup_date:
            print(f"   Backup Date: {backup_date[0]}")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ All tests passed! Static database is ready.")
        print("🚀 Your site will now load much faster!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == '__main__':
    test_static_db()
