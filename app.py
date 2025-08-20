from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create tables if they don't exist
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create 'courses' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    # Create 'pyqs' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS pyqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Create 'notes' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Create 'assignments' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Create 'extra_stuff' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS extra_stuff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            link TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Create 'resources' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Add sort_order columns to existing tables if they don't exist
    for table in ['pyqs', 'notes', 'assignments']:
        try:
            c.execute(f'ALTER TABLE {table} ADD COLUMN sort_order INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.commit()
    conn.close()

# Backup the SQLite database to backup.sql using Python's sqlite3 module
def backup_db():
    try:
        conn = sqlite3.connect('database.db')
        with open('backup.sql', 'w') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n')
        conn.close()
        print("Database backed up to backup.sql")
    except Exception as e:
        print(f"Error backing up database: {e}")

# Restore the SQLite database from backup.sql
def restore_db():
    if os.path.exists('backup.sql'):
        try:
            conn = sqlite3.connect('database.db')
            with open('backup.sql', 'r') as f:
                sql = f.read()
                conn.executescript(sql)
            conn.commit()
            conn.close()
            print("Database restored from backup.sql")
        except Exception as e:
            print(f"Error restoring database: {e}")

# Landing page route
@app.route('/')
def landing_page():
    return render_template('landing.html')

# Home - Show all courses
import time
from flask import send_file

# Home - Show all courses
@app.route('/dashboard', methods=['GET', 'POST'])
def course_view():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM courses')
    courses = c.fetchall()
    conn.close()

    admin_mode = session.get('admin_mode', False)
    return render_template('course_view.html', courses=courses, admin_mode=admin_mode)


# Admin Backup & Restore page
@app.route('/admin/backup', methods=['GET', 'POST'])
def admin_backup():
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    # Find latest backup file
    backup_dir = '.'
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('simple_backup_') and f.endswith('.db')]
    backup_files.sort(reverse=True)
    latest_backup = backup_files[0] if backup_files else None
    backup_size = os.path.getsize(latest_backup) if latest_backup else 0
    backup_time = time.strftime('%Y-%m-%d %H:%M:%S IST', time.localtime(os.path.getmtime(latest_backup))) if latest_backup else 'No backup yet'

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'backup':
            # Create a timestamped .db backup file in IST
            from datetime import datetime, timedelta, timezone
            ist_offset = timedelta(hours=5, minutes=30)
            ist_now = datetime.utcnow() + ist_offset
            fname = ist_now.strftime('simple_backup_%Y%m%d_%H%M%S_IST.db')
            import shutil
            shutil.copyfile('database.db', fname)
            return send_file(fname, as_attachment=True)
        elif action == 'restore':
            file = request.files.get('restoreFile')
            if file:
                file.save('database.db')
                # Validate the uploaded file is a real SQLite DB
                try:
                    conn = sqlite3.connect('database.db')
                    conn.execute('PRAGMA schema_version;')
                    conn.close()
                    flash('Database restored from uploaded backup!', 'success')
                except sqlite3.DatabaseError:
                    os.remove('database.db')
                    flash('Error: Uploaded file is not a valid SQLite database.', 'error')
                return redirect(url_for('admin_backup'))
            else:
                flash('No file selected for restore.', 'error')
        elif action == 'restore_existing':
            if latest_backup:
                import shutil
                shutil.copyfile(latest_backup, 'database.db')
                flash('Database restored from latest backup!', 'success')
            else:
                flash('No backup file found.', 'error')
            return redirect(url_for('admin_backup'))

    return render_template('admin_backup.html', backup_file=latest_backup, backup_size=backup_size, backup_time=backup_time)

# # Admin login (password 4129)
# @app.route('/admin_login', methods=['POST'])
# def admin_login():
#     password = request.form['password']
#     if password == '4129':
#         session['admin_mode'] = True
#     return redirect(url_for('course_view'))

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
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO courses (name) VALUES (?)', (course_name,))
        conn.commit()
        conn.close()
        backup_db()  # Backup database after adding course
        return redirect(url_for('course_view'))

    return render_template('admin_add_course.html')

