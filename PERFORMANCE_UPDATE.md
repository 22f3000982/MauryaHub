> Demo publication note: database credentials are environment-only, SECRET_KEY
> is required on Render, legacy admin login requires ADMIN_PASSWORD, and Render
> startup schema initialization is disabled unless explicitly opted in. See
> DEPLOY_DEMO.md. This supersedes the baseline startup description below.

# Small public-read performance update

Based on main commit `77d879e151a93a68cd68fe98d8ee606915bd4e08`.

## Scope

- Cache public catalog data, contributor calculations, recent homepage content,
  course lists and testimonials in memory for 120 seconds.
- Combine the two community program queries into one, preserving every resource.
- Stop evicting the whole catalog on each resource view. View increments and
  analytics events are still written exactly as before.
- Calculate the maximum recent-view count once per program for badges.
- Skip user lookups for static assets. Account authorization on pages is unchanged.
- Coalesce concurrent cache misses, bound memory, retry failed loads, and prevent
  a concurrent write from repopulating an invalidated cache.

Only public data is cached. HTML, cookies, account records, authorization decisions
and admin reports are not shared through the cache.

This update adds no database/storage write statements or migrations. Existing
resource IDs, links, publication states and files are retained. Existing database
initialization, backup, upload and deletion functions otherwise remain in place.
It does not run any of those functions while applying the patch.

## Freshness and limitations

Successful loads are reused for up to two minutes. POST/PUT/PATCH/DELETE requests
and existing backup calls clear the serving worker's public-data cache. Resource
edit/publication/rating invalidation clears its catalog entry. Other workers
refresh on expiry, so a change or new view count may take up to two minutes to
appear there. Direct database edits also appear after expiry.

The first visit after startup or expiry still queries PostgreSQL and calculates
contributors. A signed-in page visit still checks the current user. No connection
pool, worker settings, database indexes, file-delivery changes, new dependencies,
or pagination redesign is included in this small first pass. Community HTML still
contains all resources and retains the existing filters and pagination controls.

The cache is disposable: restart/expiry empties only memory, never resource data.
Warm anonymous reads can avoid database work, but production speed and a 70–80%
improvement have not been measured or guaranteed.

## Validation completed offline

Run `python -m unittest discover -s tests -v` with requirements.txt installed.
There are 15 regression checks covering cache expiry/bounds, concurrency,
invalidation, retry after failure, resource IDs/links and all sort modes, exact
view writes, private reports, static requests, and cached public endpoints.

The tests remove only the application's startup initialization before loading
declarations and substitute a fake database. They never initialize or access a
production database.

Additional comparison against the baseline found:

- Identical rendered homepage, dashboard, testimonial JSON, and all five
  community sort responses for the offline fixture.
- All 101 fixture resources preserved, including both programs and unassigned
  subjects; IDs and resource URLs unchanged.
- Warm anonymous community database queries reduced from four to zero in the
  fixture; cold community queries reduced from six to five.
- All 86 database write/schema SQL literals identical to the baseline.
- Tracked databases, SQL backups, uploaded files, templates, dependencies and
  deployment settings unchanged.

## Before deploying

The patch is a code update, not a production backup. Export the current PostgreSQL
database and separately back up uploaded Storage objects/local files. Verify that
both backups can be read/restored in isolation. Repository SQL/SQLite snapshots
and the existing in-app SQL export are not a complete current resource backup.

Apply only to the reviewed application version. The supplied installer refuses
when app.py differs or any added file would be overwritten. Test on a separate
branch and retain the same database and storage configuration. Do not run the
old migration/setup scripts or replace the database with repository snapshots.

After deployment, compare cold and warm anonymous/signed-in visits, test resource
preview/download and admin edits, and verify new submissions and feedback. Compare
production resource IDs/URLs and storage inventory to the pre-deploy record,
accounting for legitimate new submissions. No production benchmark was performed
for the changed code during preparation.

Rollback is code-only: revert the performance commit. Keep the current database
and files so submissions made after deployment are retained. Do not restore an
older production database merely to roll back this code change.
