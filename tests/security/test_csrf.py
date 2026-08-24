"""CSRF regressions.

The admin delete was `fetch(URL + 'novedades/' + codigo, {method:'DELETE'})`
with no token and no authentication, and `CORS(app)` allowed any origin -- so
any website could delete every news item from a visitor's browser.
"""

from __future__ import annotations

import pytest


@pytest.mark.security
def test_contact_post_without_token_is_rejected(client):
    response = client.post(
        "/contacto/",
        data={
            "asunto": "Consulta",
            "nombre": "Alguien",
            "email": "a@b.co",
            "motivo": "Otro",
            "mensaje": "x" * 30,
        },
    )
    assert response.status_code == 400


@pytest.mark.security
def test_login_post_without_token_is_rejected(client, admin_user):
    response = client.post(
        "/ingresar", data={"username": "admin_test", "password": "Test-Admin-Pass-2026"}
    )
    assert response.status_code == 400


@pytest.mark.security
def test_admin_delete_without_token_is_rejected(admin_client, novedad, db):
    from itsc.models import Novedad

    response = admin_client.post(f"/admin/novedades/{novedad.id}/eliminar")
    assert response.status_code == 400
    assert db.session.get(Novedad, novedad.id) is not None, "row deleted without a CSRF token"


@pytest.mark.security
def test_admin_delete_with_token_succeeds(admin_client, novedad, db, token):
    from itsc.models import Novedad

    novedad_id = novedad.id
    response = admin_client.post(
        f"/admin/novedades/{novedad_id}/eliminar",
        data={"csrf_token": token(admin_client, "/admin/novedades")},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert db.session.get(Novedad, novedad_id) is None


@pytest.mark.security
def test_forged_token_is_rejected(client):
    response = client.post(
        "/contacto/",
        data={
            "asunto": "Consulta",
            "nombre": "Alguien",
            "email": "a@b.co",
            "motivo": "Otro",
            "mensaje": "x" * 30,
            "csrf_token": "not-a-real-token",
        },
    )
    assert response.status_code == 400


@pytest.mark.security
def test_session_cookie_flags(app, client, admin_user, token):
    """__Host- prefix, HttpOnly and SameSite are what stop a sibling subdomain
    or a script from taking the session."""
    client.post(
        "/ingresar",
        data={
            "username": "admin_test",
            "password": "Test-Admin-Pass-2026",
            "csrf_token": token(client, "/ingresar"),
        },
    )
    cookies = [h for k, h in client.get("/admin/").headers if k == "Set-Cookie"]
    # In testing SESSION_COOKIE_SECURE is off (no TLS), so assert the config
    # contract instead, plus the flags that do apply everywhere.
    from itsc.config import ProductionConfig

    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_NAME.startswith("__Host-")
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Lax"
    assert all("HttpOnly" in c for c in cookies if "session" in c.lower())


@pytest.mark.security
def test_login_rotates_the_session(client, admin_user, token):
    """Session fixation: the pre-login id must not survive authentication."""
    client.get("/ingresar")
    before = client.get_cookie("session")
    before_value = before.value if before else None

    client.post(
        "/ingresar",
        data={
            "username": "admin_test",
            "password": "Test-Admin-Pass-2026",
            "csrf_token": token(client, "/ingresar"),
        },
    )
    after = client.get_cookie("session")
    assert after is not None
    if before_value:
        assert after.value != before_value, "session id was not rotated on login"
