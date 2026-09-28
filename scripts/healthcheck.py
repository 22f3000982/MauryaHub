#!/usr/bin/env python
"""
MauryaHub health check
======================

One command that answers "is everything still working, and is the UI still
consistent?" -- run it after any change, before any deploy.

    python scripts/healthcheck.py                 # full run
    python scripts/healthcheck.py --no-http       # static checks only (no server needed)
    python scripts/healthcheck.py --url http://localhost:5050

Sections
    1. Environment      docker container, database, config
    2. Assets           templates parse, JS syntax, CSS balance
    3. Routes           public + admin pages actually respond
    4. Design system    hardcoded colours / fonts that bypass the tokens
    5. Consistency      shared shell, page structure, animation coverage
    6. Accessibility    alt text, icon-button labels, form labels

Exit code is 0 only when nothing FAILed (warnings do not fail the build).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

# Pages that intentionally do not use the shared chrome / page container.
NO_PAGE_CONTAINER = {"base.html", "landing.html"}
# Templates not reachable through any route would be flagged here.
ORPHAN_TEMPLATES: set[str] = set()

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"

_ICON = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", INFO: "  ->"}
_results: list[tuple[str, str, str]] = []
_current_section = ""


def section(title: str) -> None:
    global _current_section
    _current_section = title
    print(f"\n\033[1m{title}\033[0m")
    print("-" * len(title))


def record(status: str, msg: str, detail: str = "") -> None:
    _results.append((_current_section, status, msg))
    colour = {PASS: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m", INFO: "\033[90m"}[status]
    print(f"  {colour}{_ICON[status]}\033[0m  {msg}")
    for line in (detail or "").splitlines():
        if line.strip():
            print(f"          \033[90m{line}\033[0m")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def templates() -> list[Path]:
    return sorted(TEMPLATES.glob("*.html"))


def local_env() -> dict[str, str]:
    env_file = ROOT / ".env.local"
    if not env_file.exists():
        return {}
    return {
        k.strip(): v.strip().strip('"').strip("'")
        for k, v in (
            line.split("=", 1)
            for line in read(env_file).splitlines()
            if "=" in line and not line.strip().startswith("#")
        )
    }


# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------

def check_environment(use_http: bool) -> None:
    section("1. Environment")

    env_file = ROOT / ".env.local"
    if env_file.exists():
        cfg = dict(
            line.split("=", 1)
            for line in read(env_file).splitlines()
            if "=" in line and not line.strip().startswith("#")
        )
        missing = [k for k in ("DATABASE_URL", "PORT") if not cfg.get(k, "").strip()]
        if missing:
            record(FAIL, f".env.local missing: {', '.join(missing)}")
        else:
            record(PASS, f".env.local present (port {cfg.get('PORT','?').strip()})")
    else:
        record(WARN, ".env.local not found -- app will fall back to production defaults")

    if not use_http:
        return

    docker = run(["docker", "ps", "--filter", "name=mauryahub-pg", "--format", "{{.Status}}"])
    status = docker.stdout.strip()
    if docker.returncode != 0:
        record(WARN, "docker not reachable (skipping container check)")
    elif status.startswith("Up"):
        record(PASS, f"postgres container up ({status})")
    else:
        record(FAIL, "postgres container is not running", "fix: docker start mauryahub-pg")

    ready = run(["docker", "exec", "mauryahub-pg", "pg_isready", "-U", "mauryahub"])
    if ready.returncode == 0:
        record(PASS, "database accepting connections")
    elif docker.returncode == 0:
        record(FAIL, "database not accepting connections")


# ---------------------------------------------------------------------------
# 2. Assets
# ---------------------------------------------------------------------------

def check_assets() -> None:
    section("2. Assets")

    # Templates parse
    try:
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
        broken = []
        for t in templates():
            try:
                env.get_template(t.name)
            except Exception as exc:  # noqa: BLE001
                broken.append(f"{t.name}: {exc}")
        if broken:
            record(FAIL, f"{len(broken)} template(s) fail to parse", "\n".join(broken))
        else:
            record(PASS, f"all {len(templates())} templates parse")
    except ImportError:
        record(WARN, "jinja2 unavailable -- template parse check skipped")

    # JS syntax
    js = STATIC / "js" / "app.js"
    if js.exists():
        node = run(["node", "--check", str(js)])
        if node.returncode == 0:
            record(PASS, "app.js syntax valid")
        else:
            record(FAIL, "app.js has a syntax error", node.stderr.strip()[:400])
    else:
        record(FAIL, "static/js/app.js missing")

    # CSS balance
    css_file = STATIC / "css" / "app.css"
    if css_file.exists():
        css = read(css_file)
        if css.count("{") == css.count("}"):
            record(PASS, f"app.css braces balanced ({css.count('{')} rules)")
        else:
            record(FAIL, f"app.css unbalanced: {css.count('{')} open vs {css.count('}')} close")
    else:
        record(FAIL, "static/css/app.css missing")

    # Per-template inline <style> balance
    bad = []
    for t in templates():
        body = read(t)
        for block in re.findall(r"<style[^>]*>(.*?)</style>", body, re.S):
            if block.count("{") != block.count("}"):
                bad.append(t.name)
    if bad:
        record(FAIL, "inline <style> braces unbalanced", ", ".join(sorted(set(bad))))
    else:
        record(PASS, "inline <style> blocks balanced")

    # Logo / icon assets
    required = [
        "img/logo-mark.png", "img/logo-lockup.png", "img/logo-lockup-dark.png", "img/favicon.ico",
        "img/favicon-32.png", "img/favicon-16.png", "img/apple-touch-icon.png",
    ]
    missing = [p for p in required if not (STATIC / p).exists()]
    if missing:
        record(FAIL, "missing brand assets", ", ".join(missing))
    else:
        record(PASS, f"all {len(required)} brand assets present")


# ---------------------------------------------------------------------------
# 3. Routes
# ---------------------------------------------------------------------------

PUBLIC_ROUTES = [
    ("/", 200), ("/dashboard", 200), ("/resources", 200), ("/course/1", 200),
    ("/about", 200), ("/contact", 200), ("/settings", 200),
    ("/static/css/app.css", 200), ("/static/js/app.js", 200),
    ("/static/img/logo-mark.png", 200), ("/favicon.ico", 200),
    ("/sitemap.xml", 200), ("/robots.txt", 200), ("/google3c05c71b252e3c7e.html", 200),
    ("/this-route-does-not-exist", 404),
]

ADMIN_ROUTES = [
    "/admin/analytics", "/admin/add_course", "/admin/edit_course/1",
    "/admin/backup", "/admin/resource-subjects", "/admin/resources/add",
    "/admin/resources/submissions", "/admin/add_item/quiz1/1",
]


def check_routes(base_url: str) -> None:
    section("3. Routes")
    try:
        import requests
    except ImportError:
        record(WARN, "requests unavailable -- route checks skipped")
        return

    s = requests.Session()
    try:
        s.get(base_url, timeout=5)
    except Exception:  # noqa: BLE001
        record(FAIL, f"server not responding at {base_url}",
               "fix: python app.py  (or check the port in .env.local)")
        return

    bad = []
    for path, expected in PUBLIC_ROUTES:
        try:
            got = s.get(base_url + path, timeout=10, allow_redirects=False).status_code
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{path}: {exc}")
            continue
        if got != expected:
            bad.append(f"{path}: expected {expected}, got {got}")
    if bad:
        record(FAIL, f"{len(bad)}/{len(PUBLIC_ROUTES)} public routes wrong", "\n".join(bad))
    else:
        record(PASS, f"all {len(PUBLIC_ROUTES)} public routes OK")

    # Admin -- the password comes from the environment, never from source.
    admin_pw = os.environ.get("ADMIN_PASSWORD") or local_env().get("ADMIN_PASSWORD", "")
    logged_in = False
    if admin_pw:
        s.post(base_url + "/admin_login", data={"password": admin_pw}, timeout=10)
        logged_in = s.get(base_url + "/admin/analytics", timeout=10,
                          allow_redirects=False).status_code == 200
    if not logged_in:
        record(WARN, "admin checks skipped",
               "set ADMIN_PASSWORD in .env.local to include the admin pages")
    bad = []
    for path in (ADMIN_ROUTES if logged_in else []):
        try:
            got = s.get(base_url + path, timeout=10, allow_redirects=False).status_code
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{path}: {exc}")
            continue
        if got != 200:
            bad.append(f"{path}: got {got}")
    if bad:
        record(FAIL, f"{len(bad)}/{len(ADMIN_ROUTES)} admin routes wrong", "\n".join(bad))
    elif logged_in:
        record(PASS, f"all {len(ADMIN_ROUTES)} admin routes OK")

    # Pages must actually render the shell, not just return 200.
    shell_bad = []
    shell_pages = ["/dashboard", "/resources", "/course/1"] + (["/admin/analytics"] if logged_in else [])
    for path in shell_pages:
        html = s.get(base_url + path, timeout=10).text
        for part in ("app-header", "app-sidebar", "app-footer"):
            if part not in html:
                shell_bad.append(f"{path}: missing .{part}")
    if shell_bad:
        record(FAIL, "shell missing on some pages", "\n".join(shell_bad))
    else:
        record(PASS, "header / sidebar / footer render on sampled pages")

    # AdSense belongs on public pages only, never on admin screens.
    ad_bad = []
    for path in ("/", "/dashboard", "/resources", "/course/1"):
        if "adsbygoogle" not in s.get(base_url + path, timeout=10).text:
            ad_bad.append(f"{path}: AdSense missing")
    for path in (("/admin/analytics", "/admin/backup") if logged_in else ()):
        if "adsbygoogle" in s.get(base_url + path, timeout=10).text:
            ad_bad.append(f"{path}: AdSense should not load on admin pages")
    if ad_bad:
        record(FAIL, "AdSense placement wrong", "\n".join(ad_bad))
    else:
        record(PASS, "AdSense on public pages only")


# ---------------------------------------------------------------------------
# 4. Design system
# ---------------------------------------------------------------------------

# Colours allowed to be literal: pure black/white for overlays, and the fixed
# medal + chart palettes which are deliberately theme-independent.
ALLOWED_HEX = {
    "#fff", "#ffffff", "#000", "#000000",
    "#f7d154", "#d89f00", "#e4e8eb", "#b7bcc2", "#e7c19b", "#bc7f3d", "#2c2115",
    "#2a78d6", "#eda100", "#e87ba4", "#008300", "#6d4aff",
    "#3987e5", "#c98500", "#d55181", "#8b6bff", "#17161f",
}


def check_design_system() -> None:
    section("4. Design system")

    hardcoded: dict[str, list[str]] = {}
    fonts: dict[str, list[str]] = {}

    for t in templates():
        body = read(t)
        styles = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", body, re.S))
        if not styles:
            continue

        for hx in re.findall(r"#[0-9a-fA-F]{3,8}\b", styles):
            if hx.lower() not in ALLOWED_HEX:
                hardcoded.setdefault(t.name, []).append(hx)

        for fam in re.findall(r"font-family:\s*([^;}\n]+)", styles):
            fam = fam.strip()
            if "var(--font" not in fam and "inherit" not in fam:
                fonts.setdefault(t.name, []).append(fam[:60])

    if hardcoded:
        detail = "\n".join(
            f"{k}: {', '.join(sorted(set(v))[:8])}" for k, v in sorted(hardcoded.items())
        )
        record(WARN, f"{sum(len(v) for v in hardcoded.values())} hardcoded colours "
                     f"in {len(hardcoded)} template(s) -- won't follow the theme", detail)
    else:
        record(PASS, "no off-token colours in template styles")

    if fonts:
        detail = "\n".join(f"{k}: {', '.join(sorted(set(v))[:3])}" for k, v in sorted(fonts.items()))
        record(WARN, f"{len(fonts)} template(s) set their own font-family", detail)
    else:
        record(PASS, "typography comes from the shared tokens everywhere")

    # Heavy inline styling is a smell: it bypasses the design system.
    heavy = []
    for t in templates():
        n = len(re.findall(r'\sstyle="', read(t)))
        if n > 12:
            heavy.append(f"{t.name}: {n} inline style attributes")
    if heavy:
        record(WARN, "heavy inline styling (consider promoting to classes)", "\n".join(heavy))
    else:
        record(PASS, "inline styling kept to a minimum")


# ---------------------------------------------------------------------------
# 5. Consistency
# ---------------------------------------------------------------------------

def check_consistency() -> None:
    section("5. Consistency")

    no_extends, no_container, no_reveal, no_title = [], [], [], []

    for t in templates():
        name, body = t.name, read(t)
        if name == "base.html":
            continue
        if name in ORPHAN_TEMPLATES:
            continue

        if "{% extends" not in body:
            no_extends.append(name)
            continue
        if "{% block title %}" not in body:
            no_title.append(name)
        if name not in NO_PAGE_CONTAINER:
            if 'class="page' not in body:
                no_container.append(name)
            elif "data-reveal-page" not in body:
                no_reveal.append(name)

    if no_extends:
        record(FAIL, "template(s) not on the shared layout", ", ".join(no_extends))
    else:
        record(PASS, "every reachable template extends base.html")

    if no_title:
        record(WARN, "template(s) without a <title> block", ", ".join(no_title))
    else:
        record(PASS, "every page sets its own title")

    if no_container:
        record(WARN, "template(s) without a .page container", ", ".join(no_container))
    else:
        record(PASS, "page container used consistently")

    if no_reveal:
        record(WARN, "page(s) missing scroll-reveal", ", ".join(no_reveal))
    else:
        record(PASS, "scroll-reveal applied on every content page")

    orphans = [t.name for t in templates() if t.name in ORPHAN_TEMPLATES]
    if orphans:
        record(WARN, "template(s) not rendered by any route (dead code)", ", ".join(orphans))

    # Stale class references left behind by refactors.
    css = read(STATIC / "css" / "app.css") if (STATIC / "css" / "app.css").exists() else ""
    stale = [c for c in ("footer-cols", "footer-bottom", "footer-brand")
             if c in css or any(c in read(t) for t in templates())]
    if stale:
        record(WARN, "stale CSS classes still referenced", ", ".join(stale))
    else:
        record(PASS, "no stale layout classes left over")

    # The collapsed-sidebar class must live on <html> (set before first paint).
    js = read(STATIC / "js" / "app.js")
    if "document.body.classList" in js and "sidebar-collapsed" in js:
        record(FAIL, "sidebar class toggled on <body> -- will flash on load")
    else:
        record(PASS, "sidebar state applied pre-paint on <html>")


# ---------------------------------------------------------------------------
# 6. Accessibility
# ---------------------------------------------------------------------------

def check_accessibility() -> None:
    section("6. Accessibility")

    no_alt, unlabelled, unlabelled_inputs = [], [], []

    for t in templates():
        name, body = t.name, read(t)

        for img in re.findall(r"<img\b[^>]*>", body):
            if "alt=" not in img:
                no_alt.append(f"{name}: {img[:70]}")

        # Icon-only buttons need an accessible name.
        for btn in re.findall(r"<button\b[^>]*>(?:\s*<svg.*?</svg>\s*)</button>", body, re.S):
            if "aria-label" not in btn and "title" not in btn:
                unlabelled.append(f"{name}: icon button without a label")

        # Inputs need a label, aria-label, or be hidden/submit types.
        for inp in re.findall(r"<input\b[^>]*>", body):
            if re.search(r'type="(hidden|submit|checkbox|radio)"', inp):
                continue
            has_id = re.search(r'id="([^"]+)"', inp)
            if "aria-label" in inp:
                continue
            if has_id and f'for="{has_id.group(1)}"' in body:
                continue
            unlabelled_inputs.append(f"{name}: {inp[:70]}")

    if no_alt:
        record(FAIL, f"{len(no_alt)} image(s) without alt", "\n".join(no_alt[:6]))
    else:
        record(PASS, "all images have alt attributes")

    if unlabelled:
        record(WARN, f"{len(unlabelled)} icon button(s) without a label", "\n".join(unlabelled[:6]))
    else:
        record(PASS, "icon buttons carry accessible names")

    if unlabelled_inputs:
        record(WARN, f"{len(unlabelled_inputs)} input(s) without a label",
               "\n".join(unlabelled_inputs[:6]))
    else:
        record(PASS, "form inputs are labelled")

    css = read(STATIC / "css" / "app.css")
    for feature, label in (
        ("prefers-reduced-motion", "reduced-motion support"),
        (":focus-visible", "visible focus styles"),
        ("prefers-color-scheme", "OS dark-mode support"),
    ):
        record(PASS if feature in css else WARN,
               f"{label} {'present' if feature in css else 'MISSING'}")


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="MauryaHub health check")
    ap.add_argument("--url", default="http://localhost:5050", help="base URL of the running app")
    ap.add_argument("--no-http", action="store_true", help="skip checks that need a running server")
    args = ap.parse_args()

    os.chdir(ROOT)
    print("\033[1mMauryaHub health check\033[0m")
    print(f"repo: {ROOT}")

    check_environment(not args.no_http)
    check_assets()
    if not args.no_http:
        check_routes(args.url.rstrip("/"))
    check_design_system()
    check_consistency()
    check_accessibility()

    fails = [r for r in _results if r[1] == FAIL]
    warns = [r for r in _results if r[1] == WARN]
    passes = [r for r in _results if r[1] == PASS]

    print("\n" + "=" * 52)
    print(f"  \033[32m{len(passes)} passed\033[0m   "
          f"\033[33m{len(warns)} warnings\033[0m   "
          f"\033[31m{len(fails)} failures\033[0m")
    print("=" * 52)

    if fails:
        print("\n\033[31mFailures:\033[0m")
        for sec, _, msg in fails:
            print(f"  - [{sec}] {msg}")
    if warns:
        print("\n\033[33mWarnings:\033[0m")
        for sec, _, msg in warns:
            print(f"  - [{sec}] {msg}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
