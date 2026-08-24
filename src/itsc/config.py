"""Configuration classes.

The original app hardcoded ``user='root', password=''`` at import time and ran
with ``debug=True``.  Everything here is environment-driven, and
:class:`ProductionConfig` *raises at construction* when a secret is missing or
still holds its placeholder value.  Failing to boot is strictly better than
booting insecure: a crash is noticed, a silently-weak SECRET_KEY is not.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

PLACEHOLDERS = frozenset(
    {
        "",
        "change-me",
        "change-me-generate-a-real-one",
        "secret",
        "dev",
        "changeme",
    }
)


class ConfigError(RuntimeError):
    """Raised when the environment cannot support the requested config."""


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


class BaseConfig:
    """Settings shared by every environment."""

    # --- Core ---------------------------------------------------------------
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    TESTING: bool = False
    DEBUG: bool = False

    # --- Database -----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://itsc:itsc@localhost:5432/itsc"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # pool_pre_ping fixes the bug that killed the original app after MySQL's
    # 8-hour wait_timeout: a stale pooled connection is detected and replaced
    # instead of raising on the next request.
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 5,
        "max_overflow": 5,
    }

    # --- Sessions -----------------------------------------------------------
    # The __Host- prefix is enforced by the browser: it requires Secure, Path=/
    # and no Domain attribute, which makes cookie-fixation from a sibling
    # subdomain impossible.
    SESSION_COOKIE_NAME: str = "session"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = True
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=8)
    SESSION_TYPE: str = "redis"
    SESSION_PERMANENT: bool = True
    # SESSION_USE_SIGNER is deprecated upstream and intentionally unset:
    # with server-side sessions the cookie carries only a cryptographically
    # random session id, so signing it adds no meaningful protection.
    SESSION_KEY_PREFIX: str = "itsc:sess:"

    # --- CSRF ---------------------------------------------------------------
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: int | None = None  # tied to session lifetime instead

    # --- Redis --------------------------------------------------------------
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_STORAGE_URI: str = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_HEADERS_ENABLED: bool = True

    # --- Uploads ------------------------------------------------------------
    # Deliberately OUTSIDE static/: a file served from the app's own origin can
    # execute script against it.  Uploads are served from /media/ with nosniff.
    # Default sits inside the project, not /tmp: a world-writable directory
    # lets any local user drop files into what the app then serves.
    UPLOAD_ROOT: Path = Path(
        os.environ.get("UPLOAD_ROOT") or (Path(__file__).resolve().parent.parent.parent / "uploads")
    )
    MAX_UPLOAD_MB: int = _int("MAX_UPLOAD_MB", 5)
    MAX_CONTENT_LENGTH: int = _int("MAX_UPLOAD_MB", 5) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})
    ALLOWED_DOC_EXTENSIONS: frozenset[str] = frozenset({".pdf"})

    # --- Site ---------------------------------------------------------------
    SITE_NAME: str = "Instituto Técnico Superior Córdoba"
    SITE_SHORT_NAME: str = "ITSC"
    SITE_IS_PORTFOLIO_DEMO: bool = _bool("SITE_IS_PORTFOLIO_DEMO", True)
    SITE_OFFICIAL_URL: str = os.environ.get(
        "SITE_OFFICIAL_URL", "https://www.institutotecnicocordoba.com"
    )
    PREFERRED_URL_SCHEME: str = os.environ.get("PREFERRED_URL_SCHEME", "http")

    # Real, verified contact details taken from the existing site footer.
    SITE_ADDRESS: str = "Río Negro 77, Córdoba, Argentina"
    SITE_PHONE: str = "(0351) 4337074"
    SITE_PHONE_E164: str = "+543514337074"
    SITE_SOCIAL: dict = {
        "instagram": "https://www.instagram.com/itscordoba.ok/",
        "facebook": "https://www.facebook.com/pages/Instituto-T%C3%A9cnico-Superior-C%C3%B3rdoba/443175482521454",
        "linkedin": "https://www.linkedin.com/company/instituto-t%C3%A9cnico-superior-c%C3%B3rdoba/",
    }

    # --- Content ------------------------------------------------------------
    NOVEDADES_PER_PAGE: int = 9
    DOCUMENTS_PER_PAGE: int = 20
    API_MAX_PER_PAGE: int = 50

    # --- Security -----------------------------------------------------------
    IP_HASH_PEPPER: str = os.environ.get("IP_HASH_PEPPER", "dev-only-pepper")
    CONTACT_RETENTION_DAYS: int = _int("CONTACT_RETENTION_DAYS", 730)

    # --- Mail (optional; DB is the source of truth for contact messages) -----
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT: int = _int("MAIL_PORT", 587)
    MAIL_USE_TLS: bool = _bool("MAIL_USE_TLS", True)
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.environ.get("MAIL_DEFAULT_SENDER", "")
    CONTACT_NOTIFY_TO: str = os.environ.get("CONTACT_NOTIFY_TO", "")

    # --- Observability ------------------------------------------------------
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_JSON: bool = _bool("LOG_JSON", False)
    SENTRY_DSN: str = os.environ.get("SENTRY_DSN", "")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # Without TLS locally a Secure cookie is never stored, and you get locked
    # out of the app you are trying to debug.
    SESSION_COOKIE_SECURE = False
    SESSION_TYPE = "cachelib"
    TALISMAN_FORCE_HTTPS = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SESSION_COOKIE_SECURE = False
    SESSION_TYPE = "cachelib"
    TALISMAN_FORCE_HTTPS = False
    # CSRF stays ENABLED in tests.  Suites that disable it are exactly how CSRF
    # regressions reach production; tests scrape the real token instead.
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://itsc:itsc@localhost:55432/itsc_test",
    )
    RATELIMIT_ENABLED = False
    SECRET_KEY = "testing-key-not-a-secret"
    IP_HASH_PEPPER = "testing-pepper"


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_NAME = "__Host-itsc_session"
    TALISMAN_FORCE_HTTPS = True
    LOG_JSON = True

    #: Secrets that must be present and non-placeholder before the app boots.
    REQUIRED = ("SECRET_KEY", "DATABASE_URL", "REDIS_URL", "IP_HASH_PEPPER")

    def __init__(self) -> None:
        missing = [
            name
            for name in self.REQUIRED
            if os.environ.get(name, "").strip().lower() in PLACEHOLDERS
        ]
        if missing:
            raise ConfigError(
                "Refusing to start in production. These environment variables are "
                f"missing or still hold placeholder values: {', '.join(missing)}. "
                'Generate secrets with: python -c "import secrets; '
                'print(secrets.token_urlsafe(64))"'
            )
        if _bool("FLASK_DEBUG"):
            raise ConfigError("FLASK_DEBUG must not be enabled in production.")
        if len(os.environ["SECRET_KEY"]) < 32:
            raise ConfigError("SECRET_KEY must be at least 32 characters.")


CONFIGS: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> BaseConfig:
    """Resolve and instantiate the config class for *name* (or ``FLASK_ENV``)."""
    key = (name or os.environ.get("FLASK_ENV") or "development").strip().lower()
    try:
        cls = CONFIGS[key]
    except KeyError:
        raise ConfigError(
            f"Unknown config {key!r}. Expected one of: {', '.join(sorted(CONFIGS))}"
        ) from None
    return cls()
