# PostgreSQL Database Setup Guide (Free Options)

This guide will help you set up a free PostgreSQL database and migrate your existing data for persistent storage on Render.

## Option 1: Supabase (Recommended - 500MB free)

### Step 1: Create Supabase Account
1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project" 
3. Sign in with GitHub or create an account
4. Click "New Project"

### Step 2: Create Database
1. Choose your organization
2. Enter project name: `mauryahub` (or any name you prefer)
3. Enter a strong database password and **SAVE IT**
4. Select region closest to your users
5. Click "Create new project"

### Step 3: Get Database URL
1. Wait for project to be created (2-3 minutes)
2. Go to Settings → Database
3. Copy the "Connection string" under "Connection parameters"
4. It will look like: `postgresql://postgres.xxx:PASSWORD@xxx.supabase.co:5432/postgres`
5. Replace `PASSWORD` with your actual database password

---

## Option 2: ElephantSQL (Free 20MB)

### Step 1: Create Account
1. Go to [https://www.elephantsql.com/](https://www.elephantsql.com/)
2. Click "Get a managed database today"
3. Sign up with email or GitHub

### Step 2: Create Database Instance
1. Click "Create New Instance"
2. Name: `mauryahub`
3. Plan: Select "Tiny Turtle (Free)"
4. Region: Choose closest to your users
5. Click "Create instance"

### Step 3: Get Database URL
1. Click on your newly created instance
2. Copy the URL from the "URL" field
3. It will look like: `postgres://username:password@host/database`

---

## Option 3: Railway (Free with GitHub)

### Step 1: Create Account
1. Go to [https://railway.app](https://railway.app)
2. Sign in with GitHub
3. Verify your account

### Step 2: Create Database
1. Click "New Project"
2. Select "Provision PostgreSQL"
3. Wait for deployment

### Step 3: Get Database URL
1. Click on your PostgreSQL service
2. Go to "Variables" tab
3. Copy the `DATABASE_URL` value

---

## Migration Steps

### Step 1: Install Dependencies Locally
```bash
pip install psycopg2-binary
```

### Step 2: Set Environment Variable
**Windows (PowerShell):**
```powershell
$env:DATABASE_URL="your_postgresql_url_here"
```

**Linux/Mac:**
```bash
export DATABASE_URL="your_postgresql_url_here"
```

### Step 3: Run Migration Script
```bash
python migrate_data.py
```

### Step 4: Test PostgreSQL Version
```bash
python app_postgresql.py
```

---

## Deploy to Render

### Step 1: Update Your Repository
1. Replace your `app.py` with `app_postgresql.py`:
   ```bash
   copy app_postgresql.py app.py
   ```
   (On Linux/Mac: `cp app_postgresql.py app.py`)

### Step 2: Set Environment Variable on Render
1. Go to your Render dashboard
2. Click on your web service
3. Go to "Environment" tab
4. Add new environment variable:
   - **Key:** `DATABASE_URL`
   - **Value:** Your PostgreSQL connection string from Step 3 above

### Step 3: Redeploy
1. Push changes to your GitHub repository:
   ```bash
   git add .
   git commit -m "Switch to PostgreSQL for persistent storage"
   git push
   ```
2. Render will automatically redeploy

---

## Verification

### Check if Migration Worked
1. Visit your deployed site
2. Go to admin panel (password: 4129)
3. Check if all your courses and data are there
4. Add a test course/resource
5. Wait a few hours and check if it's still there

### Backup Your Data
The PostgreSQL version includes a backup feature:
1. Go to Admin → Backup
2. Click "Create Backup" to download your data

---

## Database Limits

| Provider    | Storage | Connections | Notes |
|-------------|---------|-------------|-------|
| Supabase    | 500MB   | 60          | Best option, most generous |
| ElephantSQL | 20MB    | 5           | Smallest but reliable |
| Railway     | 100MB   | 100         | Good middle ground |

---

## Troubleshooting

### Common Issues:

**"psycopg2 not found"**
```bash
pip install psycopg2-binary
```

**"Connection refused"**
- Check your DATABASE_URL is correct
- Ensure your IP is whitelisted (most free tiers allow all IPs)

**"Database doesn't exist"**
- The database should be created automatically
- Check if you're using the correct connection string

**"Migration failed"**
- Ensure your SQLite database (`database.db`) exists
- Check that PostgreSQL connection works first

### Need Help?
If you encounter issues:
1. Check the error messages carefully
2. Verify your DATABASE_URL is correct
3. Test the connection manually
4. Make sure all required columns exist

---

## Benefits of PostgreSQL

✅ **Persistent storage** - Data won't disappear  
✅ **Better performance** - Handles concurrent users better  
✅ **Scalability** - Can upgrade to paid plans easily  
✅ **ACID compliance** - Better data integrity  
✅ **JSON support** - Modern features available  

Your data will now persist even when Render restarts your application!