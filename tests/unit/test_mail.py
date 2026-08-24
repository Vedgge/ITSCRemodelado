"""Outbound email is strictly best-effort.

Contact messages are persisted before this is called, so a mail outage can
never silently drop somebody's enquiry.
"""

from __future__ import annotations

import smtplib

import pytest

from itsc.services.mail import notify_new_contact, send


def test_send_is_a_noop_when_unconfigured(app):
    with app.app_context():
        app.config["MAIL_SERVER"] = ""
        assert send("asunto", "cuerpo", "a@b.co") is False


def test_send_is_a_noop_without_a_recipient(app):
    with app.app_context():
        app.config["MAIL_SERVER"] = "smtp.example.org"
        assert send("asunto", "cuerpo", "") is False


class _FakeSMTP:
    instances: list = []

    def __init__(self, host, port, timeout=10):
        self.host, self.port = host, port
        self.started_tls = False
        self.logged_in = None
        self.sent = []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = user

    def send_message(self, message):
        self.sent.append(message)


def test_send_uses_starttls_and_login(app, monkeypatch):
    _FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    with app.app_context():
        app.config.update(
            MAIL_SERVER="smtp.example.org",
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME="user",
            MAIL_PASSWORD="pass",
            MAIL_DEFAULT_SENDER="no-reply@example.org",
        )
        assert send("Asunto", "Cuerpo", "dest@example.org") is True

    smtp = _FakeSMTP.instances[-1]
    assert smtp.started_tls is True
    assert smtp.logged_in == "user"
    assert smtp.sent[0]["To"] == "dest@example.org"


@pytest.mark.parametrize("error", [OSError("network"), smtplib.SMTPException("refused")])
def test_send_swallows_transport_errors(app, monkeypatch, error):
    def boom(*args, **kwargs):
        raise error

    monkeypatch.setattr(smtplib, "SMTP", boom)
    with app.app_context():
        app.config.update(MAIL_SERVER="smtp.example.org", MAIL_DEFAULT_SENDER="a@b.co")
        assert send("Asunto", "Cuerpo", "dest@example.org") is False


def test_notify_is_skipped_without_a_recipient(app, db):
    from itsc.models import ContactMessage

    with app.app_context():
        app.config["CONTACT_NOTIFY_TO"] = ""
        message = ContactMessage(
            asunto="A", nombre="N", email="n@x.co", motivo="Otro", mensaje="m" * 20
        )
        db.session.add(message)
        db.session.commit()
        assert notify_new_contact(message) is False


def test_notification_links_rather_than_quoting_the_message(app, db, monkeypatch):
    """Enquiry text is personal data; it belongs in the authenticated inbox,
    not copied into an unencrypted mailbox."""
    from itsc.models import ContactMessage

    captured = {}

    def fake_send(subject, body, to):
        captured.update(subject=subject, body=body, to=to)
        return True

    monkeypatch.setattr("itsc.services.mail.send", fake_send)
    with app.app_context():
        app.config.update(CONTACT_NOTIFY_TO="staff@example.org", SERVER_NAME="localhost")
        secret = "informacion muy privada del consultante"
        message = ContactMessage(
            asunto="A", nombre="N", email="n@x.co", motivo="Otro", mensaje=secret
        )
        db.session.add(message)
        db.session.commit()
        notify_new_contact(message)

    assert captured["to"] == "staff@example.org"
    assert secret not in captured["body"], "message body must not be emailed"
    assert "/admin/mensajes/" in captured["body"]