# Admin - Edit course
@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['course_name']
        c.execute('UPDATE courses SET name = ? WHERE id = ?', (new_name, course_id))
        conn.commit()
        conn.close()
        backup_db()  # Backup database after editing course
        return redirect(url_for('course_view'))

    c.execute('SELECT name FROM courses WHERE id = ?', (course_id,))
    course = c.fetchone()
    conn.close()

    return render_template('admin_edit_course.html', course_id=course_id, course_name=course[0])

# Admin - Delete course
@app.route('/admin/delete_course/<int:course_id>')
def admin_delete_course(course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    c.execute('DELETE FROM pyqs WHERE course_id = ?', (course_id,))
    c.execute('DELETE FROM notes WHERE course_id = ?', (course_id,))
    c.execute('DELETE FROM assignments WHERE course_id = ?', (course_id,))
    conn.commit()
    conn.close()
    backup_db()  # Backup database after deleting course
    return redirect(url_for('course_view'))


# View course detail
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT name FROM courses WHERE id=?', (course_id,))
    course = c.fetchone()

    c.execute('SELECT id, name, yt_link, watch_count FROM pyqs WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    pyqs = c.fetchall()

    c.execute('SELECT id, name, yt_link, watch_count FROM notes WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    notes = c.fetchall()

    c.execute('SELECT id, name, yt_link, watch_count FROM assignments WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    assignments = c.fetchall()

    c.execute('SELECT id, name, yt_link, watch_count FROM resources WHERE course_id=? ORDER BY sort_order, id', (course_id,))
    resources = c.fetchall()

    # Fetch extra stuff for this course
    c.execute('SELECT name, link FROM extra_stuff WHERE course_id=?', (course_id,))
    extra = c.fetchone()

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
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Remove any previous extra stuff for this course (only one allowed)
    c.execute('DELETE FROM extra_stuff WHERE course_id=?', (course_id,))
    c.execute('INSERT INTO extra_stuff (course_id, name, link) VALUES (?, ?, ?)', (course_id, name, link))
    conn.commit()
    conn.close()
    return {"success": True}

# API endpoint to get extra stuff (AJAX)
@app.route('/course/<int:course_id>/get_extra')
def get_extra_stuff(course_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT name, link FROM extra_stuff WHERE course_id=?', (course_id,))
    extra = c.fetchone()
    conn.close()
    if extra:
        return {"name": extra[0], "link": extra[1]}
    else:
        return {"name": None, "link": None}

# Admin - Add PYQ / Notes / Assignment
@app.route('/admin/add_item/<item_type>/<int:course_id>', methods=['GET', 'POST'])
def admin_add_item(item_type, course_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    if request.method == 'POST':
        item_name = request.form['item_name']
        yt_link = request.form['yt_link']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Get the next sort_order value
        c.execute(f'SELECT MAX(sort_order) FROM {item_type} WHERE course_id=?', (course_id,))
        max_order = c.fetchone()[0]
        next_order = (max_order + 1) if max_order is not None else 0

        if item_type == 'pyqs':
            c.execute('INSERT INTO pyqs (course_id, name, yt_link, sort_order) VALUES (?, ?, ?, ?)', (course_id, item_name, yt_link, next_order))
        elif item_type == 'notes':
            c.execute('INSERT INTO notes (course_id, name, yt_link, sort_order) VALUES (?, ?, ?, ?)', (course_id, item_name, yt_link, next_order))
        elif item_type == 'assignments':
            c.execute('INSERT INTO assignments (course_id, name, yt_link, sort_order) VALUES (?, ?, ?, ?)', (course_id, item_name, yt_link, next_order))
        elif item_type == 'resources':
            c.execute('INSERT INTO resources (course_id, name, yt_link, sort_order) VALUES (?, ?, ?, ?)', (course_id, item_name, yt_link, next_order))

        conn.commit()
        conn.close()
        backup_db()  # Backup database after adding item
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('admin_add_pyq.html', course_id=course_id, item_type=item_type)

# Watch Count Increment (PYQs)
@app.route('/increment_watch/<int:pyq_id>')
def increment_watch(pyq_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE pyqs SET watch_count = watch_count + 1 WHERE id = ?', (pyq_id,))
    conn.commit()
    c.execute('SELECT yt_link FROM pyqs WHERE id = ?', (pyq_id,))
    link = c.fetchone()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

# Watch Count Increment (Notes)
@app.route('/increment_watch_note/<int:note_id>')
def increment_watch_note(note_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE notes SET watch_count = watch_count + 1 WHERE id = ?', (note_id,))
    conn.commit()
    c.execute('SELECT yt_link FROM notes WHERE id = ?', (note_id,))
    link = c.fetchone()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

# Watch Count Increment (Assignments)
@app.route('/increment_watch_assignment/<int:assignment_id>')
def increment_watch_assignment(assignment_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE assignments SET watch_count = watch_count + 1 WHERE id = ?', (assignment_id,))
    conn.commit()
    c.execute('SELECT yt_link FROM assignments WHERE id = ?', (assignment_id,))
    link = c.fetchone()
    conn.close()

    if link:
        return redirect(link[0])
    else:
        return "Link not found"

@app.route('/increment_watch_resource/<int:resource_id>')
def increment_watch_resource(resource_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE resources SET watch_count = watch_count + 1 WHERE id = ?', (resource_id,))
    conn.commit()
    c.execute('SELECT yt_link FROM resources WHERE id = ?', (resource_id,))
    link = c.fetchone()
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
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # Get all items for this course ordered by current sort_order
        c.execute(f'SELECT id, sort_order FROM {item_type} WHERE course_id=? ORDER BY sort_order, id', (course_id,))
        items = c.fetchall()
        
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
        c.execute(f'UPDATE {item_type} SET sort_order = ? WHERE id = ?', (new_pos, current_item_id))
        c.execute(f'UPDATE {item_type} SET sort_order = ? WHERE id = ?', (current_pos, target_item_id))
        
        conn.commit()
        return {"success": True}
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500
    finally:
        conn.close()

# Admin - Edit item (PYQ/Note/Assignment)
@app.route('/admin/edit_item/<string:item_type>/<int:course_id>/<int:item_id>', methods=['GET', 'POST'])
def admin_edit_item(item_type, course_id, item_id):
    if not session.get('admin_mode'):
        return redirect(url_for('course_view'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        new_title = request.form['title']
        new_link = request.form['link']

        if item_type == 'pyqs':
            c.execute('UPDATE pyqs SET name=?, yt_link=? WHERE id=?', (new_title, new_link, item_id))
        elif item_type == 'notes':
            c.execute('UPDATE notes SET name=?, yt_link=? WHERE id=?', (new_title, new_link, item_id))
        elif item_type == 'assignments':
            c.execute('UPDATE assignments SET name=?, yt_link=? WHERE id=?', (new_title, new_link, item_id))
        elif item_type == 'resources':
            c.execute('UPDATE resources SET name=?, yt_link=? WHERE id=?', (new_title, new_link, item_id))

        conn.commit()
        conn.close()
        backup_db()  # Backup database after editing item
        return redirect(url_for('course_detail', course_id=course_id))

    # Fetch existing item
    if item_type == 'pyqs':
        c.execute('SELECT name, yt_link FROM pyqs WHERE id=?', (item_id,))
    elif item_type == 'notes':
        c.execute('SELECT name, yt_link FROM notes WHERE id=?', (item_id,))
    elif item_type == 'assignments':
        c.execute('SELECT name, yt_link FROM assignments WHERE id=?', (item_id,))
    elif item_type == 'resources':
        c.execute('SELECT name, yt_link FROM resources WHERE id=?', (item_id,))
    
    item = c.fetchone()
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

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if item_type == 'pyqs':
        c.execute('DELETE FROM pyqs WHERE id=?', (item_id,))
    elif item_type == 'notes':
        c.execute('DELETE FROM notes WHERE id=?', (item_id,))
    elif item_type == 'assignments':
        c.execute('DELETE FROM assignments WHERE id=?', (item_id,))
    elif item_type == 'resources':
        c.execute('DELETE FROM resources WHERE id=?', (item_id,))
    else:
        flash('Invalid item type.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    conn.commit()
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

# Main
if __name__ == '__main__':
    if not os.path.exists('database.db'):
        init_db()
        restore_db()  # Restore database from backup.sql if it exists
    else:
        init_db()
        restore_db()  # Restore database from backup.sql if it exists

    app.run(debug=True)