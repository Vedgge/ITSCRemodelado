"""Flask extension singletons.

These are created unbound at import time and attached to an app inside
:func:`itsc.create_app`.  Nothing here opens a connection on import — the
original code built a live MySQL connection at module scope, which is what made
it un-testable and un-forkable.
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all models (SQLAlchemy 2.0 typed style)."""


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
server_session = Session()

# Rate limits are stored in Redis, not memory: an in-memory limiter behind
# multiple gunicorn workers counts per-worker, so the real limit is
# N_workers x the configured value — which is not a limit at all.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    strategy="fixed-window",
)

login_manager.login_view = "auth.login"
login_manager.login_message = "Iniciá sesión para acceder a esta página."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"
