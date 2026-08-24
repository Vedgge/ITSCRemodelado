"""Contact form: accept, validate server-side, persist, notify."""

from __future__ import annotations

import structlog
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from itsc.extensions import db, limiter
from itsc.forms.contact import ContactForm
from itsc.models import ContactMessage
from itsc.models.contact import hash_ip

bp = Blueprint("contacto", __name__, url_prefix="/contacto")
log = structlog.get_logger("itsc.contacto")


@bp.route("/", methods=["GET", "POST"], endpoint="form")
@limiter.limit("3 per hour", methods=["POST"])
def contact_form():  # type: ignore[no-untyped-def]
    form = ContactForm()

    if form.validate_on_submit():
        if form.is_bot():
            # Accept silently: telling a bot it failed just teaches it.
            log.info("contact_honeypot_triggered")
            return redirect(url_for("contacto.gracias"))

        message = ContactMessage(
            asunto=form.asunto.data,
            nombre=form.nombre.data,
            email=form.email.data,
            telefono=form.telefono.data or None,
            motivo=form.motivo.data,
            mensaje=form.mensaje.data,
            # Keyed hash, not the address itself.
            ip_hash=hash_ip(request.remote_addr, current_app.config["IP_HASH_PEPPER"]),
            user_agent=(request.user_agent.string or "")[:300] or None,
        )
        db.session.add(message)
        db.session.commit()
        log.info("contact_received", message_id=message.id, motivo=message.motivo)

        # Best-effort only: the database row is the source of truth, so a mail
        # outage can never silently drop somebody's enquiry.
        from itsc.services.mail import notify_new_contact

        notify_new_contact(message)

        # POST/Redirect/GET, so a refresh cannot resubmit.
        return redirect(url_for("contacto.gracias"))

    if request.method == "POST":
        flash("Revisá los campos marcados e intentá de nuevo.", "error")
        # 400, not 200: the client sent invalid data. Re-rendering with a 200
        # makes "was this accepted?" unanswerable to anything but a human.
        return render_template("contacto/form.html", form=form), 400
    return render_template("contacto/form.html", form=form)


@bp.get("/gracias")
def gracias():  # type: ignore[no-untyped-def]
    """Confirmation page.

    Deliberately echoes NOTHING from the query string. Its predecessor,
    mostrar-datos-contacto.html, interpolated six URL parameters straight into
    innerHTML — a reflected XSS on the app's own origin.
    """
    return render_template("contacto/gracias.html")
