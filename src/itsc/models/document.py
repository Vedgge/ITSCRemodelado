"""Generic institutional documents.

Four of the site's empty pages — resoluciones, actas-dictámenes,
materiales-para-descargar and convocatorias — are not prose pages at all: they
are document repositories.  One model backs all of them.

Vigencia (whether a convocatoria is still open) is *derived* from dates, never
stored as a boolean.  That is what collapses the two hand-maintained pages
``convocatorias-vigentes.html`` and ``convocatorias-novigentes.html`` into two
filters over one table, and it cannot drift out of date.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from itsc.extensions import db
from itsc.models.base import TimestampMixin
from itsc.models.novedad import STATUSES

#: Seeded, not user-created, so URLs stay stable and routes can be registered
#: from a known set rather than whatever a user typed.
CATEGORY_CONVOCATORIAS = "convocatorias"
CATEGORY_RESOLUCIONES = "resoluciones"
CATEGORY_ACTAS = "actas-dictamenes"
CATEGORY_MATERIALES = "materiales-para-descargar"
CATEGORY_MESAS = "mesas-de-examen"
CATEGORY_SLUGS = (
    CATEGORY_CONVOCATORIAS,
    CATEGORY_RESOLUCIONES,
    CATEGORY_ACTAS,
    CATEGORY_MATERIALES,
    CATEGORY_MESAS,
)


class DocumentCategory(TimestampMixin, db.Model):
    __tablename__ = "document_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    icon: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'file'"))
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    #: Only convocatorias filter by vigencia; the others are plain archives.
    has_vigencia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    documents = relationship("Document", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DocumentCategory {self.slug}>"


class Document(TimestampMixin, db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        db.CheckConstraint(f"status IN {STATUSES!r}", name="ck_documents_status"),
        db.CheckConstraint("length(btrim(titulo)) > 0", name="ck_documents_titulo_nonempty"),
        db.CheckConstraint(
            "vigente_hasta IS NULL OR vigente_desde IS NULL OR vigente_hasta >= vigente_desde",
            name="ck_documents_vigencia_ordered",
        ),
        db.CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name="ck_documents_published_has_date",
        ),
        # Slugs need only be unique within a category, so "2024" can exist in
        # both resoluciones and actas without collision.
        UniqueConstraint("category_id", "slug", name="uq_documents_category_slug"),
        UniqueConstraint("category_id", "numero", name="uq_documents_category_numero"),
        Index("ix_documents_listing", "category_id", "status", "fecha_documento"),
        Index("ix_documents_search", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("document_categories.id", ondelete="RESTRICT"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    #: e.g. "Resolución N° 123/2024". Optional — materiales have no number.
    numero: Mapped[str | None] = mapped_column(String(60))
    #: The document's own date, distinct from when it was published on the site.
    fecha_documento: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(titulo,'') || ' ' || "
            "coalesce(numero,'') || ' ' || coalesce(descripcion,''))",
            persisted=True,
        ),
    )

    category = relationship("DocumentCategory", back_populates="documents", lazy="joined")
    files = relationship(
        "DocumentFile",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentFile.orden",
        lazy="selectin",
    )
    author = relationship("User", lazy="joined", foreign_keys=[author_id])

    @property
    def vigente(self) -> bool:
        """Open now?  Derived, never stored."""
        today = date.today()  # noqa: DTZ011 - a calendar date, not an instant
        if self.vigente_desde and self.vigente_desde > today:
            return False
        return self.vigente_hasta is None or self.vigente_hasta >= today

    def __repr__(self) -> str:
        return f"<Document {self.category.slug if self.category else '?'}/{self.slug}>"


class DocumentFile(TimestampMixin, db.Model):
    """A document may carry several files (bases, anexos, formulario)."""

    __tablename__ = "document_files"
    __table_args__ = (
        UniqueConstraint("document_id", "media_asset_id", name="uq_document_files_pair"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    #: RESTRICT, not CASCADE: deleting a media row that a document still points
    #: at should fail loudly rather than silently emptying the document.
    media_asset_id: Mapped[int] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False, server_default=text("''"))
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))

    document = relationship("Document", back_populates="files")
    media = relationship("MediaAsset", lazy="joined")
