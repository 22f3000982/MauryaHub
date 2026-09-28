/* ==========================================================================
   MauryaHub — shared application shell behaviour
   Sidebar toggle, theme switching, dropdowns, toasts.
   Loaded on every page via base.html.
   ========================================================================== */

(function () {
    'use strict';

    var STORE_THEME   = 'mauryahub-theme';
    var STORE_SIDEBAR = 'mauryahub-sidebar-collapsed';
    var MOBILE_BP     = 860;

    function isMobile() {
        return window.innerWidth <= MOBILE_BP;
    }

    /* ----------------------------------------------------------------------
       Theme
       The inline script in <head> applies the stored theme before first paint
       so there is no flash. This part only handles toggling afterwards.
       ---------------------------------------------------------------------- */

    function currentTheme() {
        var explicit = document.documentElement.getAttribute('data-theme');
        if (explicit) return explicit;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem(STORE_THEME, theme);
        } catch (e) { /* private mode — theme just won't persist */ }
        syncThemeButton(theme);
    }

    function syncThemeButton(theme) {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        var isDark = theme === 'dark';
        btn.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
        btn.setAttribute('title', isDark ? 'Light mode' : 'Dark mode');
        var sun = btn.querySelector('[data-icon="sun"]');
        var moon = btn.querySelector('[data-icon="moon"]');
        if (sun)  sun.hidden  = !isDark;   /* in dark mode offer the sun */
        if (moon) moon.hidden = isDark;
    }

    function initTheme() {
        syncThemeButton(currentTheme());

        var btn = document.getElementById('themeToggle');
        if (btn) {
            btn.addEventListener('click', function () {
                applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
            });
        }

        /* Follow the OS only while the user has made no explicit choice. */
        var mq = window.matchMedia('(prefers-color-scheme: dark)');
        var onChange = function () {
            var stored = null;
            try { stored = localStorage.getItem(STORE_THEME); } catch (e) {}
            if (!stored) syncThemeButton(currentTheme());
        };
        if (mq.addEventListener) mq.addEventListener('change', onChange);
        else if (mq.addListener) mq.addListener(onChange);
    }

    /* ----------------------------------------------------------------------
       Sidebar
       Desktop: collapsed class hides it, preference persists.
       Mobile:  it is an off-canvas drawer; collapsed is the default and the
                toggle opens it. It always re-closes on navigation/resize.
       ---------------------------------------------------------------------- */

    function setSidebar(collapsed, persist) {
        document.documentElement.classList.toggle('sidebar-collapsed', collapsed);

        var btn = document.getElementById('sidebarToggle');
        if (btn) btn.setAttribute('aria-expanded', String(!collapsed));

        var sidebar = document.getElementById('appSidebar');
        if (sidebar) sidebar.setAttribute('aria-hidden', String(collapsed && isMobile()));

        if (persist && !isMobile()) {
            try {
                localStorage.setItem(STORE_SIDEBAR, collapsed ? '1' : '0');
            } catch (e) {}
        }
    }

    function initSidebar() {
        var collapsed;
        if (isMobile()) {
            collapsed = true;            /* drawer starts closed on mobile */
        } else {
            var stored = null;
            try { stored = localStorage.getItem(STORE_SIDEBAR); } catch (e) {}
            collapsed = stored === '1';
        }
        setSidebar(collapsed, false);

        var toggle = document.getElementById('sidebarToggle');
        if (toggle) {
            toggle.addEventListener('click', function () {
                setSidebar(!document.documentElement.classList.contains('sidebar-collapsed'), true);
            });
        }

        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) {
            overlay.addEventListener('click', function () { setSidebar(true, false); });
        }

        /* Close the drawer after tapping a nav link on mobile. */
        var sidebar = document.getElementById('appSidebar');
        if (sidebar) {
            sidebar.addEventListener('click', function (e) {
                if (isMobile() && e.target.closest('a')) setSidebar(true, false);
            });
        }

        /* Re-evaluate when crossing the breakpoint. */
        var wasMobile = isMobile();
        window.addEventListener('resize', debounce(function () {
            var nowMobile = isMobile();
            if (nowMobile === wasMobile) return;
            wasMobile = nowMobile;
            if (nowMobile) {
                setSidebar(true, false);
            } else {
                var stored = null;
                try { stored = localStorage.getItem(STORE_SIDEBAR); } catch (e) {}
                setSidebar(stored === '1', false);
            }
        }, 150));
    }

    /* ----------------------------------------------------------------------
       Dropdowns  —  markup: <div class="user-menu"><button data-dropdown-trigger>
       ---------------------------------------------------------------------- */

    function closeAllDropdowns(except) {
        document.querySelectorAll('.dropdown.open').forEach(function (d) {
            if (d !== except) {
                d.classList.remove('open');
                var trigger = d.parentElement && d.parentElement.querySelector('[data-dropdown-trigger]');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            }
        });
    }

    function initDropdowns() {
        document.addEventListener('click', function (e) {
            var trigger = e.target.closest('[data-dropdown-trigger]');

            if (trigger) {
                e.preventDefault();
                var menu = trigger.parentElement.querySelector('.dropdown');
                if (!menu) return;
                var willOpen = !menu.classList.contains('open');
                closeAllDropdowns(menu);
                menu.classList.toggle('open', willOpen);
                trigger.setAttribute('aria-expanded', String(willOpen));
                return;
            }

            if (!e.target.closest('.dropdown')) closeAllDropdowns(null);
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeAllDropdowns(null);
                if (isMobile()) setSidebar(true, false);
            }
        });
    }

    /* ----------------------------------------------------------------------
       Toasts  —  window.showToast(message, type, duration)
       Kept globally available: existing pages already call showToast().
       ---------------------------------------------------------------------- */

    function toastRegion() {
        var region = document.getElementById('toastRegion');
        if (!region) {
            region = document.createElement('div');
            region.id = 'toastRegion';
            region.className = 'toast-region';
            region.setAttribute('role', 'status');
            region.setAttribute('aria-live', 'polite');
            document.body.appendChild(region);
        }
        return region;
    }

    window.showToast = function (message, type, duration) {
        if (!message) return;
        var el = document.createElement('div');
        el.className = 'toast' + (type ? ' ' + type : '');
        el.textContent = message;
        toastRegion().appendChild(el);

        var ms = typeof duration === 'number' ? duration : 3600;
        setTimeout(function () {
            el.classList.add('hiding');
            setTimeout(function () { el.remove(); }, 200);
        }, ms);
    };

    /* ----------------------------------------------------------------------
       Scroll reveal
       Elements marked `data-reveal` fade/slide in as they enter the viewport.
       `data-reveal-group` on a parent stages its direct children so they
       arrive one after another instead of all at once.
       ---------------------------------------------------------------------- */

    /* Never animate these: dialogs and overlays run their own opacity, and a
       reveal class fighting them leaves the thing stuck invisible. */
    var REVEAL_SKIP = '[data-reveal-skip], [role="dialog"], .modal-backdrop, .preview-modal,' +
                      ' .toast-region, .sidebar-overlay, .dropdown, script, style, template, link';

    /* Cap the stagger so a long grid doesn't end on a a second-plus delay. */
    var REVEAL_MAX_STEP = 8;

    function stageReveal(el, index) {
        if (!el.hasAttribute('data-reveal')) el.setAttribute('data-reveal', '');
        el.style.setProperty('--reveal-i', String(Math.min(index, REVEAL_MAX_STEP)));
    }

    function initReveal() {
        var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        /* Whole-page opt-in: stage each top-level block of the container.
           A grid staggers its own cards (they cross the fold together, so the
           wave belongs inside the row); a standalone block starts at 0, since
           blocks further down are sequenced by scroll position anyway. */
        document.querySelectorAll('[data-reveal-page]').forEach(function (page) {
            Array.prototype.forEach.call(page.children, function (child) {
                if (child.matches(REVEAL_SKIP)) return;
                if (child.hasAttribute('data-reveal') || child.hasAttribute('data-reveal-group')) return;

                var cards = child.classList.contains('grid') ? child.children : null;
                if (cards && cards.length > 1) {
                    Array.prototype.forEach.call(cards, function (card, i) {
                        if (!card.matches(REVEAL_SKIP)) stageReveal(card, i);
                    });
                } else {
                    stageReveal(child, 0);
                }
            });
        });

        /* Explicit groups: stagger the direct children of the marked element. */
        document.querySelectorAll('[data-reveal-group]').forEach(function (group) {
            var step = parseInt(group.getAttribute('data-reveal-group'), 10);
            if (isNaN(step) || step < 1) step = 1;

            Array.prototype.forEach.call(group.children, function (child, i) {
                if (!child.matches(REVEAL_SKIP)) stageReveal(child, i * step);
            });
        });

        var targets = document.querySelectorAll('[data-reveal]');
        if (!targets.length) return;

        function showAll() {
            targets.forEach(function (el) { el.classList.add('is-visible', 'is-done'); });
        }

        /* No observer support, or the user prefers less motion: just show it. */
        if (reduced || !('IntersectionObserver' in window)) {
            showAll();
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;

                var el = entry.target;
                el.classList.add('is-visible');
                observer.unobserve(el);

                /* Drop the compositor hint once the transition has finished. */
                el.addEventListener('transitionend', function onEnd(e) {
                    if (e.target !== el || e.propertyName !== 'opacity') return;
                    el.classList.add('is-done');
                    el.removeEventListener('transitionend', onEnd);
                });
            });
        }, {
            root: null,
            /* Pull the trigger line well up from the bottom edge. Without this
               an element that is merely peeking into the viewport counts as
               "in view" and reveals while still half cut off by the fold --
               which reads as broken rather than as an entrance.
               threshold stays 0 so the margin alone decides, which also keeps
               elements taller than the viewport working. */
            rootMargin: '0px 0px -18% 0px',
            threshold: 0
        });

        /* Elements already properly on screen at load are handled by the
           observer itself: it delivers an initial callback for every target
           with its current intersection state, so above-the-fold content
           reveals immediately without a separate check. */
        targets.forEach(function (el) { observer.observe(el); });
    }

    /* ----------------------------------------------------------------------
       Helpers
       ---------------------------------------------------------------------- */

    function debounce(fn, wait) {
        var t;
        return function () {
            var args = arguments, ctx = this;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(ctx, args); }, wait);
        };
    }

    /* ---------------------------------------------------------------------- */

    function init() {
        initTheme();
        initSidebar();
        initDropdowns();
        initReveal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
