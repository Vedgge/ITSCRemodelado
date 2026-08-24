"""Legacy URL redirects, health endpoints and error pages."""

from __future__ import annotations

import pytest

from itsc.blueprints.legacy import REDIRECTS


@pytest.mark.parametrize("filename", sorted(REDIRECTS))
def test_legacy_url_redirects_permanently(client, categories, filename):
    response = client.get(f"/static/{filename}")
    assert response.status_code == 301, f"/static/{filename} did not redirect"
    assert response.headers["Location"]


@pytest.mark.parametrize("filename", sorted(REDIRECTS))
def test_legacy_target_actually_resolves(client, categories, admin_user, filename):
    """A 301 pointing at a 404 is worse than no redirect at all."""
    location = client.get(f"/static/{filename}").headers["Location"]
    status = client.get(location).status_code
    assert status < 400 or status == 302, f"{filename} -> {location} returned {status}"


def test_unmapped_legacy_path_is_404_not_a_silent_redirect(client):
    """Explicit rules, not a catch-all: an unknown old URL must 404."""
    assert client.get("/static/inventado.html").status_code == 404


def test_healthz_does_not_touch_the_database(client, monkeypatch):
    """If liveness checked the DB, a brief outage would restart-loop every
    container and turn a 5-second blip into a full one."""
    from itsc.extensions import db

    def explode(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(db.session, "execute", explode)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_readyz_reports_dependencies(client):
    payload = client.get("/readyz").get_json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"]["ok"] is True
    assert payload["checks"]["database"]["migration"], "migration revision not reported"
    assert payload["checks"]["uploads"]["ok"] is True


def test_404_renders_a_page_not_a_traceback(client):
    response = client.get("/no-existe-esta-pagina")
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Traceback" not in html
    assert "Página no encontrada" in html
    assert "Referencia:" in html, "request id should be shown for support"


def test_error_pages_carry_the_request_id_header(client):
    response = client.get("/no-existe")
    assert response.headers.get("X-Request-ID")


def test_json_errors_use_problem_json(client):
    response = client.get("/api/v1/novedades/nope")
    assert response.status_code == 404
    assert response.content_type.startswith("application/problem+json")
    body = response.get_json()
    assert body["status"] == 404 and "request_id" in body


def test_405_on_wrong_method(client):
    assert client.post("/nosotros").status_code == 405
