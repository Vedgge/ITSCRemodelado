"""Public content pages.

Fourteen of these routes previously existed only as static HTML shells with a
copy-pasted nav, no <main>, no footer, and half of them still titled
"Document".
"""

from __future__ import annotations

from flask import Blueprint, Response, abort, current_app, render_template, request, url_for

from itsc.content import CARRERAS, CARRERAS_BY_SLUG, FAQ, FOTOGALERIA, TESTIMONIOS_DEMO
from itsc.services import documents as doc_service
from itsc.services import novedades as novedad_service

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
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
def nosotros():
    return render_template("pages/nosotros.html")


@bp.get("/carreras")
def carreras():
    return render_template("pages/carreras.html", carreras=CARRERAS)


@bp.get("/carreras/<slug>")
def carrera(slug: str):
    item = CARRERAS_BY_SLUG.get(slug)
    if item is None:
        abort(404)
    return render_template("pages/carrera.html", carrera=item)


@bp.get("/estudiantes")
def estudiantes():
    return render_template("pages/estudiantes.html")


@bp.get("/estudiantes/examenes")
def examenes():
    """Exam schedules, backed by the documents repository."""
    category = doc_service.get_category("mesas-de-examen")
    pagination = doc_service.list_documents(category, page=1, per_page=25) if category else None
    return render_template("pages/examenes.html", category=category, pagination=pagination)


@bp.get("/estudiantes/egresados")
def egresados():
    return render_template("pages/egresados.html")


@bp.get("/estudiantes/ser-tecnico")
def ser_tecnico():
    return render_template("pages/ser-tecnico.html")


@bp.get("/cooperadora")
def cooperadora():
    return render_template("pages/cooperadora.html")


@bp.get("/preguntas-frecuentes")
def faq():
    categorias: dict[str, list] = {}
    for item in FAQ:
        categorias.setdefault(item.categoria, []).append(item)
    return render_template("pages/faq.html", categorias=categorias)


@bp.get("/fotogaleria")
def fotogaleria():
    return render_template("pages/fotogaleria.html", fotos=FOTOGALERIA)


@bp.get("/buscar")
def buscar():
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


@bp.get("/robots.txt")
def robots():
    """Crawler policy.

    While SITE_IS_PORTFOLIO_DEMO is set this disallows everything: the site
    reproduces a real institution's name and branding, and must never compete
    with — or be mistaken for — their official site in search results.
    """
    if current_app.config["SITE_IS_PORTFOLIO_DEMO"]:
        body = (
            "# Proyecto de portafolio, no afiliado al ITSC.\n"
            f"# Sitio oficial: {current_app.config['SITE_OFFICIAL_URL']}\n"
            "User-agent: *\nDisallow: /\n"
        )
    else:
        body = (
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Disallow: /ingresar\n"
            "Disallow: /media/\n"
            f"Sitemap: {url_for('public.sitemap', _external=True)}\n"
        )
    return Response(body, mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    """XML sitemap. Only meaningful once the site is indexable."""
    urls = [
        url_for(endpoint, _external=True)
        for endpoint in (
            "public.index",
            "public.nosotros",
            "public.carreras",
            "public.estudiantes",
            "public.faq",
            "public.fotogaleria",
            "public.cooperadora",
            "public.ser_tecnico",
            "public.egresados",
            "public.examenes",
            "novedades.list",
            "contacto.form",
        )
    ]
    urls += [url_for("public.carrera", slug=c.slug, _external=True) for c in CARRERAS]
    urls += [
        url_for("novedades.detail", slug=n.slug, _external=True)
        for n in novedad_service.latest(200)
    ]
    return Response(render_template("sitemap.xml", urls=urls), mimetype="application/xml")


@bp.get("/mapa-del-sitio")
def mapa_del_sitio():
    """The header linked "Mapa del sitio" to href="#" on every page."""
    return render_template("pages/mapa-del-sitio.html", categories=doc_service.all_categories())
