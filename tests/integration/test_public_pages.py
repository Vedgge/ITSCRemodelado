"""Every public page renders.

Fourteen of these existed only as static shells with no <main>, no footer, and
half of them still titled "Document".
"""

from __future__ import annotations

import pytest

PAGES = [
    "/",
    "/nosotros",
    "/carreras",
    "/estudiantes",
    "/estudiantes/examenes",
    "/estudiantes/egresados",
    "/estudiantes/ser-tecnico",
    "/cooperadora",
    "/preguntas-frecuentes",
    "/fotogaleria",
    "/mapa-del-sitio",
    "/buscar",
    "/contacto/",
    "/contacto/gracias",
    "/ingresar",
]


@pytest.mark.parametrize("path", PAGES)
def test_page_renders(client, categories, path):
    response = client.get(path)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "<title>" in html
    assert "Document</title>" not in html, "placeholder title survived"
    assert 'lang="es"' in html, "wrong document language for a Spanish site"


@pytest.mark.parametrize("path", PAGES)
def test_page_has_real_content_not_just_chrome(client, categories, path):
    """The old stubs were header + nav + scripts and nothing else."""
    html = client.get(path).get_data(as_text=True)
    assert "<main" in html
    body = html.split("<main", 1)[1].split("</main>", 1)[0]
    assert len(body) > 400, f"{path} has essentially no content"
    assert "Lorem ipsum" not in html and "Lorem," not in html


@pytest.mark.parametrize("slug", ["enfermeria", "desarrollo-de-software", "protesis-dental"])
def test_career_pages_render(client, slug):
    assert client.get(f"/carreras/{slug}").status_code == 200


def test_unknown_career_is_404(client):
    assert client.get("/carreras/no-existe").status_code == 404


def test_every_nav_link_resolves(client, categories):
    """The original nav had nine dead href="#" entries pointing at pages that
    existed on disk, and its "Inicio" link 404'd from every stub page."""
    import re

    html = client.get("/").get_data(as_text=True)
    nav = html.split('id="nav-principal"', 1)[1].split("</nav>", 1)[0]
    hrefs = set(re.findall(r'href="([^"]+)"', nav))

    dead = [h for h in hrefs if h == "#"]
    assert not dead, "nav still contains dead '#' links"

    broken = []
    for href in hrefs:
        if href.startswith(("http", "mailto:", "tel:")):
            continue
        if client.get(href).status_code >= 400:
            broken.append(href)
    assert not broken, f"broken nav links: {broken}"


def test_footer_has_no_lorem_ipsum(client):
    html = client.get("/").get_data(as_text=True)
    footer = html.split("<footer", 1)[1]
    assert "Lorem" not in footer


def test_portfolio_disclaimer_is_visible(client):
    html = client.get("/").get_data(as_text=True)
    assert "no está afiliado" in html or "No afiliada" in html
    assert 'content="noindex' in html


def test_search_finds_a_published_novedad(client, novedad):
    response = client.get("/buscar", query_string={"q": "prueba"})
    assert response.status_code == 200
    assert novedad.titulo in response.get_data(as_text=True)


def test_search_with_no_results_is_graceful(client, novedad):
    html = client.get("/buscar", query_string={"q": "zzzzqqqxyz"}).get_data(as_text=True)
    assert "Sin resultados" in html


def test_robots_disallows_everything_while_a_portfolio_demo(client, app):
    """The site reproduces a real institution's branding; it must never
    compete with their official site in search results."""
    assert app.config["SITE_IS_PORTFOLIO_DEMO"] is True
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert "Disallow: /" in body
    assert "no afiliado" in body.lower()
    assert app.config["SITE_OFFICIAL_URL"] in body


def test_robots_allows_crawling_when_not_a_demo(client, app):
    app.config["SITE_IS_PORTFOLIO_DEMO"] = False
    try:
        body = client.get("/robots.txt").get_data(as_text=True)
        assert "Disallow: /admin/" in body
        assert "Disallow: /\n" not in body
        assert "Sitemap:" in body
    finally:
        app.config["SITE_IS_PORTFOLIO_DEMO"] = True


def test_noindex_meta_is_present_while_a_demo(client):
    assert 'content="noindex' in client.get("/").get_data(as_text=True)


def test_sitemap_lists_pages_and_published_news(client, novedad):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.mimetype == "application/xml"
    body = response.get_data(as_text=True)
    assert "<urlset" in body
    assert novedad.slug in body


def test_every_page_declares_a_viewport(client, categories):
    """The original claimed responsiveness while shipping one media query."""
    for path in ("/", "/carreras", "/contacto/", "/novedades/"):
        html = client.get(path).get_data(as_text=True)
        assert 'name="viewport"' in html


def test_pages_expose_a_skip_link_and_landmarks(client):
    """The nav is ~40 links deep and previously had no keyboard bypass."""
    html = client.get("/").get_data(as_text=True)
    assert 'class="skip-link"' in html
    assert 'href="#contenido"' in html
    assert '<main id="contenido"' in html
    assert "<header" in html and "<footer" in html


def test_images_declare_dimensions(client):
    """Explicit width/height reserve layout space; the original used
    background-image divs, which cannot and caused layout shift."""
    import re

    html = client.get("/").get_data(as_text=True)
    imgs = re.findall(r"<img\b[^>]*>", html)
    assert imgs
    missing = [i for i in imgs if "width=" not in i or "height=" not in i]
    assert not missing, f"{len(missing)} img tag(s) without dimensions"
