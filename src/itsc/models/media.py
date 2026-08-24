"""Uploaded files, decoupled from whatever references them.

The original code saved the user's own filename into ``static/`` with no
validation at all, so an uploaded ``.html`` or ``.svg`` became same-origin
script.  Here the *server* chooses both the name (a UUID) and the format
(re-encoded WebP / validated PDF), and the file never lands under ``static/``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from itsc.extensions import db
from itsc.models.base import TimestampMixin

ALLOWED_MIME = ("image/webp", "image/jpeg", "image/png", "application/pdf")


class MediaAsset(TimestampMixin, db.Model):
    __tablename__ = "media_assets"
    __table_args__ = (
        db.CheckConstraint(f"mime_type IN {ALLOWED_MIME!r}", name="ck_media_mime"),
        db.CheckConstraint("byte_size > 0", name="ck_media_size_positive"),
        Index("ix_media_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    #: The only identifier that ever appears in a URL. Never the user's filename.
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    #: Display-only. Never used to build a filesystem path.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Relative path within UPLOAD_ROOT, e.g. "2026/08/<uuid>.webp".
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    #: Content hash. Uploading the same photo twice reuses one row — the old
    #: repo stored the identical 4.7 MB JPEG three times.
    checksum_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    #: Required, not optional: a decorative-only image should pass "".
    alt_text: Mapped[str] = mapped_column(String(255), nullable=False, server_default=text("''"))
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    uploaded_by = relationship("User", lazy="joined")

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    def __repr__(self) -> str:
        return f"<MediaAsset {self.public_id} {self.mime_type} {self.byte_size}B>"
