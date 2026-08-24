"""Outbound email — strictly best-effort.

Contact messages are persisted before this is called. If SMTP is unconfigured
or unreachable, the enquiry is still safely stored and visible in the admin
inbox; it is never lost because a mail server was down.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog
from flask import current_app, url_for

log = structlog.get_logger("itsc.mail")


def send(subject: str, body: str, to: str) -> bool:
    server = current_app.config.get("MAIL_SERVER")
    if not server or not to:
        log.debug("mail_skipped", reason="not_configured")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config.get("MAIL_DEFAULT_SENDER") or "no-reply@localhost"
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(server, current_app.config["MAIL_PORT"], timeout=10) as smtp:
            if current_app.config.get("MAIL_USE_TLS"):
                smtp.starttls()
            username = current_app.config.get("MAIL_USERNAME")
            if username:
                smtp.login(username, current_app.config["MAIL_PASSWORD"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        log.warning("mail_failed", error=str(exc))
        return False

    log.info("mail_sent", to_domain=to.rsplit("@", 1)[-1])
    return True


def notify_new_contact(message) -> bool:  # type: ignore[no-untyped-def]
    """Alert staff that an enquiry arrived.

    The notification carries a link, not the message body: enquiry text is
    personal data and should be read in the authenticated admin inbox rather
    than copied into an unencrypted mailbox.
    """
    to = current_app.config.get("CONTACT_NOTIFY_TO")
    if not to:
        return False
    try:
        link = url_for("admin.contacto_detail", message_id=message.id, _external=True)
    except Exception:  # noqa: BLE001
        link = "(panel de administración)"
    return send(
        subject=f"[ITSC] Nueva consulta: {message.motivo}",
        body=(
            "Se recibió una nueva consulta desde el sitio.\n\n"
            f"Motivo : {message.motivo}\n"
            f"Asunto : {message.asunto}\n"
            f"Fecha  : {message.created_at:%d/%m/%Y %H:%M}\n\n"
            f"Leerla en: {link}\n"
        ),
        to=to,
    )
