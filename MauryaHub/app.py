from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import psycopg2
import psycopg2.extras
import sqlite3
import os
import socket
import subprocess
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
RESOURCE_ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL or DATABASE_URL.strip() == '':
    # Fallback for local development - you should set DATABASE_URL environment variable
    print("ERROR: DATABASE_URL environment variable not set or empty!")
    print("Please set DATABASE_URL in your Render environment variables.")
    print("Using fallback connection string...")
    DATABASE_URL = "postgresql://postgres:India117767724@db.ncssqvmglximthdbinhm.supabase.co:5432/postgres"
else:
    print("DATABASE_URL environment variable found")
    print(f"DATABASE_URL length: {len(DATABASE_URL)}")
    print(f"DATABASE_URL starts with: {DATABASE_URL[:20]}...")  # Show first 20 chars safely

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_resource_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in RESOURCE_ALLOWED_EXTENSIONS

def get_db_connection():
    """Get database connection with IPv4 + SSL fix for Render deployment"""
    try:
        import socket
        from urllib.parse import urlparse
        
        print(f"Attempting to connect to database...")
        print(f"Raw DATABASE_URL: {DATABASE_URL[:50]}..." if len(DATABASE_URL) > 50 else f"Raw DATABASE_URL: {DATABASE_URL}")
        
        # Parse the DATABASE_URL
        if DATABASE_URL.startswith('postgres://'):
            # Fix for newer psycopg2 versions that don't support postgres://
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
        
        print(f"Parsed URL: {url[:50]}..." if len(url) > 50 else f"Parsed URL: {url}")
        
        # Parse connection details
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 5432
        dbname = parsed.path.lstrip('/') if parsed.path else 'postgres'
        username = parsed.username
        password = parsed.password
        
        print(f"Parsed details - Host: {host}, Port: {port}, DB: {dbname}, User: {username}")
        
        # Validate required fields
        if not host or not username or not password:
            raise ValueError(f"Missing required connection parameters - Host: {host}, User: {username}, Password: {'***' if password else None}")
        
        # Force IPv4 DNS lookup to avoid IPv6 issues on Render
        try:
            ipv4_host = socket.gethostbyname(host)
            print(f"Resolved {host} to IPv4: {ipv4_host}")
        except Exception as dns_error:
            print(f"DNS resolution failed: {dns_error}, using original host")
            ipv4_host = host
        
        # Connect with explicit parameters and SSL
        conn = psycopg2.connect(
            host=ipv4_host,
            port=port,
            dbname=dbname,
            user=username,
            password=password,
            sslmode='require'  # Force SSL connection
        )
        
        print("Database connection successful!")
        return conn
        
    except Exception as e:
        print(f"Database connection error: {e}")
        print(f"Connection details - Host: {host if 'host' in locals() else 'unknown'}, Port: {port if 'port' in locals() else 'unknown'}")
        return None

# ============================================================================
# HYBRID DATABASE FUNCTIONS - Ultra-Fast SQLite for Users, Supabase for Admin
# ============================================================================
# 
# OPTIMIZATION STRATEGY - MAXIMUM SPEED FOR USERS:
# 
# ✅ REGULAR USERS (NOT LOGGED IN AS ADMIN):
#    → 100% from GITHUB DATABASE (static_data.db - SQLite)
#    - Course names and IDs
#    - Video/resource names and YouTube links
#    - Watch counts (from last backup)
#    - Course structure and organization
#    - All content from backup dated Dec 19, 2025
#    → INSTANT loading, ZERO network calls, ZERO Supabase queries!
# 
# ✅ ADMIN USERS (LOGGED IN):
#    → 100% from SUPABASE (PostgreSQL) 
#    - Real-time course data
#    - Latest watch counts
#    - Newly added resources
#    - Full CRUD operations
#    - Analytics and backups
#    → Real-time data for management
# 
# RESULTS: 
#   - Regular users: 100% OFFLINE operation, INSTANT page loads!
#   - Admin users: Full control with real-time Supabase data
#   - Zero Supabase load from regular users
#   - Maximum performance and scalability
# ============================================================================

def ensure_url_scheme(url):
    """Ensure URL has http:// or https:// prefix for proper redirect"""
    if not url:
        return url
    url = url.strip()
    if not url.startswith('http://') and not url.startswith('https://'):
        return 'https://' + url
    return url

def log_view_event(content_table, content_id, course_id=None):
    """Store real view event records for analytics (no estimated values)."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO view_events (content_table, content_id, course_id, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (
                content_table,
                content_id,
                course_id,
                request.headers.get('X-Forwarded-For', request.remote_addr),
                request.headers.get('User-Agent', '')[:500]
            )
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging view event: {e}")
    finally:
        if conn:
            conn.close()

def get_local_db_connection():
    """Get connection to local SQLite database for static data"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'static_data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        print(f"Local database connection error: {e}")
        return None

def get_watch_counts_from_supabase(table_name, ids):
    """Fetch only watch counts from Supabase for given IDs"""
    if not ids:
        return {}
    
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        # Fetch only watch_count for the given IDs
        ids_str = ','.join(str(id) for id in ids)
        cur.execute(f'SELECT id, watch_count FROM {table_name} WHERE id IN ({ids_str})')
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Return as dictionary {id: watch_count}
        return {row[0]: row[1] for row in results}
    except Exception as e:
        print(f"Error fetching watch counts: {e}")
        if conn:
            conn.close()
        return {}

