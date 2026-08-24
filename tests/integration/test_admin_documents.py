"""Admin document management and upload failure paths."""

from __future__ import annotations

import io
from datetime import date

import pytest

from itsc.models import Document, MediaAsset


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def test_document_list_filters_by_category(admin_client, db, categories, token):
    resoluciones = next(c for c in categories if c.slug == "resoluciones")
    convocatorias = next(c for c in categories if c.slug == "convocatorias")
    for cat, titulo in ((resoluciones, "Doc Resolucion"), (convocatorias, "Doc Convocatoria")):
        db.session.add(
            Document(
                category_id=cat.id,
                slug=titulo.lower().replace(" ", "-"),
                titulo=titulo,
                fecha_documento=date.today(),
                status="published",
                published_at=date.today(),
            )
        )
    db.session.commit()

    html = admin_client.get("/admin/documentos?categoria=resoluciones").get_data(as_text=True)
    assert "Doc Resolucion" in html
    assert "Doc Convocatoria" not in html

    todos = admin_client.get("/admin/documentos").get_data(as_text=True)
    assert "Doc Resolucion" in todos and "Doc Convocatoria" in todos


def test_new_document_for_unknown_category_is_404(admin_client, categories):
    assert admin_client.get("/admin/documentos/nuevo/inventada").status_code == 404


def test_document_with_pdf_attachment(admin_client, db, categories, token):
    response = admin_client.post(
        "/admin/documentos/nuevo/resoluciones",
        data={
            "csrf_token": token(admin_client, "/admin/documentos/nuevo/resoluciones"),
            "titulo": "Resolución con archivo",
            "fecha_documento": date.today().isoformat(),
            "status": "published",
            "archivo": (io.BytesIO(_pdf_bytes()), "resolucion.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    doc = db.session.query(Document).filter_by(titulo="Resolución con archivo").one()
    assert len(doc.files) == 1
    assert doc.files[0].media.mime_type == "application/pdf"


def test_document_rejects_a_non_pdf_attachment(admin_client, db, categories, token, html_file):
    response = admin_client.post(
        "/admin/documentos/nuevo/resoluciones",
        data={
            "csrf_token": token(admin_client, "/admin/documentos/nuevo/resoluciones"),
            "titulo": "Resolución con archivo falso",
            "fecha_documento": date.today().isoformat(),
            "status": "draft",
            "archivo": (io.BytesIO(html_file), "falso.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert db.session.query(Document).count() == 0


def test_delete_document(admin_client, db, categories, token):
    resoluciones = next(c for c in categories if c.slug == "resoluciones")
    doc = Document(
        category_id=resoluciones.id,
        slug="a-borrar",
        titulo="A Borrar",
        fecha_documento=date.today(),
        status="draft",
    )
    db.session.add(doc)
    db.session.commit()
    doc_id = doc.id

    admin_client.post(
        f"/admin/documentos/{doc_id}/eliminar",
        data={"csrf_token": token(admin_client, "/admin/documentos")},
        follow_redirects=True,
    )
    assert db.session.get(Document, doc_id) is None


def test_delete_missing_document_is_404(admin_client, categories, token):
    response = admin_client.post(
        "/admin/documentos/999999/eliminar",
        data={"csrf_token": token(admin_client, "/admin/documentos")},
    )
    assert response.status_code == 404


def test_delete_missing_novedad_is_404(admin_client, token):
    response = admin_client.post(
        "/admin/novedades/999999/eliminar",
        data={"csrf_token": token(admin_client, "/admin/novedades")},
    )
    assert response.status_code == 404


def test_edit_missing_novedad_is_404(admin_client):
    assert admin_client.get("/admin/novedades/999999/editar").status_code == 404


def test_missing_message_is_404(admin_client):
    assert admin_client.get("/admin/mensajes/999999").status_code == 404


def test_novedad_upload_error_is_shown_on_the_form(admin_client, db, token, html_file):
    """A rejected image must re-render the form with the reason, not 500."""
    response = admin_client.post(
        "/admin/novedades/nueva",
        data={
            "csrf_token": token(admin_client, "/admin/novedades/nueva"),
            "titulo": "Con imagen mala",
            "resumen": "r" * 20,
            "cuerpo": "c",
            "status": "draft",
            "imagen_alt": "",
            "imagen": (io.BytesIO(html_file), "malicioso.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "imagen válida" in html or "Formato no permitido" in html
    from itsc.models import Novedad

    assert db.session.query(Novedad).count() == 0


def test_editing_an_image_replaces_it(admin_client, db, token, novedad, real_jpeg):
    admin_client.post(
        f"/admin/novedades/{novedad.id}/editar",
        data={
            "csrf_token": token(admin_client, f"/admin/novedades/{novedad.id}/editar"),
            "titulo": novedad.titulo,
            "resumen": novedad.resumen,
            "cuerpo": novedad.cuerpo,
            "status": "published",
            "imagen_alt": "nueva alt",
            "imagen": (io.BytesIO(real_jpeg), "nueva.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    db.session.refresh(novedad)
    assert novedad.imagen is not None
    assert db.session.query(MediaAsset).count() == 1


def test_media_route_rejects_an_unknown_id(client):
    assert client.get("/media/00000000-0000-0000-0000-000000000000").status_code == 404


def test_media_route_404s_when_the_file_is_missing_on_disk(client, db, app, real_jpeg):
    """A DB row without its file must 404, not raise."""
    from pathlib import Path

    from werkzeug.datastructures import FileStorage

    from itsc.services.media import process_image

    with app.test_request_context():
        stored = process_image(FileStorage(stream=io.BytesIO(real_jpeg), filename="x.jpg"))
    asset = MediaAsset(
        original_filename="x.jpg",
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
        checksum_sha256=stored.checksum,
        alt_text="",
    )
    db.session.add(asset)
    db.session.commit()

    (Path(app.config["UPLOAD_ROOT"]) / stored.storage_key).unlink()
    assert client.get(f"/media/{asset.public_id}").status_code == 404


@pytest.mark.parametrize(
    "page", ["/admin/novedades?page=2", "/admin/documentos?page=2", "/admin/mensajes?page=2"]
)
def test_admin_pagination_beyond_the_end_is_graceful(admin_client, categories, page):
    assert admin_client.get(page).status_code == 200
