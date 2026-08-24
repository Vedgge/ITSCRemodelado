"""Error handlers.

Two rules: never render a traceback (the original ran ``debug=True``, exposing
the Werkzeug console), and never let an error page 500 on its own.
"""

from __future__ import annotations

import structlog
from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

log = structlog.get_logger("itsc.errors")

#: Spanish, user-facing. Deliberately vague about *why* something is forbidden.
MESSAGES = {
    400: ("Solicitud inválida", "No pudimos procesar los datos enviados."),
    403: ("Acceso denegado", "No tenés permisos para ver esta página."),
    404: ("Página no encontrada", "La página que buscás no existe o fue movida."),
    405: ("Método no permitido", "Esa acción no está disponible en esta dirección."),
    413: ("Archivo demasiado grande", "El archivo supera el tamaño máximo permitido."),
    429: ("Demasiadas solicitudes", "Esperá unos minutos antes de volver a intentar."),
    500: ("Error interno", "Algo salió mal de nuestro lado. Ya fue registrado."),
}


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    return request.accept_mimetypes.best == "application/json"


def _render(code: int, description: str | None = None):  # type: ignore[no-untyped-def]
    title, message = MESSAGES.get(code, MESSAGES[500])
    request_id = getattr(g, "request_id", None)

    if _wants_json():
        # RFC 7807 problem details.
        body = {
            "type": "about:blank",
            "title": title,
            "status": code,
            "detail": description or message,
        }
        if request_id:
            body["request_id"] = request_id
        response = jsonify(body)
        response.status_code = code
        response.mimetype = "application/problem+json"
        return response

    try:
        html = render_template(
            "errors/error.html",
            code=code,
            title=title,
            message=message,
            request_id=request_id,
        )
    except Exception:
        html = (
            f"<!doctype html><meta charset='utf-8'><title>{code} {title}</title>"
            f"<h1>{code} — {title}</h1><p>{message}</p>"
            + (f"<p>Referencia: {request_id}</p>" if request_id else "")
        )
    return html, code


def register_error_handlers(app: Flask) -> None:
    for code in (400, 403, 404, 405, 413, 429):

        @app.errorhandler(code)
        def _handler(exc, _code=code):  # type: ignore[no-untyped-def]
            description = getattr(exc, "description", None)
            log.info("http_error", status=_code, detail=description)
            return _render(_code, description)

    @app.errorhandler(HTTPException)
    def _http_exception(exc: HTTPException):  # type: ignore[no-untyped-def]
        log.info("http_error", status=exc.code, detail=exc.description)
        return _render(exc.code or 500, exc.description)

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception):  # type: ignore[no-untyped-def]
        # Every step here is defensive. An exception raised *inside* the error
        # handler escapes to the WSGI server as a bare traceback -- exactly the
        # leak this handler exists to prevent.
        try:
            log.error("unhandled_exception", error=str(exc), exc_info=True)
        except Exception:
            app.logger.exception("unhandled exception (structlog unavailable)")
        try:
            from itsc.extensions import db

            db.session.rollback()
        except Exception:  # noqa: S110
            pass
        return _render(500)
