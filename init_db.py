#!/usr/bin/env python3
"""
Initialize PostgreSQL Database Tables
"""

import psycopg2
import os
import sys

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    sys.exit(1)

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        # Fix for newer psycopg2 versions that don't support postgres://
        if DATABASE_URL.startswith('postgres://'):
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
            
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for initialization")
        return False
        
    try:
        cur = conn.cursor()

        print("Creating tables...")

        # Create 'courses' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        print("✓ Created courses table")

        # Create 'pyqs' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pyqs (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Created pyqs table")

        # Create 'notes' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Created notes table")

        # Create 'assignments' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Created assignments table")

        # Create 'extra_stuff' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS extra_stuff (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                link TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Created extra_stuff table")

        # Create 'resources' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Created resources table")

        # Create 'feedback' table for landing page testimonials
        cur.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created feedback table")

        conn.commit()
        print("\n✅ Database tables initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("PostgreSQL Database Initialization")
    print("=" * 50)
    
    if init_db():
        print("\n🎉 Ready for data migration!")
        print("Next step: Run 'python migrate_data.py'")
    else:
        print("\n❌ Database initialization failed")
        sys.exit(1)