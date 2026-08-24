"""Error handling, health failure paths, and the role decorator."""

from __future__ import annotations

import pytest


def test_unhandled_exception_renders_a_page_not_a_traceback(app, client, monkeypatch):
    """Regression for app.run(debug=True), which exposed the Werkzeug console."""
    from itsc.services import novedades as service

    def boom(*args, **kwargs):
        raise RuntimeError("algo explotó")

    monkeypatch.setattr(service, "list_published", boom)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.get("/novedades/")
    assert response.status_code == 500
    html = response.get_data(as_text=True)
    assert "Traceback" not in html
    assert "algo explotó" not in html, "internal error text leaked to the user"
    assert "Referencia:" in html


def test_error_handler_survives_a_logging_failure(app, client, monkeypatch):
    """An exception raised *inside* the error handler escapes as a bare
    traceback -- exactly what the handler exists to prevent."""
    import itsc.errors as errors
    from itsc.services import novedades as service

    monkeypatch.setattr(service, "list_published", lambda *a, **k: 1 / 0)

    class BrokenLogger:
        def error(self, *args, **kwargs):
            raise RuntimeError("logging backend down")

        def info(self, *args, **kwargs):
            pass

    monkeypatch.setattr(errors, "log", BrokenLogger())
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.get("/novedades/")
    assert response.status_code == 500
    assert "Traceback" not in response.get_data(as_text=True)


def test_413_when_upload_exceeds_the_limit(admin_client, app, token):
    import io

    oversize = b"\x00" * (app.config["MAX_CONTENT_LENGTH"] + 2048)
    response = admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Grande",
            "resumen": "r" * 20,
            "cuerpo": "c",
            "status": "draft",
            "imagen": (io.BytesIO(oversize), "grande.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    assert "Traceback" not in response.get_data(as_text=True)


def test_readyz_reports_a_database_outage(client, monkeypatch):
    from itsc.extensions import db

    def explode(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db.session, "execute", explode)
    response = client.get("/readyz")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["checks"]["database"]["ok"] is False
    # The error *type* is reported, never the message: an exception string can
    # carry a connection URI, complete with credentials.
    assert "db down" not in str(payload)


def test_readyz_reports_an_unwritable_upload_directory(client, app, monkeypatch):
    from pathlib import Path

    def explode(self, *args, **kwargs):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(Path, "write_text", explode)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.get_json()["checks"]["uploads"]["ok"] is False


def test_role_required_rejects_the_wrong_role(app, client, editor_user, login):

    from itsc.security import role_required

    # Exercise the decorator directly rather than adding a route after the
    # first request, which Flask forbids.
    with app.test_request_context():
        from flask_login import login_user

        login_user(editor_user)

        @role_required("admin")
        def admin_only():
            return "ok"

        with pytest.raises(Exception) as exc:  # werkzeug Forbidden
            admin_only()
        assert "403" in str(exc.value) or "Forbidden" in str(type(exc.value).__name__)


def test_role_required_allows_the_right_role(app, admin_user):
    from itsc.security import role_required

    with app.test_request_context():
        from flask_login import login_user

        login_user(admin_user)

        @role_required("admin")
        def admin_only():
            return "ok"

        assert admin_only() == "ok"


def test_asset_helper_adds_a_content_hash(client):
    """Lets nginx serve /static as immutable for a year: the URL changes
    whenever the bytes do."""
    html = client.get("/").get_data(as_text=True)
    assert "css/main.css?v=" in html


def test_request_id_is_taken_from_the_proxy_when_provided(client):
    response = client.get("/", headers={"X-Request-ID": "abc123fromnginx"})
    assert response.headers["X-Request-ID"] == "abc123fromnginx"
