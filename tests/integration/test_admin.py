"""Admin CRUD."""

from __future__ import annotations

import io
from datetime import date

from itsc.models import Document, Novedad


def test_dashboard_shows_counts(admin_client, novedad):
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "Novedades" in html and "Mensajes sin leer" in html


def test_create_novedad(admin_client, db, token):
    response = admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Una novedad nueva",
            "resumen": "Un resumen suficientemente largo para pasar.",
            "cuerpo": "El cuerpo de la novedad.",
            "status": "published",
            "imagen_alt": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    item = db.session.query(Novedad).filter_by(titulo="Una novedad nueva").one()
    assert item.slug == "una-novedad-nueva"
    assert item.published_at is not None, "published rows must carry a date (CHECK constraint)"


def test_create_with_image(admin_client, db, token, real_jpeg):
    admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Con una imagen",
            "resumen": "Un resumen suficientemente largo para pasar.",
            "cuerpo": "Cuerpo.",
            "status": "published",
            "imagen_alt": "Una descripción accesible",
            "imagen": (io.BytesIO(real_jpeg), "foto.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    item = db.session.query(Novedad).filter_by(titulo="Con una imagen").one()
    assert item.imagen is not None
    assert item.imagen.mime_type == "image/webp"
    assert item.imagen.alt_text == "Una descripción accesible"


def test_uploaded_image_is_servable(admin_client, db, token, real_jpeg):
    admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Servible",
            "resumen": "r" * 20,
            "cuerpo": "c",
            "status": "published",
            "imagen_alt": "alt",
            "imagen": (io.BytesIO(real_jpeg), "foto.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    item = db.session.query(Novedad).filter_by(titulo="Servible").one()
    response = admin_client.get(f"/media/{item.imagen.public_id}")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "sandbox" in response.headers.get("Content-Security-Policy", "")


def test_edit_novedad(admin_client, db, token, novedad):
    original_slug = novedad.slug
    admin_client.post(
        f"/admin/novedades/{novedad.id}/editar",
        data={
            "csrf_token": token(admin_client, f"/admin/novedades/{novedad.id}/editar"),
            "titulo": "Título cambiado",
            "resumen": novedad.resumen,
            "cuerpo": novedad.cuerpo,
            "status": "published",
            "imagen_alt": "",
        },
        follow_redirects=True,
    )
    db.session.refresh(novedad)
    assert novedad.titulo == "Título cambiado"
    # The slug is frozen after first publish so inbound links keep working.
    assert novedad.slug == original_slug


def test_invalid_novedad_is_rejected(admin_client, db, token):
    response = admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "x",
            "resumen": "corto",
            "cuerpo": "",
            "status": "draft",
        },
    )
    assert response.status_code == 400
    assert db.session.query(Novedad).count() == 0


def test_create_document(admin_client, db, token, categories):
    response = admin_client.post(
        "/admin/documentos/nuevo/resoluciones",
        data={
            "csrf_token": token(admin_client, "/admin/documentos/nuevo/resoluciones"),
            "titulo": "Resolución de prueba",
            "numero": "123/2026",
            "descripcion": "Una descripción.",
            "fecha_documento": date.today().isoformat(),
            "status": "published",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert db.session.query(Document).filter_by(numero="123/2026").count() == 1


def test_document_vigencia_dates_must_be_ordered(admin_client, db, token, categories):
    response = admin_client.post(
        "/admin/documentos/nuevo/convocatorias",
        data={
            "csrf_token": token(admin_client, "/admin/documentos/nuevo/convocatorias"),
            "titulo": "Convocatoria mal fechada",
            "fecha_documento": date.today().isoformat(),
            "vigente_desde": "2026-06-01",
            "vigente_hasta": "2026-01-01",
            "status": "draft",
        },
    )
    assert response.status_code == 400
    assert db.session.query(Document).count() == 0


def test_delete_novedad(admin_client, db, token, novedad):
    novedad_id = novedad.id
    admin_client.post(
        f"/admin/novedades/{novedad_id}/eliminar",
        data={"csrf_token": token(admin_client, "/admin/novedades")},
        follow_redirects=True,
    )
    assert db.session.get(Novedad, novedad_id) is None


def test_editor_can_reach_the_panel(editor_client):
    assert editor_client.get("/admin/").status_code == 200
