"""Contact-form submissions.

There was no such table.  The original form used ``method=GET`` to a static
HTML file, so every message — name, email, phone, free text — travelled in the
URL query string (browser history, access logs, and the ``Referer`` header sent
to every third-party asset on the destination page) and then reached no server
at all.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from itsc.extensions import db
from itsc.models.base import TimestampMixin

STATUS_NEW = "new"
STATUS_READ = "read"
STATUS_ANSWERED = "answered"
STATUS_SPAM = "spam"
CONTACT_STATUSES = (STATUS_NEW, STATUS_READ, STATUS_ANSWERED, STATUS_SPAM)

#: Values carried over from the existing radio group on the homepage form.
MOTIVO_BOLETO = "Boleto Educativo Gratuito"
MOTIVO_COOPERADORA = "Cooperadora"
MOTIVO_INSCRIPCION = "Inscripción"
MOTIVO_CARRERAS = "Consulta sobre carreras"
MOTIVO_OTRO = "Otro"
MOTIVOS = (
    MOTIVO_BOLETO,
    MOTIVO_COOPERADORA,
    MOTIVO_INSCRIPCION,
    MOTIVO_CARRERAS,
    MOTIVO_OTRO,
)


def hash_ip(ip: str | None, pepper: str) -> str | None:
    """HMAC an IP for abuse tracing without retaining the address itself.

    Keyed rather than plain SHA-256: the IPv4 space is small enough to brute
    force an unkeyed digest in seconds.
    """
    if not ip:
        return None
    return hmac.new(pepper.encode(), ip.encode(), hashlib.sha256).hexdigest()


class ContactMessage(TimestampMixin, db.Model):
    __tablename__ = "contact_messages"
    __table_args__ = (
        db.CheckConstraint(f"status IN {CONTACT_STATUSES!r}", name="ck_contact_status"),
        db.CheckConstraint("length(btrim(mensaje)) > 0", name="ck_contact_mensaje_nonempty"),
        Index("ix_contact_triage", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asunto: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(40))
    motivo: Mapped[str] = mapped_column(String(60), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text(f"'{STATUS_NEW}'")
    )
    #: Keyed hash, never the raw address.
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))

    handled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    handled_by = relationship("User", lazy="joined", foreign_keys=[handled_by_id])

    def __repr__(self) -> str:
        return f"<ContactMessage {self.id} {self.status} {self.motivo!r}>"
