"""Administration panel.

Authorisation is enforced by a blueprint-level ``before_request`` rather than a
decorator on each view. That inverts the failure mode: a newly-added view is
protected by default, and forgetting a decorator cannot open a hole. The
original had no authentication anywhere.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select

from itsc.extensions import db
from itsc.forms.content import DeleteForm, DocumentForm, NovedadForm
from itsc.models import ContactMessage, Document, DocumentCategory, Novedad
from itsc.models.contact import STATUS_READ
from itsc.models.novedad import STATUS_PUBLISHED
from itsc.services.media import UploadError, store_upload
from itsc.services.slugs import unique_slug

bp = Blueprint("admin", __name__, url_prefix="/admin")
log = structlog.get_logger("itsc.admin")


@bp.before_request
@login_required
def require_login():  # type: ignore[no-untyped-def]
    """Gate every route in this blueprint, including ones added later."""
    if not current_user.has_role("admin", "editor"):
        abort(403)
    return None


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@bp.get("/")
def dashboard():  # type: ignore[no-untyped-def]
    stats = {
        "novedades": db.session.scalar(select(func.count()).select_from(Novedad)),
        "publicadas": db.session.scalar(
            select(func.count()).select_from(Novedad).where(Novedad.status == STATUS_PUBLISHED)
        ),
        "documentos": db.session.scalar(select(func.count()).select_from(Document)),
        "mensajes_nuevos": db.session.scalar(
            select(func.count()).select_from(ContactMessage).where(ContactMessage.status == "new")
        ),
    }
    recientes = db.session.scalars(
        select(Novedad).order_by(Novedad.created_at.desc()).limit(5)
    ).all()
    return render_template("admin/dashboard.html", stats=stats, recientes=recientes)


# --------------------------------------------------------------------------
# Novedades
# --------------------------------------------------------------------------
@bp.get("/novedades")
def novedad_list():  # type: ignore[no-untyped-def]
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        select(Novedad).order_by(Novedad.created_at.desc()),
        page=max(page, 1),
        per_page=20,
        error_out=False,
    )
    return render_template(
        "admin/novedad_list.html", pagination=pagination, delete_form=DeleteForm()
    )


@bp.route("/novedades/nueva", methods=["GET", "POST"])
def novedad_new():  # type: ignore[no-untyped-def]
    form = NovedadForm()
    if form.validate_on_submit():
        novedad = Novedad(
            titulo=form.titulo.data,
            resumen=form.resumen.data,
            cuerpo=form.cuerpo.data,
            status=form.status.data,
            author_id=current_user.id,
            slug=unique_slug(
                form.titulo.data or "",
                lambda s: db.session.scalar(
                    select(func.count()).select_from(Novedad).where(Novedad.slug == s)
                )
                > 0,
            ),
        )
        if form.status.data == STATUS_PUBLISHED:
            novedad.published_at = datetime.now(UTC)

        if not _attach_image(novedad, form):
            return render_template("admin/novedad_form.html", form=form, novedad=None), 400

        db.session.add(novedad)
        db.session.commit()
        log.info("novedad_created", novedad_id=novedad.id, user_id=current_user.id)
        flash("Novedad creada.", "success")
        return redirect(url_for("admin.novedad_list"))

    if request.method == "POST":
        return render_template("admin/novedad_form.html", form=form, novedad=None), 400
    return render_template("admin/novedad_form.html", form=form, novedad=None)


@bp.route("/novedades/<int:novedad_id>/editar", methods=["GET", "POST"])
def novedad_edit(novedad_id: int):  # type: ignore[no-untyped-def]
    novedad = db.session.get(Novedad, novedad_id)
    if novedad is None:
        abort(404)

    form = NovedadForm(obj=novedad)
    if form.validate_on_submit():
        was_published = novedad.status == STATUS_PUBLISHED
        novedad.titulo = form.titulo.data
        novedad.resumen = form.resumen.data
        novedad.cuerpo = form.cuerpo.data
        novedad.status = form.status.data
        # The slug is frozen after first publish so inbound links keep working.
        if form.status.data == STATUS_PUBLISHED and not was_published:
            novedad.published_at = novedad.published_at or datetime.now(UTC)

        if not _attach_image(novedad, form):
            return render_template("admin/novedad_form.html", form=form, novedad=novedad), 400

        db.session.commit()
        log.info("novedad_updated", novedad_id=novedad.id, user_id=current_user.id)
        flash("Novedad actualizada.", "success")
        return redirect(url_for("admin.novedad_list"))

    if request.method == "POST":
        return render_template("admin/novedad_form.html", form=form, novedad=novedad), 400
    return render_template("admin/novedad_form.html", form=form, novedad=novedad)


@bp.post("/novedades/<int:novedad_id>/eliminar")
def novedad_delete(novedad_id: int):  # type: ignore[no-untyped-def]
    """POST only.

    A GET-triggered delete can be fired by any <img> tag, a link prefetcher, or
    a crawler walking the admin panel.
    """
    form = DeleteForm()
    if not form.validate_on_submit():
        abort(400)
    novedad = db.session.get(Novedad, novedad_id)
    if novedad is None:
        abort(404)
    db.session.delete(novedad)
    db.session.commit()
    log.info("novedad_deleted", novedad_id=novedad_id, user_id=current_user.id)
    flash("Novedad eliminada.", "success")
    return redirect(url_for("admin.novedad_list"))


def _attach_image(novedad: Novedad, form: NovedadForm) -> bool:
    upload = form.imagen.data
    if not upload or not getattr(upload, "filename", ""):
        return True
    try:
        asset = store_upload(
            upload,
            alt_text=form.imagen_alt.data or "",
            user_id=current_user.id,
            kind="image",
        )
    except UploadError as exc:
        form.imagen.errors.append(str(exc))
        return False
    novedad.imagen_id = asset.id
    return True


# --------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------
@bp.get("/documentos")
def document_list():  # type: ignore[no-untyped-def]
    categoria = request.args.get("categoria")
    stmt = select(Document).order_by(Document.fecha_documento.desc())
    if categoria:
        stmt = stmt.join(DocumentCategory).where(DocumentCategory.slug == categoria)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(stmt, page=max(page, 1), per_page=20, error_out=False)
    return render_template(
        "admin/document_list.html",
        pagination=pagination,
        categories=db.session.scalars(
            select(DocumentCategory).order_by(DocumentCategory.orden)
        ).all(),
        categoria=categoria,
        delete_form=DeleteForm(),
    )


@bp.route("/documentos/nuevo/<categoria>", methods=["GET", "POST"])
def document_new(categoria: str):  # type: ignore[no-untyped-def]
    category = db.session.scalars(
        select(DocumentCategory).where(DocumentCategory.slug == categoria)
    ).first()
    if category is None:
        abort(404)

    form = DocumentForm()
    if form.validate_on_submit():
        document = Document(
            category_id=category.id,
            titulo=form.titulo.data,
            numero=form.numero.data or None,
            descripcion=form.descripcion.data or "",
            fecha_documento=form.fecha_documento.data,
            vigente_desde=form.vigente_desde.data,
            vigente_hasta=form.vigente_hasta.data,
            status=form.status.data,
            author_id=current_user.id,
            slug=unique_slug(
                form.titulo.data or "",
                lambda s: db.session.scalar(
                    select(func.count())
                    .select_from(Document)
                    .where(Document.slug == s, Document.category_id == category.id)
                )
                > 0,
            ),
        )
        if form.status.data == STATUS_PUBLISHED:
            document.published_at = datetime.now(UTC)

        if not _attach_pdf(document, form):
            return render_template(
                "admin/document_form.html", form=form, category=category, document=None
            ), 400

        db.session.add(document)
        db.session.commit()
        log.info("document_created", document_id=document.id, user_id=current_user.id)
        flash("Documento creado.", "success")
        return redirect(url_for("admin.document_list", categoria=categoria))

    if request.method == "POST":
        return render_template(
            "admin/document_form.html", form=form, category=category, document=None
        ), 400
    return render_template(
        "admin/document_form.html", form=form, category=category, document=None
    )


@bp.post("/documentos/<int:document_id>/eliminar")
def document_delete(document_id: int):  # type: ignore[no-untyped-def]
    form = DeleteForm()
    if not form.validate_on_submit():
        abort(400)
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404)
    categoria = document.category.slug
    db.session.delete(document)
    db.session.commit()
    log.info("document_deleted", document_id=document_id, user_id=current_user.id)
    flash("Documento eliminado.", "success")
    return redirect(url_for("admin.document_list", categoria=categoria))


def _attach_pdf(document: Document, form: DocumentForm) -> bool:
    upload = form.archivo.data
    if not upload or not getattr(upload, "filename", ""):
        return True
    try:
        asset = store_upload(upload, user_id=current_user.id, kind="pdf")
    except UploadError as exc:
        form.archivo.errors.append(str(exc))
        return False

    from itsc.models import DocumentFile

    document.files.append(DocumentFile(media_asset_id=asset.id, label=upload.filename[:160]))
    return True


# --------------------------------------------------------------------------
# Contact inbox
# --------------------------------------------------------------------------
@bp.get("/mensajes")
def contacto_list():  # type: ignore[no-untyped-def]
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        select(ContactMessage).order_by(ContactMessage.created_at.desc()),
        page=max(page, 1),
        per_page=25,
        error_out=False,
    )
    return render_template("admin/contacto_list.html", pagination=pagination)


@bp.get("/mensajes/<int:message_id>")
def contacto_detail(message_id: int):  # type: ignore[no-untyped-def]
    message = db.session.get(ContactMessage, message_id)
    if message is None:
        abort(404)
    if message.status == "new":
        message.status = STATUS_READ
        message.handled_by_id = current_user.id
        message.handled_at = datetime.now(UTC)
        db.session.commit()
    return render_template(
        "admin/contacto_detail.html",
        message=message,
        retention_days=current_app.config["CONTACT_RETENTION_DAYS"],
    )
