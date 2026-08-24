"""Shared pytest fixtures.

Two decisions here are deliberate and load-bearing:

1. **Real PostgreSQL, never SQLite.** SQLite would silently skip CITEXT,
   generated TSVECTOR columns, partial unique indexes and ON DELETE RESTRICT --
   i.e. most of the integrity guarantees the schema relies on. A green suite
   against SQLite would prove almost nothing about production.

2. **CSRF stays ENABLED.** Most suites disable it for convenience, and that is
   precisely how CSRF regressions reach production. Tests scrape the real token
   instead; `tests/security/test_csrf.py` then asserts the negative case
   honestly.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pytest
from PIL import Image

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault(
    "DATABASE_URL_TEST", "postgresql+psycopg://itsc:itsc@localhost:55432/itsc_test"
)

from itsc import create_app
from itsc.extensions import db as _db


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    upload_root = tmp_path_factory.mktemp("uploads")
    os.environ["UPLOAD_ROOT"] = str(upload_root)

    application = create_app("testing")
    application.config.update(
        UPLOAD_ROOT=upload_root,
        # Must match the host the test client sends. With SERVER_NAME set,
        # Werkzeug refuses to route a request whose Host header differs --
        # every route 404s and the cause is invisible in the response.
        SERVER_NAME="localhost",
        RATELIMIT_ENABLED=False,
    )

    with application.app_context():
        # Build the schema by running the real migrations rather than
        # db.create_all(): every test run is therefore also a migration test,
        # and a broken migration fails CI instead of production.
        from flask_migrate import upgrade

        _db.drop_all()
        _db.session.execute(_db.text("DROP TABLE IF EXISTS alembic_version"))
        _db.session.commit()
        upgrade()
        yield application


#: Every table the app owns, child-first so TRUNCATE ... CASCADE is not needed
#: for ordering reasons (it is still passed, for FK safety).
_TABLES = (
    "document_files",
    "documents",
    "document_categories",
    "novedades",
    "contact_messages",
    "media_assets",
    "users",
)


@pytest.fixture
def db(app):
    """Function-scoped isolation by truncation.

    The tidier "wrap each test in a transaction and roll back" recipe does not
    hold here: Flask-SQLAlchemy scopes its session to the *app context*, and
    every test-client request pushes its own. Those requests therefore get a
    different session, bound to the engine rather than to our connection, so
    their commits are real and survive the outer rollback.

    Truncating between tests is less elegant but is actually correct, and on
    seven small tables it costs about a millisecond.
    """
    with app.app_context():
        yield _db
        _db.session.rollback()
        _db.session.remove()
        with _db.engine.begin() as connection:
            connection.execute(_db.text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(app, db):
    return app.test_client()


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
ADMIN_PASSWORD = "Test-Admin-Pass-2026"
EDITOR_PASSWORD = "Test-Editor-Pass-2026"


@pytest.fixture
def admin_user(db):
    from itsc.models import User

    user = User(username="admin_test", email="admin@test.local", role="admin")
    user.set_password(ADMIN_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def editor_user(db):
    from itsc.models import User

    user = User(username="editor_test", email="editor@test.local", role="editor")
    user.set_password(EDITOR_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def csrf_token(client, path):
    """Scrape a real CSRF token from a rendered form."""
    html = client.get(path).get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return match.group(1) if match else None


@pytest.fixture
def token():
    return csrf_token


@pytest.fixture
def login(client):
    def _login(username: str, password: str):
        return client.post(
            "/ingresar",
            data={
                "username": username,
                "password": password,
                "csrf_token": csrf_token(client, "/ingresar"),
            },
            follow_redirects=False,
        )

    return _login


@pytest.fixture
def admin_client(client, admin_user, login):
    login("admin_test", ADMIN_PASSWORD)
    return client


@pytest.fixture
def editor_client(client, editor_user, login):
    login("editor_test", EDITOR_PASSWORD)
    return client


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------
@pytest.fixture
def categories(db):
    from itsc.models import DocumentCategory
    from itsc.models.document import CATEGORY_SLUGS

    created = []
    for i, slug in enumerate(CATEGORY_SLUGS):
        category = DocumentCategory(
            slug=slug,
            nombre=slug.replace("-", " ").title(),
            orden=i,
            has_vigencia=slug in {"convocatorias", "mesas-de-examen"},
        )
        db.session.add(category)
        created.append(category)
    db.session.commit()
    return created


@pytest.fixture
def novedad(db, admin_user):
    from datetime import UTC, datetime

    from itsc.models import Novedad

    item = Novedad(
        slug="una-novedad-de-prueba",
        titulo="Una novedad de prueba",
        resumen="Resumen de la novedad de prueba.",
        cuerpo="Cuerpo **con formato**.",
        status="published",
        published_at=datetime.now(UTC),
        author_id=admin_user.id,
    )
    db.session.add(item)
    db.session.commit()
    return item


# --------------------------------------------------------------------------
# Upload fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def real_jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 90), "steelblue").save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def jpeg_with_payload() -> bytes:
    """A genuine JPEG carrying a script tag in its comment segment."""
    buffer = io.BytesIO()
    Image.new("RGB", (120, 90), "red").save(
        buffer, "JPEG", comment=b"<script>alert('polyglot')</script>"
    )
    return buffer.getvalue()


@pytest.fixture
def html_file() -> bytes:
    return b"<!doctype html><html><script>alert('xss')</script></html>"


@pytest.fixture
def svg_file() -> bytes:
    return b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture
def upload_dir(app) -> Path:
    return Path(app.config["UPLOAD_ROOT"])
