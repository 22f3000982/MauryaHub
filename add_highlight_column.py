"""
Migration script to add is_highlighted column to quiz1, quiz2, endterm, and resources tables.
Run this script once to add the highlight feature to your database.
"""

import os
import psycopg2
from urllib.parse import urlparse

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL or DATABASE_URL.strip() == '':
    DATABASE_URL = "postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres"

def get_db_connection():
    """Get database connection"""
    try:
        import socket
        
        if DATABASE_URL.startswith('postgres://'):
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
        
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 5432
        dbname = parsed.path.lstrip('/') if parsed.path else 'postgres'
        username = parsed.username
        password = parsed.password
        
        try:
            ipv4_host = socket.gethostbyname(host)
        except Exception:
            ipv4_host = host
        
        conn = psycopg2.connect(
            host=ipv4_host,
            port=port,
            dbname=dbname,
            user=username,
            password=password,
            sslmode='require'
        )
        
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def add_highlight_columns():
    """Add is_highlighted column to all item tables"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database!")
        return False
    
    tables = ['quiz1', 'quiz2', 'endterm', 'resources']
    
    try:
        cur = conn.cursor()
        
        for table in tables:
            # Check if column already exists
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'is_highlighted'
            """)
            
            if cur.fetchone() is None:
                print(f"Adding is_highlighted column to {table}...")
                cur.execute(f"""
                    ALTER TABLE {table} 
                    ADD COLUMN is_highlighted BOOLEAN DEFAULT FALSE
                """)
                print(f"✅ Successfully added is_highlighted to {table}")
            else:
                print(f"✅ is_highlighted column already exists in {table}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Adding is_highlighted column to database tables")
    print("=" * 50)
    add_highlight_columns()
