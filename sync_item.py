"""Sync a specific item from PostgreSQL to local SQLite"""
import sqlite3
import psycopg2
import os
import socket
from urllib.parse import urlparse

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL or DATABASE_URL.strip() == '':
    DATABASE_URL = "postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres"

def get_pg_connection():
    try:
        if DATABASE_URL.startswith('postgres://'):
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
        parsed = urlparse(url)
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")
        return None

def sync_item(table, item_id):
    # Get from PostgreSQL
    pg_conn = get_pg_connection()
    if not pg_conn:
        return False
    
    cur = pg_conn.cursor()
    cur.execute(f'SELECT id, course_id, name, yt_link, watch_count, sort_order FROM {table} WHERE id = %s', (item_id,))
    item = cur.fetchone()
    cur.close()
    pg_conn.close()
    
    if not item:
        print(f"Item {item_id} not found in PostgreSQL {table}")
        return False
    
    print(f"Found in PostgreSQL: {item}")
    
    # Insert into SQLite
    sqlite_conn = sqlite3.connect('static_data.db')
    cur = sqlite_conn.cursor()
    cur.execute(f'INSERT OR REPLACE INTO {table} (id, course_id, name, yt_link, watch_count, sort_order) VALUES (?, ?, ?, ?, ?, ?)', item)
    sqlite_conn.commit()
    cur.close()
    sqlite_conn.close()
    
    print(f"Synced {table} id={item_id} to local SQLite")
    return True

if __name__ == '__main__':
    sync_item('quiz1', 59)
