"""Document repositories: the four sections that were empty HTML shells."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from itsc.models import Document

CATEGORIES = [
    "convocatorias",
    "resoluciones",
    "actas-dictamenes",
    "materiales-para-descargar",
    "mesas-de-examen",
]


def _doc(db, category, slug, *, hasta=None, status="published", titulo=None):
    item = Document(
        category_id=category.id,
        slug=slug,
        titulo=titulo or slug.replace("-", " ").title(),
        descripcion="Descripción del documento.",
        fecha_documento=date.today(),
        vigente_hasta=hasta,
        status=status,
        published_at=datetime.now(UTC) if status == "published" else None,
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.mark.parametrize("slug", CATEGORIES)
def test_category_page_renders(client, categories, slug):
    assert client.get(f"/{slug}/").status_code == 200


@pytest.mark.parametrize("slug", CATEGORIES)
def test_empty_category_shows_an_honest_empty_state(client, categories, slug):
    html = client.get(f"/{slug}/").get_data(as_text=True)
    assert "Todavía no hay" in html
    assert "lista para recibir publicaciones" in html


def test_unknown_category_is_404(client, categories):
    assert client.get("/inventada/").status_code == 404


def test_vigencia_filter_is_derived_from_dates(client, db, categories):
    """The two hand-maintained convocatorias pages could disagree; this cannot."""
    convocatorias = next(c for c in categories if c.slug == "convocatorias")
    _doc(
        db,
        convocatorias,
        "abierta",
        hasta=date.today() + timedelta(days=10),
        titulo="Abierta Ahora",
    )
    _doc(db, convocatorias, "cerrada", hasta=date.today() - timedelta(days=10), titulo="Cerrada Ya")

    vigentes = client.get("/convocatorias/vigentes/").get_data(as_text=True)
    assert "Abierta Ahora" in vigentes and "Cerrada Ya" not in vigentes

    no_vigentes = client.get("/convocatorias/no-vigentes/").get_data(as_text=True)
    assert "Cerrada Ya" in no_vigentes and "Abierta Ahora" not in no_vigentes

    todas = client.get("/convocatorias/").get_data(as_text=True)
    assert "Abierta Ahora" in todas and "Cerrada Ya" in todas


def test_open_ended_document_is_vigente(db, categories):
    convocatorias = next(c for c in categories if c.slug == "convocatorias")
    doc = _doc(db, convocatorias, "sin-vencimiento", hasta=None)
    assert doc.vigente is True


def test_vigencia_filter_rejected_for_categories_without_it(client, categories):
    assert client.get("/resoluciones/vigentes/").status_code == 404


def test_drafts_are_hidden(client, db, categories):
    resoluciones = next(c for c in categories if c.slug == "resoluciones")
    _doc(db, resoluciones, "borrador", status="draft", titulo="Resolucion Borrador")
    html = client.get("/resoluciones/").get_data(as_text=True)
    assert "Resolucion Borrador" not in html


def test_document_detail(client, db, categories):
    resoluciones = next(c for c in categories if c.slug == "resoluciones")
    doc = _doc(db, resoluciones, "una-resolucion", titulo="Una Resolucion")
    html = client.get(f"/resoluciones/doc/{doc.slug}").get_data(as_text=True)
    assert "Una Resolucion" in html


def test_examenes_page_uses_the_document_repository(client, db, categories):
    mesas = next(c for c in categories if c.slug == "mesas-de-examen")
    _doc(
        db,
        mesas,
        "turno-de-prueba",
        hasta=date.today() + timedelta(days=5),
        titulo="Turno De Prueba",
    )
    html = client.get("/estudiantes/examenes").get_data(as_text=True)
    assert "Turno De Prueba" in html


def test_examenes_empty_state_does_not_invent_dates(client, categories):
    """This project has no access to the real exam calendar; a fabricated date
    would send a student on the wrong day."""
    html = client.get("/estudiantes/examenes").get_data(as_text=True)
    assert "No hay cronogramas publicados" in html
    assert "No publicamos fechas sin" in html
