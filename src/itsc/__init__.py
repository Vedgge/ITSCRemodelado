"""ITSC application factory.

The original ``main.py`` created a Flask app, a live MySQL connection and a
route table at import time, then called ``app.run(debug=True)``.  Nothing about
that could be tested, forked by a WSGI server, or configured per-environment.

This module exposes exactly one public name: :func:`create_app`.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

__all__ = ["create_app"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal ``.env`` loader (avoids a dependency for ~15 lines of parsing).

    Existing environment variables always win, so a real deployment's env is
    never overridden by a stray file on disk.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure the application."""
    _load_dotenv(_PROJECT_ROOT / ".env")

    from itsc.config import get_config

    # static_folder=None: static serving is registered explicitly below.  Flask's
    # built-in "/static/<path:filename>" rule would otherwise shadow the legacy
    # "/static/<name>.html" redirect rules depending on Werkzeug's rule sorting,
    # which is not a coin-flip worth taking in production.
    app = Flask(
        __name__,
        static_folder=None,
        template_folder="templates",
    )

    config = get_config(config_name)
    app.config.from_object(config)
    app.config["ENV_NAME"] = config.__class__.__name__

    _configure_logging(app)
    _register_extensions(app)
    _register_static(app)
    _register_blueprints(app)
    _register_errors(app)
    _register_context(app)
    _register_cli(app)

    app.logger.info(
        "app_created",
        extra={"config": app.config["ENV_NAME"], "debug": app.debug},
    )
    return app


def _configure_logging(app: Flask) -> None:
    from itsc.logging_config import configure_logging

    configure_logging(app)


def _register_extensions(app: Flask) -> None:
    from itsc.extensions import csrf, db, limiter, login_manager, migrate, server_session

    db.init_app(app)
    migrate.init_app(
        app,
        db,
        directory=str(_PROJECT_ROOT / "migrations"),
        # Detect type and server-default drift, not just added/dropped columns.
        compare_type=True,
        compare_server_default=True,
    )
    csrf.init_app(app)
    login_manager.init_app(app)

    if app.config.get("SESSION_TYPE") == "redis":
        import redis

        app.config["SESSION_REDIS"] = redis.Redis.from_url(app.config["REDIS_URL"])
    else:
        app.config.setdefault(
            "SESSION_FILE_DIR", str(_PROJECT_ROOT / ".flask_session")
        )
    server_session.init_app(app)

    if app.config.get("RATELIMIT_ENABLED", True):
        limiter.init_app(app)

    # Trust exactly one proxy hop (nginx).  Without this the scheme is wrong
    # behind TLS termination and every rate limit keys on the proxy's own IP.
    if not app.debug and not app.testing:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    from itsc.models import User

    @login_manager.user_loader
    def _load_user(user_id: str) -> User | None:
        from itsc.extensions import db as _db

        try:
            return _db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None


def _register_static(app: Flask) -> None:
    """Serve /static explicitly (dev); nginx handles it in production."""
    from flask import send_from_directory

    static_dir = Path(__file__).resolve().parent / "static"
    legacy_dir = _PROJECT_ROOT / "static"
    app.config["STATIC_DIR"] = str(static_dir)

    @app.route("/static/<path:filename>", endpoint="static")
    def static_files(filename: str):  # type: ignore[no-untyped-def]
        target = static_dir / filename
        base = static_dir if target.is_file() else legacy_dir
        return send_from_directory(base, filename)


def _register_blueprints(app: Flask) -> None:
    from itsc.blueprints.health import bp as health_bp

    app.register_blueprint(health_bp)


def _register_errors(app: Flask) -> None:
    from itsc.errors import register_error_handlers

    register_error_handlers(app)


def _register_context(app: Flask) -> None:
    from itsc.navigation import nav_context

    app.context_processor(nav_context)


def _register_cli(app: Flask) -> None:
    from itsc.cli import itsc_cli

    app.cli.add_command(itsc_cli)