def get_new_resources_from_supabase(table_name, course_id, cutoff_date='2025-12-19'):
    """Check Supabase for resources added after the static backup date"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # Note: This assumes you have a created_at or similar column
        # If not, this will return all records and we'll compare IDs instead
        cur.execute(
            f'SELECT id, course_id, name, yt_link, watch_count, sort_order FROM {table_name} WHERE course_id = %s',
            (course_id,)
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching new resources: {e}")
        if conn:
            conn.close()
        return []

def merge_static_with_watch_counts(static_data, watch_counts):
    """Merge static data with live watch counts from Supabase"""
    merged = []
    for row in static_data:
        # Convert sqlite3.Row to list
        row_list = list(row)
        row_id = row_list[0]
        
        # Update watch_count (typically at index 3 for most tables)
        # Structure: (id, course_id, name, yt_link, watch_count, sort_order)
        if row_id in watch_counts:
            if len(row_list) > 4:
                row_list[4] = watch_counts[row_id]  # Update watch_count
        
        merged.append(tuple(row_list))
    
    return merged

def get_static_courses_with_counts():
    """Legacy compatibility wrapper now using Supabase only."""
    return get_courses_from_supabase()

def merge_courses(static_courses, supabase_courses):
    """Merge course lists with Supabase as the source of truth and SQLite as fallback."""
    merged = {}

    for course in static_courses or []:
        if not course:
            continue
        merged[course[0]] = tuple(course)

    for course in supabase_courses or []:
        if not course:
            continue
        merged[course[0]] = tuple(course)

    return [merged[course_id] for course_id in sorted(merged.keys())]

def merge_content_rows(static_rows, supabase_rows):
    """Merge content rows by id with Supabase taking precedence."""
    merged = {}

    for row in static_rows or []:
        if not row:
            continue
        merged[row[0]] = tuple(row)

    for row in supabase_rows or []:
        if not row:
            continue
        merged[row[0]] = tuple(row)

    def sort_key(row):
        sort_order = row[5] if len(row) > 5 and row[5] is not None else 0
        return (sort_order, row[0])

    return sorted(merged.values(), key=sort_key)

def get_courses_for_display():
    """
    Return courses for frontend display from Supabase only.
    """
    return get_courses_from_supabase()

def sync_course_to_local_sqlite(course_id, course_name):
    """Best-effort sync of course metadata to local SQLite fallback DB."""
    local_conn = get_local_db_connection()
    if not local_conn:
        return

    try:
        cur = local_conn.cursor()
        cur.execute('INSERT OR REPLACE INTO courses (id, name) VALUES (?, ?)', (course_id, course_name))
        local_conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error syncing course to local SQLite: {e}")
    finally:
        local_conn.close()

def delete_course_from_local_sqlite(course_id):
    """Best-effort removal of course metadata from local SQLite fallback DB."""
    local_conn = get_local_db_connection()
    if not local_conn:
        return

    try:
        cur = local_conn.cursor()
        cur.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        local_conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error deleting course from local SQLite: {e}")
    finally:
        local_conn.close()

def sync_item_to_local_sqlite(item_type, item_id, course_id, item_name, yt_link, sort_order=0, watch_count=0, is_highlighted=0):
    """Best-effort sync of content rows to local SQLite fallback DB."""
    if item_type not in ['quiz1', 'quiz2', 'endterm', 'resources']:
        return

    local_conn = get_local_db_connection()
    if not local_conn:
        return

    try:
        cur = local_conn.cursor()
        cur.execute(
            f'INSERT OR REPLACE INTO {item_type} (id, course_id, name, yt_link, watch_count, sort_order, is_highlighted) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (item_id, course_id, item_name, yt_link, watch_count, sort_order, int(bool(is_highlighted)))
        )
        local_conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error syncing item to local SQLite: {e}")
    finally:
        local_conn.close()

def delete_item_from_local_sqlite(item_type, item_id):
    """Best-effort removal of content rows from local SQLite fallback DB."""
    if item_type not in ['quiz1', 'quiz2', 'endterm', 'resources']:
        return

    local_conn = get_local_db_connection()
    if not local_conn:
        return

    try:
        cur = local_conn.cursor()
        cur.execute(f'DELETE FROM {item_type} WHERE id = ?', (item_id,))
        local_conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error deleting item from local SQLite: {e}")
    finally:
        local_conn.close()

def sync_extra_to_local_sqlite(course_id, name, link):
    """Best-effort sync of extra links to local SQLite fallback DB."""
    local_conn = get_local_db_connection()
    if not local_conn:
        return

    try:
        cur = local_conn.cursor()
        cur.execute('DELETE FROM extra_stuff WHERE course_id = ?', (course_id,))
        cur.execute('INSERT INTO extra_stuff (course_id, name, link) VALUES (?, ?, ?)', (course_id, name, link))
        local_conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error syncing extra stuff to local SQLite: {e}")
    finally:
        local_conn.close()

def get_courses_from_supabase():
    """Fallback: Get courses directly from Supabase"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM courses ORDER BY id')
        courses = cur.fetchall()
        cur.close()
        conn.close()
        return courses
    except Exception as e:
        print(f"Error fetching courses from Supabase: {e}")
        if conn:
            conn.close()
        return []

def get_course_data_hybrid(course_id, check_new_resources=False, is_admin=False):
    """Legacy compatibility wrapper now using Supabase only."""
    return get_course_data_from_supabase(course_id)

