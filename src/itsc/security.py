"""Security policy: headers, CSP, and authorisation decorators."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import Flask, abort, current_app
from flask_login import current_user

#: A strict policy with NO 'unsafe-inline'.
#:
#: This is only achievable because every inline <script> and style="" attribute
#: was moved out of the templates first, and because jQuery, Bootstrap, the
#: Font Awesome kit and Google Fonts were all replaced with self-hosted assets.
#: Reaching for a nonce instead would have been a permanent tax that quietly
#: keeps inline habits alive.
CSP = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self'",
    "img-src": "'self' data:",
    "font-src": "'self'",
    "connect-src": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
    "base-uri": "'none'",
    "object-src": "'none'",
    "frame-src": "'none'",
}

PERMISSIONS_POLICY = (
    "geolocation=(), camera=(), microphone=(), payment=(), usb=(), magnetometer=()"
)


def init_security(app: Flask) -> None:
    """Attach Talisman.

    nginx deliberately does NOT also set CSP: two CSP headers intersect, and
    debugging the result looks like a caching bug. Talisman owns app routes;
    nginx only adds headers for /static and /media, which never reach Flask.
    """
    from flask_talisman import Talisman

    force_https = bool(app.config.get("TALISMAN_FORCE_HTTPS", not app.debug))

    # Registered BEFORE Talisman: Flask runs after_request handlers in
    # reverse registration order, so this one runs last and gets the final
    # say on headers Talisman also sets.
    @app.after_request
    def _extra_headers(response):  # type: ignore[no-untyped-def]
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Assign, do not setdefault: Talisman writes its own minimal
        # Permissions-Policy first, and setdefault would silently keep it.
        existing = response.headers.get("Permissions-Policy", "")
        merged = PERMISSIONS_POLICY
        if "browsing-topics" in existing:
            merged += ", browsing-topics=()"
        response.headers["Permissions-Policy"] = merged
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        # The original set `Access-Control-Allow-Origin: *` on every route via
        # CORS(app), letting any site call the unauthenticated admin endpoints.
        response.headers.pop("Access-Control-Allow-Origin", None)
        return response

    Talisman(
        app,
        force_https=force_https,
        force_https_permanent=force_https,
        strict_transport_security=force_https,
        strict_transport_security_max_age=31_536_000,
        strict_transport_security_include_subdomains=True,
        # HSTS preload is deliberately NOT enabled: it is effectively
        # irreversible, so it should only be turned on after a stable month.
        strict_transport_security_preload=False,
        content_security_policy=CSP,
        content_security_policy_nonce_in=None,
        referrer_policy="strict-origin-when-cross-origin",
        frame_options="DENY",
        session_cookie_secure=bool(app.config.get("SESSION_COOKIE_SECURE")),
        session_cookie_http_only=True,
    )


def role_required(*roles: str) -> Callable:
    """Require an authenticated user holding one of *roles*."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                from flask_login import login_manager  # noqa: PLC0415

                return current_app.login_manager.unauthorized()
            if roles and not current_user.has_role(*roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


admin_required = role_required("admin")
editor_required = role_required("admin", "editor")
