#!/usr/bin/env python3
"""
Quick Setup Script for PostgreSQL Migration
This script automates the setup process
"""

import os
import shutil
import sys

def main():
    print("=" * 60)
    print("MauryaHub PostgreSQL Setup Script")
    print("=" * 60)
    
    print("\n🚀 Setting up PostgreSQL version...")
    
    # Step 1: Check if files exist
    files_needed = ['app_postgresql.py', 'migrate_data.py', 'database.db']
    missing_files = []
    
    for file in files_needed:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        sys.exit(1)
    
    print("✅ All required files found")
    
    # Step 2: Backup original app.py
    if os.path.exists('app.py'):
        if not os.path.exists('app_sqlite_backup.py'):
            shutil.copy2('app.py', 'app_sqlite_backup.py')
            print("✅ Backed up original app.py to app_sqlite_backup.py")
    
    # Step 3: Check DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("\n⚠️  DATABASE_URL not set!")
        print("\nBefore running migration, please:")
        print("1. Get a free PostgreSQL database (see POSTGRESQL_SETUP.md)")
        print("2. Set DATABASE_URL environment variable:")
        print("   Windows: $env:DATABASE_URL=\"your_postgresql_url\"")
        print("   Linux/Mac: export DATABASE_URL=\"your_postgresql_url\"")
        print("\nThen run: python migrate_data.py")
        return
    
    print(f"✅ DATABASE_URL is set")
    
    # Step 4: Test PostgreSQL connection
    try:
        import psycopg2
        
        # Fix postgres:// to postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(database_url)
        conn.close()
        print("✅ PostgreSQL connection successful")
        
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("Please check your DATABASE_URL")
        return
    
    # Step 5: Run migration
    print("\n🔄 Running data migration...")
    try:
        os.system('python migrate_data.py')
        print("✅ Data migration completed")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return
    
    # Step 6: Replace app.py
    try:
        shutil.copy2('app_postgresql.py', 'app.py')
        print("✅ Replaced app.py with PostgreSQL version")
    except Exception as e:
        print(f"❌ Failed to replace app.py: {e}")
        return
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test locally: python app.py")
    print("2. Add DATABASE_URL to Render environment variables")
    print("3. Push to GitHub and redeploy")
    print("\nYour data is now persistent! 🎊")

if __name__ == "__main__":
    main()