import sqlite3
import shutil
import os

# Backup current database first
if os.path.exists('database.db'):
    shutil.copy2('database.db', 'current_backup.db')
    print('Current database backed up as current_backup.db')

# Copy latest_backup.db to database.db
shutil.copy2('latest_backup.db', 'database.db')
print('latest_backup.db restored as database.db')

# Check tables in restored database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Tables in restored database:')
for table in tables:
    print(f'  - {table[0]}')
    cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
    count = cursor.fetchone()[0]
    print(f'    Records: {count}')
conn.close()
print('Database restoration completed!')
