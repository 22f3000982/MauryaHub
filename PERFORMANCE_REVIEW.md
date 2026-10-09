# MauryaHub latency review

This review is based on source inspection. Production response times and database query plans have not been measured.

## Improvements in this change

- Home navigation flows with the page instead of overlapping mobile content.
- Canvas particles are capped at 28 on mobile and 70 on desktop, instead of growing with screen area. Drawing is limited to about 30 fps, skipped while the document is hidden, and disabled for reduced-motion preferences.
- Responsive styles are shared across templates and can be cached as one static asset.

## Recommended next changes, in priority order

1. **Reuse database connections.** `get_db_connection()` resolves DNS and opens a fresh TLS PostgreSQL connection for every call; routes and logged-in user loading can open several per request. Use a bounded process-local pool and return connections reliably in `finally` blocks with rollback on errors. Budget total connections across Gunicorn workers. Use Supabase's appropriate pooled connection string, preserving all URL options.
2. **Cache small public datasets.** Home `get_recent_content()` runs three queries on every request. A short (30–60 second) cache for recent content, course counts, contributor rankings and subjects would avoid repeated work. Invalidate after admin changes. Do not cache authenticated HTML or personalized feedback globally.
3. **Reduce resources-page work.** Ranking already has a 300-second process-local cache, but contributor matching still fetches usernames and published titles on every visit. Compute contributor attribution when resources are saved, or cache contributor data separately. Profile the feedback and seven-day view aggregates with `EXPLAIN (ANALYZE, BUFFERS)` before adding indexes. Candidate indexes include feedback `resource_id` and view events `(content_table, viewed_at, content_id)`.
4. **Paginate on the server as the catalog grows.** Current resource filtering/pagination is client-side: the complete catalog is rendered and sent before pagination. Request one page and filter with SQL, so initial payload and DOM size remain bounded.
5. **Hosting and region.** Keep application and database close geographically. If the current Render service is on Free, idle spin-down causes cold starts; paid compute avoids that. A custom domain alone will not make database queries faster.
6. **Asset delivery.** Compress HTML/CSS/JS at the serving layer, set appropriate cache headers with asset versioning, and serve immutable files through storage/CDN. Keep uploaded private or pending files out of shared public caches. Measure fonts, icon CSS and ads separately; they are external dependencies on the home page.

## Measurement

Measure cold and warm TTFB for `/`, `/dashboard`, `/resources` and a course page; record p50/p95 response time, database connection time, query count and transferred bytes. Test anonymous and signed-in sessions separately. Run controlled concurrency tests on staging before selecting worker/thread counts. No percentage improvement is claimed without before/after measurements.

## Existing configuration issue

`app.py` includes an embedded database credential fallback and prints portions of connection URLs. Move credentials exclusively to environment variables, rotate the exposed credential, and remove URL logging. This change does not modify database configuration.
