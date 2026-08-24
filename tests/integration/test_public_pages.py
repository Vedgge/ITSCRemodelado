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
