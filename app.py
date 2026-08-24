from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, Response, jsonify, g
import psycopg2
import psycopg2.extras
import sqlite3
import os
import socket
import subprocess
import uuid
import hashlib
import math
import mimetypes
import secrets
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlencode
import requests

def load_local_env():
    """Load simple KEY=VALUE pairs from .env.local or .env for local runs."""
    for file_name in ('.env.local', '.env'):
        env_path = os.path.join(os.path.dirname(__file__), file_name)
        if not os.path.exists(env_path):
            continue
        try:
            with open(env_path, 'r', encoding='utf-8') as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as exc:
            print(f"Warning: could not read {file_name}: {exc}")

if not os.environ.get('RENDER'):
    load_local_env()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
RESOURCE_ALLOWED_EXTENSIONS = {'pdf', 'html', 'htm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
MAX_PENDING_RESOURCE_UPLOAD_BYTES = 5 * 1024 * 1024

# Google OAuth configuration. Add these on Render before enabling login.
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.environ.get('ADMIN_EMAILS', '').split(',')
    if email.strip()
}

# Resource ranking is intentionally cached for a short period. Feedback and
# view updates invalidate the relevant course immediately.
_resource_ranking_cache = {}
RESOURCE_RANKING_CACHE_SECONDS = 300
RESOURCE_RATING_COOLDOWN_HOURS = 6

# Supabase Storage configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '').strip()
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'resources').strip()
LOCAL_RESOURCE_UPLOADS = (
    os.environ.get('LOCAL_RESOURCE_UPLOADS', '').strip().lower() in ('1', 'true', 'yes')
    or not os.environ.get('RENDER')
)

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_supabase_public_base():
    if not SUPABASE_URL or not SUPABASE_STORAGE_BUCKET:
        return ''
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}"

def get_resource_content_type(filename, fallback):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.html', '.htm'):
        return 'text/html; charset=utf-8'
    if ext == '.pdf':
        return 'application/pdf'
    return fallback

def get_resource_content_disposition(filename):
    safe_name = secure_filename(filename)
    return f'inline; filename="{safe_name}"'

def uploaded_file_size(file_storage):
    if not file_storage or not getattr(file_storage, 'stream', None):
        return 0
    current_pos = file_storage.stream.tell()
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(current_pos)
    return size

def render_html_resource_preview(resource_link):
    if not resource_link:
        return None
    link = resource_link.strip()
    link_lower = link.lower()

    if link.startswith('/'):
        local_path = os.path.join(app.root_path, link.lstrip('/').replace('/', os.sep))
        if (link_lower.endswith('.html') or link_lower.endswith('.htm')) and os.path.exists(local_path):
            with open(local_path, 'rb') as handle:
                return Response(
                    handle.read(),
                    status=200,
                    content_type='text/html; charset=utf-8',
                    headers={'Content-Disposition': 'inline'}
                )
        return redirect(link)

    normalized_link = ensure_url_scheme(link)
    lower = normalized_link.lower()
    if lower.endswith('.html') or lower.endswith('.htm'):
        try:
            resp = requests.get(normalized_link, timeout=10)
            if resp.status_code == 200:
                return Response(
                    resp.content,
                    status=200,
                    content_type='text/html; charset=utf-8',
                    headers={'Content-Disposition': 'inline'}
                )
        except Exception as exc:
            print(f"Error fetching HTML preview: {exc}")
    return redirect(normalized_link)

