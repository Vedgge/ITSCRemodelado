"""Institutional document repositories.

Backs four sections that previously existed only as empty HTML shells:
convocatorias, resoluciones, actas-dictámenes and materiales-para-descargar.
"""

from __future__ import annotations

from flask import Blueprint, abort, current_app, render_template, request

from itsc.models.document import CATEGORY_SLUGS
from itsc.services import documents as service

bp = Blueprint("documentos", __name__)

#: Constrains "/<categoria>/" to the seeded slugs. Without this the rule
#: matches ANY single path segment, so /cualquier-cosa produced a 308
#: trailing-slash redirect instead of an immediate 404.
#: Werkzeug's any() converter wants comma-separated quoted values.
_CATS = ",".join(f"'{slug}'" for slug in CATEGORY_SLUGS)

VALID_VIGENCIA = {service.VIGENCIA_VIGENTES, service.VIGENCIA_NO_VIGENTES}


@bp.get(f"/<any({_CATS}):categoria>/")
@bp.get(f"/<any({_CATS}):categoria>/<vigencia>/")
def list(categoria: str, vigencia: str | None = None):  # noqa: A001
    category = service.get_category(categoria)
    if category is None:
        abort(404)
    if vigencia is not None and (vigencia not in VALID_VIGENCIA or not category.has_vigencia):
        abort(404)

    page = request.args.get("page", 1, type=int)
    pagination = service.list_documents(
        category,
        vigencia=vigencia,
        page=max(page, 1),
        per_page=current_app.config["DOCUMENTS_PER_PAGE"],
    )
    return render_template(
        "documentos/list.html", category=category, pagination=pagination, vigencia=vigencia
    )


@bp.get(f"/<any({_CATS}):categoria>/doc/<slug>")
def detail(categoria: str, slug: str):  # type: ignore[no-untyped-def]
    document = service.get_document(categoria, slug)
    if document is None:
        abort(404)
    return render_template("documentos/detail.html", document=document)
