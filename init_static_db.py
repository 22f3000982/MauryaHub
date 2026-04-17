"""
Script to create static SQLite database from backup SQL file.
This database contains all static data (courses, videos, resources) with watch_count set to 0.
Run this script whenever you want to update the static database with latest backup.
"""

import sqlite3
import re
from datetime import datetime

def create_static_db():
    """Create SQLite database from backup(1).sql file"""
    
    # Connect to SQLite database (creates if doesn't exist)
    conn = sqlite3.connect('static_data.db')
    cursor = conn.cursor()
    
    print("📦 Creating static database tables...")
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz1 (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz2 (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS endterm (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extra_stuff (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            link TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            feedback TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("✅ Tables created successfully!")
    print("\n📖 Reading backup file...")
    
    # Read and parse backup file
    with open('backup (1).sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Extract INSERT statements for each table
    tables = ['courses', 'quiz1', 'quiz2', 'endterm', 'resources', 'extra_stuff', 'feedback']
    
    for table in tables:
        print(f"\n📥 Processing table: {table}")
        
        # Clear existing data
        cursor.execute(f'DELETE FROM {table}')
        
        # Find INSERT statements for this table
        pattern = rf"INSERT INTO {table} \([^)]+\) VALUES \(([^;]+)\);"
        matches = re.findall(pattern, sql_content)
        
        if matches:
            for match in matches:
                # Parse values
                values_str = match.strip()
                
                # Build INSERT statement
                if table == 'courses':
                    # Extract id and name
                    parts = values_str.split(',', 1)
                    id_val = parts[0].strip()
                    name_val = parts[1].strip().strip("'")
                    cursor.execute(f'INSERT INTO courses (id, name) VALUES (?, ?)', (id_val, name_val))
                
                elif table in ['quiz1', 'quiz2', 'endterm', 'resources']:
                    # Extract: id, course_id, name, yt_link, watch_count (ignored), sort_order
                    parts = values_str.split(',')
                    if len(parts) >= 6:
                        id_val = parts[0].strip()
                        course_id_val = parts[1].strip()
                        name_val = parts[2].strip().strip("'")
                        yt_link_val = parts[3].strip().strip("'")
                        # watch_count is ignored (set to 0 in DB)
                        sort_order_val = parts[5].strip() if len(parts) > 5 else '0'
                        
                        cursor.execute(
                            f'INSERT INTO {table} (id, course_id, name, yt_link, watch_count, sort_order) VALUES (?, ?, ?, ?, 0, ?)',
                            (id_val, course_id_val, name_val, yt_link_val, sort_order_val)
                        )
                
                elif table == 'extra_stuff':
                    # Extract: id, course_id, name, link
                    parts = values_str.split(',')
                    if len(parts) >= 4:
                        id_val = parts[0].strip()
                        course_id_val = parts[1].strip()
                        name_val = parts[2].strip().strip("'")
                        link_val = parts[3].strip().strip("'")
                        cursor.execute(
                            'INSERT INTO extra_stuff (id, course_id, name, link) VALUES (?, ?, ?, ?)',
                            (id_val, course_id_val, name_val, link_val)
                        )
                
                elif table == 'feedback':
                    # Extract: id, username, feedback, created_at
                    # This is complex due to commas in feedback text
                    # Simple approach: just skip feedback for now or handle carefully
                    pass
            
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"✅ Inserted {count} records into {table}")
        else:
            print(f"⚠️  No data found for {table}")
    
    # Commit and close
    conn.commit()
    
    # Store backup date as metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute(
        'INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
        ('backup_date', '2025-12-19T02:53:25.729894')
    )
    conn.commit()
    
    print("\n" + "="*50)
    print("🎉 Static database created successfully!")
    print("📁 File: static_data.db")
    print(f"📅 Backup date: 2025-12-19")
    print("="*50)
    
    # Show statistics
    print("\n📊 Database Statistics:")
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} records")
    
    conn.close()

if __name__ == '__main__':
    create_static_db()
