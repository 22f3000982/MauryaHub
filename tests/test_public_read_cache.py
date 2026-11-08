"""Offline regression checks. Never import app startup or use a live database.

Run: python -m unittest discover -s tests -v
"""
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from threading import Barrier, Event
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from read_cache import ReadCache


class CacheTests(unittest.TestCase):
    def test_expiry_bound_and_exceptions(self):
        now = [0]
        cache = ReadCache(max_entries=2, clock=lambda: now[0])
        calls = []
        def load():
            calls.append(1)
            return len(calls)
        self.assertEqual(cache.get_or_load('a', load, 120), 1)
        self.assertEqual(cache.get_or_load('a', load, 120), 1)
        now[0] = 121
        self.assertEqual(cache.get_or_load('a', load, 120), 2)
        cache.get_or_load('b', load, 120)
        cache.get_or_load('c', load, 120)
        self.assertEqual(len(cache._entries), 2)
        def fail():
            raise RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            cache.get_or_load('fail', fail, 120)
        self.assertNotIn('fail', cache._entries)

    def test_concurrent_misses_load_once(self):
        cache = ReadCache()
        gate = Barrier(8)
        calls = []
        def worker(_):
            gate.wait(timeout=5)
            return cache.get_or_load('catalog', lambda: calls.append(1) or 'catalog', 120)
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(list(executor.map(worker, range(8))), ['catalog'] * 8)
        self.assertEqual(calls, [1])

    def test_invalidation_during_load_does_not_repopulate(self):
        for invalidate in ('clear', 'invalidate'):
            with self.subTest(invalidate=invalidate):
                cache = ReadCache()
                started, finish = Event(), Event()
                def loader():
                    started.set()
                    self.assertTrue(finish.wait(timeout=5))
                    return 'old'
                with ThreadPoolExecutor(max_workers=1) as executor:
                    pending = executor.submit(cache.get_or_load, 'catalog', loader, 120)
                    self.assertTrue(started.wait(timeout=5))
                    getattr(cache, invalidate)(*(['catalog'] if invalidate == 'invalidate' else []))
                    finish.set()
                    self.assertEqual(pending.result(timeout=5), 'old')
                self.assertEqual(cache.get_or_load('catalog', lambda: 'new', 120), 'new')


def load_app_without_startup():
    """Execute declarations only; explicitly remove the production initializer."""
    path = ROOT / 'app.py'
    tree = ast.parse(path.read_text())
    final = tree.body[-1]
    assert isinstance(final, ast.If) and '__name__' in ast.unparse(final.test)
    assert 'init_db' in ast.unparse(final)
    tree.body.pop()
    spec = importlib.util.spec_from_file_location('mauryahub_offline_tests', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Let Flask resolve templates from __file__.
    with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://USER:PASSWORD@HOST:5432/DATABASE',
                                  'SECRET_KEY': 'offline-test-secret', 'RENDER': 'true'}), \
         patch('psycopg2.connect', side_effect=AssertionError('Live DB forbidden')), \
         patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden')):
        exec(compile(tree, str(path), 'exec'), module.__dict__)
    module.app.config.update(TESTING=True)
    return module


