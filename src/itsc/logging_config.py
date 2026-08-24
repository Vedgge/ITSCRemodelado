"""Structured logging with per-request correlation IDs.

The original code used bare ``print()`` (``main.py:128`` printed whole database
rows to stdout).  Here every log line in a request carries the same
``request_id``, which is also echoed to the client and shown on error pages, so
a user's screenshot maps to a log line.
"""

from __future__ import annotations

import contextlib
import logging
import re
import sys
import uuid
from typing import Any

import structlog
from flask import Flask, g, request

#: Keys whose values must never appear in a log line or an error report.
#: Enforced by :func:`_redact_sensitive`, which runs on every structlog event.
SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "password_confirm",
        "current_password",
        "new_password",
        "csrf_token",
        "token",
        "secret",
        "authorization",
        "cookie",
        "session",
        "email",
        "telefono",
        "phone",
        "mensaje",
        "nombre",
        "ip",
        "remote_addr",
    }
)

REDACTED = "[redacted]"

#: Correlation ids are echoed into logs and into a response header, so the
#: value must be inert in both. Anything outside this alphabet is rejected
#: rather than escaped: there is no legitimate request id containing a control
#: character.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
MAX_REQUEST_ID_LENGTH = 64


def _new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def safe_request_id(candidate: str | None) -> str:
    """Return *candidate* only if it is a safe correlation id.

    ``X-Request-ID`` arrives from the client. Trusting it verbatim let an
    attacker (a) inject ANSI escapes and control characters into console log
    output, (b) write an unbounded number of bytes into every log line for
    every request, inflating log storage at will, and (c) trigger a 500 by
    including a carriage return, which Werkzeug refuses to write back out as a
    response header.

    A rejected value is replaced with a generated one, so correlation still
    works and nothing attacker-controlled reaches the log or the response.
    """
    if candidate and _REQUEST_ID_RE.match(candidate):
        return candidate
    return _new_request_id()


def _redact_sensitive(_logger: Any, _name: str, event: dict[str, Any]) -> dict[str, Any]:
    """Replace the values of sensitive keys before the event is rendered.

    Without this the module-level promise that these fields are "never logged"
    was only enforced inside the Sentry reporter, so any ``log.info(...,
    email=...)`` anywhere in the codebase went straight to stdout.
    """

    def scrub(value: Any, depth: int = 0) -> Any:
        if depth > 4:  # bound the walk; log payloads are not deep trees
            return value
        if isinstance(value, dict):
            return {
                k: (REDACTED if str(k).lower() in SENSITIVE_FIELDS else scrub(v, depth + 1))
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return type(value)(scrub(v, depth + 1) for v in value)
        return value

    for key in list(event):
        if str(key).lower() in SENSITIVE_FIELDS:
            event[key] = REDACTED
        else:
            event[key] = scrub(event[key])
    return event


def _add_request_context(_logger: Any, _name: str, event: dict[str, Any]) -> dict[str, Any]:
    """Attach request metadata to every record emitted inside a request."""
    if request:
        event.setdefault("request_id", getattr(g, "request_id", None))
        event.setdefault("method", request.method)
        # request.path is percent-decoded, so it can carry control characters.
        # Truncate and strip them: a log line must never be forgeable.
        event.setdefault("path", _safe_text(request.path, 200))
        event.setdefault("endpoint", request.endpoint)
    return event


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _safe_text(value: str | None, limit: int) -> str:
    """Strip control characters and truncate, so a value cannot forge a line."""
    if not value:
        return ""
    cleaned = _CONTROL_CHARS.sub("", value)
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


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
        """Strip personal data before anything leaves the process.

        Scrubs every place Sentry can carry request data, not just
        ``request.data``: a JSON body arrives as a string rather than a dict,
        log records become breadcrumbs, and ``extra`` is free-form.
        """
        return _scrub_sentry_event(event)

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        send_default_pii=False,
        traces_sample_rate=0.1,
        before_send=scrub,
        before_send_transaction=scrub,
        # Belt and braces alongside the explicit scrubber below.
        send_client_reports=False,
        max_request_body_size="never",
        before_breadcrumb=lambda crumb, _hint: _scrub_mapping(crumb),
        environment=app.config.get("ENV_NAME", "unknown"),
    )
    return True


def _scrub_mapping(value: Any, depth: int = 0) -> Any:
    """Recursively redact sensitive keys in an arbitrary nested structure."""
    if depth > 6:
        return value
    if isinstance(value, dict):
        return {
            k: (REDACTED if str(k).lower() in SENSITIVE_FIELDS else _scrub_mapping(v, depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub_mapping(v, depth + 1) for v in value]
    return value


def _scrub_sentry_event(event: dict) -> dict:
    request_data = event.get("request")
    if isinstance(request_data, dict):
        # A non-form body reaches Sentry as a string, which key-based scrubbing
        # cannot inspect. Drop it wholesale rather than ship it.
        if not isinstance(request_data.get("data"), dict):
            request_data.pop("data", None)
        else:
            request_data["data"] = _scrub_mapping(request_data["data"])
        # The contact form is the main source of personal data here, and the
        # query string is exactly where it used to leak.
        request_data.pop("query_string", None)
        request_data.pop("cookies", None)
        headers = request_data.get("headers")
        if isinstance(headers, dict):
            request_data["headers"] = _scrub_mapping(headers)
        env = request_data.get("env")
        if isinstance(env, dict):
            env.pop("REMOTE_ADDR", None)

    for key in ("extra", "contexts", "tags"):
        if isinstance(event.get(key), dict):
            event[key] = _scrub_mapping(event[key])

    if isinstance(event.get("breadcrumbs"), dict):
        values = event["breadcrumbs"].get("values")
        if isinstance(values, list):
            event["breadcrumbs"]["values"] = [_scrub_mapping(v) for v in values]
    event.pop("user", None)
    return event


def configure_logging(app: Flask) -> None:
    level = getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    as_json = bool(app.config.get("LOG_JSON", False))

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_request_context,
        # Runs last of the enrichers, so it also covers keys added above.
        _redact_sensitive,
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
        # Prefer nginx's $request_id so app logs correlate with access logs --
        # but only after validating it, since the header is client-supplied.
        g.request_id = safe_request_id(request.headers.get("X-Request-ID"))
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
