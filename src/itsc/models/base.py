"""Shared model building blocks."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now.

    The original code used naive ``datetime.now()``, which silently records the
    server's local time and compares incorrectly against anything stored in
    UTC.  Ruff's DTZ ruleset is enabled to keep naive calls out of the codebase.
    """
    return datetime.now(UTC)


class TimestampMixin:
    """``created_at`` / ``updated_at`` maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
