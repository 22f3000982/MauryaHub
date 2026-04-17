from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import psycopg2
import psycopg2.extras
import os
import subprocess
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://username:password@localhost:5432/mauryahub"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        # Parse the DATABASE_URL
        if DATABASE_URL.startswith('postgres://'):
            # Fix for newer psycopg2 versions that don't support postgres://
            url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            url = DATABASE_URL
            
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

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

        # Create 'feedback' table for landing page testimonials
        cur.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        tables = ['courses', 'pyqs', 'notes', 'assignments', 'resources', 'extra_stuff', 'feedback']
        
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
                            values.append(f"'{value.replace('\'', '\'\'')}'")
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

# Landing page route
@app.route('/')
def landing_page():
    return render_template('landing.html')

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
    conn = get_db_connection()
    if not conn:
        return render_template('course_view.html', courses=[], admin_mode=session.get('admin_mode', False))
        
    cur = conn.cursor()
    cur.execute('SELECT * FROM courses ORDER BY id')
    courses = cur.fetchall()
    cur.close()
    conn.close()

    admin_mode = session.get('admin_mode', False)
    return render_template('course_view.html', courses=courses, admin_mode=admin_mode)

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
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO courses (name) VALUES (%s)', (course_name,))
            conn.commit()
            cur.close()
            conn.close()
            backup_db()  # Backup database after adding course
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
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
        
    cur = conn.cursor()
    cur.execute('SELECT name FROM courses WHERE id=%s', (course_id,))
    course = cur.fetchone()

    cur.execute('SELECT id, name, yt_link, watch_count FROM pyqs WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
    pyqs = cur.fetchall()

    cur.execute('SELECT id, name, yt_link, watch_count FROM notes WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
    notes = cur.fetchall()

    cur.execute('SELECT id, name, yt_link, watch_count FROM assignments WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
    assignments = cur.fetchall()

    cur.execute('SELECT id, name, yt_link, watch_count FROM resources WHERE course_id=%s ORDER BY sort_order, id', (course_id,))
    resources = cur.fetchall()

    # Fetch extra stuff for this course
    cur.execute('SELECT name, link FROM extra_stuff WHERE course_id=%s', (course_id,))
    extra = cur.fetchone()

    cur.close()
    conn.close()

    if course:
        admin_mode = session.get('admin_mode', False)
        return render_template('course_detail.html',
                               course_id=course_id,
                               course_name=course[0],
                               pyqs=pyqs,
                               notes=notes,
                               assignments=assignments,
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

        if item_type in ['pyqs', 'notes', 'assignments', 'resources']:
            cur.execute(f'INSERT INTO {item_type} (course_id, name, yt_link, sort_order) VALUES (%s, %s, %s, %s)', 
                       (course_id, item_name, yt_link, next_order))

        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after adding item
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('admin_add_pyq.html', course_id=course_id, item_type=item_type)

# Watch Count Increment functions
@app.route('/increment_watch/<int:pyq_id>')
def increment_watch(pyq_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
        
    cur = conn.cursor()
    cur.execute('UPDATE pyqs SET watch_count = watch_count + 1 WHERE id = %s', (pyq_id,))
    conn.commit()
    cur.execute('SELECT yt_link FROM pyqs WHERE id = %s', (pyq_id,))
    link = cur.fetchone()
    cur.close()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

@app.route('/increment_watch_note/<int:note_id>')
def increment_watch_note(note_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
        
    cur = conn.cursor()
    cur.execute('UPDATE notes SET watch_count = watch_count + 1 WHERE id = %s', (note_id,))
    conn.commit()
    cur.execute('SELECT yt_link FROM notes WHERE id = %s', (note_id,))
    link = cur.fetchone()
    cur.close()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

@app.route('/increment_watch_assignment/<int:assignment_id>')
def increment_watch_assignment(assignment_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
        
    cur = conn.cursor()
    cur.execute('UPDATE assignments SET watch_count = watch_count + 1 WHERE id = %s', (assignment_id,))
    conn.commit()
    cur.execute('SELECT yt_link FROM assignments WHERE id = %s', (assignment_id,))
    link = cur.fetchone()
    cur.close()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

@app.route('/increment_watch_resource/<int:resource_id>')
def increment_watch_resource(resource_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
        
    cur = conn.cursor()
    cur.execute('UPDATE resources SET watch_count = watch_count + 1 WHERE id = %s', (resource_id,))
    conn.commit()
    cur.execute('SELECT yt_link FROM resources WHERE id = %s', (resource_id,))
    link = cur.fetchone()
    cur.close()
    conn.close()

    if link:
        return redirect(link[0])
    else:
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
    
    if item_type not in ['pyqs', 'notes', 'assignments', 'resources']:
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

        if item_type in ['pyqs', 'notes', 'assignments', 'resources']:
            cur.execute(f'UPDATE {item_type} SET name=%s, yt_link=%s WHERE id=%s', (new_title, new_link, item_id))

        conn.commit()
        cur.close()
        conn.close()
        backup_db()  # Backup database after editing item
        return redirect(url_for('course_detail', course_id=course_id))

    # Fetch existing item
    if item_type in ['pyqs', 'notes', 'assignments', 'resources']:
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
        
        if item_type in ['pyqs', 'notes', 'assignments', 'resources']:
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

    if item_type in ['pyqs', 'notes', 'assignments', 'resources']:
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