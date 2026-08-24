"""Query helpers for news items."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from itsc.extensions import db
from itsc.models import Novedad
from itsc.models.novedad import STATUS_PUBLISHED


def published_query():  # type: ignore[no-untyped-def]
    return (
        select(Novedad)
        .where(Novedad.status == STATUS_PUBLISHED)
        .order_by(Novedad.published_at.desc())
    )


def list_published(page: int = 1, per_page: int = 9) -> Any:
    """Paginated published news.

    The original endpoint returned the entire table as JSON on every request
    and truncated it in the browser with `MAX_NOVEDADES = 9`.
    """
    return db.paginate(published_query(), page=page, per_page=per_page, error_out=False)


def latest(limit: int = 3) -> list[Novedad]:
    return list(db.session.scalars(published_query().limit(limit)))


def get_by_slug(slug: str, *, published_only: bool = True) -> Novedad | None:
    stmt = select(Novedad).where(Novedad.slug == slug)
    if published_only:
        stmt = stmt.where(Novedad.status == STATUS_PUBLISHED)
    return db.session.scalars(stmt).first()


def search(query: str, limit: int = 20) -> list[Novedad]:
    """Full-text search over the generated tsvector column.

    Uses `plainto_tsquery`, which treats the input as literal words rather than
    tsquery syntax — so a user typing `&` or `!` gets no results instead of a
    SyntaxError, and cannot inject query operators.
    """
    if not query.strip():
        return []
    ts = func.plainto_tsquery("spanish", query)
    stmt = (
        published_query()
        .where(Novedad.search_vector.op("@@")(ts))
        .order_by(func.ts_rank(Novedad.search_vector, ts).desc())
        .limit(limit)
    )
    return list(db.session.scalars(stmt))
