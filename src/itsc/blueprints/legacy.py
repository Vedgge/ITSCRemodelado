"""301 redirects from the old ``/static/*.html`` URLs.

Registered as explicit rules rather than a catch-all, so an unmapped old path
correctly 404s instead of silently redirecting everything to the homepage.
"""

from __future__ import annotations

from flask import Blueprint, redirect, url_for

bp = Blueprint("legacy", __name__)

#: old filename -> (endpoint, kwargs)
REDIRECTS: dict[str, tuple[str, dict[str, str]]] = {
    "index.html": ("public.index", {}),
    "nosotros.html": ("public.nosotros", {}),
    "carreras.html": ("public.carreras", {}),
    "contacto.html": ("contacto.form", {}),
    "FAQ.html": ("public.faq", {}),
    "fotogaleria.html": ("public.fotogaleria", {}),
    "estudiantes.html": ("public.estudiantes", {}),
    "examenes.html": ("public.examenes", {}),
    "egresados.html": ("public.egresados", {}),
    "ser-tecnico.html": ("public.ser_tecnico", {}),
    "cooperadora.html": ("public.cooperadora", {}),
    "novedades.html": ("novedades.list", {}),
    "admin-novedades.html": ("admin.novedad_list", {}),
    "agregar-novedad.html": ("admin.novedad_new", {}),
    "convocatorias.html": ("documentos.list", {"categoria": "convocatorias"}),
    "convocatorias-vigentes.html": (
        "documentos.list",
        {"categoria": "convocatorias", "vigencia": "vigentes"},
    ),
    "convocatorias-novigentes.html": (
        "documentos.list",
        {"categoria": "convocatorias", "vigencia": "no-vigentes"},
    ),
    "resoluciones.html": ("documentos.list", {"categoria": "resoluciones"}),
    "actas-dictamenes.html": ("documentos.list", {"categoria": "actas-dictamenes"}),
    "materiales-para-descargar.html": (
        "documentos.list",
        {"categoria": "materiales-para-descargar"},
    ),
    # Its predecessor reflected six query parameters into innerHTML.
    "mostrar-datos-contacto.html": ("contacto.gracias", {}),
}


def register(app) -> None:
    for filename, (endpoint, kwargs) in REDIRECTS.items():

        def _view(_endpoint=endpoint, _kwargs=kwargs):
            return redirect(url_for(_endpoint, **_kwargs), code=301)

        app.add_url_rule(
            f"/static/{filename}",
            endpoint=f"legacy_{filename.replace('.', '_').replace('-', '_')}",
            view_func=_view,
            methods=["GET"],
        )
