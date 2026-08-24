"""Response-header and CSP regressions."""

from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "itsc" / "templates"


@pytest.mark.security
@pytest.mark.parametrize(
    "header,expected",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
    ],
)
def test_security_headers_present(client, header, expected):
    assert client.get("/").headers.get(header) == expected


@pytest.mark.security
@pytest.mark.parametrize(
    "directive",
    [
        "default-src 'self'",
        "script-src 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
    ],
)
def test_csp_directives(client, directive):
    assert directive in client.get("/").headers.get("Content-Security-Policy", "")


@pytest.mark.security
def test_csp_has_no_unsafe_escape_hatches(client):
    """A CSP with 'unsafe-inline' that will be "tightened later" never is."""
    csp = client.get("/").headers.get("Content-Security-Policy", "")
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


@pytest.mark.security
def test_no_cors_headers_anywhere(client, novedad):
    """Regression for CORS(app) at main.py:6."""
    for path in ("/", "/novedades/", "/api/v1/novedades", "/ingresar", "/contacto/"):
        headers = client.get(path).headers
        assert "Access-Control-Allow-Origin" not in headers, f"CORS header present on {path}"


@pytest.mark.security
def test_permissions_policy_is_not_clobbered(client):
    """Flask runs after_request in reverse registration order; this asserts our
    policy wins over Talisman's default rather than being silently replaced."""
    policy = client.get("/").headers.get("Permissions-Policy", "")
    for feature in ("geolocation=()", "camera=()", "microphone=()"):
        assert feature in policy


@pytest.mark.security
def test_request_id_is_returned(client):
    assert client.get("/").headers.get("X-Request-ID")


@pytest.mark.security
def test_no_inline_scripts_or_styles_in_templates():
    """Keeps the strict CSP from rotting.

    A single inline <script> added later would silently break every page under
    `script-src 'self'`; this fails the build instead.
    """
    import re

    script_body = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", re.IGNORECASE)
    inline_style_attr = re.compile(r"\sstyle\s*=\s*[\"']", re.IGNORECASE)
    style_block = re.compile(r"<style[^>]*>", re.IGNORECASE)

    offenders = []
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(TEMPLATES)
        if script_body.search(text):
            offenders.append(f"{rel}: inline <script> body")
        if inline_style_attr.search(text):
            offenders.append(f"{rel}: inline style= attribute")
        if style_block.search(text):
            offenders.append(f"{rel}: <style> block")
    assert not offenders, "CSP-incompatible markup: " + "; ".join(offenders)


@pytest.mark.security
def test_templates_have_no_absolute_or_localhost_urls():
    """`const URL = "http://127.0.0.1:5000/"` was copy-pasted seven times and
    is the reason the original deployment never worked."""
    offenders = []
    roots = [TEMPLATES, TEMPLATES.parent / "static" / "js"]
    for root in roots:
        if not root.exists():
            continue
        for path in list(root.rglob("*.html")) + list(root.rglob("*.js")):
            text = path.read_text(encoding="utf-8")
            for needle in ("127.0.0.1", "localhost:5000", "http://localhost"):
                if needle in text:
                    offenders.append(f"{path.name}: {needle}")
    assert not offenders, "hardcoded host found: " + "; ".join(offenders)
