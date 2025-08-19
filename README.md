# MauryaHub (Ashish Maurya)

## Overview

This is a web portal for managing and sharing resources (PYQs, notes) for courses in the IITM BS program. It is built using Flask and SQLite, with a simple admin interface for adding, editing, and deleting course content.

## Features

- View all available courses
- View details and resources (PYQs, notes, assignments) for each course
- Admin login for managing courses and resources
- Add, edit, and delete courses and items (PYQs, notes, assignments)
- Track watch counts for YouTube-linked resources
- Database backup and restore functionality

## Project Structure

- `app.py`: Main Flask application
- `setup_db.py`: (empty, reserved for DB setup scripts)
- `requirements.txt`: Python dependencies
- `Procfile`: For deployment (Gunicorn)
- `database.db`: SQLite database
- `backup.sql`: SQL backup of the database
- `static/`: CSS files
- `templates/`: HTML templates for all pages

## Setup Instructions

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the application**
   ```bash
   python app.py
   ```
3. **Access the portal**
   Open your browser and go to `http://localhost:5000`



## Deployment

- The app can be deployed using Gunicorn and a Procfile (for platforms like Heroku).

## License

This project is for educational purposes and is not officially affiliated with IITM.
