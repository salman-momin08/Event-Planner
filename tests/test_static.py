from __future__ import annotations

import re
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "frontend"


def _sources():
    return [p for ext in ("*.js", "*.html", "*.css") for p in PUBLIC.rglob(ext)]


def test_073_frontend_has_no_xss_sinks_inline_handlers_or_external_resources():
    forbidden = [
        r"\.innerHTML\b", r"\.outerHTML\b", r"insertAdjacentHTML", r"document\.write", r"\beval\s*\(",
        r"new\s+Function\s*\(", r"setTimeout\s*\(\s*['\"`]", r"javascript:", r"srcdoc",
    ]
    files = _sources()
    assert len(files) >= 8
    for f in files:
        text = f.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert not re.search(pattern, text, re.I), f"{f.name} matches {pattern}"
        assert not re.search(r"https?://", text, re.I), f"{f.name} references an external URL"
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"\son[a-z]+\s*=", html, re.I)
    assert not re.search(r"\sstyle\s*=", html, re.I)
    assert not re.search(r"<script(?![^>]*\ssrc=)", html, re.I)


def test_074_index_has_language_viewport_skip_link_landmarks_and_live_region():
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    assert '<html lang="en"' in html
    assert '<meta name="viewport" content="width=device-width, initial-scale=1"' in html
    assert not re.search(r"user-scalable\s*=\s*no|maximum-scale", html, re.I)
    assert re.search(r"<title>[^<]+</title>", html)
    assert '<a class="skip-link" href="#main">' in html
    assert re.search(r"<header[\s>]", html)
    assert re.search(r'<nav[^>]*aria-label="[^"]+"', html)
    assert '<main id="main"' in html
    assert 'role="status"' in html and 'aria-live="polite"' in html


def test_074b_css_reduced_motion_and_focus_visible():
    css = (PUBLIC / "styles.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css and ":focus-visible" in css
