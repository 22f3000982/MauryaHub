"""
Fix PostgreSQL sequences that are out of sync with existing data.
Run this script once to reset all sequences to the correct values.
"""
import psycopg2
import os
import socket
from urllib.parse import urlparse

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL or DATABASE_URL.strip() == '':
    DATABASE_URL = "postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres"

def get_db_connection():
    try:
        if DATABASE_URL.startswith('postgres://'):
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
        
        parsed = urlparse(url)
        host = parsed.hostname
        
        # Try direct connection first
        try:
            ipv4_host = socket.gethostbyname(host)
            print(f"Resolved {host} to {ipv4_host}")
        except:
            ipv4_host = host
        
        conn = psycopg2.connect(
            host=ipv4_host,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip('/') if parsed.path else 'postgres',
            user=parsed.username,
            password=parsed.password,
            sslmode='require',
            connect_timeout=30
        )
        print("Connected successfully!")
        return conn
    except Exception as e:
        print(f"Connection error: {e}")
        print(f"Trying direct URL connection...")
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            print("Direct connection successful!")
            return conn
        except Exception as e2:
            print(f"Direct connection also failed: {e2}")
            return None

def fix_sequences():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    cur = conn.cursor()
    
    # Tables with auto-increment id columns
    tables = ['courses', 'quiz1', 'quiz2', 'endterm', 'resources', 'extra_stuff', 'feedback']
    
    for table in tables:
        try:
            # Get the max id in the table
            cur.execute(f'SELECT MAX(id) FROM {table}')
            max_id = cur.fetchone()[0]
            
            if max_id is not None:
                # Reset the sequence to max_id + 1
                sequence_name = f'{table}_id_seq'
                cur.execute(f"SELECT setval('{sequence_name}', {max_id}, true)")
                print(f"✓ Fixed {table}: sequence set to {max_id}")
            else:
                print(f"- {table}: no data, skipping")
        except Exception as e:
            print(f"✗ Error fixing {table}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("\nSequences fixed successfully!")

if __name__ == '__main__':
    fix_sequences()
