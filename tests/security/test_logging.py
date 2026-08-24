"""Observability leak regressions.

Logs and error reports are a second, easily-forgotten copy of everything a
request touched. Three defects lived here:

1. ``X-Request-ID`` was taken from the client verbatim, so an attacker chose
   what appeared in every log line and in a response header.
2. ``SENSITIVE_FIELDS`` declared that certain values are "never logged", but
   was only consulted by the Sentry reporter -- the structlog pipeline applied
   no redaction at all.
3. The Sentry scrubber inspected only ``request["data"]`` when it was a dict,
   missing string bodies, headers, breadcrumbs and ``extra``.
"""

from __future__ import annotations

import io

import pytest

from itsc.logging_config import (
    MAX_REQUEST_ID_LENGTH,
    REDACTED,
    _redact_sensitive,
    _scrub_sentry_event,
    safe_request_id,
)


def raw_wsgi_request(app, path: str = "/", request_id: str | None = None) -> int:
    """Drive the app through WSGI with hand-built headers.

    Werkzeug's test client validates header values itself and refuses to send a
    newline, so it cannot express this attack. A real request arrives as bytes
    off a socket, which is what this reproduces.

    The returned iterable MUST be consumed and closed: it is a ClosingIterator,
    and skipping close() leaves Flask's request context pushed, which corrupts
    every later test in the session.
    """
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.BytesIO(),
        "HTTP_HOST": "localhost",
    }
    if request_id is not None:
        environ["HTTP_X_REQUEST_ID"] = request_id

    captured: dict = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        return lambda _b: None

    iterable = app(environ, start_response)
    try:
        for _ in iterable:
            pass
    finally:
        close = getattr(iterable, "close", None)
        if close is not None:
            close()
        # Release the SQLAlchemy session. These requests run inside the
        # session-scoped app context, so Flask-SQLAlchemy does not tear the
        # session down for us; the connection would stay idle-in-transaction
        # and the next fixture's TRUNCATE would block forever on
        # ACCESS EXCLUSIVE.
        from itsc.extensions import db as _sa

        _sa.session.remove()
    return int(captured.get("status", "500").split()[0])


# --------------------------------------------------------------------------
# 1. Correlation id is attacker-controlled input
# --------------------------------------------------------------------------
@pytest.mark.security
@pytest.mark.parametrize(
    "hostile",
    [
        "AAA\n2026-01-01T00:00:00Z [error] FORGED admin_deleted=True",
        "AAA\r\nFORGED",
        "\x1b[31mANSI-FORGED\x1b[0m",
        "\x00nullbyte",
        "Q" * 4000,
        "id with spaces",
        "id;with;semicolons",
        '{"json":"injection"}',
    ],
)
def test_hostile_request_id_is_replaced(hostile):
    result = safe_request_id(hostile)
    assert result != hostile, "hostile correlation id was accepted verbatim"
    assert len(result) <= MAX_REQUEST_ID_LENGTH
    assert result.isalnum()


@pytest.mark.security
def test_legitimate_request_id_is_preserved():
    """nginx's $request_id must still flow through, or correlation breaks."""
    for good in ("abc123", "a1b2c3d4e5f6", "req-2026-01-01_42", "A.B-C_D"):
        assert safe_request_id(good) == good


@pytest.mark.security
def test_missing_request_id_is_generated():
    generated = safe_request_id(None)
    assert generated and len(generated) <= MAX_REQUEST_ID_LENGTH
    assert generated != safe_request_id(None)


@pytest.mark.security
def test_control_characters_never_reach_the_log(app, db, capsys):
    """End to end, through the real WSGI path.

    Werkzeug's test client rejects newline headers itself, so this builds the
    environ directly -- which is how a request actually arrives from a socket.
    """
    raw_wsgi_request(app, "/", request_id="AAA\n[error] FORGED_LOG_LINE")
    captured = capsys.readouterr()
    assert "FORGED_LOG_LINE" not in captured.err
    assert "FORGED_LOG_LINE" not in captured.out


@pytest.mark.security
def test_oversized_request_id_is_not_echoed_back(client):
    """Otherwise an attacker inflates every log line and response at will."""
    response = client.get("/", headers={"X-Request-ID": "Q" * 4000})
    echoed = response.headers.get("X-Request-ID", "")
    assert len(echoed) <= MAX_REQUEST_ID_LENGTH


