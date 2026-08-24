"""Public news listing, detail page, and RSS feed."""

from __future__ import annotations

from flask import Blueprint, Response, abort, current_app, render_template, request, url_for

from itsc.services import novedades as service

bp = Blueprint("novedades", __name__, url_prefix="/novedades")


@bp.get("/")
def list():  # noqa: A001 - matches the endpoint name used across templates
    page = request.args.get("page", 1, type=int)
    pagination = service.list_published(
        page=max(page, 1), per_page=current_app.config["NOVEDADES_PER_PAGE"]
    )
    return render_template("novedades/list.html", pagination=pagination)


@bp.get("/<slug>")
def detail(slug: str):  # type: ignore[no-untyped-def]
    novedad = service.get_by_slug(slug)
    if novedad is None:
        abort(404)
    return render_template("novedades/detail.html", novedad=novedad, relacionadas=service.latest(3))


@bp.get("/feed.xml", endpoint="feed")
def feed():  # type: ignore[no-untyped-def]
    """RSS. The header linked to an RSS icon that pointed at href="#"."""
    items = service.latest(20)
    xml = render_template("novedades/feed.xml", items=items, now=None)
    return Response(xml, mimetype="application/rss+xml")


@bp.get("/<int:codigo>")
def legacy_numeric(codigo: int):  # type: ignore[no-untyped-def]
    """The old integer URLs (/novedades/3) 301 to the slug form."""
    from flask import redirect

    from itsc.extensions import db
    from itsc.models import Novedad

    novedad = db.session.get(Novedad, codigo)
    if novedad is None:
        abort(404)
    return redirect(url_for("novedades.detail", slug=novedad.slug), code=301)
