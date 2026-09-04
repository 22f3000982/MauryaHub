# MauryaHub

MauryaHub is a Flask-based academic resource portal for browsing and managing course material such as Quiz-1, Quiz-2, end-term content, videos, notes, PYQs, assignments, and other learning resources.

Live site: [mauryahub.onrender.com](https://mauryahub.onrender.com/)

## Features

- Course dashboard with course-level resource navigation.
- Separate sections for Quiz-1, Quiz-2, end-term material, and resources.
- YouTube links with watch-count tracking and highlighted items.
- General resource library with subjects, tags, PDF/HTML previews, search, sorting, and recommended ranking.
- Signed-in users can submit resources for admin approval.
- Ratings, helpfulness feedback, written reviews, review votes, and resource reports.
- Google OAuth login, user profiles, usernames, and role-based admin access.
- Admin CRUD for courses and course resources.
- Admin moderation for submitted resources and reported content.
- Learning analytics dashboard with CSV export.
- Database backup and restore tools.
- Responsive HTML/CSS/Jinja2 interface.

## How MauryaHub works

### Student workflow

1. Open the landing page and go to the course dashboard.
2. Select a course from the available course catalog.
3. Open Quiz-1, Quiz-2, End Term, or Resources.
4. Open a YouTube video or learning link. Watch counts are tracked automatically.
5. Browse the General Resources library by subject, tags, search, or sorting mode.
6. Sign in with Google when submitting a new resource or accessing user-specific features.
7. Track submitted resources from **My Submissions**.

### Resource submission workflow

Authenticated users can submit a PDF or HTML resource with a title, subject, tags, and link/file content. New submissions remain pending until an administrator previews and approves them. Approved resources become visible in the public resource library; rejected submissions remain available to the submitting user with their status.

### Admin workflow

Administrators are selected through the `ADMIN_EMAILS` environment variable. After signing in with an allowlisted Google account, the admin menu provides access to:

- Add, edit, reorder, highlight, and delete courses and course items.
- Add, edit, publish, and delete general resources.
- Create and manage resource subjects for diploma and degree courses.
- Review, approve, or reject user submissions.
- Review reported resources and remove resolved reports.
- View analytics for course content, views, and resource performance.
- Create database backups and restore an earlier backup when required.

## Technology

- **Backend:** Python, Flask 3, Werkzeug
- **Database:** PostgreSQL, normally hosted through Supabase
- **Fast read snapshot:** SQLite (`static_data.db`)
- **Storage:** Supabase Storage for production resource uploads; local storage is used during local development
- **Authentication:** Google OAuth 2.0
- **Frontend:** HTML5, CSS3, JavaScript, Jinja2 templates
- **Production server:** Gunicorn
- **Deployment:** Render

## Project layout

```text
app.py                 Main Flask application
templates/             Jinja2 pages
static/                Styles, favicon, and local development uploads
static_data.db         Bundled SQLite snapshot for fast reads
requirements.txt       Python dependencies
Procfile               Render/Gunicorn start command
init_db.py             PostgreSQL schema initialization helper
init_static_db.py      Rebuild the SQLite snapshot from backup data
test_static_db.py      Validate the SQLite snapshot
*_SETUP.md             Database, OAuth, and architecture notes
```

## Main routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page and public feedback |
| `/dashboard` | Course dashboard |
| `/course/<course_id>` | Course detail and learning items |
| `/resources` | General resource library |
| `/resources/submit` | Authenticated resource submission form |
| `/my-submissions` | Current user’s submission history |
| `/auth/google` | Start Google OAuth login |
| `/logout` | Sign out the current user |
| `/settings` | User settings and profile picture |
| `/contact` | Contact page |
| `/about` | Developer/about page |
| `/admin/analytics` | Admin analytics dashboard |
| `/admin/backup` | Admin backup and restore tools |
| `/admin/resources/submissions` | Admin submission moderation |

Administrative routes require an authenticated account with the admin role.

## Local setup

### 1. Create an environment

Python 3.11 or newer is recommended.

```bash
git clone https://github.com/22f3000982/MauryaHub.git
cd MauryaHub
python -m venv .venv
```

Activate it:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

The app loads `.env.local` or `.env` during local development. These files should not be committed.

#### Core database configuration

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

#### Authentication and storage configuration

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
ADMIN_EMAILS=admin@example.com,another-admin@example.com

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_STORAGE_BUCKET=resources
```

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection URL used by the application and admin features. |
| `GOOGLE_CLIENT_ID` | For login | Google OAuth client ID. |
| `GOOGLE_CLIENT_SECRET` | For login | Google OAuth client secret. Keep it private. |
| `GOOGLE_REDIRECT_URI` | For login | Exact OAuth callback URL for local or production use. |
| `ADMIN_EMAILS` | For admin access | Comma-separated Google email allowlist. |
| `SUPABASE_URL` | For production uploads | Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | For production uploads | Server-side Supabase service key. Never expose it in frontend code. |
| `SUPABASE_STORAGE_BUCKET` | No | Storage bucket name; defaults to `resources`. |
| `LOCAL_RESOURCE_UPLOADS` | No | Set to `true` to allow local resource uploads outside Render. |

For local development, the app automatically enables local resource uploads when it is not running on Render. Production should use Supabase Storage because Render’s local filesystem is temporary.

`ADMIN_EMAILS` is a comma-separated allowlist. Users whose Google email is in this list receive the admin role.

See [GOOGLE_LOGIN_SETUP.md](GOOGLE_LOGIN_SETUP.md) and [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) for provider-specific setup instructions.

### 3. Prepare the PostgreSQL database

Create the PostgreSQL schema using the project helper or let the application initialize it on startup:

```bash
python init_db.py
```

The schema contains course tables, Quiz-1/Quiz-2/end-term/resources tables, users, general resources, resource subjects, pending submissions, feedback, reviews, reports, view events, and supporting indexes. Use a PostgreSQL database with SSL enabled, such as a Supabase project.

The bundled `static_data.db` is optional for basic startup, but should be kept in the repository when using the hybrid read architecture. Validate it with:

```bash
python test_static_db.py
```

### 4. Run the app

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Production uses the same Flask application through Gunicorn:

```bash
gunicorn app:app
```

## Data architecture

Course pages use the bundled SQLite snapshot for fast, read-heavy access and merge live values such as watch counts and newly added content from PostgreSQL/Supabase. Admin operations write to PostgreSQL/Supabase. General resources and user-generated feedback are stored in PostgreSQL.

When the snapshot becomes stale, regenerate and verify it before committing:

```bash
python init_static_db.py
python test_static_db.py
```

More detail is available in [HYBRID_DATABASE_FLOW.md](HYBRID_DATABASE_FLOW.md) and [GENERAL_RESOURCES_RANKING.md](GENERAL_RESOURCES_RANKING.md).

### Keeping the snapshot current

`static_data.db` is a committed read snapshot, not the primary write database. Refresh it after a substantial content update or when the static catalog needs to reflect new course material:

```bash
python init_static_db.py
python test_static_db.py
git add static_data.db
git commit -m "Refresh static course data"
```

Live watch counts, newly added records, user accounts, submissions, feedback, and admin changes continue to use PostgreSQL/Supabase.

## Deployment on Render

1. Create a Render web service connected to this repository.
2. Set the build command to install `requirements.txt`.
3. Use the start command from `Procfile`: `gunicorn app:app`.
4. Add `DATABASE_URL` and the Supabase variables in the Render environment.
5. Add Google OAuth variables and set the callback URL to:
   `https://YOUR-RENDER-DOMAIN/auth/google/callback`
6. Add the production admin email addresses to `ADMIN_EMAILS`.
7. Configure the matching Google OAuth redirect URI and redeploy.

Render’s filesystem is ephemeral, so production resource uploads should use Supabase Storage. The app automatically enables local uploads when running outside Render.

### Production checklist

- Confirm the Render service uses `gunicorn app:app` as its start command.
- Set `DATABASE_URL` in Render without committing it to the repository.
- Configure Supabase Storage and verify that the `resources` bucket is available.
- Add the production Google OAuth callback URL in Google Cloud Console.
- Set `ADMIN_EMAILS` to the exact lowercase email addresses that should have admin access.
- Confirm `static_data.db` is committed if hybrid reads are enabled.
- Test login, course browsing, resource submission, approval, and backup access after deployment.
- Review Render logs after the first deployment for database, OAuth, or storage errors.

## Testing and maintenance

Run the static database validation before deployment:

```bash
python test_static_db.py
```

Run the available project checks when changing related functionality:

```bash
python test_feedback.py
python verify_watch_counts.py
```

Useful maintenance scripts include:

- `init_db.py` — initialize the PostgreSQL schema.
- `init_static_db.py` — rebuild `static_data.db` from the configured backup source.
- `migrate_data.py` and `migrate_table_data.py` — migrate legacy data when required.
- `cleanup_old_tables.py` — clean up obsolete database tables during maintenance.
- `fix_sequences.py` — repair PostgreSQL sequences after manual data restoration.
- `sync_item.py` — synchronize an individual course item with the local snapshot.

Always create a database backup before a migration, bulk deletion, or restore operation.

## Troubleshooting

### The app cannot connect to PostgreSQL

- Check that `DATABASE_URL` is present and has the correct username, password, host, port, and database name.
- Confirm that the database accepts SSL connections.
- Check the application logs for DNS, authentication, or connection errors.
- Run `python init_db.py` after creating a new database.

### Google login does not work

- Confirm both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set.
- Make sure `GOOGLE_REDIRECT_URI` exactly matches the URI registered in Google Cloud Console.
- Use `http://127.0.0.1:5000/auth/google/callback` locally and the HTTPS Render callback in production.
- Check that the Google OAuth consent screen and test-user settings permit the account to sign in.

### A signed-in user cannot access admin tools

The Google email must appear in the comma-separated `ADMIN_EMAILS` value. After changing the variable, redeploy or restart the application and sign in again.

### Resource uploads fail on Render

Check `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_STORAGE_BUCKET`. Also confirm the bucket exists and that the service key has permission to upload and delete objects. Do not rely on `static/uploads` for persistent production files.

### Course data looks outdated

Refresh `static_data.db` with `init_static_db.py`, validate it with `test_static_db.py`, then commit and redeploy the updated snapshot. Live admin changes and watch counts are still read from PostgreSQL/Supabase where applicable.

### Watch counts or feedback appear incorrect

Check the PostgreSQL connection first, then run the relevant validation script. The application caches resource ranking briefly, but feedback and view updates invalidate the affected ranking cache.

## Security notes

- Never commit `.env`, `.env.local`, database URLs, OAuth secrets, or Supabase service keys.
- Use `ADMIN_EMAILS` as the only source of admin allowlisting.
- Keep database and storage credentials in Render environment variables or a local untracked environment file.
- Review uploaded files and pending submissions before publishing them.
- Create a backup before restoring or deleting production data.

## Related documentation

- [Google login setup](GOOGLE_LOGIN_SETUP.md)
- [PostgreSQL setup](POSTGRESQL_SETUP.md)
- [Hybrid database flow](HYBRID_DATABASE_FLOW.md)
- [General resource ranking and feedback](GENERAL_RESOURCES_RANKING.md)
- [Quick start and static database notes](QUICK_START.md)

## License

This project is provided for educational purposes. See [LICENSE](LICENSE).
