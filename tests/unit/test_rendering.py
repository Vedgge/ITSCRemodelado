"""Markdown rendering and sanitisation."""

from __future__ import annotations

import pytest

from itsc.services.rendering import excerpt, render_markdown


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<iframe src='https://evil.example'></iframe>",
        "<object data='x'></object>",
        "<embed src='x'>",
        "<style>body{display:none}</style>",
        "<form action='/'><input name=x></form>",
        "<svg onload=alert(1)>",
    ],
)
def test_dangerous_tags_are_stripped(app, payload):
    with app.app_context():
        assert "<script" not in str(render_markdown(payload))
        out = str(render_markdown(payload)).lower()
        for tag in ("<iframe", "<object", "<embed", "<style", "<form", "<svg"):
            assert tag not in out


def test_event_handlers_are_stripped(app):
    with app.app_context():
        out = str(render_markdown('<img src="x" onerror="alert(1)">'))
    assert "onerror" not in out


@pytest.mark.parametrize("scheme", ["javascript:", "vbscript:", "data:text/html"])
def test_dangerous_url_schemes_are_stripped(app, scheme):
    with app.app_context():
        out = str(render_markdown(f'<a href="{scheme}alert(1)">x</a>'))
    assert scheme not in out


def test_legitimate_markdown_survives(app):
    with app.app_context():
        out = str(render_markdown("**negrita** y *cursiva*\n\n- uno\n- dos"))
    assert "<strong>" in out and "<em>" in out and "<li>" in out


def test_external_links_get_noopener(app):
    with app.app_context():
        out = str(render_markdown("[x](https://example.org)"))
    assert "noopener" in out


def test_empty_input(app):
    with app.app_context():
        assert str(render_markdown(None)) == ""
        assert str(render_markdown("")) == ""


def test_excerpt_strips_markup_and_truncates(app):
    with app.app_context():
        result = excerpt("**Hola** " + "palabra " * 100, length=50)
    assert "<strong>" not in result and "**" not in result
    assert len(result) <= 55
    assert result.endswith("…")


def test_excerpt_leaves_short_text_intact(app):
    with app.app_context():
        assert excerpt("Texto corto") == "Texto corto"