def upload_resource_to_supabase(file_storage, folder='general_resources'):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        if not LOCAL_RESOURCE_UPLOADS:
            raise RuntimeError(
                'Supabase Storage is not configured. Set SUPABASE_URL and '
                'SUPABASE_SERVICE_KEY in Render environment variables.'
            )

        # Local development fallback. Render uses Supabase Storage because its
        # local filesystem is ephemeral and can be cleared on redeploy.
        safe_name = secure_filename(file_storage.filename)
        local_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(local_folder, exist_ok=True)
        local_name = f'{uuid.uuid4().hex}_{safe_name}'
        file_storage.save(os.path.join(local_folder, local_name))
        return f'/{app.config["UPLOAD_FOLDER"]}/{folder}/{local_name}'.replace('\\', '/')

    safe_name = secure_filename(file_storage.filename)
    stamp = int(datetime.utcnow().timestamp())
    unique = uuid.uuid4().hex
    object_name = f"{folder}/{unique}_{stamp}_{safe_name}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{object_name}"

    file_storage.stream.seek(0)
    content_type = get_resource_content_type(
        safe_name,
        file_storage.mimetype or 'application/octet-stream'
    )

    response = requests.post(
        upload_url,
        headers={
            'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
            'Content-Type': content_type,
            'Content-Disposition': get_resource_content_disposition(safe_name),
            'x-upsert': 'true'
        },
        data=file_storage.stream.read()
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")

    public_base = get_supabase_public_base()
    return f"{public_base}/{object_name}"

def extract_supabase_object_path(resource_link):
    public_base = get_supabase_public_base()
    if not public_base:
        return None
    if not resource_link or not resource_link.startswith(public_base + '/'):
        return None
    return resource_link.replace(public_base + '/', '', 1)

def delete_supabase_object(resource_link):
    object_path = extract_supabase_object_path(resource_link)
    if not object_path:
        return
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return

    delete_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{object_path}"
    response = requests.delete(
        delete_url,
        headers={
            'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
            'x-upsert': 'true'
        }
    )

    if response.status_code not in (200, 204):
        print(f"Warning: failed to delete Supabase object {object_path}: {response.status_code}")

def upload_file_path_to_supabase(file_path, object_name):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError('Supabase Storage is not configured')

    guessed_type, _ = mimetypes.guess_type(file_path)
    fallback_type = guessed_type or 'application/octet-stream'
    content_type = get_resource_content_type(os.path.basename(file_path), fallback_type)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{object_name}"

    with open(file_path, 'rb') as handle:
        response = requests.post(
            upload_url,
            headers={
                'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
                'Content-Type': content_type,
                'Content-Disposition': get_resource_content_disposition(os.path.basename(file_path)),
                'x-upsert': 'true'
            },
            data=handle.read()
        )

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")

    public_base = get_supabase_public_base()
    return f"{public_base}/{object_name}"

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

def anonymous_identity():
    """Return a lightweight login-free identity and a privacy-safe IP hash."""
    anonymous_id = request.cookies.get('mh_anon_id') or uuid.uuid4().hex
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    ip_hash = hashlib.sha256(f'{app.secret_key}:{ip}'.encode('utf-8')).hexdigest()
    return anonymous_id, ip_hash, not request.cookies.get('mh_anon_id')

def fetch_user_by_id(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''
            SELECT id, google_id, name, email, username, profile_picture, role, is_active
            FROM users
            WHERE id=%s AND is_active=TRUE
            ''',
            (user_id,)
        )
        user = cur.fetchone()
        cur.close()
        return dict(user) if user else None
    except Exception as exc:
        print(f'Error fetching current user: {exc}')
        return None
    finally:
        conn.close()

@app.before_request
def load_current_user():
    g.current_user = fetch_user_by_id(session.get('user_id'))
    if g.current_user and g.current_user.get('role') == 'admin':
        session['admin_mode'] = True

@app.context_processor
def inject_current_user():
    return {'current_user': getattr(g, 'current_user', None)}

def login_required(next_endpoint='general_resources_page'):
    if not getattr(g, 'current_user', None):
        flash('Please login with Google to continue.', 'error')
        return redirect(url_for('google_login', next=request.path or url_for(next_endpoint)))
    return None

def invalidate_resource_ranking(course_id=None):
    if course_id is None:
        _resource_ranking_cache.clear()
    else:
        _resource_ranking_cache.pop(course_id, None)

def wilson_score(positive, total, z=1.96):
    if not total:
        return 0.0
    n = float(total)
    p = float(positive) / n
    denominator = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denominator)

def resource_score(avg_rating, rating_count, helpful_yes, helpful_total, views, updated_at):
    """Return the normalized weighted recommendation score and components."""
    prior_rating = 4.0
    prior_count = 3.0
    bayesian = ((rating_count / (rating_count + prior_count)) * avg_rating +
                (prior_count / (rating_count + prior_count)) * prior_rating) / 5.0
    helpful = wilson_score(helpful_yes, helpful_total)
    if updated_at:
        age_days = max(0.0, (datetime.utcnow() - updated_at.replace(tzinfo=None)).total_seconds() / 86400)
        freshness = 1 / (1 + age_days / 180)
    else:
        freshness = 0.35
    view_score = math.log10(max(0, views) + 1) / 6.0
    score = 0.35 * bayesian + 0.30 * helpful + 0.25 * freshness + 0.10 * min(1.0, view_score)
    helpful_pct = (helpful_yes / helpful_total * 100) if helpful_total else 0
    return score, bayesian, helpful, freshness, helpful_pct

def general_resource_badge(resource, all_resources):
    """Return exactly one lightweight, data-driven badge for a resource."""
    rating_count, helpful_total = resource[9], resource[11]
    max_recent_views = max((item[18] for item in all_resources), default=0)
    if helpful_total >= 3 and resource[12] >= 80:
        return '🎯 Exam Favorite'
    if resource[18] >= 5 and resource[18] >= max_recent_views * 0.6:
        return '📈 Trending'
    if helpful_total >= 3 and resource[15] >= 0.55:
        return '🔥 Most Helpful'
    if rating_count >= 3 and resource[14] >= 0.78:
        return '⭐ Top Rated'
    return None

def sort_general_resources(resources, sort_key='recommended'):
    items = list(resources)
    if sort_key == 'top-rated':
        items.sort(key=lambda item: (item[14], item[9], item[0]), reverse=True)
    elif sort_key == 'most-helpful':
        items.sort(key=lambda item: (item[15], item[11], item[0]), reverse=True)
    elif sort_key == 'latest':
        items.sort(key=lambda item: (item[17] or datetime.min, item[0]), reverse=True)
    elif sort_key == 'most-viewed':
        items.sort(key=lambda item: (item[4] or 0, item[0]), reverse=True)
    else:
        items.sort(key=lambda item: (item[13], item[0]), reverse=True)
    return [item + (general_resource_badge(item, items),) for item in items]

def decorate_general_resources(rows):
    decorated = []
    for row in rows:
        avg_rating = float(row[8] or 0)
        rating_count = int(row[9] or 0)
        helpful_yes = int(row[10] or 0)
        helpful_total = int(row[11] or 0)
        score, bayesian, helpful, freshness, helpful_pct = resource_score(
            avg_rating, rating_count, helpful_yes, helpful_total,
            int(row[4] or 0), row[13]
        )
        helpful_pct = (float(row[12] or 0) / 4.0) * 100 if helpful_total else 0
        decorated.append(tuple(row[:8]) + (
            avg_rating, rating_count, helpful_yes, helpful_total, helpful_pct,
            score, bayesian, helpful, freshness, row[13], int(row[14] or 0), row[15]
        ))
    return decorated

def migrate_local_general_resources_to_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print('Supabase Storage not configured, skipping migration')
        return

    local_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'general_resources')
    if not os.path.isdir(local_dir):
        print('No local general_resources folder found, skipping migration')
        return

    conn = get_db_connection()
    if not conn:
        print('Database connection failed, skipping migration')
        return

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, resource_link FROM general_resources WHERE resource_link LIKE %s",
            ('/static/uploads/general_resources/%',)
        )
        rows = cur.fetchall()

        migrated = 0
        for resource_id, resource_link in rows:
            if not resource_link:
                continue
            file_name = resource_link.replace('/static/uploads/general_resources/', '', 1)
            local_path = os.path.join(local_dir, file_name)
            if not os.path.exists(local_path):
                continue

            object_name = f"general_resources/legacy_{resource_id}_{file_name}"
            try:
                public_url = upload_file_path_to_supabase(local_path, object_name)
            except Exception as exc:
                print(f"Migration failed for {file_name}: {exc}")
                continue

            cur.execute(
                'UPDATE general_resources SET resource_link=%s WHERE id=%s',
                (public_url, resource_id)
            )
            migrated += 1

        if migrated:
            conn.commit()
            print(f"Migrated {migrated} general_resources files to Supabase")
    except Exception as exc:
        conn.rollback()
        print(f"Migration error: {exc}")
    finally:
        conn.close()

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

def normalize_tags(raw_tags):
    if not raw_tags:
        return ''
    seen = set()
    normalized = []
    for tag in raw_tags.split(','):
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return ', '.join(normalized)

def fetch_general_resource_subjects(conn):
    subjects_by_program = {'diploma': [], 'degree': []}
    if not conn:
        return subjects_by_program

    try:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT id, name, program_type
            FROM general_resource_subjects
            ORDER BY sort_order, id
            '''
        )
        for subject_id, name, program_type in cur.fetchall():
            if program_type in subjects_by_program:
                subjects_by_program[program_type].append({'id': subject_id, 'name': name})
        cur.close()
    except Exception as exc:
        print(f"Error fetching resource subjects: {exc}")

    return subjects_by_program

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

        # Create 'general_resource_subjects' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resource_subjects (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                program_type TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create 'general_resources' table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resources (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                resource_link TEXT NOT NULL,
                program_type TEXT NOT NULL,
                subject_id INTEGER,
                tags TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS tags TEXT')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS subject_id INTEGER')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT TRUE')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS submitted_by INTEGER')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS approved_by INTEGER')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        cur.execute('ALTER TABLE general_resources ADD COLUMN IF NOT EXISTS source_submission_id INTEGER')
        cur.execute('UPDATE general_resources SET is_published=TRUE WHERE is_published IS NULL')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                google_id TEXT UNIQUE,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                profile_picture TEXT,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT')
        cur.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
            ON users (LOWER(username))
            WHERE username IS NOT NULL AND username <> ''
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS member_contributions (
                username TEXT PRIMARY KEY,
                contribution_count INTEGER NOT NULL DEFAULT 0 CHECK (contribution_count >= 0),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.executemany(
            '''
            INSERT INTO member_contributions (username, contribution_count)
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
            ''',
            [
                ('Anmol Kansal', 20),
                ('Ashish Maurya', 11),
                ('Optimus Prime', 9),
                ('Sumit Gupta', 5),
                ('Sanket Mishra', 3),
                ('Code Synth', 3),
                ('Abhay', 2),
                ('Alok Tripathi', 2),
                ('Kailash', 1),
                ('Kshitij', 1),
                ('Piush', 1),
                ('Piyush Duggal', 1),
                ('Prashasti Sarraf', 1),
                ('Vinil', 1)
            ]
        )

        cur.execute('''
            CREATE TABLE IF NOT EXISTS pending_general_resources (
                id SERIAL PRIMARY KEY,
                submitted_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                resource_link TEXT NOT NULL,
                program_type TEXT NOT NULL,
                subject_id INTEGER,
                description TEXT,
                tags TEXT,
                status TEXT DEFAULT 'pending',
                rejection_reason TEXT,
                reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_pending_general_resources_status ON pending_general_resources(status)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_pending_general_resources_user ON pending_general_resources(submitted_by)')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resource_feedback (
                id SERIAL PRIMARY KEY,
                resource_id INTEGER NOT NULL,
                anonymous_id TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                resource_link TEXT,
                resource_title TEXT,
                rating SMALLINT CHECK (rating BETWEEN 1 AND 5),
                helpful BOOLEAN,
                helpfulness SMALLINT CHECK (helpfulness BETWEEN 1 AND 4),
                review TEXT,
                review_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (resource_id, anonymous_id)
            )
        ''')
        cur.execute('ALTER TABLE general_resource_feedback ADD COLUMN IF NOT EXISTS review TEXT')
        cur.execute('ALTER TABLE general_resource_feedback ADD COLUMN IF NOT EXISTS helpfulness SMALLINT')
        cur.execute('ALTER TABLE general_resource_feedback ADD COLUMN IF NOT EXISTS review_tags TEXT')
        cur.execute('ALTER TABLE general_resource_feedback ADD COLUMN IF NOT EXISTS resource_link TEXT')
        cur.execute('ALTER TABLE general_resource_feedback ADD COLUMN IF NOT EXISTS resource_title TEXT')
        cur.execute('''
            UPDATE general_resource_feedback f
            SET resource_link = r.resource_link,
                resource_title = r.title
            FROM general_resources r
            WHERE f.resource_id = r.id
              AND (f.resource_link IS NULL OR f.resource_title IS NULL)
        ''')
        # Feedback must outlive resource deletions and backup restores. It is
        # intentionally not foreign-key cascaded; resource_link is the stable
        # fallback when a resource id changes after a restore.
        cur.execute('ALTER TABLE general_resource_feedback DROP CONSTRAINT IF EXISTS general_resource_feedback_resource_id_fkey')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_general_resource_feedback_resource ON general_resource_feedback(resource_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_general_resource_feedback_link ON general_resource_feedback(resource_link)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_general_resource_feedback_ip_resource ON general_resource_feedback(ip_hash, resource_id)')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resource_review_votes (
                id SERIAL PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES general_resource_feedback(id) ON DELETE CASCADE,
                anonymous_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (review_id, anonymous_id)
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_general_resource_review_votes_review ON general_resource_review_votes(review_id)')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS general_resource_reports (
                id SERIAL PRIMARY KEY,
                resource_id INTEGER NOT NULL REFERENCES general_resources(id) ON DELETE CASCADE,
                anonymous_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (resource_id, anonymous_id, issue_type)
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_general_resource_reports_resource ON general_resource_reports(resource_id)')

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
        tables = [
            'courses', 'quiz1', 'quiz2', 'endterm', 'resources',
            'users', 'general_resource_subjects', 'general_resources',
            'pending_general_resources', 'general_resource_feedback',
            'general_resource_review_votes', 'general_resource_reports',
            'extra_stuff', 'feedback', 'view_events'
        ]
        
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

def google_redirect_uri():
    configured = os.environ.get('GOOGLE_REDIRECT_URI', '').strip()
    if configured:
        return configured
    return url_for('google_callback', _external=True)

@app.route('/auth/google')
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google login is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on Render.', 'error')
        return redirect(url_for('general_resources_page'))

    next_url = request.values.get('next') or url_for('general_resources_page')
    state = secrets.token_urlsafe(24)
    session['google_oauth_state'] = state
    session['google_oauth_next'] = next_url
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': google_redirect_uri(),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account'
    }
    return redirect(f'{GOOGLE_AUTH_URL}?{urlencode(params)}')

@app.route('/auth/google/callback')
def google_callback():
    state = request.args.get('state', '')
    if not state or state != session.get('google_oauth_state'):
        flash('Google login session expired. Please try again.', 'error')
        return redirect(url_for('general_resources_page'))

    code = request.args.get('code')
    if not code:
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('general_resources_page'))

    try:
        token_response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                'code': code,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'redirect_uri': google_redirect_uri(),
                'grant_type': 'authorization_code'
            },
            timeout=10
        )
        token_response.raise_for_status()
        access_token = token_response.json().get('access_token')
        if not access_token:
            raise RuntimeError('Missing Google access token')

        user_response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        user_response.raise_for_status()
        profile = user_response.json()
        email = (profile.get('email') or '').strip().lower()
        google_id = profile.get('id')
        name = profile.get('name') or email.split('@')[0]
        picture = profile.get('picture')
        if not email or not google_id:
            raise RuntimeError('Google did not return a usable profile')

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed after Google login.', 'error')
            return redirect(url_for('general_resources_page'))

        try:
            role = 'admin' if email in ADMIN_EMAILS else 'user'
            cur = conn.cursor()
            cur.execute('SELECT id, role, username FROM users WHERE email=%s', (email,))
            existing = cur.fetchone()
            if existing:
                user_id, existing_role, username = existing
                final_role = existing_role or role
                if email in ADMIN_EMAILS:
                    final_role = 'admin'
                cur.execute(
                    '''
                    UPDATE users
                    SET google_id=%s, name=%s, profile_picture=%s, role=%s,
                        is_active=TRUE, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                    ''',
                    (google_id, name, picture, final_role, user_id)
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO users (google_id, name, email, profile_picture, role)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    ''',
                    (google_id, name, email, picture, role)
                )
                user_id = cur.fetchone()[0]
                final_role = role
                username = None
            conn.commit()
            cur.close()
        finally:
            conn.close()

        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['user_role'] = final_role
        if final_role == 'admin':
            session['admin_mode'] = True
        session.pop('google_oauth_state', None)
        next_url = session.pop('google_oauth_next', None) or url_for('general_resources_page')
        if not username:
            return redirect(url_for('set_username', next=next_url))
        flash('Logged in successfully.', 'success')
        return redirect(next_url)
    except Exception as exc:
        print(f'Google login error: {exc}')
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('general_resources_page'))

@app.route('/set-username', methods=['GET', 'POST'])
def set_username():
    if not getattr(g, 'current_user', None):
        return redirect(url_for('google_login', next=request.args.get('next') or url_for('general_resources_page')))

    next_url = request.values.get('next') or url_for('general_resources_page')
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = url_for('general_resources_page')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            flash('Please enter a username.', 'error')
            return render_template('set_username.html', username=username, next_url=next_url)

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed. Please try again.', 'error')
            return render_template('set_username.html', username=username, next_url=next_url)

        try:
            cur = conn.cursor()
            cur.execute(
                'UPDATE users SET username=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s',
                (username, g.current_user['id'])
            )
            conn.commit()
            cur.close()
            session['user_name'] = g.current_user['name']
            flash('Username saved successfully.', 'success')
            return redirect(next_url)
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('That username is already taken. Please choose another.', 'error')
        except Exception as exc:
            conn.rollback()
            print(f'Error saving username: {exc}')
            flash('Could not save your username. Please try again.', 'error')
        finally:
            conn.close()

        return render_template('set_username.html', username=username, next_url=next_url)

    return render_template('set_username.html', username=g.current_user.get('username') or '', next_url=next_url)

@app.route('/logout')
def user_logout():
    was_google_admin = session.get('user_role') == 'admin'
    for key in ['user_id', 'user_name', 'user_email', 'user_role', 'google_oauth_state', 'google_oauth_next']:
        session.pop(key, None)
    if session.get('admin_mode') and was_google_admin and not session.get('legacy_admin_mode'):
        session.pop('admin_mode', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('general_resources_page'))

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
    if getattr(g, 'current_user', None) and not g.current_user.get('username'):
        return redirect(url_for('set_username', next=request.full_path))

    sort_key = request.args.get('sort', 'recommended')
    if sort_key not in {'recommended', 'top-rated', 'most-helpful', 'latest', 'most-viewed'}:
        sort_key = 'recommended'
    conn = get_db_connection()
    reports = []
    if not conn:
        flash('Database connection failed', 'error')
        return render_template(
            'resources.html',
            diploma_resources=[],
            degree_resources=[],
            admin_mode=session.get('admin_mode', False),
            all_tags=[],
            resource_sort=sort_key,
            subjects_by_program={'diploma': [], 'degree': []},
            has_unassigned={'diploma': False, 'degree': False},
            reports=[],
            top_contributors=[]
        )

    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT username, contribution_count
            FROM member_contributions
            WHERE username IS NOT NULL AND username <> ''
            ORDER BY contribution_count DESC, LOWER(username)
            LIMIT 10
        ''')
        top_contributors = cur.fetchall()
        cache_key = 'general:diploma'
        diploma_cache = _resource_ranking_cache.get(cache_key)
        if diploma_cache and time.time() - diploma_cache['created'] < RESOURCE_RANKING_CACHE_SECONDS:
            diploma_resources = diploma_cache['resources']
        else:
            cur.execute('''
            SELECT gr.id,
                   gr.title,
                   gr.resource_link,
                   gr.program_type,
                   gr.watch_count,
                   gr.tags,
                   gr.subject_id,
                   s.name,
                   COALESCE(rf.avg_rating, 0), COALESCE(rf.rating_count, 0),
                   COALESCE(rf.helpful_yes, 0), COALESCE(rf.helpful_total, 0),
                     COALESCE(rf.helpful_avg, 0), gr.updated_at, COALESCE(rv.recent_views, 0),
                     u.username
            FROM general_resources gr
            LEFT JOIN general_resource_subjects s ON s.id = gr.subject_id
                 LEFT JOIN users u ON u.id = gr.submitted_by
            LEFT JOIN (
                SELECT resource_id, AVG(rating) FILTER (WHERE rating IS NOT NULL) AS avg_rating,
                       COUNT(rating) AS rating_count,
                       COUNT(*) FILTER (WHERE helpfulness >= 3) AS helpful_yes,
                       COUNT(helpfulness) AS helpful_total,
                       COALESCE(AVG(helpfulness), 0) AS helpful_avg
                FROM general_resource_feedback GROUP BY resource_id
            ) rf ON rf.resource_id = gr.id
            LEFT JOIN (
                SELECT content_id, COUNT(*) AS recent_views
                FROM view_events
                WHERE content_table='general_resources'
                  AND viewed_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                GROUP BY content_id
            ) rv ON rv.content_id = gr.id
            WHERE gr.program_type = %s
              AND COALESCE(gr.is_published, TRUE) = TRUE
            ORDER BY COALESCE(s.sort_order, 9999), COALESCE(s.name, ''), gr.sort_order, gr.id
        ''', ('diploma',))
            diploma_resources = decorate_general_resources(cur.fetchall())
            _resource_ranking_cache[cache_key] = {'created': time.time(), 'resources': diploma_resources}

        cache_key = 'general:degree'
        degree_cache = _resource_ranking_cache.get(cache_key)
        if degree_cache and time.time() - degree_cache['created'] < RESOURCE_RANKING_CACHE_SECONDS:
            degree_resources = degree_cache['resources']
        else:
            cur.execute('''
            SELECT gr.id,
                   gr.title,
                   gr.resource_link,
                   gr.program_type,
                   gr.watch_count,
                   gr.tags,
                   gr.subject_id,
                   s.name,
                   COALESCE(rf.avg_rating, 0), COALESCE(rf.rating_count, 0),
                   COALESCE(rf.helpful_yes, 0), COALESCE(rf.helpful_total, 0),
                     COALESCE(rf.helpful_avg, 0), gr.updated_at, COALESCE(rv.recent_views, 0),
                     u.username
            FROM general_resources gr
            LEFT JOIN general_resource_subjects s ON s.id = gr.subject_id
                 LEFT JOIN users u ON u.id = gr.submitted_by
            LEFT JOIN (
                SELECT resource_id, AVG(rating) FILTER (WHERE rating IS NOT NULL) AS avg_rating,
                       COUNT(rating) AS rating_count,
                       COUNT(*) FILTER (WHERE helpfulness >= 3) AS helpful_yes,
                       COUNT(helpfulness) AS helpful_total,
                       COALESCE(AVG(helpfulness), 0) AS helpful_avg
                FROM general_resource_feedback GROUP BY resource_id
            ) rf ON rf.resource_id = gr.id
            LEFT JOIN (
                SELECT content_id, COUNT(*) AS recent_views
                FROM view_events
                WHERE content_table='general_resources'
                  AND viewed_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                GROUP BY content_id
            ) rv ON rv.content_id = gr.id
            WHERE gr.program_type = %s
              AND COALESCE(gr.is_published, TRUE) = TRUE
            ORDER BY COALESCE(s.sort_order, 9999), COALESCE(s.name, ''), gr.sort_order, gr.id
        ''', ('degree',))
            degree_resources = decorate_general_resources(cur.fetchall())
            _resource_ranking_cache[cache_key] = {'created': time.time(), 'resources': degree_resources}

        diploma_resources = sort_general_resources(diploma_resources, sort_key)
        degree_resources = sort_general_resources(degree_resources, sort_key)

        subjects_by_program = fetch_general_resource_subjects(conn)
        if session.get('admin_mode', False):
            try:
                cur.execute('''
                    SELECT rr.id, rr.resource_id, COALESCE(gr.title, 'Deleted resource'),
                           rr.issue_type, rr.details, rr.anonymous_id, rr.created_at
                    FROM general_resource_reports rr
                    LEFT JOIN general_resources gr ON gr.id = rr.resource_id
                    ORDER BY rr.created_at DESC
                    LIMIT 100
                ''')
                reports = cur.fetchall()
            except Exception as report_error:
                print(f"Error fetching resource reports: {report_error}")
                reports = []
        cur.close()
    except Exception as e:
        print(f"Error fetching general resources: {e}")
        diploma_resources = []
        degree_resources = []
        subjects_by_program = {'diploma': [], 'degree': []}
        reports = []
        top_contributors = []
    finally:
        conn.close()

    tag_set = set()
    has_unassigned = {'diploma': False, 'degree': False}
    for resource in diploma_resources + degree_resources:
        tags_value = resource[5]
        if tags_value:
            for tag in tags_value.split(','):
                cleaned = tag.strip().lower()
                if cleaned:
                    tag_set.add(cleaned)
        program_key = resource[3]
        if program_key in has_unassigned and not resource[6]:
            has_unassigned[program_key] = True

    return render_template(
        'resources.html',
        diploma_resources=diploma_resources,
        degree_resources=degree_resources,
        admin_mode=session.get('admin_mode', False),
        all_tags=sorted(tag_set),
        resource_sort=sort_key,
        subjects_by_program=subjects_by_program,
        has_unassigned=has_unassigned,
        reports=reports,
        top_contributors=top_contributors
    )

