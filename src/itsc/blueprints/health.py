"""Liveness and readiness endpoints.

The distinction matters operationally.  ``/healthz`` must NOT touch the
database: if it did, a brief DB blip would fail the container healthcheck and
restart-loop every web container, turning a 5-second outage into a full one.
``/readyz`` checks dependencies and is what a deploy script waits on.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():  # type: ignore[no-untyped-def]
    """Liveness: is the process running? No dependency checks, by design."""
    return jsonify({"status": "ok"}), 200


@bp.get("/readyz")
def readyz():  # type: ignore[no-untyped-def]
    """Readiness: can we actually serve traffic?"""
    checks: dict[str, object] = {}
    healthy = True

    # --- database ---
    try:
        from itsc.extensions import db

        db.session.execute(text("SELECT 1"))
        revision = db.session.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar()
        checks["database"] = {"ok": True, "migration": revision}
    except Exception as exc:
        healthy = False
        checks["database"] = {"ok": False, "error": type(exc).__name__}

    # --- redis (only when actually used) ---
    if current_app.config.get("SESSION_TYPE") == "redis":
        try:
            import redis

            redis.Redis.from_url(current_app.config["REDIS_URL"]).ping()
            checks["redis"] = {"ok": True}
        except Exception as exc:
            healthy = False
            checks["redis"] = {"ok": False, "error": type(exc).__name__}
    else:
        checks["redis"] = {"ok": True, "skipped": "not configured"}

    # --- upload directory must be writable, or every upload 500s ---
    try:
        root = Path(current_app.config["UPLOAD_ROOT"])
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".readyz"
        probe.write_text("ok")
        probe.unlink()
        checks["uploads"] = {"ok": True, "path": str(root)}
    except Exception as exc:
        healthy = False
        checks["uploads"] = {"ok": False, "error": type(exc).__name__}

    return jsonify({"status": "ok" if healthy else "degraded", "checks": checks}), (
        200 if healthy else 503
    )
