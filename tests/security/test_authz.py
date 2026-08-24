"""Authorisation regressions.

The original had no authentication anywhere: POST, PUT and DELETE on
/novedades were reachable by anyone on the internet, and `CORS(app)` meant any
website could invoke them from a visitor's browser.
"""

from __future__ import annotations

import pytest

PLACEHOLDERS = {
    "<int:novedad_id>": "1",
    "<int:document_id>": "1",
    "<int:message_id>": "1",
    "<int:codigo>": "1",
    "<slug>": "una-novedad-de-prueba",
    "<categoria>": "convocatorias",
    "<vigencia>": "vigentes",
    "<path:filename>": "css/main.css",
}


def _concrete(rule: str) -> str | None:
    for placeholder, value in PLACEHOLDERS.items():
        rule = rule.replace(placeholder, value)
    return None if "<" in rule else rule


@pytest.mark.security
def test_every_admin_route_rejects_anonymous(app, client):
    """Enumerates the url_map, so a newly-added admin view is covered
    automatically rather than requiring someone to remember a test."""
    leaks = []
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/admin"):
            continue
        path = _concrete(str(rule))
        if path is None:
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            response = client.open(path, method=method)
            if response.status_code not in (301, 302, 400, 401, 403, 405):
                leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "unauthenticated access permitted: " + "; ".join(leaks)


@pytest.mark.security
def test_every_non_get_route_rejects_anonymous(app, client):
    """No mutating endpoint anywhere may succeed without a session."""
    allowed_public = {"/contacto/", "/ingresar"}  # public forms, CSRF-protected
    leaks = []
    for rule in app.url_map.iter_rules():
        methods = rule.methods - {"HEAD", "OPTIONS", "GET"}
        if not methods:
            continue
        path = _concrete(str(rule))
        if path is None or path in allowed_public:
            continue
        for method in sorted(methods):
            response = client.open(path, method=method)
            if response.status_code not in (301, 302, 400, 401, 403, 405):
                leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "unauthenticated mutation permitted: " + "; ".join(leaks)


@pytest.mark.security
def test_admin_accessible_once_authenticated(admin_client):
    assert admin_client.get("/admin/").status_code == 200


@pytest.mark.security
def test_delete_rejects_get(admin_client, novedad):
    """A GET-triggered delete is reachable by any <img> tag or link prefetcher."""
    response = admin_client.get(f"/admin/novedades/{novedad.id}/eliminar")
    assert response.status_code == 405


@pytest.mark.security
def test_login_next_parameter_cannot_redirect_offsite(client, admin_user, token):
    """Without this guard the login form is an open redirect, i.e. a phishing
    primitive: a link to the real site that lands on an attacker's page."""
    for hostile in (
        "https://evil.example/phish",
        "//evil.example",
        "http://evil.example",
        "\\\\evil.example",
    ):
        response = client.post(
            "/ingresar",
            query_string={"next": hostile},
            data={
                "username": "admin_test",
                "password": "Test-Admin-Pass-2026",
                "csrf_token": token(client, "/ingresar"),
            },
        )
        location = response.headers.get("Location", "")
        assert "evil.example" not in location, f"open redirect via {hostile!r}"


@pytest.mark.security
def test_logout_requires_post(admin_client):
    assert admin_client.get("/salir").status_code == 405


@pytest.mark.security
def test_account_locks_after_repeated_failures(client, admin_user, db, token):
    from itsc.models.user import MAX_FAILED_LOGINS

    for _ in range(MAX_FAILED_LOGINS):
        client.post(
            "/ingresar",
            data={
                "username": "admin_test",
                "password": "definitely-wrong",
                "csrf_token": token(client, "/ingresar"),
            },
        )
    db.session.refresh(admin_user)
    assert admin_user.is_locked, "account should lock after repeated failures"

    # Correct credentials must still be refused while locked.
    response = client.post(
        "/ingresar",
        data={
            "username": "admin_test",
            "password": "Test-Admin-Pass-2026",
            "csrf_token": token(client, "/ingresar"),
        },
    )
    assert response.status_code == 429


@pytest.mark.security
def test_login_failure_message_is_identical_for_unknown_user_and_bad_password(
    client, admin_user, token
):
    """Differing messages turn the login form into a username oracle."""
    unknown = client.post(
        "/ingresar",
        data={
            "username": "no_such_user",
            "password": "x" * 12,
            "csrf_token": token(client, "/ingresar"),
        },
    ).get_data(as_text=True)
    bad_password = client.post(
        "/ingresar",
        data={
            "username": "admin_test",
            "password": "x" * 12,
            "csrf_token": token(client, "/ingresar"),
        },
    ).get_data(as_text=True)

    from itsc.blueprints.auth import GENERIC_FAILURE

    assert GENERIC_FAILURE in unknown
    assert GENERIC_FAILURE in bad_password
