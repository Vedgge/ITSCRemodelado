"""Institutional news items."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from itsc.extensions import db
from itsc.models.base import TimestampMixin

STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"
STATUSES = (STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ARCHIVED)


class Novedad(TimestampMixin, db.Model):
    __tablename__ = "novedades"
    __table_args__ = (
        db.CheckConstraint(f"status IN {STATUSES!r}", name="ck_novedades_status"),
        db.CheckConstraint("length(btrim(titulo)) > 0", name="ck_novedades_titulo_nonempty"),
        # A published row without a publication date would sort unpredictably
        # and leak into "latest" listings at the wrong position.
        db.CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name="ck_novedades_published_has_date",
        ),
        Index("ix_novedades_listing", "status", "published_at"),
        Index("ix_novedades_search", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    #: Card text and meta description. The old cards dumped the whole body.
    resumen: Mapped[str] = mapped_column(String(400), nullable=False, server_default=text("''"))
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))

    imagen_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text(f"'{STATUS_DRAFT}'")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    #: Maintained by Postgres. Delivers the README's unbuilt "search engine"
    #: checklist item without any application code.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(titulo,'') || ' ' || "
            "coalesce(resumen,'') || ' ' || coalesce(cuerpo,''))",
            persisted=True,
        ),
    )

    imagen = relationship("MediaAsset", lazy="joined", foreign_keys=[imagen_id])
    author = relationship("User", lazy="joined", foreign_keys=[author_id])

    @property
    def is_published(self) -> bool:
        return self.status == STATUS_PUBLISHED

    def __repr__(self) -> str:
        return f"<Novedad {self.slug!r} {self.status}>"
