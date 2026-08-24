"""Cross-site scripting regressions.

Stored XSS: four near-identical JS loops concatenated database values into
innerHTML (static/novedades.html:288-292, static/admin-novedades.html:239-243,
templates/template-novedad.html:212-217). `imagen_url` landed inside
style="background-image: url(...)" -- a CSS-context injection that HTML
escaping alone would not have fixed.

Reflected XSS: static/mostrar-datos-contacto.html:22-29 interpolated six URL
query parameters straight into innerHTML.
"""

from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "itsc" / "templates"

SCRIPT = "<script>alert('xss')</script>"


@pytest.mark.security
def test_stored_xss_in_titulo_is_escaped(client, db, admin_user):
    from datetime import UTC, datetime

    from itsc.models import Novedad

    db.session.add(
        Novedad(
            slug="xss-titulo",
            titulo=SCRIPT,
            resumen=f"resumen {SCRIPT}",
            cuerpo="cuerpo",
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    db.session.commit()

    for path in ("/novedades/", "/novedades/xss-titulo", "/"):
        html = client.get(path).get_data(as_text=True)
        assert "<script>alert(" not in html, f"unescaped payload rendered at {path}"
        assert "&lt;script&gt;" in html, f"payload not present as text at {path}"


@pytest.mark.security
@pytest.mark.parametrize(
    "payload,forbidden",
    [
        ("<script>alert(1)</script>", "<script>"),
        ('<img src=x onerror="alert(1)">', "onerror"),
        ('<iframe src="https://evil.example"></iframe>', "<iframe"),
        ("[link](javascript:alert(1))", "javascript:"),
        ('<a href="vbscript:alert(1)">x</a>', "vbscript:"),
        ("<object data='evil'></object>", "<object"),
        ("<style>body{display:none}</style>", "<style>"),
    ],
)
def test_markdown_body_is_sanitised(client, db, payload, forbidden):
    from datetime import UTC, datetime

    from itsc.models import Novedad

    db.session.add(
        Novedad(
            slug="xss-cuerpo",
            titulo="Titulo limpio",
            resumen="Resumen limpio",
            cuerpo=payload,
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    db.session.commit()

    response = client.get("/novedades/xss-cuerpo")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # No closing quote in the needle: the element carries two classes
    # (class="article__body wrap"), so an exact-attribute match never hits.
    marker = 'class="article__body'
    assert marker in html, "article body not rendered"
    body = html.split(marker, 1)[1].split("</div>", 1)[0]
    assert forbidden not in body, f"{forbidden!r} survived sanitisation"


@pytest.mark.security
def test_sanitiser_keeps_legitimate_markup(client, db):
    from datetime import UTC, datetime

    from itsc.models import Novedad

    db.session.add(
        Novedad(
            slug="markdown-ok",
            titulo="Formato",
            resumen="Resumen",
            cuerpo="Texto **fuerte** y [un enlace](https://example.org).",
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    db.session.commit()

    html = client.get("/novedades/markdown-ok").get_data(as_text=True)
    assert "<strong>" in html
    assert "https://example.org" in html
    # nh3 adds rel=noopener, so an external link cannot reach window.opener.
    assert "noopener" in html


@pytest.mark.security
def test_media_url_contains_no_user_controlled_bytes(admin_client, db, real_jpeg, token):
    """Regression for the background-image:url() CSS-context sink.

    The image URL is now built from a server-generated UUID, so there is no
    attacker-controlled substring in it at all.
    """
    import io

    # No double quotes: those break multipart Content-Disposition parsing,
    # so the filename would arrive mangled and the test would prove nothing.
    # The CSS-context characters that matter are still present.
    hostile_name = "x);background:url(evil-payload.jpg"
    response = admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Con imagen",
            "resumen": "r" * 20,
            "cuerpo": "cuerpo",
            "status": "published",
            "imagen_alt": "alt",
            "imagen": (io.BytesIO(real_jpeg), hostile_name),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    from itsc.models import MediaAsset

    asset = db.session.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
    assert asset is not None
    assert "evil" not in asset.storage_key
    assert "background" not in asset.storage_key
    assert asset.storage_key.endswith(".webp")


@pytest.mark.security
def test_contact_gracias_ignores_query_parameters(client):
    """Regression for mostrar-datos-contacto.html:22-29."""
    response = client.get(
        "/contacto/gracias",
        query_string={
            "nombre": "<img src=x onerror=alert(1)>",
            "email": "<script>alert(2)</script>",
            "mensaje": "javascript:alert(3)",
        },
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "onerror" not in html
    assert "<script>alert" not in html
    assert "javascript:alert" not in html


@pytest.mark.security
def test_safe_filter_is_confined_to_one_audited_line():
    """`|safe` and autoescape-off must not spread beyond the sanitised body."""
    import re

    # Strip {# Jinja comments #} first: prose *describing* the rule is not a
    # violation of it, and matching raw lines flags this file's own docs.
    comment = re.compile(r"\{#.*?#\}", re.DOTALL)
    unsafe_expr = re.compile(r"\{\{[^}]*\|\s*safe\b")
    autoescape_off = re.compile(r"\{%-?\s*autoescape\s+false")

    offenders = []
    for path in TEMPLATES.rglob("*.html"):
        text = comment.sub("", path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(text.splitlines(), 1):
            if unsafe_expr.search(line) or autoescape_off.search(line):
                offenders.append(f"{path.relative_to(TEMPLATES)}:{lineno}")
    assert not offenders, "unescaped output outside the audited boundary: " + ", ".join(offenders)
