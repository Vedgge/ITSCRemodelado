"""Public content pages.

Fourteen of these routes previously existed only as static HTML shells with a
copy-pasted nav, no <main>, no footer, and half of them still titled
"Document".
"""

from __future__ import annotations

from flask import Blueprint, abort, render_template, request

from itsc.content import CARRERAS, CARRERAS_BY_SLUG, FAQ, FOTOGALERIA, TESTIMONIOS_DEMO
from itsc.services import documents as doc_service
from itsc.services import novedades as novedad_service

bp = Blueprint("public", __name__)


@bp.get("/")
def index():  # type: ignore[no-untyped-def]
    return render_template(
        "pages/index.html",
        # Real news from the database. The homepage previously showed five
        # hardcoded lorem-ipsum cards; the code meant to fetch real ones was
        # commented out and targeted an element id that did not exist.
        novedades=novedad_service.latest(4),
        carreras=CARRERAS,
        fotogaleria=FOTOGALERIA,
        faq=FAQ[:7],
        testimonios=TESTIMONIOS_DEMO,
    )


@bp.get("/nosotros")
def nosotros():  # type: ignore[no-untyped-def]
    return render_template("pages/nosotros.html")


@bp.get("/carreras")
def carreras():  # type: ignore[no-untyped-def]
    return render_template("pages/carreras.html", carreras=CARRERAS)


@bp.get("/carreras/<slug>")
def carrera(slug: str):  # type: ignore[no-untyped-def]
    item = CARRERAS_BY_SLUG.get(slug)
    if item is None:
        abort(404)
    return render_template("pages/carrera.html", carrera=item)


@bp.get("/estudiantes")
def estudiantes():  # type: ignore[no-untyped-def]
    return render_template("pages/estudiantes.html")


@bp.get("/estudiantes/examenes")
def examenes():  # type: ignore[no-untyped-def]
    """Exam schedules, backed by the documents repository."""
    category = doc_service.get_category("mesas-de-examen")
    pagination = doc_service.list_documents(category, page=1, per_page=25) if category else None
    return render_template("pages/examenes.html", category=category, pagination=pagination)


@bp.get("/estudiantes/egresados")
def egresados():  # type: ignore[no-untyped-def]
    return render_template("pages/egresados.html")


@bp.get("/estudiantes/ser-tecnico")
def ser_tecnico():  # type: ignore[no-untyped-def]
    return render_template("pages/ser-tecnico.html")


@bp.get("/cooperadora")
def cooperadora():  # type: ignore[no-untyped-def]
    return render_template("pages/cooperadora.html")


@bp.get("/preguntas-frecuentes")
def faq():  # type: ignore[no-untyped-def]
    categorias: dict[str, list] = {}
    for item in FAQ:
        categorias.setdefault(item.categoria, []).append(item)
    return render_template("pages/faq.html", categorias=categorias)


@bp.get("/fotogaleria")
def fotogaleria():  # type: ignore[no-untyped-def]
    return render_template("pages/fotogaleria.html", fotos=FOTOGALERIA)


@bp.get("/buscar")
def buscar():  # type: ignore[no-untyped-def]
    """Site search.

    The header search box existed on all 21 pages with no action, no method and
    no name attribute -- submitting it reloaded the page. It now queries the
    Postgres full-text indexes, delivering the README's unbuilt checklist item
    ("Add a search engine").
    """
    query = (request.args.get("q") or "").strip()[:100]
    resultados_novedades = novedad_service.search(query) if query else []
    resultados_documentos = doc_service.search(query) if query else []
    return render_template(
        "pages/buscar.html",
        query=query,
        novedades=resultados_novedades,
        documentos=resultados_documentos,
        total=len(resultados_novedades) + len(resultados_documentos),
    )


@bp.get("/mapa-del-sitio")
def mapa_del_sitio():  # type: ignore[no-untyped-def]
    """The header linked "Mapa del sitio" to href="#" on every page."""
    return render_template("pages/mapa-del-sitio.html", categories=doc_service.all_categories())
