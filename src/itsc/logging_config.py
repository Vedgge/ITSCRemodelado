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


def _add_request_context(_logger: Any, _name: str, event: dict) -> dict:
    """Attach request metadata to every record emitted inside a request."""
    if request:
        event.setdefault("request_id", getattr(g, "request_id", None))
        event.setdefault("method", request.method)
        event.setdefault("path", request.path)
        event.setdefault("endpoint", request.endpoint)
    return event


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
    def _finish_request(response):  # type: ignore[no-untyped-def]
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