def get_course_data_from_supabase(course_id):
    """Fallback: Get all course data from Supabase"""
    conn = get_db_connection()
    if not conn:
        return (None, [], [], [], [], None)
    
    try:
        cur = conn.cursor()
        
        cur.execute('SELECT name FROM courses WHERE id=%s', (course_id,))
        course = cur.fetchone()
        course_name = course[0] if course else None
        
        cur.execute('SELECT id, name, yt_link, watch_count, COALESCE(is_highlighted, false) FROM quiz1 WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
        quiz1 = cur.fetchall()
        
        cur.execute('SELECT id, name, yt_link, watch_count, COALESCE(is_highlighted, false) FROM quiz2 WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
        quiz2 = cur.fetchall()
        
        cur.execute('SELECT id, name, yt_link, watch_count, COALESCE(is_highlighted, false) FROM endterm WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
        endterm = cur.fetchall()
        
        cur.execute('SELECT id, name, yt_link, watch_count, COALESCE(is_highlighted, false) FROM resources WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
        resources = cur.fetchall()
        
        cur.execute('SELECT name, link FROM extra_stuff WHERE course_id=%s', (course_id,))
        extra = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return (course_name, quiz1, quiz2, endterm, resources, extra)
        
    except Exception as e:
        print(f"Error fetching from Supabase: {e}")
        if conn:
            conn.close()
        return (None, [], [], [], [], None)

# ============================================================================
# END OF HYBRID DATABASE FUNCTIONS
# ============================================================================

# Create tables if they don't exist
def init_db():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for initialization")
        return
        
    try:
        cur = conn.cursor()

        # Create 'courses' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')

        # Create 'quiz1' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS quiz1 (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')

        # Create 'quiz2' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS quiz2 (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')

        # Create 'endterm' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS endterm (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')

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

        # Create 'general_resources' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resources (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                resource_link TEXT NOT NULL,
                program_type TEXT NOT NULL,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create 'feedback' table for landing page testimonials
        cur.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Real analytics event log (required for time-based and user-behavior analytics)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS view_events (
                id SERIAL PRIMARY KEY,
                content_table TEXT NOT NULL,
                content_id INTEGER NOT NULL,
                course_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("Database tables initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Backup the database to a SQL file
def backup_db():
    try:
        conn = get_db_connection()
        if not conn:
            print("Failed to connect to database for backup")
            return
            
        cur = conn.cursor()
        
        # Create a simple backup by dumping data as INSERT statements
        backup_content = []
        backup_content.append("-- Database backup created at " + datetime.now().isoformat())
        backup_content.append("")
        
        # Backup each table
        tables = ['courses', 'quiz1', 'quiz2', 'endterm', 'resources', 'general_resources', 'extra_stuff', 'feedback', 'view_events']
        
        for table in tables:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            
            if rows:
                # Get column names
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position")
                columns = [row[0] for row in cur.fetchall()]
                
                backup_content.append(f"-- Backup for table {table}")
                backup_content.append(f"DELETE FROM {table};")
                
                for row in rows:
                    values = []
                    for value in row:
                        if value is None:
                            values.append('NULL')
                        elif isinstance(value, str):
                            escaped_value = value.replace("'", "''")
                            values.append(f"'{escaped_value}'")
                        else:
                            values.append(str(value))
                    
                    backup_content.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});")
                
                backup_content.append("")
        
        with open('backup.sql', 'w', encoding='utf-8') as f:
            f.write('\n'.join(backup_content))
        
        print("Database backed up to backup.sql")
        
    except Exception as e:
        print(f"Error backing up database: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

# Function to get recently added content
def get_recent_content():
    # Supabase-only recent content.
    conn = get_db_connection()
    if not conn:
        return []
    
    cur = conn.cursor()
    recent = []
    
    # Get recent items from each table
    for table, display_name in [('quiz1', 'Quiz-1'), ('quiz2', 'Quiz-2'), ('endterm', 'End Term')]:
        try:
            cur.execute(f'''
                SELECT c.name, {table}.name, {table}.id, {table}.course_id, {table}.watch_count
                FROM {table} 
                JOIN courses c ON {table}.course_id = c.id 
                WHERE {table}.yt_link IS NOT NULL AND {table}.yt_link != ''
                ORDER BY {table}.id DESC 
                LIMIT 3
            ''')
            items = cur.fetchall()
            for item in items:
                recent.append({
                    'course': item[0],
                    'name': item[1], 
                    'type': display_name,
                    'url': f'/course/{item[3]}',
                    'views': item[4] or 0,
                    'item_id': item[2]
                })
        except Exception as e:
            print(f'Error fetching recent {table}: {e}')
            continue
    
    cur.close()
    conn.close()
    
    # Sort by item_id (most recent first) and return top 6
    recent.sort(key=lambda x: x['item_id'], reverse=True)
    return recent[:6]

# Landing page route
@app.route('/')
def landing_page():
    recent_content = get_recent_content()
    return render_template('landing.html', recent_content=recent_content)

# Submit feedback route
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        feedback_text = data.get('feedback', '').strip()
        
        if not username or not feedback_text:
            return {'error': 'Missing required fields'}, 400
            
        # Insert feedback into database
        conn = get_db_connection()
        if not conn:
            return {'error': 'Database connection failed'}, 500
            
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO feedback (username, feedback)
            VALUES (%s, %s)
        ''', (username, feedback_text))
        conn.commit()
        cur.close()
        conn.close()
        
        # Backup database after adding feedback
        backup_db()
        
        return {'success': True, 'message': 'Feedback submitted successfully'}
        
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return {'error': 'Internal server error'}, 500

# Get feedback route
@app.route('/get-feedback')
def get_feedback():
    try:
        conn = get_db_connection()
        if not conn:
            from flask import jsonify
            return jsonify([])
            
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT username, feedback, created_at
            FROM feedback
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        
        feedback_list = []
        for row in cur.fetchall():
            feedback_list.append({
                'username': row['username'],
                'feedback': row['feedback'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })
        
        cur.close()
        conn.close()
        
        from flask import jsonify
        return jsonify(feedback_list)
        
    except Exception as e:
        print(f"Error getting feedback: {e}")
        from flask import jsonify
        return jsonify([])

# Delete feedback route
@app.route('/delete-feedback', methods=['POST'])
def delete_feedback():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        feedback_text = data.get('feedback', '').strip()
        created_at = data.get('created_at', '').strip()
        
        if not username or not feedback_text:
            return {'error': 'Missing required fields'}, 400
            
        # Delete feedback from database
        conn = get_db_connection()
        if not conn:
            return {'error': 'Database connection failed'}, 500
            
        cur = conn.cursor()
        cur.execute('''
            DELETE FROM feedback 
            WHERE username = %s AND feedback = %s AND created_at = %s
        ''', (username, feedback_text, created_at))
        
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return {'error': 'Feedback not found'}, 404
            
        conn.commit()
        cur.close()
        conn.close()
        
        # Backup database after deleting feedback
        backup_db()
        
        return {'success': True, 'message': 'Feedback deleted successfully'}
        
    except Exception as e:
        print(f"Error deleting feedback: {e}")
        return {'error': 'Internal server error'}, 500

# Home - Show all courses
import time
from flask import send_file

# Home - Show all courses
@app.route('/dashboard', methods=['GET', 'POST'])
def course_view():
    courses = get_courses_for_display()
    
    if not courses:
        return render_template('course_view.html', courses=[], admin_mode=session.get('admin_mode', False))

    admin_mode = session.get('admin_mode', False)
    return render_template('course_view.html', courses=courses, admin_mode=admin_mode)

@app.route('/resources')
def general_resources_page():
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template(
            'resources.html',
            diploma_resources=[],
            degree_resources=[],
            admin_mode=session.get('admin_mode', False)
        )

    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, title, resource_link, program_type, watch_count
            FROM general_resources
            WHERE program_type = %s
            ORDER BY sort_order, id
        ''', ('diploma',))
        diploma_resources = cur.fetchall()

        cur.execute('''
            SELECT id, title, resource_link, program_type, watch_count
            FROM general_resources
            WHERE program_type = %s
            ORDER BY sort_order, id
        ''', ('degree',))
        degree_resources = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error fetching general resources: {e}")
        diploma_resources = []
        degree_resources = []
    finally:
        conn.close()

    return render_template(
        'resources.html',
        diploma_resources=diploma_resources,
        degree_resources=degree_resources,
        admin_mode=session.get('admin_mode', False)
    )

@app.route('/admin/resources/add', methods=['GET', 'POST'])
def admin_add_general_resource():
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        program_type = request.form.get('program_type', '').strip().lower()
        resource_link = request.form.get('resource_link', '').strip()
        pdf_file = request.files.get('resource_pdf')

        if not title or program_type not in ['diploma', 'degree']:
            flash('Please provide a valid title and program type.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        final_link = None

        if pdf_file and pdf_file.filename:
            if not allowed_resource_file(pdf_file.filename):
                flash('Only PDF uploads are allowed.', 'error')
                return redirect(url_for('admin_add_general_resource'))

            safe_name = secure_filename(pdf_file.filename)
            stored_name = f"{program_type}_{int(datetime.utcnow().timestamp())}_{safe_name}"
            resources_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'general_resources')
            os.makedirs(resources_dir, exist_ok=True)
            pdf_file.save(os.path.join(resources_dir, stored_name))
            final_link = url_for('static', filename=f'uploads/general_resources/{stored_name}')
        elif resource_link:
            final_link = ensure_url_scheme(resource_link)
        else:
            flash('Please add either a direct link or a PDF file.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('admin_add_general_resource'))

        try:
            cur = conn.cursor()
            cur.execute('SELECT COALESCE(MAX(sort_order), -1) FROM general_resources WHERE program_type=%s', (program_type,))
            next_order = cur.fetchone()[0] + 1
            cur.execute(
                '''
                INSERT INTO general_resources (title, resource_link, program_type, sort_order)
                VALUES (%s, %s, %s, %s)
                ''',
                (title, final_link, program_type, next_order)
            )
            conn.commit()
            cur.close()
            backup_db()
            flash('General resource added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed to add resource: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('general_resources_page'))

    return render_template('admin_add_general_resource.html')

@app.route('/admin/resources/delete/<int:resource_id>', methods=['POST'])
def admin_delete_general_resource(resource_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('general_resources_page'))

    try:
        cur = conn.cursor()
        cur.execute('SELECT resource_link FROM general_resources WHERE id=%s', (resource_id,))
        resource = cur.fetchone()

        if resource is None:
            flash('Resource not found.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('general_resources_page'))

        resource_link = resource[0]
        cur.execute('DELETE FROM general_resources WHERE id=%s', (resource_id,))
        conn.commit()
        cur.close()

        static_prefix = '/static/uploads/general_resources/'
        if resource_link and resource_link.startswith(static_prefix):
            file_name = resource_link.replace(static_prefix, '', 1)
            file_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'general_resources', file_name)
            if os.path.exists(file_path):
                os.remove(file_path)

        backup_db()
        flash('Resource deleted successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Failed to delete resource: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('general_resources_page'))

@app.route('/open_general_resource/<int:resource_id>')
def open_general_resource(resource_id):
    conn = get_db_connection()
    if not conn:
        return "Resource link not found"

    try:
        cur = conn.cursor()
        cur.execute(
            'UPDATE general_resources SET watch_count = watch_count + 1 WHERE id=%s RETURNING resource_link',
            (resource_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()

        if not row or not row[0]:
            return "Resource link not found"

        link = row[0].strip()
        log_view_event('general_resources', resource_id, None)

        if link.startswith('/'):
            return redirect(link)

        return redirect(ensure_url_scheme(link))
    except Exception:
        return "Resource link not found"
    finally:
        conn.close()

# Admin Backup & Restore page
@app.route('/admin/backup', methods=['GET', 'POST'])
def admin_backup():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    backup_time = 'Available on demand'
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'backup':
            # Create a backup file
            backup_db()
            if os.path.exists('backup.sql'):
                return send_file('backup.sql', as_attachment=True)
            else:
                flash('Error creating backup file', 'error')

    return render_template('admin_backup.html', backup_file='backup.sql', backup_size=0, backup_time=backup_time)

from flask import flash  # Make sure this is imported

# Admin login (password 4129)
@app.route('/admin_login', methods=['POST'])
def admin_login():
    password = request.form['password']
    if password == '4129':
        session['admin_mode'] = True
    else:
        flash('काहे को छेड़ता है पराई वेबसाइट को? 😜😉')
    return redirect(url_for('course_view'))

# Admin view analytics - Total views count
@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('course_view'))
    
    try:
        cur = conn.cursor()
        
        # Real-data analytics only: watch_count + view_events log.
        analytics = {}
        tables = ['quiz1', 'quiz2', 'endterm', 'resources']
        table_labels = {
            'quiz1': 'Quiz 1',
            'quiz2': 'Quiz 2',
            'endterm': 'End Term',
            'resources': 'Resources'
        }
        
        overall_total_views = 0
        overall_total_videos = 0
        detailed_rows = {key: [] for key in tables}
        all_course_names = set()
        top_video_candidate = None
        
        for table in tables:
            cur.execute(f'SELECT COUNT(*), COALESCE(SUM(watch_count), 0) FROM {table}')
            count, total_views = cur.fetchone()
            total_views = total_views or 0
            overall_total_views += total_views
            overall_total_videos += count
            
            # Get top 10 most viewed for each category
            cur.execute(f'''
                SELECT c.name, {table}.name, {table}.watch_count 
                FROM {table}
                JOIN courses c ON {table}.course_id = c.id
                WHERE {table}.watch_count > 0
                ORDER BY {table}.watch_count DESC
                LIMIT 10
            ''')
            top_items = cur.fetchall()

            # Build detailed rows using real last-view timestamps from view_events.
            cur.execute(f'''
                SELECT c.name,
                       {table}.name,
                       COALESCE({table}.watch_count, 0),
                       (
                           SELECT MAX(ve.viewed_at)
                           FROM view_events ve
                           WHERE ve.content_table = %s AND ve.content_id = {table}.id
                       ) AS last_viewed_at
                FROM {table}
                JOIN courses c ON {table}.course_id = c.id
                ORDER BY {table}.watch_count DESC, {table}.id ASC
            ''', (table,))
            raw_rows = cur.fetchall()

            for course_name, item_name, views, last_viewed_at in raw_rows:
                views = views or 0
                last_viewed = last_viewed_at.strftime('%Y-%m-%d %H:%M') if last_viewed_at else 'N/A'

                row = {
                    'content_type': table_labels[table],
                    'video_name': item_name,
                    'course_name': course_name,
                    'views': int(views),
                    'last_viewed': last_viewed
                }
                detailed_rows[table].append(row)
                all_course_names.add(course_name)

                if not top_video_candidate or views > top_video_candidate['views']:
                    top_video_candidate = {
                        'video_name': item_name,
                        'course_name': course_name,
                        'views': int(views)
                    }
            
            analytics[table] = {
                'total_videos': count,
                'total_views': total_views,
                'top_items': top_items
            }

        # Aggregate course performance for charting and insights.
        cur.execute('''
            SELECT course_name, SUM(views)::int AS total_views
            FROM (
                SELECT c.name AS course_name, q1.watch_count AS views FROM quiz1 q1 JOIN courses c ON q1.course_id = c.id
                UNION ALL
                SELECT c.name AS course_name, q2.watch_count AS views FROM quiz2 q2 JOIN courses c ON q2.course_id = c.id
                UNION ALL
                SELECT c.name AS course_name, et.watch_count AS views FROM endterm et JOIN courses c ON et.course_id = c.id
                UNION ALL
                SELECT c.name AS course_name, r.watch_count AS views FROM resources r JOIN courses c ON r.course_id = c.id
            ) grouped
            GROUP BY course_name
            ORDER BY total_views DESC
            LIMIT 8
        ''')
        top_courses = cur.fetchall()

        # Real daily trend from event log (last 7 days).
        now = datetime.now()
        trend_labels = [(now - timedelta(days=(6 - i))).strftime('%d %b') for i in range(7)]
        trend_map = {label: 0 for label in trend_labels}
        cur.execute('''
            SELECT TO_CHAR(viewed_at::date, 'DD Mon') AS day_label, COUNT(*)::int
            FROM view_events
            WHERE viewed_at::date >= CURRENT_DATE - INTERVAL '6 days'
            GROUP BY viewed_at::date
        ''')
        for day_label, count in cur.fetchall():
            if day_label in trend_map:
                trend_map[day_label] = count
        trend_values = [trend_map[label] for label in trend_labels]

        # Real hourly heatmap from event log (last 30 days).
        heatmap_values = [0] * 24
        cur.execute('''
            SELECT EXTRACT(HOUR FROM viewed_at)::int AS hr, COUNT(*)::int
            FROM view_events
            WHERE viewed_at >= NOW() - INTERVAL '30 days'
            GROUP BY hr
            ORDER BY hr
        ''')
        for hour, count in cur.fetchall():
            if 0 <= hour < 24:
                heatmap_values[hour] = count

        avg_views_per_video = round(overall_total_views / overall_total_videos, 1) if overall_total_videos else 0

        # Real user counts based on distinct IP addresses.
        cur.execute('''
            SELECT COUNT(DISTINCT ip_address)
            FROM view_events
            WHERE ip_address IS NOT NULL AND viewed_at >= NOW() - INTERVAL '1 day'
        ''')
        daily_active_users = cur.fetchone()[0] or 0

        cur.execute('''
            SELECT COUNT(DISTINCT ip_address)
            FROM view_events
            WHERE ip_address IS NOT NULL AND viewed_at >= NOW() - INTERVAL '7 days'
        ''')
        weekly_active_users = cur.fetchone()[0] or 0

        cur.execute('''
            WITH ip_first_seen AS (
                SELECT ip_address, MIN(viewed_at) AS first_seen, MAX(viewed_at) AS last_seen
                FROM view_events
                WHERE ip_address IS NOT NULL
                GROUP BY ip_address
            )
            SELECT
                COUNT(*) FILTER (WHERE first_seen >= NOW() - INTERVAL '7 days') AS new_users,
                COUNT(*) FILTER (WHERE first_seen < NOW() - INTERVAL '7 days' AND last_seen >= NOW() - INTERVAL '7 days') AS returning_users
            FROM ip_first_seen
        ''')
        new_users, returning_users = cur.fetchone()
        new_users = new_users or 0
        returning_users = returning_users or 0

        # Real device split based on user-agent text.
        cur.execute('''
            SELECT
                COUNT(*) FILTER (
                    WHERE user_agent ILIKE '%%mobile%%' OR user_agent ILIKE '%%android%%' OR user_agent ILIKE '%%iphone%%'
                ) AS mobile_events,
                COUNT(*) FILTER (
                    WHERE user_agent IS NOT NULL
                      AND user_agent NOT ILIKE '%%mobile%%'
                      AND user_agent NOT ILIKE '%%android%%'
                      AND user_agent NOT ILIKE '%%iphone%%'
                ) AS desktop_events
            FROM view_events
            WHERE viewed_at >= NOW() - INTERVAL '30 days'
        ''')
        mobile_events, desktop_events = cur.fetchone()
        mobile_events = mobile_events or 0
        desktop_events = desktop_events or 0
        total_device_events = mobile_events + desktop_events
        mobile_share = round((mobile_events * 100 / total_device_events), 1) if total_device_events else 0
        desktop_share = round((desktop_events * 100 / total_device_events), 1) if total_device_events else 0

        # If view_events table exists but has no historic event rows, weekly deltas are unknown.
        views_change_pct = None
        if sum(trend_values[:-1]) > 0:
            previous_period = sum(trend_values[:-1])
            views_change_pct = round(((trend_values[-1] - previous_period / 6) / (previous_period / 6)) * 100, 1)

        top_course_name = top_courses[0][0] if top_courses else 'N/A'
        top_course_views = int(top_courses[0][1]) if top_courses else 0

        quiz1_avg_views = (analytics['quiz1']['total_views'] / analytics['quiz1']['total_videos']) if analytics['quiz1']['total_videos'] else 0
        quiz2_avg_views = (analytics['quiz2']['total_views'] / analytics['quiz2']['total_videos']) if analytics['quiz2']['total_videos'] else 0
        quiz_drop_percent = round(max(0, ((quiz1_avg_views - quiz2_avg_views) / quiz1_avg_views) * 100), 1) if quiz1_avg_views else 0

        best_hour_index = max(range(len(heatmap_values)), key=lambda i: heatmap_values[i]) if heatmap_values else 18
        best_hour_label = f"{best_hour_index:02d}:00 - {(best_hour_index + 1) % 24:02d}:00"
        events_7d = sum(trend_values)
        events_30d = sum(heatmap_values)

        overview_metrics = {
            'total_views': overall_total_views,
            'views_change_pct': views_change_pct,
            'total_videos': overall_total_videos,
            'avg_views_per_video': avg_views_per_video,
            'events_7d': events_7d,
            'events_30d': events_30d,
            'daily_active_users': daily_active_users,
            'weekly_active_users': weekly_active_users,
            'new_users': new_users,
            'returning_users': returning_users,
            'mobile_share': mobile_share,
            'desktop_share': desktop_share,
            'peak_hour_label': best_hour_label
        }

        chart_data = {
            'trend': {
                'labels': trend_labels,
                'values': trend_values
            },
            'top_courses': {
                'labels': [row[0] for row in top_courses],
                'values': [int(row[1]) for row in top_courses]
            },
            'content_distribution': {
                'labels': ['Quiz 1', 'Quiz 2', 'End Term', 'Resources'],
                'values': [
                    analytics['quiz1']['total_views'],
                    analytics['quiz2']['total_views'],
                    analytics['endterm']['total_views'],
                    analytics['resources']['total_views']
                ]
            },
            'hourly_heatmap': heatmap_values
        }

        insights = [
            f"Top performing video this week: {top_video_candidate['video_name']} ({top_video_candidate['views']} views)" if top_video_candidate else 'Top performing video this week: Not enough data yet',
            f"Most viewed course: {top_course_name} ({top_course_views} total views)",
            f"Drop detected in Quiz 2: {quiz_drop_percent}% lower average views than Quiz 1" if quiz_drop_percent > 0 else 'Quiz 2 average views are stable compared to Quiz 1',
            f"Best time users are active: {best_hour_label}"
        ]

        courses_for_filter = sorted(list(all_course_names))
        
        cur.close()
        conn.close()
        
        return render_template('admin_analytics.html', 
                             analytics=analytics,
                             overall_total_views=overall_total_views,
                             overall_total_videos=overall_total_videos,
                             overview_metrics=overview_metrics,
                             chart_data=chart_data,
                             detailed_rows=detailed_rows,
                             insights=insights,
                             courses_for_filter=courses_for_filter,
                             admin_mode=True)
    
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        flash('Error fetching analytics', 'error')
        if conn:
            conn.close()
        return redirect(url_for('course_view'))

# Admin logout
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_mode', None)
    return redirect(url_for('course_view'))

# Admin - Add course
@app.route('/admin/add_course', methods=['GET', 'POST'])
def admin_add_course():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        
        # First, insert into PostgreSQL (Supabase) - primary database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('INSERT INTO courses (name) VALUES (%s) RETURNING id', (course_name,))
                cur.fetchone()
                conn.commit()
                cur.close()
                conn.close()
                backup_db()  # Backup database after adding course
                flash(f'Course "{course_name}" added successfully!', 'success')
            except Exception as e:
                print(f"Error adding course to PostgreSQL: {e}")
                flash(f'Error adding course: {e}', 'error')
                conn.close()
        else:
            flash('Database connection failed!', 'error')
        
        return redirect(url_for('course_view'))

    return render_template('admin_add_course.html')

# Admin - Edit course
@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('course_view'))
        
    cur = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['course_name']
        cur.execute('UPDATE courses SET name = %s WHERE id = %s', (new_name, course_id))
        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after editing course
        return redirect(url_for('course_view'))

    cur.execute('SELECT name FROM courses WHERE id = %s', (course_id,))
    course = cur.fetchone()
    cur.close()
    conn.close()

    if course:
        return render_template('admin_edit_course.html', course_id=course_id, course_name=course[0])
    else:
        return redirect(url_for('course_view'))

# Admin - Delete course
@app.route('/admin/delete_course/<int:course_id>', methods=['GET', 'POST'])
def admin_delete_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'GET':
        # Get course name for confirmation
        conn = get_db_connection()
        if not conn:
            return redirect(url_for('course_view'))
            
        cur = conn.cursor()
        cur.execute('SELECT name FROM courses WHERE id = %s', (course_id,))
        course = cur.fetchone()
        cur.close()
        conn.close()
        
        if course:
            return render_template('confirm_delete.html', 
                                 item_type='course', 
                                 item_name=course[0],
                                 delete_url=url_for('admin_delete_course', course_id=course_id),
                                 cancel_url=url_for('course_view'))
        else:
            flash('Course not found.', 'error')
            return redirect(url_for('course_view'))

    # POST request - actual deletion
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        # Due to CASCADE, related records will be deleted automatically
        cur.execute('DELETE FROM courses WHERE id = %s', (course_id,))
        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after deleting course
        flash('Course deleted successfully!', 'success')
    return redirect(url_for('course_view'))

# View course detail
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    # Check if admin is logged in
    admin_mode = session.get('admin_mode', False)

    course_name, quiz1, quiz2, endterm, resources, extra = get_course_data_from_supabase(course_id)
    
    if course_name:
        return render_template('course_detail.html',
                               course_id=course_id,
                               course_name=course_name,
                               quiz1=quiz1,
                               quiz2=quiz2,
                               endterm=endterm,
                               resources=resources,
                               admin_mode=admin_mode,
                               extra_stuff=extra)
    else:
        return "Course not found"

# API endpoint to add extra stuff (AJAX)
@app.route('/course/<int:course_id>/add_extra', methods=['POST'])
def add_extra_stuff(course_id):
    if not session.get('admin_mode'):
        return {"success": False, "error": "Unauthorized"}, 403
    name = request.form.get('name')
    link = request.form.get('link')
    if not name or not link:
        return {"success": False, "error": "Missing name or link"}, 400
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed"}, 500
        
    cur = conn.cursor()
    # Remove any previous extra stuff for this course (only one allowed)
    cur.execute('DELETE FROM extra_stuff WHERE course_id=%s', (course_id,))
    cur.execute('INSERT INTO extra_stuff (course_id, name, link) VALUES (%s, %s, %s)', (course_id, name, link))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

# API endpoint to get extra stuff (AJAX)
@app.route('/course/<int:course_id>/get_extra')
def get_extra_stuff(course_id):
    conn = get_db_connection()
    if not conn:
        return {"name": None, "link": None}
        
    cur = conn.cursor()
    cur.execute('SELECT name, link FROM extra_stuff WHERE course_id=%s', (course_id,))
    extra = cur.fetchone()
    cur.close()
    conn.close()
    
    if extra:
        return {"name": extra[0], "link": extra[1]}
    else:
        return {"name": None, "link": None}

# Admin - Add PYQ / Notes / Assignment / Resources
@app.route('/admin/add_item/<item_type>/<int:course_id>', methods=['GET', 'POST'])
def admin_add_item(item_type, course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'POST':
        item_name = request.form['item_name']
        yt_link = request.form['yt_link']
        new_item_id = None

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('course_detail', course_id=course_id))
            
        cur = conn.cursor()

        # Get the next sort_order value
        cur.execute(f'SELECT MAX(sort_order) FROM {item_type} WHERE course_id=%s', (course_id,))
        result = cur.fetchone()
        max_order = result[0] if result[0] is not None else -1
        next_order = max_order + 1

        if item_type in ['quiz1', 'quiz2', 'endterm', 'resources']:
            cur.execute(f'INSERT INTO {item_type} (course_id, name, yt_link, sort_order) VALUES (%s, %s, %s, %s) RETURNING id', 
                       (course_id, item_name, yt_link, next_order))
            new_item_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after adding item
        
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('admin_add_pyq.html', course_id=course_id, item_type=item_type)

# Watch Count Increment functions
@app.route('/increment_watch_quiz1/<int:quiz1_id>')
def increment_watch_quiz1(quiz1_id):
    conn = get_db_connection()
    if not conn:
        return "Link not found"

    try:
        cur = conn.cursor()
        cur.execute('UPDATE quiz1 SET watch_count = watch_count + 1 WHERE id = %s RETURNING yt_link, course_id', (quiz1_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result[0]:
            log_view_event('quiz1', quiz1_id, result[1])
            return redirect(ensure_url_scheme(result[0]))
    except Exception:
        if conn:
            conn.close()
    
    return "Link not found"

@app.route('/increment_watch_quiz2/<int:quiz2_id>')
def increment_watch_quiz2(quiz2_id):
    conn = get_db_connection()
    if not conn:
        return "Link not found"

    try:
        cur = conn.cursor()
        cur.execute('UPDATE quiz2 SET watch_count = watch_count + 1 WHERE id = %s RETURNING yt_link, course_id', (quiz2_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result[0]:
            log_view_event('quiz2', quiz2_id, result[1])
            return redirect(ensure_url_scheme(result[0]))
    except Exception:
        if conn:
            conn.close()
    
    return "Link not found"

@app.route('/increment_watch_endterm/<int:endterm_id>')
def increment_watch_endterm(endterm_id):
    conn = get_db_connection()
    if not conn:
        return "Link not found"

    try:
        cur = conn.cursor()
        cur.execute('UPDATE endterm SET watch_count = watch_count + 1 WHERE id = %s RETURNING yt_link, course_id', (endterm_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result[0]:
            log_view_event('endterm', endterm_id, result[1])
            return redirect(ensure_url_scheme(result[0]))
    except Exception:
        if conn:
            conn.close()
    
    return "Link not found"

@app.route('/increment_watch_resource/<int:resource_id>')
def increment_watch_resource(resource_id):
    conn = get_db_connection()
    if not conn:
        return "Link not found"

    try:
        cur = conn.cursor()
        cur.execute('UPDATE resources SET watch_count = watch_count + 1 WHERE id = %s RETURNING yt_link, course_id', (resource_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result[0]:
            log_view_event('resources', resource_id, result[1])
            return redirect(ensure_url_scheme(result[0]))
    except Exception:
        if conn:
            conn.close()
    
    return "Link not found"

# Admin - Move item up/down
@app.route('/admin/move_item', methods=['POST'])
def move_item():
    if not session.get('admin_mode'):
        return {"success": False, "error": "Unauthorized"}, 403
    
    item_type = request.form.get('item_type')
    item_id = int(request.form.get('item_id'))
    direction = request.form.get('direction')
    course_id = int(request.form.get('course_id'))
    
    if item_type not in ['quiz1', 'quiz2', 'endterm', 'resources']:
        return {"success": False, "error": "Invalid item type"}, 400
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed"}, 500
        
    cur = conn.cursor()
    
    try:
        # Get all items for this course ordered by current sort_order
        cur.execute(f'SELECT id, sort_order FROM {item_type} WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
        items = cur.fetchall()
        
        # Find current item's position
        current_pos = None
        for i, (id_, sort_order) in enumerate(items):
            if id_ == item_id:
                current_pos = i
                break
        
        if current_pos is None:
            return {"success": False, "error": "Item not found"}, 404
        
        # Calculate new position
        if direction == 'up' and current_pos > 0:
            new_pos = current_pos - 1
        elif direction == 'down' and current_pos < len(items) - 1:
            new_pos = current_pos + 1
        else:
            return {"success": False, "error": "Cannot move in that direction"}, 400
        
        # Swap sort_order values
        current_item_id = items[current_pos][0]
        target_item_id = items[new_pos][0]
        
        # Update sort_order values
        cur.execute(f'UPDATE {item_type} SET sort_order = %s WHERE id = %s', (new_pos, current_item_id))
        cur.execute(f'UPDATE {item_type} SET sort_order = %s WHERE id = %s', (current_pos, target_item_id))
        
        conn.commit()

        return {"success": True}
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500
    finally:
        cur.close()
        conn.close()

# Admin - Edit item (PYQ/Note/Assignment/Resource)
@app.route('/admin/edit_item/<string:item_type>/<int:course_id>/<int:item_id>', methods=['GET', 'POST'])
def admin_edit_item(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('course_detail', course_id=course_id))
        
    cur = conn.cursor()

    if request.method == 'POST':
        new_title = request.form['title']
        new_link = request.form['link']

        if item_type in ['quiz1', 'quiz2', 'endterm', 'resources']:
            cur.execute(
                f'UPDATE {item_type} SET name=%s, yt_link=%s WHERE id=%s RETURNING sort_order, watch_count, COALESCE(is_highlighted, false)',
                (new_title, new_link, item_id)
            )
            cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after editing item
        return redirect(url_for('course_detail', course_id=course_id))

    # Fetch existing item
    if item_type in ['quiz1', 'quiz2', 'endterm', 'resources']:
        cur.execute(f'SELECT name, yt_link FROM {item_type} WHERE id=%s', (item_id,))
    
    item = cur.fetchone()
    cur.close()
    conn.close()

    if item:
        item_data = {
            'title': item[0],
            'link': item[1]
        }
        return render_template('admin_edit_pyq.html', item=item_data, item_type=item_type, course_id=course_id, item_id=item_id)
    else:
        return "Item not found"

# Admin delete item route
@app.route('/admin/delete_item/<string:item_type>/<int:course_id>/<int:item_id>', methods=['POST', 'GET'])
def admin_delete_item(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'GET':
        # Get item name for confirmation
        conn = get_db_connection()
        if not conn:
            return redirect(url_for('course_detail', course_id=course_id))
            
        cur = conn.cursor()
        
        if item_type in ['quiz1', 'quiz2', 'endterm', 'resources']:
            cur.execute(f'SELECT name FROM {item_type} WHERE id=%s', (item_id,))
        else:
            flash('Invalid item type.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('course_detail', course_id=course_id))
            
        item = cur.fetchone()
        cur.close()
        conn.close()
        
        if item:
            return render_template('confirm_delete.html', 
                                 item_type=item_type.rstrip('s'),  # Remove 's' from plural
                                 item_name=item[0],
                                 delete_url=url_for('admin_delete_item', item_type=item_type, course_id=course_id, item_id=item_id),
                                 cancel_url=url_for('course_detail', course_id=course_id))
        else:
            flash('Item not found.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))

    # POST request - actual deletion
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
        
    cur = conn.cursor()

    if item_type in ['quiz1', 'quiz2', 'endterm', 'resources']:
        cur.execute(f'DELETE FROM {item_type} WHERE id=%s', (item_id,))
    else:
        flash('Invalid item type.', 'error')
        cur.close()
        conn.close()
        return redirect(url_for('course_detail', course_id=course_id))

    conn.commit()
    cur.close()
    conn.close()
    backup_db()  # Backup database after deleting item
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

# Admin toggle highlight route
@app.route('/admin/toggle_highlight/<string:item_type>/<int:course_id>/<int:item_id>', methods=['POST'])
def admin_toggle_highlight(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return {"success": False, "error": "Unauthorized"}, 403
    
    if item_type not in ['quiz1', 'quiz2', 'endterm', 'resources']:
        return {"success": False, "error": "Invalid item type"}, 400
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed"}, 500
    
    try:
        cur = conn.cursor()
        # First, check if the column exists and get current value
        cur.execute(f'SELECT is_highlighted FROM {item_type} WHERE id=%s', (item_id,))
        result = cur.fetchone()
        
        if result is None:
            cur.close()
            conn.close()
            return {"success": False, "error": "Item not found"}, 404
        
        current_value = result[0] if result[0] is not None else False
        new_value = not current_value
        
        cur.execute(f'UPDATE {item_type} SET is_highlighted=%s WHERE id=%s', (new_value, item_id))
        conn.commit()

        cur.close()
        conn.close()
        
        return {"success": True, "is_highlighted": new_value}
    except Exception as e:
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}, 500

# Contact Us route
@app.route('/contact')
def contact_us():
    return render_template('contact_us.html')

# About Admin route
@app.route('/about')
def about_admin():
    # Check if profile picture exists
    profile_pic = None
    pic_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pic.jpg')
    if os.path.exists(pic_path):
        profile_pic = 'uploads/profile_pic.jpg'
    else:
        # Check for other extensions
        for ext in ['png', 'jpeg', 'gif']:
            pic_path = os.path.join(app.config['UPLOAD_FOLDER'], f'profile_pic.{ext}')
            if os.path.exists(pic_path):
                profile_pic = f'uploads/profile_pic.{ext}'
                break
    
    return render_template('about_admin.html', profile_pic=profile_pic)

# Upload profile picture route
@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))
    
    if 'profile_pic' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('about_admin'))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('about_admin'))
    
    if file and allowed_file(file.filename):
        # Remove existing profile pictures
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            old_pic = os.path.join(app.config['UPLOAD_FOLDER'], f'profile_pic.{ext}')
            if os.path.exists(old_pic):
                os.remove(old_pic)
        
        # Save new profile picture
        filename = f"profile_pic.{file.filename.rsplit('.', 1)[1].lower()}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Profile picture updated successfully!', 'success')
    else:
        flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF files only.', 'error')
    
    return redirect(url_for('about_admin'))

# Serve uploaded files
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Settings route
@app.route('/settings')
def settings():
    return render_template('settings.html')

# Favicon route
@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        # Return empty response if favicon doesn't exist
        return '', 204

# Error handlers
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500

# Main
if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # For production (gunicorn)
    init_db()
