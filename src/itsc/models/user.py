"""Administrative users.

The original application had no user model at all: every mutating endpoint was
reachable by anyone on the internet.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from itsc.extensions import db
from itsc.models.base import TimestampMixin, utcnow

#: argon2id with library defaults — the current best-practice password KDF.
_hasher = PasswordHasher()

#: Failed attempts before the account itself locks, independent of the per-IP
#: rate limit.  A distributed attack rotating IPs still trips this.
MAX_FAILED_LOGINS = 10
LOCKOUT_DURATION = timedelta(minutes=15)

ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLES = (ROLE_ADMIN, ROLE_EDITOR)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(f"role IN {ROLES!r}", name="ck_users_role"),
        Index("ix_users_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT(), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'editor'"))
    is_active_flag: Mapped[bool] = mapped_column(
        "is_active", Boolean, nullable=False, server_default=text("true")
    )
    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(String(64))
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    # -- password handling ---------------------------------------------------
    def set_password(self, raw: str) -> None:
        self.password_hash = _hasher.hash(raw)
        self.password_changed_at = utcnow()

    def check_password(self, raw: str) -> bool:
        """Verify *raw*, transparently upgrading the hash when parameters change."""
        try:
            _hasher.verify(self.password_hash, raw)
        except (VerifyMismatchError, InvalidHashError):
            return False
        if _hasher.check_needs_rehash(self.password_hash):
            self.password_hash = _hasher.hash(raw)
        return True

    # -- lockout -------------------------------------------------------------
    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > utcnow()

    def register_failed_login(self) -> None:
        self.failed_login_count += 1
        if self.failed_login_count >= MAX_FAILED_LOGINS:
            self.locked_until = utcnow() + LOCKOUT_DURATION
            self.failed_login_count = 0

    def register_successful_login(self, ip: str | None = None) -> None:
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = utcnow()
        self.last_login_ip = ip

    # -- flask-login ---------------------------------------------------------
    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.is_active_flag and not self.is_locked

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


def dummy_verify() -> None:
    """Burn a hash verification for an unknown username.

    Without this, "no such user" returns measurably faster than "wrong
    password", which turns the login form into a username oracle.
    """
    # The verification is expected to fail; spending the CPU time is the whole
    # point, so the exception is discarded deliberately.
    with contextlib.suppress(Exception):
        _hasher.verify(
            "$argon2id$v=19$m=65536,t=3,p=4$"
            "c29tZXNhbHRzb21lc2FsdA$8sQhH0P7yZ0Q1gGKq0m4rN3Kx0z9Yl8vJ2Xq7Wn5Tz0",
            "not-the-password",
        )