class FakeDB:
    def __init__(self):
        self.queries = []
        self.connections = 0
        self.closes = 0
        self.commits = 0
        self.views = 0
        self.rows = [
            (i, f'Notes {i}', f'https://files.invalid/resource-{i}.pdf',
             'diploma' if i % 2 else 'degree', i, 'revision,exam',
             None if i == 1 else (1 if i % 2 else 2),
             None if i == 1 else ('Diploma Subject' if i % 2 else 'Degree Subject'),
             4.0, 3, 3, 4, 3.5, datetime(2026, 1, 1), i % 11, 'Alice')
            for i in range(1, 102)
        ]

    def connect(self):
        self.connections += 1
        db = self
        class Connection:
            def cursor(self, **kwargs):
                return Cursor()
            def close(self):
                db.closes += 1
            def commit(self):
                db.commits += 1
        class Cursor:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
            def close(self):
                pass
            def execute(self, query, params=None):
                q = ' '.join(query.split())
                db.queries.append(q)
                if q.startswith('SELECT username FROM member_contributions'):
                    self.result = [('Alice',)]
                elif q.startswith('SELECT username FROM users'):
                    self.result = [('Alice',)]
                elif q.startswith('SELECT gr.title, u.username'):
                    self.result = [(r[1], r[15]) for r in db.rows]
                elif q.startswith('SELECT gr.id,'):
                    self.result = [r for r in db.rows if not params or r[3] == params[0]]
                elif q.startswith('SELECT id, name, program_type FROM general_resource_subjects'):
                    self.result = [(1, 'Diploma Subject', 'diploma'), (2, 'Degree Subject', 'degree')]
                elif q.startswith('SELECT rr.id,'):
                    self.result = [(1, 2, 'PRIVATE_REPORT_MARKER', 'broken', 'admin only', 'anon', datetime(2026, 1, 1))]
                elif q.startswith('SELECT c.name,'):
                    self.result = [('Course', 'Recent Item', 1, 1, 12)]
                elif q.startswith('SELECT id, name FROM courses'):
                    self.result = [(1, 'Course')]
                elif q.startswith('SELECT username, feedback, created_at FROM feedback'):
                    self.result = [{'username': 'Alice', 'feedback': 'Great resources', 'created_at': datetime(2026, 1, 1)}]
                elif q.startswith('UPDATE general_resources SET watch_count'):
                    db.views += 1
                    self.result = [('https://files.invalid/resource-1.pdf', 'diploma')]
                elif q.startswith('INSERT INTO view_events'):
                    self.result = []
                else:
                    raise AssertionError('Unexpected SQL (no migrations or resource writes allowed): ' + q)
            def fetchall(self):
                return self.result
            def fetchone(self):
                return self.result[0] if self.result else None
        return Connection()


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_app_without_startup()

    def setUp(self):
        self.db = FakeDB()
        self.module._read_cache.clear()
        self.db_patch = patch.object(self.module, 'get_db_connection', self.db.connect)
        self.db_patch.start()
        self.client = self.module.app.test_client()

    def tearDown(self):
        self.db_patch.stop()
        self.assertEqual(self.db.connections, self.db.closes)

    def test_full_catalog_preserved_and_warm_requests_do_no_db_work(self):
        a = self.client.get('/resources')
        self.assertEqual(a.status_code, 200)
        queries = len(self.db.queries)
        connections = self.db.connections
        b = self.client.get('/resources')
        self.assertEqual(a.data, b.data)
        self.assertEqual(len(self.db.queries), queries)
        self.assertEqual(self.db.connections, connections)
        self.assertEqual(queries, 5)
        for row in self.db.rows:
            self.assertIn(f'Notes {row[0]}'.encode(), b.data)
            self.assertIn(f'/open_general_resource/{row[0]}'.encode(), b.data)
        catalog = self.module.load_general_resources_catalog()
        rows = catalog[0] + catalog[1]
        self.assertEqual({(r[0], r[2], r[3]) for r in rows}, {(r[0], r[2], r[3]) for r in self.db.rows})
        self.assertEqual(catalog[3], [('Alice', 101)])

    def test_sorts_preserve_all_rows_and_do_not_mutate_cached_catalog(self):
        original = self.module.load_general_resources_catalog()
        for sort in ('recommended', 'top-rated', 'most-helpful', 'latest', 'most-viewed', 'invalid'):
            response = self.client.get('/resources?sort=' + sort)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Notes 101', response.data)
            self.assertIn(b'Notes 100', response.data)
        self.assertEqual(len(self.db.queries), 5)
        self.assertEqual(self.module.load_general_resources_catalog(), original)
        self.assertTrue(all(len(r) == 20 for r in original[0] + original[1]))

    def test_home_dashboard_and_testimonials_cached(self):
        for path in ('/', '/dashboard', '/get-feedback'):
            with self.subTest(path=path):
                a = self.client.get(path)
                self.assertEqual(a.status_code, 200)
                queries = len(self.db.queries)
                connections = self.db.connections
                b = self.client.get(path)
                self.assertEqual(a.data, b.data)
                self.assertEqual(len(self.db.queries), queries)
                self.assertEqual(self.db.connections, connections)

    def test_resource_views_keep_exact_writes_without_evicting_catalog(self):
        self.client.get('/resources')
        catalog = self.module.load_general_resources_catalog()
        response = self.client.get('/open_general_resource/1')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'https://files.invalid/resource-1.pdf')
        self.assertEqual(self.db.views, 1)
        self.assertEqual(self.db.commits, 2)
        self.assertEqual(self.module.load_general_resources_catalog(), catalog)
        queries = len(self.db.queries)
        self.client.get('/resources')
        self.assertEqual(len(self.db.queries), queries)

    def test_catalog_invalidation_reloads_new_resources(self):
        self.client.get('/resources')
        self.db.rows.append((102, 'Brand new notes', 'https://files.invalid/new.pdf', 'degree',
                             0, '', 2, 'Degree Subject', 0, 0, 0, 0, 0, datetime(2026, 1, 1), 0, 'Alice'))
        self.module.invalidate_resource_ranking('general:degree')
        response = self.client.get('/resources')
        self.assertIn(b'Brand new notes', response.data)
        self.assertEqual(len(self.db.rows), 102)

    def test_post_invalidates_public_read_cache(self):
        self.client.get('/resources')
        queries = len(self.db.queries)
        self.client.post('/logout')  # 405 also invalidates conservatively.
        self.client.get('/resources')
        self.assertEqual(len(self.db.queries), queries + 5)

    def test_failed_catalog_load_is_not_cached(self):
        with patch.object(self.module, 'get_db_connection', return_value=None):
            response = self.client.get('/resources')
            self.assertIn(b'Could not load resources', response.data)
        response = self.client.get('/resources')
        self.assertIn(b'Notes 101', response.data)

    def test_admin_reports_never_leak_into_guest_page(self):
        self.client.get('/resources')
        with self.client.session_transaction() as session:
            session['admin_mode'] = True
        admin = self.client.get('/resources')
        self.assertIn(b'PRIVATE_REPORT_MARKER', admin.data)
        guest = self.module.app.test_client().get('/resources')
        self.assertNotIn(b'PRIVATE_REPORT_MARKER', guest.data)
        self.assertNotIn(b'admin only', guest.data)

    def test_contributor_matching_preserves_legacy_scores_and_ties(self):
        cases = [
            ('notes by Ann Marie', ['Ann', 'Ann Marie'], 'Ann Marie'),
            ('ab cd', ['abc', 'AbC'], 'abc'),
            ('guide', ['!!!', ''], None),
            ('aaaa', ['aaa', 'aaaa'], 'aaaa'),
            ('abc', ['abd', 'abe'], 'abd'),
            ('abcd', ['abce', 'abcdx'], 'abcdx'),
            ('xyz', ['abc'], None),
            ('', ['Alice'], None),
            ('DL | Code-Synth', ['Code Synth'], 'Code Synth'),
        ]
        for title, usernames, expected in cases:
            with self.subTest(title=title, usernames=usernames):
                self.assertEqual(self.module.match_contributor_from_title(title, usernames), expected)

    def test_production_startup_skips_database_and_storage_migrations(self):
        tree = ast.parse((ROOT / 'app.py').read_text())
        startup = tree.body[-1]
        callbacks = []
        import os
        namespace = {'__name__': 'app', 'os': os,
                     'init_db': lambda: callbacks.append('schema'),
                     'migrate_local_general_resources_to_supabase': lambda: callbacks.append('files')}
        with patch.dict('os.environ', {'RENDER': 'true', 'INIT_DB_ON_STARTUP': 'false',
                                      'AUTO_MIGRATE_GENERAL_RESOURCES': 'false'}):
            exec(compile(ast.Module(body=[startup], type_ignores=[]), 'startup', 'exec'), namespace)
        self.assertEqual(callbacks, [])

    def test_legacy_admin_login_requires_explicit_password(self):
        with patch.dict('os.environ', {'ADMIN_PASSWORD': ''}):
            response = self.client.post('/admin_login', data={'password': '4129'})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertFalse(session.get('admin_mode', False))

    def test_logged_in_static_requests_skip_user_lookup_but_pages_do_not(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 7
        with patch.object(self.module, 'fetch_user_by_id', return_value={'id': 7, 'username': 'Alice', 'role': 'user'}) as lookup:
            response = self.client.get('/static/style2.css')
            self.assertEqual(response.status_code, 200)
            response.close()
            lookup.assert_not_called()
            self.client.get('/resources')
            lookup.assert_called_once_with(7)


if __name__ == '__main__':
    unittest.main()