@app.route('/admin/resource-subjects', methods=['GET', 'POST'])
def admin_resource_subjects():
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('general_resources_page'))

    if request.method == 'POST':
        subject_name = request.form.get('subject_name', '').strip()
        program_type = request.form.get('program_type', '').strip().lower()

        if not subject_name or program_type not in ['diploma', 'degree']:
            flash('Please provide a valid subject name and program type.', 'error')
            conn.close()
            return redirect(url_for('admin_resource_subjects'))

        try:
            cur = conn.cursor()
            cur.execute(
                '''
                SELECT id FROM general_resource_subjects
                WHERE program_type=%s AND LOWER(name)=LOWER(%s)
                LIMIT 1
                ''',
                (program_type, subject_name)
            )
            if cur.fetchone():
                flash('Subject already exists for this program.', 'error')
                cur.close()
                conn.close()
                return redirect(url_for('admin_resource_subjects'))

            cur.execute(
                'SELECT COALESCE(MAX(sort_order), -1) FROM general_resource_subjects WHERE program_type=%s',
                (program_type,)
            )
            next_order = cur.fetchone()[0] + 1

            cur.execute(
                '''
                INSERT INTO general_resource_subjects (name, program_type, sort_order)
                VALUES (%s, %s, %s)
                ''',
                (subject_name, program_type, next_order)
            )
            conn.commit()
            cur.close()
            backup_db()
            flash('Subject added successfully!', 'success')
        except Exception as exc:
            conn.rollback()
            flash(f'Failed to add subject: {exc}', 'error')
        finally:
            conn.close()

        return redirect(url_for('admin_resource_subjects'))

    subjects_by_program = fetch_general_resource_subjects(conn)
    conn.close()
    return render_template(
        'admin_resource_subjects.html',
        subjects_by_program=subjects_by_program,
        admin_mode=session.get('admin_mode', False)
    )

