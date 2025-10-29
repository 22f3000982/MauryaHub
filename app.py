from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import sqlite3
import os
import subprocess
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import shutil
from flask import send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key') # Recommended to use environment variable

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection based on environment"""
    if DATABASE_URL:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=RealDictCursor)
        return conn
    else:
        # SQLite for local development
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to execute queries with proper parameterization
def execute_query(cursor, query, params=()):
    """Execute query with proper parameterization for both DB types"""
    if DATABASE_URL:
        # PostgreSQL uses %s
        query = query.replace('?', '%s')
    cursor.execute(query, params)

# Create tables if they don't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pyqs (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extra_stuff (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                link TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite syntax (existing code)
        cursor.execute('PRAGMA foreign_keys = ON;') # Enable foreign key support for SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pyqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extra_stuff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                link TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                yt_link TEXT,
                watch_count INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

# Backup function for SQLite ONLY
def backup_db():
    if DATABASE_URL:
        return # Skip for PostgreSQL
    try:
        conn = sqlite3.connect('database.db')
        with open('backup.sql', 'w') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n')
        conn.close()
        print("Database backed up to backup.sql")
    except Exception as e:
        print(f"Error backing up database: {e}")

# Restore function for SQLite ONLY
def restore_db():
    if DATABASE_URL:
        return # Skip for PostgreSQL
    if os.path.exists('backup.sql'):
        try:
            with open('backup.sql', 'r') as f:
                content = f.read().strip()
                if not content:
                    print("backup.sql is empty, skipping restore")
                    return
            
            conn = sqlite3.connect('database.db')
            with open('backup.sql', 'r') as f:
                sql = f.read()
                conn.executescript(sql)
            conn.commit()
            conn.close()
            print("Database restored from backup.sql")
        except Exception as e:
            print(f"Error restoring database: {e}")
    else:
        print("No backup.sql found, skipping restore")

# Manual restore for SQLite ONLY
def restore_from_backup_file(backup_filename):
    if DATABASE_URL:
        return False # Skip for PostgreSQL
    if os.path.exists(backup_filename):
        try:
            if os.path.exists('database.db'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_current = f'backup_before_restore_{timestamp}.db'
                shutil.copy2('database.db', backup_current)
                print(f"Current database backed up as {backup_current}")
            
            shutil.copy2(backup_filename, 'database.db')
            print(f"Database successfully restored from {backup_filename}")
            return True
        except Exception as e:
            print(f"Error restoring from {backup_filename}: {e}")
            return False
    else:
        print(f"Backup file {backup_filename} not found")
        return False

# --- Routes ---

@app.route('/')
def landing_page():
    return render_template('landing.html')

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        feedback_text = data.get('feedback', '').strip()
        
        if not username or not feedback_text:
            return jsonify({'error': 'Missing required fields'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        execute_query(cursor, 'INSERT INTO feedback (username, feedback) VALUES (?, ?)', (username, feedback_text))
        conn.commit()
        conn.close()
        
        backup_db()
        return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/get-feedback')
def get_feedback():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        execute_query(cursor, 'SELECT username, feedback, created_at FROM feedback ORDER BY created_at DESC LIMIT 20')
        
        feedback_list = []
        for row in cursor.fetchall():
            feedback_list.append({
                'username': row['username'],
                'feedback': row['feedback'],
                'created_at': row['created_at'].isoformat() # Use isoformat for consistency
            })
        
        conn.close()
        return jsonify(feedback_list)
        
    except Exception as e:
        print(f"Error getting feedback: {e}")
        return jsonify([])

@app.route('/delete-feedback', methods=['POST'])
def delete_feedback():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        feedback_text = data.get('feedback', '').strip()
        created_at = data.get('created_at', '').strip()
        
        if not username or not feedback_text or not created_at:
            return jsonify({'error': 'Missing required fields'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Adjust query for PostgreSQL timestamp comparison
        query = 'DELETE FROM feedback WHERE username = ? AND feedback = ? AND created_at = ?'
        if DATABASE_URL:
            # For PostgreSQL, we cast the parameter to TIMESTAMP WITH TIME ZONE
             query = 'DELETE FROM feedback WHERE username = %s AND feedback = %s AND created_at = %s::timestamptz'
             cursor.execute(query, (username, feedback_text, created_at))
        else:
            # SQLite can compare the ISO format string directly
             cursor.execute(query, (username, feedback_text, created_at))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Feedback not found'}), 404
            
        conn.commit()
        conn.close()
        backup_db()
        
        return jsonify({'success': True, 'message': 'Feedback deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting feedback: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard', methods=['GET', 'POST'])
def course_view():
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, 'SELECT * FROM courses ORDER BY name')
    courses = cursor.fetchall()
    conn.close()

    admin_mode = session.get('admin_mode', False)
    return render_template('course_view.html', courses=courses, admin_mode=admin_mode)

@app.route('/admin/backup', methods=['GET', 'POST'])
def admin_backup():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    # This feature is for SQLite only
    if DATABASE_URL:
        flash('Manual backup/restore is disabled for cloud databases.', 'info')
        return render_template('admin_backup.html', backup_file=None, backup_size=0, backup_time='N/A')

    backup_dir = '.'
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('simple_backup_') and f.endswith('.db')]
    backup_files.sort(reverse=True)
    latest_backup = backup_files[0] if backup_files else None
    backup_size = os.path.getsize(latest_backup) if latest_backup and os.path.exists(latest_backup) else 0
    backup_time = time.strftime('%Y-%m-%d %H:%M:%S IST', time.localtime(os.path.getmtime(latest_backup))) if latest_backup and os.path.exists(latest_backup) else 'No backup yet'

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'backup':
            ist_offset = timedelta(hours=5, minutes=30)
            ist_tz = timezone(ist_offset)
            fname = datetime.now(ist_tz).strftime('simple_backup_%Y%m%d_%H%M%S_IST.db')
            shutil.copyfile('database.db', fname)
            return send_file(fname, as_attachment=True)
        elif action == 'restore':
            file = request.files.get('restoreFile')
            if file and file.filename.endswith('.db'):
                file.save('database.db')
                try:
                    conn = sqlite3.connect('database.db')
                    conn.execute('PRAGMA integrity_check;')
                    conn.close()
                    flash('Database restored from uploaded backup!', 'success')
                except sqlite3.DatabaseError:
                    os.remove('database.db') # remove corrupt file
                    flash('Error: Uploaded file is not a valid SQLite database.', 'error')
                return redirect(url_for('admin_backup'))
            else:
                flash('No valid .db file selected for restore.', 'error')
        elif action == 'restore_existing':
            if latest_backup:
                shutil.copyfile(latest_backup, 'database.db')
                flash('Database restored from latest backup!', 'success')
            else:
                flash('No backup file found.', 'error')
            return redirect(url_for('admin_backup'))

    return render_template('admin_backup.html', backup_file=latest_backup, backup_size=backup_size, backup_time=backup_time)

@app.route('/admin_login', methods=['POST'])
def admin_login():
    password = request.form['password']
    # Use environment variable for password in a real app
    if password == os.environ.get('ADMIN_PASSWORD', '4129'):
        session['admin_mode'] = True
    else:
        flash('काहे को छेड़ता है पराई वेबसाइट को? 😜😉')
    return redirect(url_for('course_view'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_mode', None)
    return redirect(url_for('course_view'))

@app.route('/admin/add_course', methods=['GET', 'POST'])
def admin_add_course():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        if course_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            execute_query(cursor, 'INSERT INTO courses (name) VALUES (?)', (course_name,))
            conn.commit()
            conn.close()
            backup_db()
            flash(f'Course "{course_name}" added successfully!', 'success')
        else:
            flash('Course name cannot be empty.', 'error')
        return redirect(url_for('course_view'))

    return render_template('admin_add_course.html')

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['course_name']
        if new_name:
            execute_query(cursor, 'UPDATE courses SET name = ? WHERE id = ?', (new_name, course_id))
            conn.commit()
            flash('Course name updated successfully!', 'success')
        else:
            flash('Course name cannot be empty.', 'error')
        conn.close()
        backup_db()
        return redirect(url_for('course_view'))

    execute_query(cursor, 'SELECT name FROM courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()
    conn.close()

    if course:
        return render_template('admin_edit_course.html', course_id=course_id, course_name=course['name'])
    else:
        flash('Course not found.', 'error')
        return redirect(url_for('course_view'))

@app.route('/admin/delete_course/<int:course_id>', methods=['GET', 'POST'])
def admin_delete_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        execute_query(cursor, 'DELETE FROM courses WHERE id = ?', (course_id,))
        conn.commit()
        conn.close()
        backup_db()
        flash('Course and all its contents deleted successfully!', 'success')
        return redirect(url_for('course_view'))

    # GET request for confirmation page
    execute_query(cursor, 'SELECT name FROM courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()
    conn.close()
    
    if course:
        return render_template('confirm_delete.html', 
                               item_type='course', 
                               item_name=course['name'],
                               delete_url=url_for('admin_delete_course', course_id=course_id),
                               cancel_url=url_for('course_view'))
    else:
        flash('Course not found.', 'error')
        return redirect(url_for('course_view'))

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    execute_query(cursor, 'SELECT name FROM courses WHERE id=?', (course_id,))
    course = cursor.fetchone()

    if not course:
        flash("Course not found.", 'error')
        return redirect(url_for('course_view'))

    execute_query(cursor, 'SELECT id, name, yt_link, watch_count FROM pyqs WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    pyqs = cursor.fetchall()

    execute_query(cursor, 'SELECT id, name, yt_link, watch_count FROM notes WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    notes = cursor.fetchall()

    execute_query(cursor, 'SELECT id, name, yt_link, watch_count FROM assignments WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    assignments = cursor.fetchall()

    execute_query(cursor, 'SELECT id, name, yt_link, watch_count FROM resources WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    resources = cursor.fetchall()

    execute_query(cursor, 'SELECT name, link FROM extra_stuff WHERE course_id=?', (course_id,))
    extra = cursor.fetchone()

    conn.close()

    admin_mode = session.get('admin_mode', False)
    return render_template('course_detail.html',
                           course_id=course_id,
                           course_name=course['name'],
                           pyqs=pyqs,
                           notes=notes,
                           assignments=assignments,
                           resources=resources,
                           admin_mode=admin_mode,
                           extra_stuff=extra)

# --- Watch Count Routes ---

def handle_increment_watch(item_type, item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, f'UPDATE {item_type} SET watch_count = watch_count + 1 WHERE id = ?', (item_id,))
    conn.commit()
    execute_query(cursor, f'SELECT yt_link FROM {item_type} WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    conn.close()
    if item and item['yt_link']:
        return redirect(item['yt_link'])
    flash('Link not found for this item.', 'error')
    return redirect(request.referrer or url_for('course_view'))

@app.route('/increment_watch_pyq/<int:item_id>')
def increment_watch_pyq(item_id):
    return handle_increment_watch('pyqs', item_id)

@app.route('/increment_watch_note/<int:item_id>')
def increment_watch_note(item_id):
    return handle_increment_watch('notes', item_id)

@app.route('/increment_watch_assignment/<int:item_id>')
def increment_watch_assignment(item_id):
    return handle_increment_watch('assignments', item_id)

@app.route('/increment_watch_resource/<int:item_id>')
def increment_watch_resource(item_id):
    return handle_increment_watch('resources', item_id)

# --- Admin Item Management ---

@app.route('/admin/add_item/<item_type>/<int:course_id>', methods=['GET', 'POST'])
def admin_add_item(item_type, course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if item_type not in ['pyqs', 'notes', 'assignments', 'resources']:
        flash('Invalid item type.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    if request.method == 'POST':
        item_name = request.form['item_name']
        yt_link = request.form['yt_link']

        conn = get_db_connection()
        cursor = conn.cursor()
        execute_query(cursor, f'SELECT MAX(sort_order) as max_order FROM {item_type} WHERE course_id=?', (course_id,))
        max_order_row = cursor.fetchone()
        max_order = max_order_row['max_order'] if max_order_row and max_order_row['max_order'] is not None else -1
        next_order = max_order + 1
        
        query = f'INSERT INTO {item_type} (course_id, name, yt_link, sort_order) VALUES (?, ?, ?, ?)'
        execute_query(cursor, query, (course_id, item_name, yt_link, next_order))
        conn.commit()
        conn.close()
        backup_db()
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('admin_add_item.html', course_id=course_id, item_type=item_type)


@app.route('/admin/edit_item/<string:item_type>/<int:course_id>/<int:item_id>', methods=['GET', 'POST'])
def admin_edit_item(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if item_type not in ['pyqs', 'notes', 'assignments', 'resources']:
        flash('Invalid item type.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_title = request.form['title']
        new_link = request.form['link']
        query = f'UPDATE {item_type} SET name=?, yt_link=? WHERE id=?'
        execute_query(cursor, query, (new_title, new_link, item_id))
        conn.commit()
        conn.close()
        backup_db()
        return redirect(url_for('course_detail', course_id=course_id))

    execute_query(cursor, f'SELECT name, yt_link FROM {item_type} WHERE id=?', (item_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        return render_template('admin_edit_item.html', item=item, item_type=item_type, course_id=course_id, item_id=item_id)
    else:
        flash("Item not found.", 'error')
        return redirect(url_for('course_detail', course_id=course_id))


@app.route('/admin/delete_item/<string:item_type>/<int:course_id>/<int:item_id>', methods=['GET', 'POST'])
def admin_delete_item(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))
    
    if item_type not in ['pyqs', 'notes', 'assignments', 'resources']:
        flash('Invalid item type.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        execute_query(cursor, f'DELETE FROM {item_type} WHERE id=?', (item_id,))
        conn.commit()
        conn.close()
        backup_db()
        flash('Item deleted successfully!', 'success')
        return redirect(url_for('course_detail', course_id=course_id))

    # GET request for confirmation
    execute_query(cursor, f'SELECT name FROM {item_type} WHERE id=?', (item_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        return render_template('confirm_delete.html', 
                               item_type=item_type.rstrip('s'), 
                               item_name=item['name'],
                               delete_url=url_for('admin_delete_item', item_type=item_type, course_id=course_id, item_id=item_id),
                               cancel_url=url_for('course_detail', course_id=course_id))
    else:
        flash('Item not found.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

@app.route('/admin/move_item', methods=['POST'])
def move_item():
    if not session.get('admin_mode'):
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    data = request.get_json()
    item_type = data.get('item_type')
    item_id = int(data.get('item_id'))
    direction = data.get('direction')
    course_id = int(data.get('course_id'))
    
    if item_type not in ['pyqs', 'notes', 'assignments', 'resources']:
        return jsonify({"success": False, "error": "Invalid item type"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        execute_query(cursor, f'SELECT id, sort_order FROM {item_type} WHERE course_id=? ORDER BY sort_order, id', (course_id,))
        items = cursor.fetchall()
        
        # Re-index sort_order to ensure it's contiguous
        for i, item in enumerate(items):
            execute_query(cursor, f'UPDATE {item_type} SET sort_order = ? WHERE id = ?', (i, item['id']))

        conn.commit() # Commit re-indexing before proceeding

        # Fetch re-indexed items
        execute_query(cursor, f'SELECT id, sort_order FROM {item_type} WHERE course_id=? ORDER BY sort_order, id', (course_id,))
        items = cursor.fetchall()
        
        item_ids = [item['id'] for item in items]
        if item_id not in item_ids:
             return jsonify({"success": False, "error": "Item not found"}), 404
        
        current_pos = item_ids.index(item_id)

        if direction == 'up' and current_pos > 0:
            swap_with_pos = current_pos - 1
        elif direction == 'down' and current_pos < len(items) - 1:
            swap_with_pos = current_pos + 1
        else:
            return jsonify({"success": False, "error": "Cannot move further"}), 400
        
        item_to_move = items[current_pos]
        item_to_swap_with = items[swap_with_pos]

        # Swap sort_order values
        execute_query(cursor, f'UPDATE {item_type} SET sort_order = ? WHERE id = ?', (item_to_swap_with['sort_order'], item_to_move['id']))
        execute_query(cursor, f'UPDATE {item_type} SET sort_order = ? WHERE id = ?', (item_to_move['sort_order'], item_to_swap_with['id']))
        
        conn.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        conn.rollback()
        print(f"Error moving item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

# --- Extra Stuff & Static Pages ---

@app.route('/course/<int:course_id>/add_extra', methods=['POST'])
def add_extra_stuff(course_id):
    if not session.get('admin_mode'):
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    name = request.form.get('name')
    link = request.form.get('link')
    if not name or not link:
        return jsonify({"success": False, "error": "Missing name or link"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, 'DELETE FROM extra_stuff WHERE course_id=?', (course_id,))
    execute_query(cursor, 'INSERT INTO extra_stuff (course_id, name, link) VALUES (?, ?, ?)', (course_id, name, link))
    conn.commit()
    conn.close()
    backup_db()
    return jsonify({"success": True})

@app.route('/course/<int:course_id>/get_extra')
def get_extra_stuff(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    execute_query(cursor, 'SELECT name, link FROM extra_stuff WHERE course_id=?', (course_id,))
    extra = cursor.fetchone()
    conn.close()
    if extra:
        return jsonify({"name": extra['name'], "link": extra['link']})
    else:
        return jsonify({"name": None, "link": None})

@app.route('/contact')
def contact_us():
    return render_template('contact_us.html')

@app.route('/about')
def about_admin():
    profile_pic = None
    for ext in ALLOWED_EXTENSIONS:
        pic_path = os.path.join(app.config['UPLOAD_FOLDER'], f'profile_pic.{ext}')
        if os.path.exists(pic_path):
            profile_pic = f'uploads/profile_pic.{ext}?t={os.path.getmtime(pic_path)}' # Cache busting
            break
    return render_template('about_admin.html', profile_pic=profile_pic)

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))
    
    if 'profile_pic' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('about_admin'))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('about_admin'))
    
    if file and allowed_file(file.filename):
        # Remove existing profile pictures
        for ext in ALLOWED_EXTENSIONS:
            old_pic = os.path.join(app.config['UPLOAD_FOLDER'], f'profile_pic.{ext}')
            if os.path.exists(old_pic):
                os.remove(old_pic)
        
        # Save new profile picture
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"profile_pic.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Profile picture updated successfully!', 'success')
    else:
        flash(f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}', 'error')
    
    return redirect(url_for('about_admin'))

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- Error Handlers ---

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500

# --- Main Execution ---

if __name__ == '__main__':
    # Initialize database on first run
    if not DATABASE_URL and not os.path.exists('database.db'):
        init_db()
        restore_db() # Restore from backup.sql if it exists for a fresh local setup
    else:
        init_db() # Ensure tables exist on every run

    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # For production (gunicorn), just ensure tables exist
    init_db()