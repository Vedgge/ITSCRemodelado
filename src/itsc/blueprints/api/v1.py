"""Versioned, read-only JSON API.

Deliberately read-only and paginated. The original ``GET /novedades`` returned
``jsonify(rows)`` -- the entire table, every column, unpaginated -- and the
site's own pages consumed it. Now the pages render server-side and this exists
purely as a documented public surface.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, url_for

from itsc.services import novedades as service

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _serialize(novedad) -> dict:  # type: ignore[no-untyped-def]
    """Explicit field list.

    Never `SELECT *` of an ORM row into JSON: a column added later (an internal
    note, a moderation flag) would be published automatically.
    """
    return {
        "slug": novedad.slug,
        "titulo": novedad.titulo,
        "resumen": novedad.resumen,
        "publicado": novedad.published_at.isoformat() if novedad.published_at else None,
        "url": url_for("novedades.detail", slug=novedad.slug, _external=True),
        "imagen": (
            url_for("media.serve", public_id=novedad.imagen.public_id, _external=True)
            if novedad.imagen
            else None
        ),
    }


@bp.get("/novedades")
def novedades():  # type: ignore[no-untyped-def]
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(
        max(request.args.get("per_page", 20, type=int), 1),
        current_app.config["API_MAX_PER_PAGE"],
    )
    pagination = service.list_published(page=page, per_page=per_page)
    return jsonify(
        {
            "data": [_serialize(n) for n in pagination.items],
            "meta": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }
    )


@bp.get("/novedades/<slug>")
def novedad_detail(slug: str):  # type: ignore[no-untyped-def]
    from flask import abort

    novedad = service.get_by_slug(slug)
    if novedad is None:
        abort(404)
    payload = _serialize(novedad)
    payload["cuerpo"] = novedad.cuerpo
    return jsonify({"data": payload})