@app.route('/admin/resource-subjects/delete/<int:subject_id>', methods=['POST'])
def admin_delete_resource_subject(subject_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin_resource_subjects'))

    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT COUNT(*) FROM general_resources WHERE subject_id=%s',
            (subject_id,)
        )
        if cur.fetchone()[0] > 0:
            flash('Move or delete resources under this subject first.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('admin_resource_subjects'))

        cur.execute('DELETE FROM general_resource_subjects WHERE id=%s', (subject_id,))
        if cur.rowcount == 0:
            flash('Subject not found.', 'error')
        else:
            conn.commit()
            backup_db()
            flash('Subject deleted successfully.', 'success')
        cur.close()
    except Exception as exc:
        conn.rollback()
        flash(f'Failed to delete subject: {exc}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_resource_subjects'))

@app.route('/admin/resources/add', methods=['GET', 'POST'])
def admin_add_general_resource():
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        program_type = request.form.get('program_type', '').strip().lower()
        subject_id_raw = request.form.get('subject_id', '').strip()
        resource_link = request.form.get('resource_link', '').strip()
        raw_tags = request.form.get('tags', '').strip()
        pdf_file = request.files.get('resource_pdf')

        if not title or program_type not in ['diploma', 'degree']:
            flash('Please provide a valid title and program type.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        if not subject_id_raw:
            flash('Please select a subject first.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        final_link = None
        try:
            subject_id = int(subject_id_raw)
        except ValueError:
            flash('Invalid subject selected.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        if pdf_file and pdf_file.filename:
            if not allowed_resource_file(pdf_file.filename):
                flash('Only PDF or HTML uploads are allowed.', 'error')
                return redirect(url_for('admin_add_general_resource'))

            try:
                final_link = upload_resource_to_supabase(pdf_file, folder='general_resources')
            except Exception as exc:
                flash(f'Failed to upload file: {exc}', 'error')
                return redirect(url_for('admin_add_general_resource'))
        elif resource_link:
            if resource_link.startswith('/'):
                final_link = resource_link
            else:
                final_link = ensure_url_scheme(resource_link)
        else:
            flash('Please add either a direct link or a PDF/HTML file.', 'error')
            return redirect(url_for('admin_add_general_resource'))

        tags_value = normalize_tags(raw_tags)

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('admin_add_general_resource'))

        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT id FROM general_resource_subjects WHERE id=%s AND program_type=%s',
                (subject_id, program_type)
            )
            if not cur.fetchone():
                flash('Selected subject is not valid for this program.', 'error')
                cur.close()
                conn.close()
                return redirect(url_for('admin_add_general_resource'))

            cur.execute(
                '''
                SELECT id FROM general_resources
                WHERE program_type=%s
                  AND subject_id=%s
                  AND (LOWER(title)=LOWER(%s) OR resource_link=%s)
                LIMIT 1
                ''',
                (program_type, subject_id, title, final_link)
            )
            if cur.fetchone():
                flash('Duplicate resource detected (same title or link).', 'error')
                cur.close()
                conn.close()
                return redirect(url_for('admin_add_general_resource'))

            cur.execute(
                'SELECT COALESCE(MAX(sort_order), -1) FROM general_resources WHERE program_type=%s AND subject_id=%s',
                (program_type, subject_id)
            )
            next_order = cur.fetchone()[0] + 1
            cur.execute(
                '''
                INSERT INTO general_resources
                    (title, resource_link, program_type, subject_id, tags, sort_order,
                     is_published, approved_by, approved_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
                ''',
                (
                    title, final_link, program_type, subject_id, tags_value,
                    next_order, g.current_user['id'] if getattr(g, 'current_user', None) else None
                )
            )
            conn.commit()
            cur.close()
            backup_db()
            # The general-resources page caches its ranked lists for a few
            # minutes. Clear that cache immediately after a successful insert
            # so the new item is visible on the redirect right away.
            invalidate_resource_ranking(f'general:{program_type}')
            flash('General resource added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed to add resource: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    subjects_by_program = fetch_general_resource_subjects(conn) if conn else {'diploma': [], 'degree': []}
    if conn:
        conn.close()
    return render_template('admin_add_general_resource.html', subjects_by_program=subjects_by_program)

@app.route('/resources/submit', methods=['GET', 'POST'])
def submit_general_resource():
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        program_type = request.form.get('program_type', '').strip().lower()
        subject_id_raw = request.form.get('subject_id', '').strip()
        resource_link = request.form.get('resource_link', '').strip()
        description = request.form.get('description', '').strip()
        raw_tags = request.form.get('tags', '').strip()
        pdf_file = request.files.get('resource_pdf')

        if not title or program_type not in ['diploma', 'degree']:
            flash('Please provide a valid title and program type.', 'error')
            return redirect(url_for('submit_general_resource'))

        if not subject_id_raw:
            flash('Please select a subject first.', 'error')
            return redirect(url_for('submit_general_resource'))

        try:
            subject_id = int(subject_id_raw)
        except ValueError:
            flash('Invalid subject selected.', 'error')
            return redirect(url_for('submit_general_resource'))

        final_link = None
        if pdf_file and pdf_file.filename:
            if not allowed_resource_file(pdf_file.filename):
                flash('Only PDF or HTML uploads are allowed.', 'error')
                return redirect(url_for('submit_general_resource'))
            if uploaded_file_size(pdf_file) > MAX_PENDING_RESOURCE_UPLOAD_BYTES:
                flash('Files above 5 MB are not allowed here. Please upload the file to Google Drive and submit the Drive link instead.', 'error')
                return redirect(url_for('submit_general_resource'))
            try:
                final_link = upload_resource_to_supabase(pdf_file, folder='pending_general_resources')
            except Exception as exc:
                flash(f'Failed to upload file: {exc}', 'error')
                return redirect(url_for('submit_general_resource'))
        elif resource_link:
            final_link = resource_link if resource_link.startswith('/') else ensure_url_scheme(resource_link)
        else:
            flash('Please add either a direct link or a PDF/HTML file.', 'error')
            return redirect(url_for('submit_general_resource'))

        tags_value = normalize_tags(raw_tags)
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('submit_general_resource'))

        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT id FROM general_resource_subjects WHERE id=%s AND program_type=%s',
                (subject_id, program_type)
            )
            if not cur.fetchone():
                flash('Selected subject is not valid for this program.', 'error')
                cur.close()
                conn.close()
                return redirect(url_for('submit_general_resource'))

            cur.execute(
                '''
                SELECT id FROM pending_general_resources
                WHERE submitted_by=%s
                  AND status='pending'
                  AND (LOWER(title)=LOWER(%s) OR resource_link=%s)
                LIMIT 1
                ''',
                (g.current_user['id'], title, final_link)
            )
            if cur.fetchone():
                flash('You already have a pending submission with the same title or link.', 'error')
                cur.close()
                conn.close()
                return redirect(url_for('submit_general_resource'))

            cur.execute(
                '''
                INSERT INTO pending_general_resources
                    (submitted_by, title, resource_link, program_type, subject_id, description, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (g.current_user['id'], title, final_link, program_type, subject_id, description, tags_value)
            )
            conn.commit()
            cur.close()
            backup_db()
            flash('Resource submitted for admin approval.', 'success')
            return redirect(url_for('submit_general_resource'))
        except Exception as exc:
            conn.rollback()
            flash(f'Failed to submit resource: {exc}', 'error')
        finally:
            conn.close()

        return redirect(url_for('submit_general_resource'))

    conn = get_db_connection()
    subjects_by_program = fetch_general_resource_subjects(conn) if conn else {'diploma': [], 'degree': []}
    submissions = []
    submission_stats = {'total': 0, 'approved': 0, 'pending': 0, 'rejected': 0}
    if conn:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                '''
                SELECT p.id, p.title, p.resource_link, p.program_type, p.description,
                       p.tags, p.status, p.rejection_reason, p.created_at, p.reviewed_at,
                       s.name AS subject_name
                FROM pending_general_resources p
                LEFT JOIN general_resource_subjects s ON s.id = p.subject_id
                WHERE p.submitted_by=%s
                ORDER BY p.created_at DESC
                ''',
                (g.current_user['id'],)
            )
            submissions = [dict(row) for row in cur.fetchall()]
            cur.execute(
                '''
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='approved') AS approved,
                    COUNT(*) FILTER (WHERE status='pending') AS pending,
                    COUNT(*) FILTER (WHERE status='rejected') AS rejected
                FROM pending_general_resources
                WHERE submitted_by=%s
                ''',
                (g.current_user['id'],)
            )
            row = cur.fetchone()
            if row:
                submission_stats = {
                    'total': int(row['total'] or 0),
                    'approved': int(row['approved'] or 0),
                    'pending': int(row['pending'] or 0),
                    'rejected': int(row['rejected'] or 0)
                }
            cur.close()
        except Exception as exc:
            print(f'Error loading submission dashboard: {exc}')
            flash('Failed to load your submission history.', 'error')
        finally:
            conn.close()
    return render_template(
        'submit_general_resource.html',
        subjects_by_program=subjects_by_program,
        submissions=submissions,
        submission_stats=submission_stats
    )

@app.route('/admin/resources/submissions/<int:submission_id>/preview')
def admin_preview_resource_submission(submission_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin_pending_resource_submissions'))

    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT resource_link FROM pending_general_resources WHERE id=%s',
            (submission_id,)
        )
        row = cur.fetchone()
        cur.close()
        if not row or not row[0]:
            flash('Submission preview link not found.', 'error')
            return redirect(url_for('admin_pending_resource_submissions'))
        return render_html_resource_preview(row[0])
    except Exception as exc:
        print(f'Error previewing submission: {exc}')
        flash('Could not preview this submission.', 'error')
        return redirect(url_for('admin_pending_resource_submissions'))
    finally:
        conn.close()

@app.route('/my-submissions')
def my_resource_submissions():
    return redirect(url_for('submit_general_resource'))

@app.route('/admin/resources/submissions')
def admin_pending_resource_submissions():
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    submissions = []
    if not conn:
        flash('Database connection failed', 'error')
    else:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                '''
                SELECT p.id, p.title, p.resource_link, p.program_type, p.description,
                       p.tags, p.status, p.rejection_reason, p.created_at, p.reviewed_at,
                       s.name AS subject_name, u.name AS submitter_name, u.email AS submitter_email
                FROM pending_general_resources p
                JOIN users u ON u.id = p.submitted_by
                LEFT JOIN general_resource_subjects s ON s.id = p.subject_id
                ORDER BY
                    CASE p.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
                    p.created_at DESC
                LIMIT 200
                '''
            )
            submissions = [dict(row) for row in cur.fetchall()]
            cur.close()
        except Exception as exc:
            print(f'Error fetching pending resources: {exc}')
            flash('Failed to load pending submissions.', 'error')
        finally:
            conn.close()

    return render_template('admin_pending_resources.html', submissions=submissions)

@app.route('/admin/resources/submissions/<int:submission_id>/approve', methods=['POST'])
def admin_approve_resource_submission(submission_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin_pending_resource_submissions'))

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''
            SELECT * FROM pending_general_resources
            WHERE id=%s AND status='pending'
            FOR UPDATE
            ''',
            (submission_id,)
        )
        submission = cur.fetchone()
        if not submission:
            flash('Submission not found or already reviewed.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('admin_pending_resource_submissions'))

        cur.execute(
            '''
            SELECT id FROM general_resources
            WHERE program_type=%s
              AND subject_id=%s
              AND (LOWER(title)=LOWER(%s) OR resource_link=%s)
            LIMIT 1
            ''',
            (submission['program_type'], submission['subject_id'], submission['title'], submission['resource_link'])
        )
        if cur.fetchone():
            flash('Duplicate public resource detected. Reject it or edit existing resource first.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('admin_pending_resource_submissions'))

        cur.execute(
            'SELECT COALESCE(MAX(sort_order), -1) AS next_base FROM general_resources WHERE program_type=%s AND subject_id=%s',
            (submission['program_type'], submission['subject_id'])
        )
        next_order = cur.fetchone()['next_base'] + 1
        reviewer_id = g.current_user['id'] if getattr(g, 'current_user', None) else None
        cur.execute(
            '''
            INSERT INTO general_resources
                (title, resource_link, program_type, subject_id, tags, sort_order,
                 is_published, submitted_by, approved_by, approved_at, source_submission_id)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s, CURRENT_TIMESTAMP, %s)
            ''',
            (
                submission['title'], submission['resource_link'], submission['program_type'],
                submission['subject_id'], submission['tags'], next_order,
                submission['submitted_by'], reviewer_id, submission['id']
            )
        )
        cur.execute(
            '''
            UPDATE pending_general_resources
            SET status='approved', reviewed_by=%s, reviewed_at=CURRENT_TIMESTAMP,
                rejection_reason=NULL, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            ''',
            (reviewer_id, submission_id)
        )
        conn.commit()
        cur.close()
        invalidate_resource_ranking(f"general:{submission['program_type']}")
        backup_db()
        flash('Submission approved and published.', 'success')
    except Exception as exc:
        conn.rollback()
        flash(f'Failed to approve submission: {exc}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_pending_resource_submissions'))

@app.route('/admin/resources/submissions/<int:submission_id>/reject', methods=['POST'])
def admin_reject_resource_submission(submission_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('Please add a rejection reason.', 'error')
        return redirect(url_for('admin_pending_resource_submissions'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin_pending_resource_submissions'))

    try:
        reviewer_id = g.current_user['id'] if getattr(g, 'current_user', None) else None
        cur = conn.cursor()
        cur.execute(
            '''
            UPDATE pending_general_resources
            SET status='rejected', rejection_reason=%s, reviewed_by=%s,
                reviewed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status='pending'
            ''',
            (reason, reviewer_id, submission_id)
        )
        if cur.rowcount == 0:
            flash('Submission not found or already reviewed.', 'error')
        else:
            conn.commit()
            backup_db()
            flash('Submission rejected with reason.', 'success')
        cur.close()
    except Exception as exc:
        conn.rollback()
        flash(f'Failed to reject submission: {exc}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_pending_resource_submissions'))

@app.route('/admin/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
def admin_edit_general_resource(resource_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('general_resources_page'))

    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT title, resource_link, program_type, tags, subject_id FROM general_resources WHERE id=%s',
            (resource_id,)
        )
        resource = cur.fetchone()

        if resource is None:
            flash('Resource not found.', 'error')
            cur.close()
            return redirect(url_for('general_resources_page'))

        existing_title, existing_link, existing_program, existing_tags, existing_subject_id = resource

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            program_type = request.form.get('program_type', '').strip().lower()
            subject_id_raw = request.form.get('subject_id', '').strip()
            resource_link = request.form.get('resource_link', '').strip()
            raw_tags = request.form.get('tags', '').strip()
            pdf_file = request.files.get('resource_pdf')

            if not title or program_type not in ['diploma', 'degree']:
                flash('Please provide a valid title and program type.', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            if not subject_id_raw:
                flash('Please select a subject first.', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            try:
                subject_id = int(subject_id_raw)
            except ValueError:
                flash('Invalid subject selected.', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            final_link = existing_link
            tags_value = normalize_tags(raw_tags)

            if pdf_file and pdf_file.filename:
                if not allowed_resource_file(pdf_file.filename):
                    flash('Only PDF or HTML uploads are allowed.', 'error')
                    return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

                try:
                    final_link = upload_resource_to_supabase(pdf_file, folder='general_resources')
                except Exception as exc:
                    flash(f'Failed to upload file: {exc}', 'error')
                    return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))
            elif resource_link:
                if resource_link.startswith('/'):
                    final_link = resource_link
                else:
                    final_link = ensure_url_scheme(resource_link)
            else:
                flash('Please add either a direct link or a PDF/HTML file.', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            cur.execute(
                '''
                SELECT id FROM general_resources
                WHERE program_type=%s
                  AND id<>%s
                  AND subject_id=%s
                  AND (LOWER(title)=LOWER(%s) OR resource_link=%s)
                LIMIT 1
                ''',
                (program_type, resource_id, subject_id, title, final_link)
            )
            if cur.fetchone():
                flash('Duplicate resource detected (same title or link).', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            cur.execute(
                'SELECT id FROM general_resource_subjects WHERE id=%s AND program_type=%s',
                (subject_id, program_type)
            )
            if not cur.fetchone():
                flash('Selected subject is not valid for this program.', 'error')
                return redirect(url_for('admin_edit_general_resource', resource_id=resource_id))

            new_sort_order = None
            if program_type != existing_program or subject_id != existing_subject_id:
                cur.execute(
                    'SELECT COALESCE(MAX(sort_order), -1) FROM general_resources WHERE program_type=%s AND subject_id=%s',
                    (program_type, subject_id)
                )
                new_sort_order = cur.fetchone()[0] + 1

            if new_sort_order is None:
                cur.execute(
                    '''
                    UPDATE general_resources
                    SET title=%s, resource_link=%s, program_type=%s, subject_id=%s, tags=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                    ''',
                    (title, final_link, program_type, subject_id, tags_value, resource_id)
                )
            else:
                cur.execute(
                    '''
                    UPDATE general_resources
                    SET title=%s, resource_link=%s, program_type=%s, subject_id=%s, tags=%s, sort_order=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                    ''',
                    (title, final_link, program_type, subject_id, tags_value, new_sort_order, resource_id)
                )

            conn.commit()
            invalidate_resource_ranking(f'general:{existing_program}')
            invalidate_resource_ranking(f'general:{program_type}')

            static_prefix = '/static/uploads/general_resources/'
            if existing_link and existing_link != final_link and existing_link.startswith(static_prefix):
                file_name = existing_link.replace(static_prefix, '', 1)
                file_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'general_resources', file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            if existing_link and existing_link != final_link:
                delete_supabase_object(existing_link)

            backup_db()
            flash('General resource updated successfully!', 'success')
            return redirect(url_for('general_resources_page'))

        resource_data = {
            'title': existing_title,
            'resource_link': existing_link,
            'program_type': existing_program,
            'tags': existing_tags or '',
            'subject_id': existing_subject_id
        }
        subjects_by_program = fetch_general_resource_subjects(conn)
        return render_template(
            'admin_edit_general_resource.html',
            resource=resource_data,
            resource_id=resource_id,
            subjects_by_program=subjects_by_program
        )
    except Exception as e:
        conn.rollback()
        flash(f'Failed to update resource: {e}', 'error')
        return redirect(url_for('general_resources_page'))
    finally:
        conn.close()

@app.route('/admin/resources/move/<int:resource_id>/<string:direction>', methods=['POST'])
def admin_move_general_resource(resource_id, direction):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    if direction not in ['up', 'down']:
        flash('Invalid move direction.', 'error')
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('general_resources_page'))

    try:
        cur = conn.cursor()
        cur.execute('SELECT program_type FROM general_resources WHERE id=%s', (resource_id,))
        row = cur.fetchone()

        if row is None:
            flash('Resource not found.', 'error')
            cur.close()
            return redirect(url_for('general_resources_page'))

        program_type = row[0]
        cur.execute(
            '''
            SELECT id FROM general_resources
            WHERE program_type=%s
            ORDER BY sort_order, id
            ''',
            (program_type,)
        )
        items = [item[0] for item in cur.fetchall()]

        if resource_id not in items:
            flash('Resource not found.', 'error')
            cur.close()
            return redirect(url_for('general_resources_page'))

        current_pos = items.index(resource_id)
        if direction == 'up' and current_pos > 0:
            new_pos = current_pos - 1
        elif direction == 'down' and current_pos < len(items) - 1:
            new_pos = current_pos + 1
        else:
            cur.close()
            return redirect(url_for('general_resources_page'))

        items[current_pos], items[new_pos] = items[new_pos], items[current_pos]
        for idx, item_id in enumerate(items):
            cur.execute('UPDATE general_resources SET sort_order=%s WHERE id=%s', (idx, item_id))

        conn.commit()
        cur.close()
        invalidate_resource_ranking(f'general:{program_type}')
        backup_db()
        return redirect(url_for('general_resources_page'))
    except Exception as e:
        conn.rollback()
        flash(f'Failed to move resource: {e}', 'error')
        return redirect(url_for('general_resources_page'))
    finally:
        conn.close()

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
        cur.execute(
            'SELECT resource_link, program_type FROM general_resources WHERE id=%s',
            (resource_id,)
        )
        resource = cur.fetchone()

        if resource is None:
            flash('Resource not found.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('general_resources_page'))

        resource_link, program_type = resource
        cur.execute('DELETE FROM general_resources WHERE id=%s', (resource_id,))
        conn.commit()
        cur.close()
        invalidate_resource_ranking(f'general:{program_type}')

        static_prefix = '/static/uploads/general_resources/'
        if resource_link and resource_link.startswith(static_prefix):
            file_name = resource_link.replace(static_prefix, '', 1)
            file_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'general_resources', file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
        if resource_link:
            delete_supabase_object(resource_link)

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
            'UPDATE general_resources SET watch_count = watch_count + 1 WHERE id=%s RETURNING resource_link, program_type',
            (resource_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()

        if not row or not row[0]:
            return "Resource link not found"

        link = row[0].strip()
        invalidate_resource_ranking(f'general:{row[1]}')
        log_view_event('general_resources', resource_id, None)

        return render_html_resource_preview(link)
    except Exception:
        return "Resource link not found"
    finally:
        conn.close()

@app.route('/api/general-resources/<int:resource_id>/feedback', methods=['POST'])
def submit_general_resource_feedback(resource_id):
    data = request.get_json(silent=True) or {}
    rating_provided = 'rating' in data
    helpfulness_provided = 'helpfulness' in data
    review_provided = 'review' in data
    tags_provided = 'review_tags' in data
    rating = data.get('rating')
    helpful = data.get('helpful')
    helpfulness = data.get('helpfulness')
    review = (data.get('review') or '').strip()
    allowed_review_tags = {
        'Easy to understand', 'Complete syllabus', 'Good for revision',
        'Good examples', 'Outdated', 'Missing topics'
    }
    review_tags = [tag for tag in (data.get('review_tags') or []) if tag in allowed_review_tags]
    try:
        rating = int(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None
    if rating is not None and rating not in range(1, 6):
        return {'success': False, 'error': 'Rating must be between 1 and 5.'}, 400
    if helpful is not None and not isinstance(helpful, bool):
        return {'success': False, 'error': 'Helpful vote must be yes or no.'}, 400
    try:
        helpfulness = int(helpfulness) if helpfulness is not None else None
    except (TypeError, ValueError):
        helpfulness = None
    if helpfulness is not None and helpfulness not in range(1, 5):
        return {'success': False, 'error': 'Please choose one of the four helpfulness levels.'}, 400
    if len(review) > 500:
        return {'success': False, 'error': 'Review must be 500 characters or less.'}, 400
    if (rating is None and helpful is None and helpfulness is None and not review
            and not review_tags and not review_provided and not tags_provided):
        return {'success': False, 'error': 'Please add a rating, helpful vote, or review.'}, 400

    anonymous_id, ip_hash, needs_cookie = anonymous_identity()
    conn = get_db_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed.'}, 500
    cur = conn.cursor()
    try:
        cur.execute('SELECT program_type, resource_link, title FROM general_resources WHERE id=%s', (resource_id,))
        resource = cur.fetchone()
        if not resource:
            return {'success': False, 'error': 'Resource not found.'}, 404
        cur.execute('''
            SELECT rating, helpfulness, updated_at FROM general_resource_feedback
            WHERE (resource_id=%s OR resource_link=%s)
              AND (anonymous_id=%s OR ip_hash=%s)
            ORDER BY updated_at DESC LIMIT 1
        ''', (resource_id, resource[1], anonymous_id, ip_hash))
        previous = cur.fetchone()
        rating_changed = bool(previous and rating_provided and rating is not None and previous[0] != rating)
        helpfulness_changed = bool(previous and helpfulness_provided and helpfulness is not None and previous[1] != helpfulness)
        if previous and previous[2] and (rating_changed or helpfulness_changed):
            elapsed = datetime.utcnow() - previous[2].replace(tzinfo=None)
            cooldown = timedelta(hours=RESOURCE_RATING_COOLDOWN_HOURS)
            if elapsed < cooldown:
                remaining = max(1, math.ceil((cooldown - elapsed).total_seconds() / 3600))
                return {'success': False, 'error': f'You can rate this resource again in about {remaining} hour(s).'}, 429

        cur.execute('''
            INSERT INTO general_resource_feedback (resource_id, anonymous_id, ip_hash, resource_link, resource_title, rating, helpful, helpfulness, review, review_tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (resource_id, anonymous_id) DO UPDATE SET
                resource_link = EXCLUDED.resource_link,
                resource_title = EXCLUDED.resource_title,
                rating = COALESCE(EXCLUDED.rating, general_resource_feedback.rating),
                helpful = COALESCE(EXCLUDED.helpful, general_resource_feedback.helpful),
                helpfulness = COALESCE(EXCLUDED.helpfulness, general_resource_feedback.helpfulness),
                review = COALESCE(EXCLUDED.review, general_resource_feedback.review),
                review_tags = COALESCE(EXCLUDED.review_tags, general_resource_feedback.review_tags),
                ip_hash = EXCLUDED.ip_hash,
                updated_at = CURRENT_TIMESTAMP
        ''', (
            resource_id, anonymous_id, ip_hash, resource[1], resource[2], rating, helpful,
            helpfulness, review if review_provided else None,
            ','.join(review_tags) if tags_provided else None
        ))
        conn.commit()
        invalidate_resource_ranking(f'general:{resource[0]}')
        response = jsonify({'success': True, 'message': 'Feedback updated successfully.' if previous else 'Thanks for your feedback!'})
        if needs_cookie:
            response.set_cookie('mh_anon_id', anonymous_id, max_age=60 * 60 * 24 * 365,
                               httponly=True, samesite='Lax', secure=request.is_secure)
        return response
    except Exception as exc:
        conn.rollback()
        print(f'Error saving general resource feedback: {exc}')
        return {'success': False, 'error': 'Could not save feedback.'}, 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/general-resources/<int:resource_id>/reviews')
def get_general_resource_reviews(resource_id):
    anonymous_id, _, _ = anonymous_identity()
    conn = get_db_connection()
    if not conn:
        return {'reviews': []}
    try:
        cur = conn.cursor()
        cur.execute('SELECT resource_link FROM general_resources WHERE id=%s', (resource_id,))
        resource = cur.fetchone()
        resource_link = resource[0] if resource else None
        cur.execute('''
            SELECT f.id, f.review, f.review_tags, f.updated_at,
                   (SELECT COUNT(*) FROM general_resource_review_votes v WHERE v.review_id=f.id) AS helpful_count,
                   EXISTS(
                       SELECT 1 FROM general_resource_review_votes v2
                       WHERE v2.review_id=f.id AND v2.anonymous_id=%s
                   ) AS viewer_helpful
            FROM general_resource_feedback f
            WHERE (f.resource_id=%s OR (%s IS NOT NULL AND f.resource_link=%s))
              AND f.review IS NOT NULL AND BTRIM(f.review) <> ''
            ORDER BY helpful_count DESC, f.updated_at DESC
            LIMIT 5
        ''', (anonymous_id, resource_id, resource_link, resource_link))
        reviews = [
            {'id': row[0], 'review': row[1], 'tags': row[2].split(',') if row[2] else [],
             'date': row[3].strftime('%d %b %Y') if row[3] else '',
             'helpfulCount': row[4] or 0, 'viewerHelpful': bool(row[5])}
            for row in cur.fetchall()
        ]
        cur.execute('''
            SELECT rating, helpfulness, review, review_tags
            FROM general_resource_feedback
            WHERE (resource_id=%s OR (%s IS NOT NULL AND resource_link=%s))
              AND anonymous_id=%s
            ORDER BY updated_at DESC LIMIT 1
        ''', (resource_id, resource_link, resource_link, anonymous_id))
        mine = cur.fetchone()
        return {
            'reviews': reviews,
            'mine': ({
                'rating': mine[0], 'helpfulness': mine[1], 'review': mine[2] or '',
                'tags': mine[3].split(',') if mine[3] else []
            } if mine else None)
        }
    except Exception as exc:
        print(f'Error fetching general resource reviews: {exc}')
        return {'reviews': []}
    finally:
        conn.close()

@app.route('/api/general-resources/<int:resource_id>/reviews/<int:review_id>/helpful', methods=['POST'])
def vote_general_resource_review_helpful(resource_id, review_id):
    anonymous_id, _, needs_cookie = anonymous_identity()
    conn = get_db_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed.'}, 500
    try:
        cur = conn.cursor()
        cur.execute('SELECT resource_link FROM general_resources WHERE id=%s', (resource_id,))
        resource = cur.fetchone()
        resource_link = resource[0] if resource else None
        cur.execute('''
            SELECT f.id FROM general_resource_feedback f
            WHERE f.id=%s
              AND (f.resource_id=%s OR (%s IS NOT NULL AND f.resource_link=%s))
              AND f.review IS NOT NULL AND BTRIM(f.review) <> ''
        ''', (review_id, resource_id, resource_link, resource_link))
        if not cur.fetchone():
            return {'success': False, 'error': 'Review not found.'}, 404
        cur.execute('''
            SELECT id FROM general_resource_review_votes
            WHERE review_id=%s AND anonymous_id=%s
        ''', (review_id, anonymous_id))
        existing = cur.fetchone()
        if existing:
            cur.execute('DELETE FROM general_resource_review_votes WHERE id=%s', (existing[0],))
            voted = False
        else:
            cur.execute('''
                INSERT INTO general_resource_review_votes (review_id, anonymous_id)
                VALUES (%s, %s) ON CONFLICT (review_id, anonymous_id) DO NOTHING
            ''', (review_id, anonymous_id))
            voted = True
        cur.execute('SELECT COUNT(*) FROM general_resource_review_votes WHERE review_id=%s', (review_id,))
        count = cur.fetchone()[0]
        conn.commit()
        response = jsonify({'success': True, 'helpfulCount': count, 'viewerHelpful': voted})
        if needs_cookie:
            response.set_cookie('mh_anon_id', anonymous_id, max_age=60 * 60 * 24 * 365,
                                httponly=True, samesite='Lax', secure=request.is_secure)
        return response
    except Exception as exc:
        conn.rollback()
        print(f'Error saving review helpful vote: {exc}')
        return {'success': False, 'error': 'Could not save helpful vote.'}, 500
    finally:
        conn.close()

@app.route('/api/general-resources/<int:resource_id>/report', methods=['POST'])
def report_general_resource(resource_id):
    data = request.get_json(silent=True) or {}
    issue_type = (data.get('issue_type') or '').strip()
    details = (data.get('details') or '').strip()[:300]
    allowed_issues = {'outdated', 'broken', 'incorrect', 'other'}
    if issue_type not in allowed_issues:
        return {'success': False, 'error': 'Please select a valid issue.'}, 400

    anonymous_id, _, needs_cookie = anonymous_identity()
    conn = get_db_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed.'}, 500
    cur = conn.cursor()
    try:
        cur.execute('SELECT id FROM general_resources WHERE id=%s', (resource_id,))
        if not cur.fetchone():
            return {'success': False, 'error': 'Resource not found.'}, 404
        cur.execute('''
            INSERT INTO general_resource_reports (resource_id, anonymous_id, issue_type, details)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (resource_id, anonymous_id, issue_type) DO NOTHING
        ''', (resource_id, anonymous_id, issue_type, details or None))
        conn.commit()
        response = jsonify({'success': True, 'message': 'Thanks, we will review this resource.'})
        if needs_cookie:
            response.set_cookie('mh_anon_id', anonymous_id, max_age=60 * 60 * 24 * 365,
                               httponly=True, samesite='Lax', secure=request.is_secure)
        return response
    except Exception as exc:
        conn.rollback()
        print(f'Error saving resource report: {exc}')
        return {'success': False, 'error': 'Could not submit report.'}, 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/resource-reports/delete/<int:report_id>', methods=['POST'])
def admin_delete_resource_report(report_id):
    if not session.get('admin_mode'):
        return redirect(url_for('general_resources_page'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('general_resources_page'))
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM general_resource_reports WHERE id=%s', (report_id,))
        if cur.rowcount:
            conn.commit()
            backup_db()
            flash('Report dismissed successfully.', 'success')
        else:
            conn.rollback()
            flash('Report not found.', 'error')
    except Exception as exc:
        conn.rollback()
        flash(f'Failed to dismiss report: {exc}', 'error')
    finally:
        conn.close()
    return redirect(url_for('general_resources_page'))

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
        session['legacy_admin_mode'] = True
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
    session.pop('legacy_admin_mode', None)
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

    if os.environ.get('AUTO_MIGRATE_GENERAL_RESOURCES', '').strip().lower() in ('1', 'true', 'yes'):
        migrate_local_general_resources_to_supabase()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # For production (gunicorn)
    init_db()

    if os.environ.get('AUTO_MIGRATE_GENERAL_RESOURCES', '').strip().lower() in ('1', 'true', 'yes'):
        migrate_local_general_resources_to_supabase()
