"""Structured logging with per-request correlation IDs.

The original code used bare ``print()`` (``main.py:128`` printed whole database
rows to stdout).  Here every log line in a request carries the same
``request_id``, which is also echoed to the client and shown on error pages, so
a user's screenshot maps to a log line.
"""

from __future__ import annotations

import contextlib
import logging
import sys
import uuid
from typing import Any

import structlog
from flask import Flask, g, request

#: Never log the values of these form fields.
SENSITIVE_FIELDS = frozenset(
    {"password", "password_confirm", "csrf_token", "email", "telefono", "mensaje"}
)


def _add_request_context(_logger: Any, _name: str, event: dict[str, Any]) -> dict[str, Any]:
    """Attach request metadata to every record emitted inside a request."""
    if request:
        event.setdefault("request_id", getattr(g, "request_id", None))
        event.setdefault("method", request.method)
        event.setdefault("path", request.path)
        event.setdefault("endpoint", request.endpoint)
    return event


def init_sentry(app: Flask) -> bool:
    """Wire Sentry when a DSN is configured and the SDK is installed.

    Kept an optional import rather than a hard dependency: the DSN is
    meaningless without an account, and structured logs plus an external
    uptime check already cover a single-node deployment. Returns whether it
    was enabled, so the caller can log it.
    """
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        app.logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    def scrub(event: dict, _hint: dict) -> dict:
        """Strip personal data before anything leaves the process."""
        request = event.get("request") or {}
        data = request.get("data")
        if isinstance(data, dict):
            for key in list(data):
                if key.lower() in SENSITIVE_FIELDS:
                    data[key] = "[filtered]"
        # The contact form is the main source of personal data, and query
        # strings were where it used to leak.
        request.pop("query_string", None)
        return event

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        send_default_pii=False,
        traces_sample_rate=0.1,
        before_send=scrub,
        environment=app.config.get("ENV_NAME", "unknown"),
    )
    return True


def configure_logging(app: Flask) -> None:
    level = getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    as_json = bool(app.config.get("LOG_JSON", False))

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_request_context,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if as_json
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level, force=True)
    for noisy in ("werkzeug", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    log = structlog.get_logger("itsc")

    @app.before_request
    def _start_request() -> None:
        # Prefer nginx's $request_id so app logs correlate with access logs.
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        structlog.contextvars.bind_contextvars(request_id=g.request_id)

    @app.after_request
    def _finish_request(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        # Health checks would otherwise dominate the log volume.
        if request.endpoint not in {"health.healthz", "health.readyz", "static"}:
            # after_request runs on error responses too; a logging failure here
            # would replace the user's error page with a traceback.
            with contextlib.suppress(Exception):
                log.info(
                    "request",
                    status=response.status_code,
                    # Deliberately NOT request.query_string: the contact form
                    # used to carry names, emails and phone numbers in the URL,
                    # and logging query strings would reintroduce that leak.
                    bytes=response.content_length,
                )
        structlog.contextvars.clear_contextvars()
        return response
