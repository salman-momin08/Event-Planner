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


def _rel_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(c1: str, c2: str) -> float:
    l1, l2 = _rel_luminance(c1), _rel_luminance(c2)
    bright, dark = max(l1, l2), min(l1, l2)
    return (bright + 0.05) / (dark + 0.05)


def test_075_design_token_contrast_ratios_meet_wcag_aa():
    css = (PUBLIC / "styles.css").read_text(encoding="utf-8")
    blocks = css.split("@media (prefers-color-scheme: dark)")
    assert len(blocks) == 2

    for mode, block in (("light", blocks[0]), ("dark", blocks[1])):
        tokens = dict(re.findall(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", block))
        text_pairs = [
            ("text", "bg", 4.5),
            ("text", "surface", 4.5),
            ("text", "surface-2", 4.5),
            ("muted", "surface", 4.5),
            ("primary-text", "surface", 4.5),
            ("primary", "on-primary", 4.5),
            ("danger-text", "surface", 4.5),
            ("danger-text", "danger-soft", 4.5),
            ("ok", "ok-soft", 4.5),
            ("warn", "warn-soft", 4.5),
        ]
        for fg, bg, min_ratio in text_pairs:
            ratio = _contrast(tokens[fg], tokens[bg])
            assert ratio >= min_ratio, f"{mode} --{fg} ({tokens[fg]}) on --{bg} ({tokens[bg]}) ratio {ratio:.2f} < {min_ratio}"


def test_076_accessible_dialog_checkbox_multiselect_table_roles_and_focus_restoration():
    dom_js = (PUBLIC / "dom.js").read_text(encoding="utf-8")
    app_js = (PUBLIC / "app.js").read_text(encoding="utf-8")
    assert "'dialog'" in dom_js and "showModal" in dom_js
    assert "checkbox-fieldset" in dom_js and "role: 'table'" in dom_js and "role: 'rowheader'" in dom_js
    assert "captureFocusState" in app_js and "restoreFocusState" in app_js


def test_077_frontend_modules_execute_in_node():
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node is not None
    script = """
    import { parseMoney, centsToInput, formatDate } from './frontend/dom.js';
    if (parseMoney('1250.50') !== 125050) throw new Error('parseMoney failed');
    if (parseMoney('invalid') !== null) throw new Error('parseMoney invalid failed');
    if (centsToInput(125050) !== '1250.50') throw new Error('centsToInput failed');
    if (!formatDate('2027-06-12').includes('2027')) throw new Error('formatDate failed');
    """
    res = subprocess.run([node, "--input-type=module", "-e", script], cwd=PUBLIC.parent, capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
