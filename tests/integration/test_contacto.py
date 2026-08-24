"""Contact form end to end.

Previously: method=GET to a static HTML file, so submissions put personal data
in the URL and reached no server. There was no table, no validation, no email.
"""

from __future__ import annotations

import pytest

from itsc.models import ContactMessage

VALID = {
    "asunto": "Consulta sobre inscripción",
    "nombre": "Persona Consultante",
    "email": "persona@example.org",
    "telefono": "+543514337074",
    "motivo": "Inscripción",
    "mensaje": "Quisiera saber cuándo abren las inscripciones para el año que viene.",
}


def _post(client, token, **overrides):
    data = {**VALID, **overrides, "csrf_token": token(client, "/contacto/")}
    return client.post("/contacto/", data=data)


def test_valid_submission_is_persisted(client, db, token):
    response = _post(client, token)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/contacto/gracias")

    message = db.session.query(ContactMessage).one()
    assert message.email == VALID["email"]
    assert message.status == "new"


def test_form_uses_post_not_get(client):
    html = client.get("/contacto/").get_data(as_text=True)
    # Target the contact form specifically: the first <form> on every page is
    # the header search box, which is legitimately a GET.
    marker = 'action="/contacto/"'
    assert marker in html
    form = html[: html.index(marker)].rsplit("<form", 1)[1] + marker
    assert 'method="post"' in form.lower()


def test_ip_is_stored_as_a_keyed_hash_not_an_address(client, db, token):
    _post(client, token)
    message = db.session.query(ContactMessage).one()
    assert message.ip_hash is not None
    assert len(message.ip_hash) == 64
    assert "127.0.0.1" not in message.ip_hash


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "no-es-un-email"),
        ("nombre", ""),
        ("mensaje", "corto"),
        ("asunto", ""),
        ("telefono", "no-es-un-telefono"),
        ("motivo", "Motivo Inventado"),
    ],
)
def test_server_side_validation_rejects_bad_input(client, db, token, field, value):
    """The original validated only in JavaScript, i.e. advisory only."""
    response = _post(client, token, **{field: value})
    assert response.status_code == 400
    assert db.session.query(ContactMessage).count() == 0


def test_honeypot_is_accepted_silently_but_not_stored(client, db, token):
    response = _post(client, token, website="http://spam.example")
    assert response.status_code == 302
    assert db.session.query(ContactMessage).count() == 0


def test_gracias_page_does_not_claim_a_false_success(client):
    """The old page said "Datos enviados correctamente" while sending nothing."""
    html = client.get("/contacto/gracias").get_data(as_text=True)
    assert "Recibimos tu consulta" in html


def test_message_appears_in_the_admin_inbox(admin_client, db, token):
    _post(admin_client, token)
    html = admin_client.get("/admin/mensajes").get_data(as_text=True)
    assert VALID["asunto"] in html


def test_reading_a_message_marks_it_read(admin_client, db, token):
    _post(admin_client, token)
    message = db.session.query(ContactMessage).one()
    assert message.status == "new"
    admin_client.get(f"/admin/mensajes/{message.id}")
    db.session.refresh(message)
    assert message.status == "read"


def test_mail_failure_does_not_lose_the_message(client, db, token, monkeypatch):
    """The DB row is the source of truth; email is best-effort."""
    import itsc.services.mail as mail

    monkeypatch.setattr(mail, "send", lambda *a, **k: (_ for _ in ()).throw(OSError("smtp down")))
    try:
        _post(client, token)
    except OSError:
        pytest.fail("an SMTP failure escaped and lost the enquiry")
    assert db.session.query(ContactMessage).count() == 1
