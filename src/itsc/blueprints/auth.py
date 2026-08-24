"""Login and logout.

The original application had no authentication of any kind: POST, PUT and
DELETE on /novedades were reachable by anyone on the internet, and CORS(app)
meant any website could invoke them from a visitor's browser.
"""

from __future__ import annotations

from urllib.parse import urlparse

import structlog
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from itsc.extensions import db, limiter
from itsc.forms.auth import LoginForm
from itsc.models.user import User, dummy_verify

bp = Blueprint("auth", __name__)
log = structlog.get_logger("itsc.auth")

#: One message for every failure mode. Distinguishing "no such user" from
#: "wrong password" turns the login form into a username oracle.
GENERIC_FAILURE = "Usuario o contraseña incorrectos."


def _safe_next(target: str | None) -> str:
    """Return *target* only if it is a local path.

    Without this check, ``/ingresar?next=https://evil.example`` turns the login
    form into an open redirect, which is a phishing primitive.
    """
    if not target:
        return url_for("admin.dashboard")
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return url_for("admin.dashboard")
    return target


@bp.route("/ingresar", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def login():  # type: ignore[no-untyped-def]
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data or ""
        user = db.session.query(User).filter(User.username == username).first()

        if user is None:
            # Burn an equivalent hash verification so the "unknown user" path
            # takes the same time as the "wrong password" path.
            dummy_verify()
            log.warning("login_failed", reason="unknown_user")
            flash(GENERIC_FAILURE, "error")
            return render_template("auth/login.html", form=form), 401

        if user.is_locked:
            log.warning("login_blocked", reason="locked", user_id=user.id)
            flash(
                "La cuenta está bloqueada temporalmente por intentos fallidos. "
                "Probá de nuevo en unos minutos.",
                "error",
            )
            return render_template("auth/login.html", form=form), 429

        if not user.check_password(form.password.data or ""):
            user.register_failed_login()
            db.session.commit()
            log.warning("login_failed", reason="bad_password", user_id=user.id)
            flash(GENERIC_FAILURE, "error")
            return render_template("auth/login.html", form=form), 401

        if not user.is_active_flag:
            log.warning("login_blocked", reason="inactive", user_id=user.id)
            flash(GENERIC_FAILURE, "error")
            return render_template("auth/login.html", form=form), 401

        # Session-fixation defence: issue a brand-new session ID before the
        # session becomes authenticated, so an ID an attacker planted earlier
        # is worthless.
        #
        # Deliberately NOT session.clear(): with a server-side store, clearing
        # puts the session object into a discard state where every subsequent
        # write in the request is dropped -- including Flask-WTF's CSRF seed,
        # which then makes the next POST fail with "CSRF session token is
        # missing". regenerate() rotates the storage key, which is the actual
        # protection; an anonymous session holds nothing worth wiping.
        regenerate = getattr(current_app.session_interface, "regenerate", None)
        if callable(regenerate):
            regenerate(session)
        login_user(user, remember=bool(form.remember.data))
        user.register_successful_login(ip=request.remote_addr)
        db.session.commit()
        log.info("login_ok", user_id=user.id, role=user.role)

        return redirect(_safe_next(request.args.get("next")))

    if request.method == "POST":
        return render_template("auth/login.html", form=form), 400
    return render_template("auth/login.html", form=form)


@bp.post("/salir")
@login_required
def logout():  # type: ignore[no-untyped-def]
    """POST-only: a GET logout can be triggered by any <img> tag on any site."""
    log.info("logout", user_id=current_user.id)
    logout_user()
    session.clear()
    flash("Cerraste sesión.", "success")
    return redirect(url_for("public.index"))