@pytest.mark.security
def test_percent_decoded_path_cannot_forge_a_log_line(app, db, capsys):
    """request.path is percent-decoded, so %0a arrives as a real newline."""
    raw_wsgi_request(app, "/x\n[error] FORGED_VIA_PATH")
    captured = capsys.readouterr()
    assert "FORGED_VIA_PATH" not in captured.err


# --------------------------------------------------------------------------
# 2. SENSITIVE_FIELDS must actually be enforced
# --------------------------------------------------------------------------
@pytest.mark.security
@pytest.mark.parametrize(
    "field", ["password", "csrf_token", "email", "telefono", "mensaje", "authorization"]
)
def test_sensitive_keys_are_redacted_in_log_events(field):
    event = _redact_sensitive(None, "info", {"event": "test", field: "el-valor-secreto"})
    assert event[field] == REDACTED
    assert "el-valor-secreto" not in str(event)


@pytest.mark.security
def test_sensitive_keys_are_redacted_when_nested():
    event = _redact_sensitive(
        None, "info", {"event": "x", "form": {"nombre": "Ana", "password": "hunter2"}}
    )
    assert event["form"]["password"] == REDACTED
    assert event["form"]["nombre"] == REDACTED
    assert "hunter2" not in str(event)


@pytest.mark.security
def test_redaction_leaves_ordinary_fields_alone():
    event = _redact_sensitive(None, "info", {"event": "x", "status": 200, "user_id": 7})
    assert event["status"] == 200
    assert event["user_id"] == 7


@pytest.mark.security
def test_a_submitted_contact_message_never_appears_in_logs(client, db, token, capsys):
    """The end-to-end version of the above: real PII through the real form."""
    secret_message = "MENSAJE-CONFIDENCIAL-QUE-NO-DEBE-APARECER"
    client.post(
        "/contacto/",
        data={
            "asunto": "Consulta",
            "nombre": "Persona Real",
            "email": "persona-real@example.org",
            "telefono": "+543514337074",
            "motivo": "Otro",
            "mensaje": secret_message + " " * 5 + "relleno para el minimo",
            "csrf_token": token(client, "/contacto/"),
        },
    )
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert secret_message not in combined
    assert "persona-real@example.org" not in combined
    assert "+543514337074" not in combined


# --------------------------------------------------------------------------
# 3. Sentry scrubbing must cover every carrier
# --------------------------------------------------------------------------
@pytest.mark.security
def test_sentry_drops_a_non_dict_request_body():
    """A JSON body arrives as a string, which key-based scrubbing cannot read."""
    event = _scrub_sentry_event({"request": {"data": '{"email":"a@b.co","password":"hunter2"}'}})
    assert "data" not in event["request"]


@pytest.mark.security
def test_sentry_scrubs_form_bodies_headers_and_query_strings():
    event = _scrub_sentry_event(
        {
            "request": {
                "data": {"email": "a@b.co", "mensaje": "privado", "asunto": "ok"},
                "query_string": "email=a@b.co",
                "cookies": {"session": "abc"},
                "headers": {"Authorization": "Bearer tok", "Accept": "text/html"},
                "env": {"REMOTE_ADDR": "203.0.113.9", "SERVER_NAME": "x"},
            }
        }
    )
    req = event["request"]
    assert req["data"]["email"] == REDACTED
    assert req["data"]["mensaje"] == REDACTED
    assert req["data"]["asunto"] == "ok", "non-sensitive fields must survive"
    assert "query_string" not in req
    assert "cookies" not in req
    assert req["headers"]["Authorization"] == REDACTED
    assert req["headers"]["Accept"] == "text/html"
    assert "REMOTE_ADDR" not in req["env"]


@pytest.mark.security
def test_sentry_scrubs_breadcrumbs_and_extra():
    """structlog records become breadcrumbs; extra is free-form."""
    event = _scrub_sentry_event(
        {
            "extra": {"password": "hunter2", "count": 3},
            "breadcrumbs": {"values": [{"data": {"email": "a@b.co"}, "message": "ok"}]},
            "user": {"ip_address": "203.0.113.9"},
        }
    )
    assert event["extra"]["password"] == REDACTED
    assert event["extra"]["count"] == 3
    assert event["breadcrumbs"]["values"][0]["data"]["email"] == REDACTED
    assert "user" not in event, "user context carries an IP with pii disabled"


@pytest.mark.security
def test_sentry_scrub_handles_an_empty_event():
    assert _scrub_sentry_event({}) == {}
