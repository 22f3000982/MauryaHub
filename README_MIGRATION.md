# Why Your Data Disappears on Render (And How to Fix It)

## The Problem 🤔

You're experiencing data loss because:

1. **Render's Free Tier Uses Ephemeral Storage**: Your SQLite database file (`database.db`) is stored on Render's temporary filesystem
2. **Render Restarts Regularly**: Free tier services restart/sleep after inactivity, wiping the filesystem
3. **No Persistent Volumes**: Unlike paid plans, free tier doesn't provide persistent disk storage

## The Solution ✅

**Switch from SQLite to PostgreSQL** - a dedicated database service that provides persistent storage.

## What We've Created For You

### 1. `app_postgresql.py`
- **What**: PostgreSQL version of your Flask app
- **Changes**: 
  - Replaced `sqlite3` with `psycopg2` (PostgreSQL driver)
  - Updated all SQL queries to use PostgreSQL syntax (`%s` instead of `?`)
  - Added proper database connection handling
  - Uses `SERIAL` for auto-increment instead of `AUTOINCREMENT`

### 2. `migrate_data.py`
- **What**: Script to transfer your existing data from SQLite to PostgreSQL
- **Does**:
  - Connects to both databases
  - Copies all your courses, notes, assignments, etc.
  - Handles data type conversions
  - Resets PostgreSQL sequences properly

### 3. `setup_postgresql.py`
- **What**: Automated setup script
- **Does**: 
  - Tests your PostgreSQL connection
  - Runs the migration
  - Backs up your original files
  - Replaces app.py with PostgreSQL version

### 4. `POSTGRESQL_SETUP.md`
- **What**: Step-by-step guide for getting free PostgreSQL
- **Covers**: Supabase, ElephantSQL, and Railway options

## Free PostgreSQL Options Comparison

| Service | Storage | Best For |
|---------|---------|----------|
| **Supabase** | 500MB | Most generous, includes dashboard |
| **Railway** | 100MB | Easy GitHub integration |
| **ElephantSQL** | 20MB | Simple, reliable |

## Step-by-Step Instructions

### 1. Get Free PostgreSQL Database
Choose one option from `POSTGRESQL_SETUP.md` (I recommend **Supabase**)

### 2. Install Dependencies
```bash
pip install psycopg2-binary
```

### 3. Set Environment Variable
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://your_connection_string_here"

# Linux/Mac
export DATABASE_URL="postgresql://your_connection_string_here"
```

### 4. Run Automated Setup
```bash
python setup_postgresql.py
```

OR do it manually:
```bash
python migrate_data.py
copy app_postgresql.py app.py
```

### 5. Test Locally
```bash
python app.py
```

### 6. Deploy to Render
1. Add `DATABASE_URL` to Render environment variables
2. Push to GitHub
3. Render will redeploy automatically

## What Changes in Your Code

### Before (SQLite):
```python
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('SELECT * FROM courses WHERE id=?', (course_id,))
```

### After (PostgreSQL):
```python
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT * FROM courses WHERE id=%s', (course_id,))
```

## Benefits You'll Get

✅ **Permanent Data Storage** - Never lose data again  
✅ **Better Performance** - PostgreSQL handles multiple users better  
✅ **Professional Setup** - Industry standard database  
✅ **Scalability** - Easy to upgrade when you grow  
✅ **Backup Features** - Built-in backup/restore capabilities  

## After Migration

Your app will work exactly the same, but:
- Data persists across Render restarts
- Multiple users can access simultaneously
- You can upgrade to larger databases as you grow
- Professional database features available

## Cost Comparison

| Option | Current (SQLite) | New (PostgreSQL) |
|--------|------------------|------------------|
| **Hosting** | Free (Render) | Free (Render) |
| **Database** | Included | Free (Supabase/others) |
| **Total** | $0/month | $0/month |
| **Data Persistence** | ❌ No | ✅ Yes |

## Need Help?

If you encounter issues:
1. Check `POSTGRESQL_SETUP.md` for detailed instructions
2. Ensure your `DATABASE_URL` is correct
3. Test the connection before migration
4. Keep your original `database.db` as backup

Your education platform will be much more reliable with persistent data! 🎓