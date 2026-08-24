"""Serve uploaded files.

Uploads live outside ``static/`` on a volume. In production nginx serves this
path directly with ``nosniff`` and a sandboxing CSP; this route is the
development equivalent and the authoritative access point.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, abort, current_app, send_file

from itsc.extensions import db
from itsc.models import MediaAsset

bp = Blueprint("media", __name__, url_prefix="/media")


@bp.get("/<uuid:public_id>")
def serve(public_id: uuid.UUID):
    asset = db.session.query(MediaAsset).filter_by(public_id=public_id).first()
    if asset is None:
        abort(404)

    root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    path = (root / asset.storage_key).resolve()
    # storage_key is server-generated, but verify containment anyway: a single
    # bad migration should not become an arbitrary-file-read.
    if not path.is_relative_to(root) or not path.is_file():
        abort(404)

    response = send_file(path, mimetype=asset.mime_type, conditional=True)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Even if something non-image were ever stored, this stops it executing.
    response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
