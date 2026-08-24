"""Query helpers for institutional documents."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, or_, select

from itsc.extensions import db
from itsc.models import Document, DocumentCategory
from itsc.models.novedad import STATUS_PUBLISHED

VIGENCIA_VIGENTES = "vigentes"
VIGENCIA_NO_VIGENTES = "no-vigentes"


def get_category(slug: str) -> DocumentCategory | None:
    return db.session.scalars(select(DocumentCategory).where(DocumentCategory.slug == slug)).first()


def all_categories() -> list[DocumentCategory]:
    return list(db.session.scalars(select(DocumentCategory).order_by(DocumentCategory.orden)))


def list_documents(
    category: DocumentCategory,
    *,
    vigencia: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> Any:
    """Published documents in *category*, optionally filtered by vigencia.

    Vigencia is computed from dates in SQL, never read from a stored boolean —
    so "vigentes" cannot drift out of date the way two hand-maintained pages
    (convocatorias-vigentes.html / convocatorias-novigentes.html) did.
    """
    today = date.today()  # noqa: DTZ011 - a calendar date, not an instant
    stmt = (
        select(Document)
        .where(Document.category_id == category.id, Document.status == STATUS_PUBLISHED)
        .order_by(Document.fecha_documento.desc(), Document.id.desc())
    )

    if vigencia == VIGENCIA_VIGENTES:
        stmt = stmt.where(
            or_(Document.vigente_hasta.is_(None), Document.vigente_hasta >= today),
            or_(Document.vigente_desde.is_(None), Document.vigente_desde <= today),
        )
    elif vigencia == VIGENCIA_NO_VIGENTES:
        stmt = stmt.where(Document.vigente_hasta.is_not(None), Document.vigente_hasta < today)

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_document(category_slug: str, slug: str) -> Document | None:
    return db.session.scalars(
        select(Document)
        .join(DocumentCategory)
        .where(
            DocumentCategory.slug == category_slug,
            Document.slug == slug,
            Document.status == STATUS_PUBLISHED,
        )
    ).first()


def search(query: str, limit: int = 20) -> list[Document]:
    if not query.strip():
        return []
    ts = func.plainto_tsquery("spanish", query)
    stmt = (
        select(Document)
        .where(Document.status == STATUS_PUBLISHED, Document.search_vector.op("@@")(ts))
        .order_by(func.ts_rank(Document.search_vector, ts).desc())
        .limit(limit)
    )
    return list(db.session.scalars(stmt))
