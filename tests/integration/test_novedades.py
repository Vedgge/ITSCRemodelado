"""News listing, detail, feed and API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from itsc.models import Novedad


def _make(db, slug, *, status="published", days_ago=0, titulo=None):
    item = Novedad(
        slug=slug,
        titulo=titulo or slug.replace("-", " ").title(),
        resumen="Resumen de prueba suficientemente largo.",
        cuerpo="Cuerpo de la novedad.",
        status=status,
        published_at=datetime.now(UTC) - timedelta(days=days_ago)
        if status == "published"
        else None,
    )
    db.session.add(item)
    db.session.commit()
    return item


def test_listing_shows_published(client, db):
    _make(db, "publicada-uno")
    html = client.get("/novedades/").get_data(as_text=True)
    assert "Publicada Uno" in html


def test_listing_hides_drafts(client, db):
    _make(db, "un-borrador", status="draft", titulo="Borrador Secreto")
    html = client.get("/novedades/").get_data(as_text=True)
    assert "Borrador Secreto" not in html


def test_draft_detail_is_404(client, db):
    _make(db, "otro-borrador", status="draft")
    assert client.get("/novedades/otro-borrador").status_code == 404


def test_detail_renders(client, novedad):
    html = client.get(f"/novedades/{novedad.slug}").get_data(as_text=True)
    assert novedad.titulo in html
    assert "<strong>" in html, "markdown body was not rendered"


def test_listing_is_newest_first(client, db):
    _make(db, "vieja", days_ago=30, titulo="Noticia Vieja")
    _make(db, "nueva", days_ago=1, titulo="Noticia Nueva")
    html = client.get("/novedades/").get_data(as_text=True)
    assert html.index("Noticia Nueva") < html.index("Noticia Vieja")


def test_pagination(client, db, app):
    per_page = app.config["NOVEDADES_PER_PAGE"]
    for i in range(per_page + 3):
        _make(db, f"novedad-{i}", days_ago=i)
    page1 = client.get("/novedades/").get_data(as_text=True)
    assert "Siguiente" in page1
    assert client.get("/novedades/?page=2").status_code == 200


def test_empty_state(client, db):
    html = client.get("/novedades/").get_data(as_text=True)
    assert "Todavía no hay novedades" in html


def test_rss_feed(client, novedad):
    response = client.get("/novedades/feed.xml")
    assert response.status_code == 200
    assert response.mimetype == "application/rss+xml"
    body = response.get_data(as_text=True)
    assert "<rss" in body and novedad.titulo in body


def test_legacy_numeric_url_redirects_to_slug(client, novedad):
    response = client.get(f"/novedades/{novedad.id}")
    assert response.status_code == 301
    assert novedad.slug in response.headers["Location"]


def test_api_returns_published_only(client, db):
    _make(db, "api-publicada", titulo="Api Publicada")
    _make(db, "api-borrador", status="draft", titulo="Api Borrador")
    data = client.get("/api/v1/novedades").get_json()
    titles = [item["titulo"] for item in data["data"]]
    assert "Api Publicada" in titles
    assert "Api Borrador" not in titles


def test_api_per_page_is_capped(client, app, db):
    _make(db, "una")
    data = client.get("/api/v1/novedades?per_page=99999").get_json()
    assert data["meta"]["per_page"] <= app.config["API_MAX_PER_PAGE"]


def test_api_never_exposes_internal_columns(client, novedad):
    """Explicit serialisation: the old endpoint returned whole ORM rows."""
    item = client.get("/api/v1/novedades").get_json()["data"][0]
    assert set(item) == {"slug", "titulo", "resumen", "publicado", "url", "imagen"}
    assert "author_id" not in item and "search_vector" not in item


def test_api_404_is_json_problem(client):
    response = client.get("/api/v1/novedades/no-existe")
    assert response.status_code == 404
    assert "application/problem+json" in response.content_type
    assert response.get_json()["status"] == 404
