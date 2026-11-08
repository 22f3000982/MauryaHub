# Deploy the performance demo on Render

This is the updated full application and bundled repository resources. SQL dumps,
SQLite snapshots, credentials, local environment files and bytecode are excluded.
Live PostgreSQL records and Supabase Storage objects were not copied, migrated,
restored, deleted or changed while preparing/publishing this repository.

## Render

- Branch: main
- Runtime: Python
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Keep the existing database/storage environment values to display existing resources.
- Add SECRET_KEY with a strong random value; it is required on Render. Prefer the
  existing site's key if deliberately sharing compatible sessions, otherwise use
  a separate demo key.
- Configure ADMIN_EMAILS for Google admin login. ADMIN_PASSWORD is optional and
  enables legacy password login only when explicitly set.
- Change GOOGLE_REDIRECT_URI to https://YOUR-DEMO.onrender.com/auth/google/callback
  and add that exact callback in the Google OAuth client's authorized redirect URIs.
- Keep INIT_DB_ON_STARTUP=false and AUTO_MIGRATE_GENERAL_RESOURCES=false. On
  Render both initialization and automatic resource migration are disabled by default.
  Do not enable migration flags when only testing performance against existing data.

An isolated empty database requires explicit schema setup before use; initialization
is intentionally not run on the existing production database by demo startup.

## Shared database warning

Using the same DATABASE_URL and storage bucket shares the LIVE records/files.
Opening resources still increments real counters and records analytics. Uploads,
ratings, approvals, edits and deletions affect live data. This is not an isolated
sandbox and should not be used for destructive admin tests. Use cloned database
and storage data for isolated testing.

Export and verify the live database and separately back up Storage objects before
making changes through either site. Repo snapshots are not a production backup.

## Verification

python -m unittest discover -s tests -v

15 offline regression checks cover caching and resource preservation. Warm public
reads use a two-minute in-memory cache; account checks and private reports remain
uncached. Changes across workers/direct DB edits may take up to two minutes to
appear. No production latency percentage is guaranteed before measurement.
